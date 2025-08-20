from typing import Optional
import numpy as np

try: from .avantes_spectrometer import Avantes_Spectrometer
except Exception as e:
    Avantes_Spectrometer = None #fix the path of dll in a_spec file

class AvantesController:
    def __init__(self, dll_path = None):
        self._ava = None
        self.dll_path = dll_path
    
    def connect(self):
        if Avantes_Spectrometer is None:
            raise RuntimeError("Avantes Spec not available. Fix the Wrapper")
        self._ava = Avantes_Spectrometer()
        if self.dll_path:
            self._ava.dll_path = self.dll_path
        self._ava.connect()

    def disconnect(self):
        if self._ava:
            try:
                self._ava.disconnect(dofree=True)
            except Exception:
                pass
        self._ava = None

    @property
    def serial_number(self):
        return getattr(self._ava, "sn", "UNKNOWN") if self._ava else "UNKNOWN"
    
    @property
    def npix_active(self):
        return int(getattr(self._ava, "npix_active", 2048)) if self._ava else 2048
    
    def set_integration_ms(self, ms):
        if not self._ava:
            raise RuntimeError("Spectromete not conneceted")
        res = self._ava.set_it(ms)
        if isinstance(res, str) and res != 'OK':
            raise RuntimeError(f"set_it error: {res}")
        
    def _wait_ok(self):
        if not self.ava:
            raise RuntimeError("Spec not Connected")
        res = self._ava.wait_for_measurement()
        if isinstance(res, str) and res != "OK":
            raise RuntimeError(f"Measurement error: {res}")
        
    def read_frame(self):
        if not self._ava:
            raise RuntimeError("Spec not connected")
        self._ava.measure(ncy=1)
        self._wait_ok()
        y = np.array(self._ava.rcm, dtype = float)
        return y

    def read_many(self, n): # for number of cycles
        if not self._ava:
            raise RuntimeError("Spec not connected")
        if n <=0:
            raise ValueError("n must be >= 1")
        self._ava.measure(ncy = int(n))
        self._wait_ok()
        y = np.array(self._ava.rcm, dtype=float)
        return y