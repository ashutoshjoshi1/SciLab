from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import yaml
import os
from pathlib import Path

@dataclass
class SerialConfig:
    obis_port: Optional[str] = None
    cube_port: Optional[str] = None
    relay_port: Optional[str] = None
    baudrate_obis: int = 115200
    baudrate_cube: int = 19200
    baudrate_relay: int = 9600
    timeout_sec: float = 1.0

@dataclass
class AvantesConfig:
    dll_path: Optional[str] = None  # e.g., "C:/Program Files/Avantes/SDK/bin/avaspecx64.dll"

@dataclass
class LaserSpec:
    id: str                 # "377", "405", ...
    type: str               # "CUBE", "OBIS", "RELAY"
    enabled: bool = True
    channel: Optional[int] = None        # OBIS channel
    power_w: Optional[float] = None      # OBIS
    power_mw: Optional[float] = None     # CUBE
    relay_channel: Optional[int] = None  # RELAY

@dataclass
class MeasureConfig:
    target_low: float = 60000.0
    target_high: float = 65000.0
    it_min_ms: float = 0.2
    it_max_ms: float = 10000.0
    start_it_ms: Dict[str, float] = field(
        default_factory=lambda: {"532": 1000.0, "517": 80.0, "default": 2.4}
    )
    step_up_ms: float = 0.3
    step_down_ms: float = 0.1
    max_adjust_iters: int = 300
    sat_thresh: float = 65535.0
    n_sig: int = 50
    n_dark: int = 50
    n_sig_640: int = 10
    n_dark_640: int = 10

@dataclass
class OutputConfig:
    base_dir: str = "./runs"

@dataclass
class AppConfig:
    serial: SerialConfig = field(default_factory=SerialConfig)
    avantes: AvantesConfig = field(default_factory=AvantesConfig)
    lasers: List[LaserSpec] = field(default_factory=list)
    measure: MeasureConfig = field(default_factory=MeasureConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

DEFAULT_CONFIG = AppConfig(
    lasers=[
        LaserSpec(id="377", type="CUBE", power_mw=12, enabled=True),
        LaserSpec(id="405", type="OBIS", channel=5, power_w=0.005, enabled=True),
        LaserSpec(id="445", type="OBIS", channel=4, power_w=0.003, enabled=True),
        LaserSpec(id="488", type="OBIS", channel=3, power_w=0.03,  enabled=True),
        LaserSpec(id="517", type="RELAY", relay_channel=3, enabled=False),
        LaserSpec(id="532", type="RELAY", relay_channel=1, enabled=False),
    ]
)

def load_config(path: Union[str, os.PathLike]) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _from_dict(raw)

def save_config(cfg: AppConfig, path: Union[str, os.PathLike]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(_to_dict(cfg), f, sort_keys=False)

def _from_dict(d: Dict[str, Any]) -> AppConfig:
    serial = SerialConfig(**d.get("serial", {}))
    avantes = AvantesConfig(**d.get("avantes", {}))
    measure = MeasureConfig(**d.get("measure", {}))
    output  = OutputConfig(**d.get("output", {}))
    lasers  = [LaserSpec(**ld) for ld in d.get("lasers", [])]
    return AppConfig(serial=serial, avantes=avantes, lasers=lasers, measure=measure, output=output)

def _to_dict(cfg: AppConfig) -> Dict[str, Any]:
    return {
        "serial": vars(cfg.serial),
        "avantes": vars(cfg.avantes),
        "measure": vars(cfg.measure),
        "output": vars(cfg.output),
        "lasers": [vars(l) for l in cfg.lasers],
    }
