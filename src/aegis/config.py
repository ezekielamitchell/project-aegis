"""Configuration loading for AEGIS.

Config is read from a YAML file (see configs/default.yaml). Unknown keys are
ignored so the file can carry documentation/future settings without breaking
older code. Missing keys fall back to the defaults defined here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a hard dependency at runtime
    yaml = None


@dataclass
class Config:
    """Runtime configuration. Mirrors keys in configs/default.yaml."""

    simulation_mode: bool = True
    camera_index: int = 0
    target_class: str = "person"
    confidence_threshold: float = 0.55
    required_consecutive_frames: int = 4
    max_missed_frames: int = 8
    motor_speed_default: float = 0.4
    telemetry_enabled: bool = True
    mqtt_enabled: bool = False
    debug: bool = False

    # Geometry stability: max allowed centroid drift (fraction of frame width)
    # between consecutive frames for a detection to still count as the same
    # target during verification.
    max_centroid_drift: float = 0.15

    # MQTT connection details (only used when mqtt_enabled is true).
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "aegis/telemetry"

    # Where session logs are written.
    log_dir: str = "data"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str) -> "Config":
        if yaml is None:
            raise RuntimeError("PyYAML is required to load config; pip install pyyaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)
