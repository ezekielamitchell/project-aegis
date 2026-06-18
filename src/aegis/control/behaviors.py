"""Behavior planner — Python binding to the Rust `aegis_motor` crate.

Both the motion planning (state -> behavior -> wheel speeds) and the motor
driver now live in Rust (crates/aegis-motor). `BehaviorPlanner` owns its
`MotorDriver`, so the entire control loop stays in Rust; Python only feeds it
the verified detection state and the target centroid.

Rust `BehaviorPlanner` API:
    BehaviorPlanner(simulation_mode=True, default_speed=0.4, frame_width=640.0)
    .enable()
    .plan(state: str, target_cx: float | None) -> str   # behavior name
    .emergency_stop()
    .enabled / .left_speed / .right_speed / .current_behavior  (read-only)

`plan` takes a DetectionState *value* (a string) and the target centroid x in
pixels. It returns the behavior name, which compares equal to the matching
`Behavior` member below (Behavior is a str enum).
"""

from __future__ import annotations

from enum import Enum

try:
    from aegis_motor import BehaviorPlanner  # native Rust extension
except ImportError as exc:  # pragma: no cover - depends on build step
    raise ImportError(
        "The Rust motor extension `aegis_motor` is not built. Run:\n"
        "    pip install maturin\n"
        "    maturin develop -m crates/aegis-motor/Cargo.toml\n"
        f"(original error: {exc})"
    ) from exc


class Behavior(str, Enum):
    """Behavior names, mirroring the README table. Values match the strings
    returned by the Rust planner's `plan()`."""

    PATROL = "patrol"
    SCAN = "scan"
    ORIENT_TOWARD_TARGET = "orient_toward_target"
    STOP = "stop"
    EMERGENCY_STOP = "emergency_stop"


__all__ = ["Behavior", "BehaviorPlanner"]
