from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
import plotly.graph_objs as go

def _pixel_cols(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if str(c).startswith("Pixel_")]

def get_normalized_lsf(df: pd.DataFrame, wavelength: str, sat_thresh: float = 65535.0, use_latest=True) -> Optional[np.ndarray]:
    pixel_cols = _pixel_cols(df)
    if not pixel_cols: return None

    sig_rows = df[df["Wavelength"] == wavelength]
    dark_rows = df[df["Wavelength"] == f"{wavelength}_dark"]
    if sig_rows.empty or dark_rows.empty: return None

    sig_row = sig_rows.iloc[-1] if use_latest else sig_rows.iloc[0]
    dark_row = dark_rows.iloc[-1] if use_latest else dark_rows.iloc[0]

    sig = sig_row[pixel_cols].astype(float).to_numpy()
    dark = dark_row[pixel_cols].astype(float).to_numpy()
    if sig.shape != dark.shape or sig.size == 0: return None
    if np.any(sig >= sat_thresh): return None

    corrected = sig - dark
    corrected -= np.min(corrected)
    denom = float(np.max(corrected))
    if not np.isfinite(denom) or denom <= 0: return None
    return corrected / denom

def _peak_pixel(y: np.ndarray) -> int:
    return int(np.argmax(y))

def build_lsf_map(df: pd.DataFrame, wavelengths: List[str], sat_thresh: float = 65535.0) -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    for w in wavelengths:
        lsf = get_normalized_lsf(df, w, sat_thresh=sat_thresh)
        if lsf is not None:
            out[w] = lsf
    return out

def build_sdf(lsf_map: Dict[str, np.ndarray]) -> Tuple[np.ndarray, List[str]]:
    if not lsf_map: return np.empty((0,)), []
    keys = sorted(lsf_map.keys(), key=lambda k: float(k.replace("_dark","")))
    arr = np.stack([lsf_map[k] for k in keys], axis=0)
    return arr, keys

def fit_dispersion(peak_pixels: List[int], wavelengths_nm: List[float], order: int = 3) -> np.ndarray:
    x = np.array(peak_pixels, dtype=float)
    y = np.array(wavelengths_nm, dtype=float)
    a = np.polyfit(x, y, deg=order)
    return a  # np.polyval(a, x) for fitted

def compute_fwhm(y: np.ndarray) -> float:
    if y.size == 0: return float("nan")
    y0 = y - np.min(y)
    m = np.max(y0)
    if m <= 0: return float("nan")
    y0 = y0 / m
    half = 0.5
    try:
        i_left = np.where(y0 >= half)[0][0]
        i_right = np.where(y0 >= half)[0][-1]
    except IndexError:
        return float("nan")

    def interp_x(i1, i2, v1, v2, target):
        if v2 == v1: return float(i1)
        return i1 + (target - v1) * (i2 - i1) / (v2 - v1)

    xL = interp_x(i_left-1, i_left, y0[i_left-1] if i_left>0 else y0[i_left], y0[i_left], half)
    xR = interp_x(i_right, i_right+1 if i_right<len(y0)-1 else i_right, y0[i_right], y0[i_right+1] if i_right<len(y0)-1 else y0[i_right], half)
    return float(xR - xL)

def resolution_curve(lsf_map: Dict[str, np.ndarray], dispersion_poly: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    keys = sorted(lsf_map.keys(), key=lambda k: float(k.replace("_dark","")))
    lambdas = []
    fwhm_nm = []
    deriv = np.polyder(dispersion_poly)
    for k in keys:
        y = lsf_map[k]
        pix_fwhm = compute_fwhm(y)
        peak_pix = _peak_pixel(y)
        dldx = np.polyval(deriv, peak_pix)
        lambdas.append(float(k))
        fwhm_nm.append(float(pix_fwhm * dldx))
    return np.array(lambdas), np.array(fwhm_nm)

# Go figures
def fig_lsf(lsf_map: Dict[str, np.ndarray]) -> go.Figure:
    fig = go.Figure()
    for k in sorted(lsf_map.keys(), key=lambda x: float(x)):
        fig.add_trace(go.Scatter(y=lsf_map[k].tolist(), mode="lines", name=f"{k} nm"))
    fig.update_layout(title="LSFs (normalized)", xaxis_title="Pixel", yaxis_title="Norm counts")
    return fig

def fig_sdf(sdf: np.ndarray, wavelengths: List[str]) -> go.Figure:
    fig = go.Figure(data=go.Heatmap(z=sdf, x=list(range(sdf.shape[1])), y=wavelengths))
    fig.update_layout(title="SDF Heatmap", xaxis_title="Pixel", yaxis_title="Wavelength (nm)")
    return fig

def fig_resolution(lmbd: np.ndarray, fwhm_nm: np.ndarray) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lmbd.tolist(), y=fwhm_nm.tolist(), mode="lines+markers", name="Resolution (FWHM)"))
    fig.update_layout(title="Spectral Resolution", xaxis_title="Wavelength (nm)", yaxis_title="FWHM (nm)")
    return fig
# API
def analyze_run(parquet_path: str, wavelengths_to_use: Optional[List[str]]=None, poly_order: int = 3):
    df = pd.read_parquet(parquet_path)
    if wavelengths_to_use is None:
        cand = sorted({w for w in df["Wavelength"].unique() if not str(w).endswith("_dark")},
                      key=lambda x: float(str(x)))
        wavelengths_to_use = cand

    lsf_map = build_lsf_map(df, wavelengths_to_use)
    if not lsf_map:
        raise RuntimeError("No valid LSFs found (check data).")

    peaks = [int(np.argmax(lsf_map[w])) for w in wavelengths_to_use]
    lambdas = [float(w) for w in wavelengths_to_use]
    poly = fit_dispersion(peaks, lambdas, order=poly_order)

    sdf, ordered = build_sdf(lsf_map)
    lam_res, fwhm_nm = resolution_curve(lsf_map, poly)

    figs = {
        "lsf": fig_lsf(lsf_map),
        "sdf": fig_sdf(sdf, ordered),
        "resolution": fig_resolution(lam_res, fwhm_nm)
    }
    return {
        "lsf_map": lsf_map,
        "poly": poly,
        "sdf": sdf,
        "ordered": ordered,
        "resolution": (lam_res, fwhm_nm),
        "figs": figs
    }