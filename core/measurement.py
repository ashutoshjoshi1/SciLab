from dataclasses import dataclass
from typing import Callable, Optional, Dict
from datetime import datetime
import numpy as np

from .config import AppConfig, LaserSpec
from .auto_it import AutoIT, AutoITParams
from .datalogger import DataLogger, prepare_run_dir
from ..drivers.avantes_controller import AvantesController
from ..drivers.obis_controller import ObisController
from ..drivers.cube_controller import CubeController
from ..drivers.relay_controller import RelayController

@dataclass
class MeasurementResult:
    run_dir: str
    success_map: Dict[str, bool]

class MeasurementRunner:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.spec = AvantesController(
            dll_path=self.cfg.avantes.dll_path,
            simulate=self.cfg.avantes.simulate
        )
        self.obis: Optional[ObisController] = None
        self.cube: Optional[CubeController] = None
        self.relay: Optional[RelayController] = None

    def _connect_devices(self):
        self.spec.connect()
        if self.cfg.serial.obis_port:
            self.obis = ObisController(self.cfg.serial.obis_port, self.cfg.serial.baudrate_obis, self.cfg.serial.timeout_sec)
            self.obis.connect()
        if self.cfg.serial.cube_port:
            self.cube = CubeController(self.cfg.serial.cube_port, self.cfg.serial.baudrate_cube, self.cfg.serial.timeout_sec)
            self.cube.connect()
        if self.cfg.serial.relay_port:
            self.relay = RelayController(self.cfg.serial.relay_port, self.cfg.serial.baudrate_relay, self.cfg.serial.timeout_sec)
            self.relay.connect()

    def _disconnect_devices(self):
        try: self.spec.disconnect()
        except: pass
        for dev in (self.obis, self.cube, self.relay):
            try:
                if dev: dev.close()
            except: pass

    def _laser_on(self, ls: LaserSpec):
        if ls.type == "CUBE":
            if not self.cube: raise RuntimeError("CUBE port not configured")
            self.cube.on(power_mw=ls.power_mw or 12.0)
        elif ls.type == "OBIS":
            if not self.obis or ls.channel is None: raise RuntimeError("OBIS port or channel missing")
            self.obis.on(ls.channel)
            if ls.power_w is not None:
                self.obis.set_power_w(ls.channel, ls.power_w)
        elif ls.type == "RELAY":
            if not self.relay or ls.relay_channel is None: raise RuntimeError("Relay port/channel missing")
            self.relay.on(ls.relay_channel)
        else:
            raise ValueError(f"Unknown laser type {ls.type}")

    def _laser_off(self, ls: LaserSpec):
        if ls.type == "CUBE":
            if self.cube: self.cube.off()
        elif ls.type == "OBIS":
            if self.obis and ls.channel is not None: self.obis.off(ls.channel)
        elif ls.type == "RELAY":
            if self.relay and ls.relay_channel is not None: self.relay.off(ls.relay_channel)

    def run(self, on_live: Optional[Callable[[np.ndarray, float, float, str], None]] = None) -> MeasurementResult:
        self._connect_devices()
        try:
            paths = prepare_run_dir(self.cfg.output.base_dir, self.spec.serial_number)
            logger = DataLogger(paths)
            logger.log_meta({
                "serial_number": self.spec.serial_number,
                "npix": self.spec.npix_active,
                "config": {
                    "measure": vars(self.cfg.measure),
                    "lasers": [vars(l) for l in self.cfg.lasers],
                    "avantes": vars(self.cfg.avantes),
                }
            })

            success_map: Dict[str, bool] = {}
            p = self.cfg.measure
            auto = AutoIT(AutoITParams(
                it_min_ms=p.it_min_ms, it_max_ms=p.it_max_ms,
                target_low=p.target_low, target_high=p.target_high,
                step_up_ms=p.step_up_ms, step_down_ms=p.step_down_ms,
                max_adjust_iters=p.max_adjust_iters, sat_thresh=p.sat_thresh
            ))

            for ls in self.cfg.lasers:
                if not ls.enabled:
                    success_map[ls.id] = False
                    continue

                try:
                    self._laser_on(ls)
                except Exception as e:
                    print(f"[{ls.id}] Laser ON failed: {e}")
                    success_map[ls.id] = False
                    continue

                start_it = self.cfg.measure.start_it_ms.get(ls.id, self.cfg.measure.start_it_ms.get("default", 2.4))
                current_it = [start_it]

                def set_it(ms: float):
                    self.spec.set_integration_ms(ms)

                def read_peak():
                    y = self.spec.read_frame()
                    peak = float(np.max(y)) if y.size else float("nan")
                    if on_live: on_live(y, peak, current_it[0], ls.id)
                    return peak, y

                def progress(it, peak, iters):
                    current_it[0] = it
                    if on_live: on_live(np.array([]), peak, it, ls.id)

                it_final, last_peak, ok = auto.tune(read_peak, set_it, start_it, on_progress=progress)
                success_map[ls.id] = ok
                if not ok:
                    print(f"[{ls.id}] Auto-IT failed (peak={last_peak:.1f}). Skipping capture.")
                    self._laser_off(ls)
                    continue

                # Signal
                self.spec.set_integration_ms(it_final)
                y_sig = self.spec.read_many(self.cfg.measure.n_sig)
                ts = datetime.now().isoformat(timespec="seconds")
                logger.add_frame(ts, ls.id, "SIG", 0, it_final, y_sig.tolist())

                # Dark
                self._laser_off(ls)
                y_dark = self.spec.read_many(self.cfg.measure.n_dark)
                ts = datetime.now().isoformat(timespec="seconds")
                logger.add_frame(ts, f"{ls.id}_dark", "DARK", 0, it_final, y_dark.tolist())

                logger.flush()

            return MeasurementResult(run_dir=str(paths.root), success_map=success_map)
        finally:
            self._disconnect_devices()
