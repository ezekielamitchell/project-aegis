"""Motor driver — Python binding to the Rust `aegis_control` crate.

The motor control + safety/emergency-stop logic lives in Rust
(crates/aegis-control) and is compiled to a native extension module via PyO3.
This module re-exports that `MotorDriver` so the rest of the Python code can
keep importing `from aegis.control.motor_driver import MotorDriver`.

Build the extension before running:

    pip install maturin
    maturin develop -m crates/aegis-control/Cargo.toml

The exposed API (set_speeds/stop/emergency_stop/enable/disable plus the
enabled/left_speed/right_speed properties) is identical to the previous pure
-Python driver, so BehaviorPlanner and the test suite are unchanged.
"""

from __future__ import annotations

try:
    from aegis_control import MotorDriver  # native Rust extension
except ImportError as exc:  # pragma: no cover - depends on build step
    raise ImportError(
        "The Rust motor extension `aegis_control` is not built. Run:\n"
        "    pip install maturin\n"
        "    maturin develop -m crates/aegis-control/Cargo.toml\n"
        f"(original error: {exc})"
    ) from exc

__all__ = ["MotorDriver"]
