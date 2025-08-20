from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List
import json
import time
import pandas as pd

@dataclass
class RunPaths:
    root: Path
    csv_path: Path
    parquet_path: Path
    meta_path: Path

def prepare_run_dir(base_dir: str, device_sn: str) -> RunPaths:
    ts = time.strftime("%Y%m%d_%H%M%S")
    root = Path(base_dir) / f"run_{device_sn}_{ts}"
    root.mkdir(parents=True, exist_ok=True)
    return RunPaths(
        root= root,
        csv_path= root / "frames.csv",
        parquet_path=root / "frames.parquet",
        meta_path=root / "run.json"
    )

class DataLogger:
    def __init__(self, paths: RunPaths):
        self.paths = paths
        self.rows: List[Dict[str, Any]] = []
    
    def log_meta(self, meta: Dict[str,Any]):
        with open(self.paths.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def add_frame(self, timestamp: str, laser_id: str, cycle_type: str, cycle_idx: int, integration_ms: float, pixels: list[float]):
        row: Dict[str, Any] = {
            "Timestamp": timestamp,
            "LaserID": laser_id,
            "CycleType": cycle_type,
            "CycleIDX": cycle_idx,
            "IntegrationMS": integration_ms
        }
        for i, val in enumerate(pixels):
            row[f"Pixel_{i}"] = float(val)
        self.rows.append(row)

    def flush(self):
        if not self.rows:
            return
        df = pd.DataFrame(self.rows)
        if self.paths.csv_path.exists():
            df.to_csv(self.paths.csv_path, mode = 'a', header=False, index=False)
        else:
            df.to_csv(self.paths.csv_path, index=False)
        if self.paths.parquet_path.exists():
            old = pd.read_parquet(self.paths.parquet_path)
            pd.concat([old,df], ignore_index=True).to_parquet(self.paths.parquet_path, index=False)
        else:
            df.to_parquet(self.paths.parquet_path, index=False)
        self.rows.clear()