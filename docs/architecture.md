# AEGIS Architecture

This document expands on the pipeline summarized in the README.

## Data flow

```
CameraSource ──frame──▶ Detector ──detections──▶ Tracker ──target?──▶ TemporalFilter
                                                                          │ state
                                                                          ▼
                                            MotorDriver ◀──commands── BehaviorPlanner
                                                                          │
                                                                          ▼
                                                          SessionLogger / MqttClient
```

## Modules

| Module | File | Responsibility |
|---|---|---|
| Camera | `perception/camera.py` | Frame source (OpenCV on HW, synthetic in sim) |
| Detector | `perception/detector.py` | YOLOv8n inference, threshold + class filter |
| Tracker | `perception/tracker.py` | Select single best target per frame |
| TemporalFilter | `verification/temporal_filter.py` | State machine; suppress false positives |
| BehaviorPlanner | `crates/aegis-motor` (Rust) | State → behavior → wheel speeds; owns the MotorDriver |
| MotorDriver | `crates/aegis-motor` (Rust) | Differential drive, safety gating, e-stop |
| ↳ bindings | `control/behaviors.py`, `control/motor_driver.py` | Re-export the Rust `aegis_motor` PyO3 classes |
| SessionLogger | `telemetry/logger.py` | JSONL session logs |
| MqttClient | `telemetry/mqtt_client.py` | Optional telemetry publishing |

## Verification state machine

A detection must persist for `required_consecutive_frames` with stable
bounding-box geometry (centroid drift ≤ `max_centroid_drift`) before reaching
`CONFIRMED`. A confirmed target survives up to `max_missed_frames` of absence
before transitioning to `LOST`. See `verification/temporal_filter.py`.

## Safety model

The motor driver and emergency-stop path live in the Rust `aegis-motor` crate
(`crates/aegis-motor/src/lib.rs`), compiled to a native Python module via PyO3.

- Motors are disabled until `MotorDriver.enable()` is called.
- GPIO output is gated behind both `simulation_mode == false` and the `hardware`
  cargo feature; a build without that feature refuses to arm real motors.
- `emergency_stop()` zeroes speeds and disables the driver, and is invoked by
  the `main.py` signal handler on SIGINT/SIGTERM.
- Real PWM/GPIO translation is stubbed pending confirmed pin mapping.

## Simulation mode

With `simulation_mode: true`, the camera emits a synthetic moving box, the
detector derives a detection from it, and the motor driver only logs commands.
This lets the entire perception-to-action loop run on any machine — used by the
test suite (`tests/test_pipeline.py`).
