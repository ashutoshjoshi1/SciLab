# SciLab/drivers/avantes_controller.py
from __future__ import annotations

import os
import sys
import logging
import traceback
from typing import Optional

import numpy as np

# -----------------------------------------------------------------------------
# Import shim so the driver (which uses absolute imports) can be found either
# when running as a package (python -m SciLab.ui.app) or as flat scripts.
# -----------------------------------------------------------------------------
DRIVERS_DIR = os.path.dirname(__file__)  # .../SciLab/drivers
if DRIVERS_DIR not in sys.path:
    sys.path.insert(0, DRIVERS_DIR)

_IMPORT_ERROR: Optional[BaseException] = None
_IMPORT_TB: Optional[str] = None
Avantes_Spectrometer = None  # will be replaced if import succeeds

try:
    # Package mode first
    from .avantes_spectrometer import Avantes_Spectrometer  # type: ignore
    _IMPORT_ERROR, _IMPORT_TB = None, None
except Exception as e1:
    _IMPORT_ERROR, _IMPORT_TB = e1, traceback.format_exc()
    try:
        # Flat / script mode fallback
        from avantes_spectrometer import Avantes_Spectrometer  # type: ignore
        _IMPORT_ERROR, _IMPORT_TB = None, None
    except Exception as e2:
        _IMPORT_ERROR, _IMPORT_TB = e2, traceback.format_exc()
        Avantes_Spectrometer = None  # type: ignore

# -----------------------------------------------------------------------------
# Default logger exposed by drivers package (if present)
# -----------------------------------------------------------------------------
try:
    from . import LOGGER as DEFAULT_LOGGER  # type: ignore
except Exception:
    DEFAULT_LOGGER = logging.getLogger("SciLab.AvantesController")
    if not DEFAULT_LOGGER.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
        DEFAULT_LOGGER.addHandler(h)
        DEFAULT_LOGGER.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Lightweight simulator (used if simulate=True OR driver import/hardware fails)
# -----------------------------------------------------------------------------
class _SimAvantes:
    def __init__(self, npix: int = 2048):
        self.sn = "SIM-AVA-0000"
        self.npix_active = int(npix)
        self.rcm = np.zeros(self.npix_active, float)
        self._it_ms = 2.4
        self.dll_path = None
        self.logger = DEFAULT_LOGGER
        self.alias = "Avantes (Simulated)"
        self.simulate = True
        self.parlist = object()  # dummy so attributes exist in driver-style code

    def connect(self):  # mimic OK path
        if self.logger:
            self.logger.info(f"[simulate] connect {self.alias}")
        return "OK"

    def disconnect(self, dofree: bool = True, **_):
        if self.logger:
            self.logger.info(f"[simulate] disconnect {self.alias}")
        return "OK"

    def set_it(self, ms: float):
        self._it_ms = float(ms)
        if self.logger:
            self.logger.info(f"[simulate] set_it = {self._it_ms:.2f} ms")
        return "OK"

    def _spectrum(self) -> np.ndarray:
        x = np.arange(self.npix_active, dtype=float)
        center = self.npix_active * (0.3 + 0.4/(1.0 + np.exp(-(self._it_ms - 2.0))))
        sigma = 2.5 + 0.02 * self._it_ms
        amp = min(60000.0, 8000.0 * max(0.5, self._it_ms))
        y = amp * np.exp(-0.5 * ((x - center) / sigma) ** 2) + 100.0 * np.random.randn(self.npix_active)
        return np.clip(y, 0, 65535)

    def measure(self, ncy: int = 1):
        ncy = max(1, int(ncy))
        y = np.zeros(self.npix_active, float)
        for _ in range(ncy):
            y += self._spectrum()
        self.rcm = y / ncy
        return "OK"

    def wait_for_measurement(self) -> str:
        return "OK"


