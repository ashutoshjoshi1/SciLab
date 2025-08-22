from __future__ import annotations
import os, traceback
from typing import Optional
import numpy as np

# Try to import relative, but capture the real error.
_IMPORT_ERROR: Optional[BaseException] = None
_IMPORT_TB: Optional[str] = None
try:
    from .avantes_spectrometer import Avantes_Spectrometer  # type: ignore
except Exception as e1:
    _IMPORT_ERROR, _IMPORT_TB = e1, traceback.format_exc()
    try:
        # Fallback to absolute import if running as scripts
        from avantes_spectrometer import Avantes_Spectrometer  # type: ignore
        _IMPORT_ERROR, _IMPORT_TB = None, None
    except Exception as e2:
        _IMPORT_ERROR, _IMPORT_TB = e2, traceback.format_exc()
        Avantes_Spectrometer = None  # type: ignore

class _SimAvantes:
    """Tiny simulator so UI can run without hardware/DLL."""
    def __init__(self, npix: int = 2048):
        self.sn = "SIM-AVA-0000"
        self.npix_active = int(npix)
        self._last = np.zeros(self.npix_active, float)
        self.rcm = self._last.copy()
        self._it_ms = 2.4
        self.dll_path = None

    def connect(self):  # same API as real wrapper
        return "OK"

    def disconnect(self, dofree: bool = True, **_):
        return "OK"

    def set_it(self, ms: float):
        self._it_ms = float(ms)
        return "OK"

    def _make_spectrum(self) -> np.ndarray:
        x = np.arange(self.npix_active, dtype=float)
        # Move peak with IT (purely for visual effect)
        center = self.npix_active * (0.3 + 0.4/(1.0 + np.exp(-(self._it_ms-2.0))))
        sigma = 2.5 + 0.02 * (self._it_ms)
        amp = 10000 + min(55000, (self._it_ms * 8000))
        y = amp * np.exp(-0.5*((x-center)/sigma)**2) + 100*np.random.randn(self.npix_active)
        y = np.clip(y, 0, 65535)
        return y

    def measure(self, ncy: int = 1):
        y = np.zeros(self.npix_active, float)
        for _ in range(max(1, int(ncy))):
            y += self._make_spectrum()
        self.rcm = y / max(1, int(ncy))
        self._last = self.rcm.copy()
        return "OK"

    def wait_for_measurement(self) -> str:
        return "OK"

class AvantesController:
    def __init__(self, dll_path: Optional[str] = None, simulate: bool = False):
        self._ava = None
        self.dll_path = dll_path
        self.simulate = bool(simulate)

    # ---- lifecycle ----
    def connect(self):
        # Explicit simulation (config/env) always wins
        if self.simulate or os.environ.get("SCILAB_SIMULATE", "") in ("1", "true", "True"):
            self._ava = _SimAvantes()
            self._ava.connect()
            return

        # Import error? Surface the real reason.
        if Avantes_Spectrometer is None:
            raise RuntimeError(
                "Failed to import avantes_spectrometer.\n\n"
                f"{type(_IMPORT_ERROR).__name__ if _IMPORT_ERROR else 'ImportError'}: "
                f"{_IMPORT_ERROR}\n\nTraceback:\n{_IMPORT_TB or '(none)'}\n\n"
                "Fixes:\n"
                " • Place avantes_spectrometer.py in SciLab/drivers/ (or on PYTHONPATH)\n"
                " • Ensure Avantes runtime DLL is available (Windows: avaspecx64.dll) — either on PATH "
                "   or set avantes.dll_path in SciLab.yaml\n"
                " • Or run with simulation: set avantes.simulate: true in SciLab.yaml"
            )

        # Real device path
        self._ava = Avantes_Spectrometer()
        if self.dll_path:
            # Many wrappers expect this before connect()
            self._ava.dll_path = self.dll_path

        try:
            self._ava.connect()
        except OSError as e:
            # Common when the DLL can't be found/loaded
            raise RuntimeError(
                "Could not load Avantes runtime (DLL/SO). "
                "Set avantes.dll_path in SciLab.yaml OR add the DLL folder to PATH.\n\n"
                f"OSError: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Avantes connect() failed: {e}") from e

    def disconnect(self):
        if self._ava:
            try:
                # real wrapper supports dofree; simulator ignores
                self._ava.disconnect(dofree=True)
            except Exception:
                pass
        self._ava = None

    # ---- properties ----
    @property
    def serial_number(self) -> str:
        return getattr(self._ava, "sn", "UNKNOWN") if self._ava else "UNKNOWN"

    @property
    def npix_active(self) -> int:
        return int(getattr(self._ava, "npix_active", 2048)) if self._ava else 2048

    # ---- controls ----
    def set_integration_ms(self, ms: float):
        if not self._ava:
            raise RuntimeError("Spectrometer not connected.")
        res = self._ava.set_it(ms)
        if isinstance(res, str) and res not in ("OK", ""):
            raise RuntimeError(f"set_it failed: {res}")

    # ---- acquisition ----
    def _wait_ok(self):
        if not self._ava:
            raise RuntimeError("Spectrometer not connected.")
        res = self._ava.wait_for_measurement()
        if isinstance(res, str) and res not in ("OK", ""):
            raise RuntimeError(f"Measurement error: {res}")

    def read_frame(self) -> np.ndarray:
        if not self._ava:
            raise RuntimeError("Spectrometer not connected.")
        self._ava.measure(ncy=1)
        self._wait_ok()
        return np.array(self._ava.rcm, dtype=float)

    def read_many(self, n: int) -> np.ndarray:
        if not self._ava:
            raise RuntimeError("Spectrometer not connected.")
        if n <= 0:
            raise ValueError("n must be >= 1")
        self._ava.measure(ncy=int(n))
        self._wait_ok()
        return np.array(self._ava.rcm, dtype=float)
