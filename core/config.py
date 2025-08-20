from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import yaml
import os
from pathlib import Path

@dataclass
class SerialConfig:
    obis_port: Optional[str] = None # COM ports
    cube_port: Optional[str] = None
    relay_port: Optional[str] = None
    baudrate_obis = 115200
    baudrate_cube = 19200
    baudrate_relay = 9600
    timeout_sec = 1.0

@dataclass
class AvantesConfig:
    dll_path = None

@dataclass
class LaserSpec:
    id: str
    type: str
    enable: bool = True
    channel = None
    power_w = None
    power_nw = None
    relay_channel = None

@dataclass
class MeasureConfig:
    target_low = 60000.0
    target_high = 65000.0
    it_min_ms = 0.2
    it_max_ms = 10000.0
    start_it_ms = field(default_factory = lambda: {'531': 1000.0, '517':80.0,'default':2.4})
    step_up_ms = 0.3 #increse
    step_down_ms = 0.1 #decrease
    max_adjust_iters = 300 #max iteration
    sat_thresh = 65535.0 #saturation threshold
    n_sig = 50
    n_dark = 50
    n_sig_640 = 10
    n_dark_640 = 10

@dataclass
class OutputConfig:
    base_dir = "./runs"

@dataclass
class AppConfig:
    serial: SerialConfig = field(default_factory=SerialConfig)
    avantes: AvantesConfig = field(default_factory=AvantesConfig)
    lasers: List[LaserSpec] = field(default_factory=list)
    measure: MeasureConfig = field(default_factory=MeasureConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

DEFAULT_CONFIG = AppConfig(
    lasers = [
        LaserSpec(id = "377", type= "CUBE", power_nw = 12, enabled = True), #channel would be default
        LaserSpec(id = "405", type = "OBIS", channel = 5, power_w = 0.005, enabled = True), #power change be changed in UI
        LaserSpec(id = "445", type = "OBIS", channel = 4, power_w = 0.003, enabled = True),
        LaserSpec(id = '448', type = "OBIS", channel = 3, power_w = 0.03, enabled = True),
        LaserSpec(id = "517", type = "RELAY", relay_channel = 3, enabled = False),
        LaserSpec(id = "532", type = 'RELAY', relay_channel = 1, enabled = False)
    ]
)

def load_config(path: str | os.PathLike) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, "r", encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}
    return _from_dict(raw)

def save_config(cfg: AppConfig, path: str | os.PathLike) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p,'w', encoding='utf-8') as f:
        yaml.safe_dump(_to_dict(cfg), f, sort_keys=False)

def _from_dict(d: Dict[str, Any]) -> AppConfig:
    serial = SerialConfig(**d.get('serial', {}))
    avantes = AvantesConfig(**d.get("avantes", {}))
    measure = MeasureConfig(**d.get('measure',{}))
    output = OutputConfig(**d.get("output", {}))
    lasers = []
    for ld in d.get("lasers",[]):
        lasers.append(LaserSpec(**ld))
    return AppConfig(serial=serial, lasers=lasers, measure=measure, output=output)

def _to_dict(cfg: AppConfig) -> Dict[str, Any]:
    return {
        'serial': vars(cfg.serial),
        "avantes": vars(cfg.avantes),
        'measure': vars(cfg.measure),
        'output': vars(cfg.output),
        'lasers': [vars(l) for l in cfg.lasers]
    }