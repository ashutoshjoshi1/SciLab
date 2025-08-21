import numpy as np
from dataclasses import dataclass
from typing import Tuple

@dataclass
class AutoITParams:
    it_min_ms: float
    it_max_ms: float
    target_low: float
    target_high: float
    step_up_ms: float
    step_down_ms: float
    max_adjust_iters: int
    sat_thresh: float

class AutoIT:
    def __init__(self, params: AutoITParams):
        self.p = params

    def tune(self, read_peak, set_it, start_it_ms: float, on_progress = None) -> Tuple[float, float, bool]:
        it = float(np.clip(start_it_ms, self.p.it_min_ms, self.p.it_max_ms))
        target_mid = 0.5* (self.p.target_low + self.p.target_high)
        peak = np.nan
        success = False
        iters = 0

        while True:
            set_it(it)
            peak, _ = read_peak()
            if on_progress: on_progress(it, peak, iters)
            if not np.isfinite(peak):
                iters += 1
                if iters > self.p.max_adjust_iters: break
                continue
                
            if peak >= self.p.sat_thresh:
                it = max(self.p.it_min_ms, it * 0.7)
                iters += 1
                if iters > self.p.max_adjust_iters: break
                continue

            if self.p.target_low <= peak <= self.p.target_high:
                success = True
                break

            err = target_mid - peak

            if err > 0:
                delta = min(self.p.step_up_ms, max(0.05, abs(err)/5000.0))
                it = min(self.p.it_max_ms, it + delta)
            else:
                delta = min(self.p.step_down_ms, max(0.05, abs(err)/5000.0))
                it = max(self.p.it_min_ms, it - delta)

            iters += 1
            if iters > self.p.max_adjust_iters:
                break
        return it, float(peak) if np.isfinite(peak) else float("nan"), success