# -----------------------------------------------------------------------------
# Controller (does NOT modify avantes_spectrometer.py)
# -----------------------------------------------------------------------------
class AvantesController:
    """
    Thin adapter around Avantes_Spectrometer that:
      - accepts arbitrary config kwargs (dll_path, simulate, alias, etc.)
      - injects a valid logger and alias
      - sets attributes on the driver instance (no driver edits)
      - ensures the driver's 'parlist' exists before calling set_it()
      - provides simple acquisition helpers compatible with core/measurement.py
    """

    def __init__(self, *_, **kwargs):
        self.dll_path: Optional[str] = kwargs.get("dll_path")
        self.simulate: bool = bool(kwargs.get("simulate", False))
        self.alias: str = kwargs.get("alias", "Avantes")

        self.logger = kwargs.get("logger") or DEFAULT_LOGGER
        if not self.logger.handlers:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
            self.logger.addHandler(h)
            self.logger.setLevel(logging.INFO)

        self._ava = None
        self._connected = False

    # -----------------------------
    # lifecycle
    # -----------------------------
    def connect(self):
        # Choose real driver unless simulate is requested or import failed
        use_sim = self.simulate or (Avantes_Spectrometer is None) or (_IMPORT_ERROR is not None)

        if self._ava is None:
            if use_sim:
                self._ava = _SimAvantes()
            else:
                self._ava = Avantes_Spectrometer()  # type: ignore

            # Push config into the driver instance (no driver edits)
            try:
                if getattr(self._ava, "logger", None) is None:
                    self._ava.logger = self.logger
            except Exception:
                self._ava.logger = self.logger

            try:
                self._ava.alias = self.alias or "Avantes"
            except Exception:
                pass

            if self.dll_path:
                try:
                    self._ava.dll_path = self.dll_path
                except Exception:
                    pass

            try:
                self._ava.simulate = bool(use_sim or getattr(self._ava, "simulate", False))
            except Exception:
                pass

        self.logger.info(f"AvantesController: connecting {self.alias}")
        self._ava.connect()
        self._connected = True

        # Proactively make sure 'parlist' exists to avoid m_IntegrationTime crashes
        self._ensure_parlist()

    def disconnect(self):
        if self._ava:
            try:
                self._ava.disconnect(dofree=True)
            except Exception:
                pass
        self._ava = None
        self._connected = False

    def _ensure_connected(self):
        if not self._ava or not self._connected:
            self.connect()

    # -----------------------------
    # parameter-list preparation
    # -----------------------------
    def _ensure_parlist(self) -> bool:
        """
        Make sure the driver has a usable 'parlist' object.
        Try common initializer names if the driver didn’t populate it in connect().
        """
        if not self._ava:
            return False

        if getattr(self._ava, "parlist", None) is not None:
            return True

        candidates = [
            "get_parameter_list",
            "get_parlist",
            "read_parameter_list",
            "read_parlist",
            "init_parlist",
            "prepare_measurement",
            "init_measurement",
            "setup_default",
            "create_default_parlist",
        ]

        for name in candidates:
            if hasattr(self._ava, name):
                try:
                    pl = getattr(self._ava, name)()
                    if getattr(self._ava, "parlist", None) is None and pl is not None:
                        self._ava.parlist = pl
                    if getattr(self._ava, "parlist", None) is not None:
                        return True
                except Exception:
                    continue

        # As a last resort for simulate paths, attach a simple object with the field
        try:
            class _PL:  # minimal stub
                pass
            pl = _PL()
            setattr(pl, "m_IntegrationTime", 10.0)
            self._ava.parlist = pl
            return True
        except Exception:
            return False

    # -----------------------------
    # properties
    # -----------------------------
    @property
    def serial_number(self) -> str:
        return getattr(self._ava, "sn", "UNKNOWN") if self._ava else "UNKNOWN"

    @property
    def npix_active(self) -> int:
        return int(getattr(self._ava, "npix_active", 2048)) if self._ava else 2048

    # -----------------------------
    # controls
    # -----------------------------
    def set_integration_ms(self, ms: float):
        """
        Ensure device + parlist are ready, then set integration time.
        Retries once if the driver complains about missing m_IntegrationTime.
        """
        self._ensure_connected()

        # Short-circuit in simulation
        try:
            if getattr(self._ava, "simulate", False):
                try:
                    self._ava._it_ms = float(ms)  # for our simulator
                except Exception:
                    pass
                self.logger.info(f"[simulate] set integration to {ms} ms")
                return
        except Exception:
            pass

        if not self._ensure_parlist():
            self.logger.warning("AvantesController: could not initialize 'parlist' before set_it().")

        try:
            res = self._ava.set_it(float(ms))
        except AttributeError as e:
            # Typical: 'NoneType' object has no attribute 'm_IntegrationTime'
            if "m_IntegrationTime" in str(e):
                self.logger.info("AvantesController: initializing 'parlist' and retrying set_it() once.")
                if self._ensure_parlist():
                    res = self._ava.set_it(float(ms))
                else:
                    raise
            else:
                raise

        if isinstance(res, str) and res not in ("OK", ""):
            raise RuntimeError(f"set_it failed: {res}")

    # -----------------------------
    # acquisition
    # -----------------------------
    def _wait_ok(self):
        if not self._ava:
            raise RuntimeError("Spectrometer not connected.")
        res = self._ava.wait_for_measurement()
        if isinstance(res, str) and res not in ("OK", ""):
            raise RuntimeError(f"Measurement error: {res}")

    def read_frame(self) -> np.ndarray:
        self._ensure_connected()
        self._ava.measure(ncy=1)
        self._wait_ok()
        return np.array(self._ava.rcm, dtype=float)

    def read_many(self, n: int) -> np.ndarray:
        self._ensure_connected()
        if n <= 0:
            raise ValueError("n must be >= 1")
        self._ava.measure(ncy=int(n))
        self._wait_ok()
        return np.array(self._ava.rcm, dtype=float)
