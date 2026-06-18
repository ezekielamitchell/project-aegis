//! AEGIS motor control + safety layer.
//!
//! This crate owns the safety-critical, real-time-sensitive part of AEGIS: the
//! differential-drive motor driver and the emergency-stop path. It is compiled
//! as a native Python extension (`aegis_control`) via PyO3 and consumed by the
//! Python `BehaviorPlanner`.
//!
//! SAFETY model (mirrors README "Safety"):
//!   * Motors are disabled until `enable()` is called.
//!   * GPIO output is only attempted when `simulation_mode == false` AND the
//!     `hardware` cargo feature is compiled in.
//!   * `emergency_stop()` zeroes speeds and disables the driver. It always wins.
//!   * Real PWM/GPIO is stubbed pending confirmed pin mapping.

use pyo3::prelude::*;

/// Placeholder BCM pin assignments — confirm against wiring before enabling.
#[allow(dead_code)]
const LEFT_MOTOR_PINS: (u8, u8) = (17, 18);
#[allow(dead_code)]
const RIGHT_MOTOR_PINS: (u8, u8) = (22, 23);

#[inline]
fn clamp_unit(value: f64) -> f64 {
    value.clamp(-1.0, 1.0)
}

/// Differential-drive motor driver with safety gating.
#[pyclass]
pub struct MotorDriver {
    #[pyo3(get)]
    simulation_mode: bool,
    #[pyo3(get)]
    default_speed: f64,
    #[pyo3(get)]
    enabled: bool,
    #[pyo3(get)]
    left_speed: f64,
    #[pyo3(get)]
    right_speed: f64,
}

#[pymethods]
impl MotorDriver {
    #[new]
    #[pyo3(signature = (simulation_mode = true, default_speed = 0.4))]
    fn new(simulation_mode: bool, default_speed: f64) -> Self {
        MotorDriver {
            simulation_mode,
            default_speed,
            enabled: false,
            left_speed: 0.0,
            right_speed: 0.0,
        }
    }

    /// Arm the driver. Required before any movement on hardware.
    fn enable(&mut self) {
        if self.simulation_mode {
            self.enabled = true;
            eprintln!("[SIM] motor driver enabled");
            return;
        }
        #[cfg(feature = "hardware")]
        {
            // TODO: GPIO setup (BCM mode, configure LEFT/RIGHT pins as output).
            self.enabled = true;
            eprintln!("motor driver enabled (GPIO armed)");
        }
        #[cfg(not(feature = "hardware"))]
        {
            // Built without hardware support: refuse to arm real motors.
            eprintln!("hardware feature not compiled; staying disabled");
            self.enabled = false;
        }
    }

    /// Set normalized wheel speeds in [-1.0, 1.0] (values are clamped).
    fn set_speeds(&mut self, left: f64, right: f64) {
        self.left_speed = clamp_unit(left);
        self.right_speed = clamp_unit(right);

        if !self.enabled {
            return;
        }
        if self.simulation_mode {
            eprintln!(
                "[SIM] set_speeds left={:.2} right={:.2}",
                self.left_speed, self.right_speed
            );
            return;
        }
        #[cfg(feature = "hardware")]
        {
            // TODO: translate normalized speed to PWM duty cycle on the pins.
        }
    }

    /// Halt motor output but keep the driver armed.
    fn stop(&mut self) {
        self.set_speeds(0.0, 0.0);
        let prefix = if self.simulation_mode { "[SIM] " } else { "" };
        eprintln!("{prefix}motors stopped");
    }

    /// Immediate full stop and disable. Takes priority over everything.
    fn emergency_stop(&mut self) {
        self.left_speed = 0.0;
        self.right_speed = 0.0;
        let prefix = if self.simulation_mode { "[SIM] " } else { "" };
        eprintln!("{prefix}EMERGENCY STOP");
        self.disable();
    }

    fn disable(&mut self) {
        self.enabled = false;
        #[cfg(feature = "hardware")]
        {
            // TODO: GPIO cleanup.
        }
        let prefix = if self.simulation_mode { "[SIM] " } else { "" };
        eprintln!("{prefix}motor driver disabled");
    }

    fn __repr__(&self) -> String {
        format!(
            "MotorDriver(simulation_mode={}, enabled={}, left={:.2}, right={:.2})",
            self.simulation_mode, self.enabled, self.left_speed, self.right_speed
        )
    }
}

/// Default reference frame width (px) for normalizing the orient error.
const FRAME_WIDTH_DEFAULT: f64 = 640.0;

/// Behavior planner: maps a verified detection state to a patrol behavior and
/// drives the motor. Owns its `MotorDriver` so the whole control loop —
/// motion planning, motor output, and emergency stop — stays in Rust.
///
/// Behaviors mirror the README table:
///   patrol               execute waypoint loop
///   scan                 rotate in place, observe environment
///   orient_toward_target rotate to center a confirmed target in frame
///   stop                 halt all motor output
///   emergency_stop       immediate full stop, disable the motor driver
#[pyclass]
pub struct BehaviorPlanner {
    motor: MotorDriver,
    #[pyo3(get)]
    default_speed: f64,
    #[pyo3(get)]
    frame_width: f64,
    #[pyo3(get)]
    current_behavior: String,
}

#[pymethods]
impl BehaviorPlanner {
    #[new]
    #[pyo3(signature = (simulation_mode = true, default_speed = 0.4, frame_width = FRAME_WIDTH_DEFAULT))]
    fn new(simulation_mode: bool, default_speed: f64, frame_width: f64) -> Self {
        BehaviorPlanner {
            motor: MotorDriver::new(simulation_mode, default_speed),
            default_speed,
            frame_width,
            current_behavior: "scan".to_string(),
        }
    }

    /// Arm the underlying motor driver.
    fn enable(&mut self) {
        self.motor.enable();
    }

    /// Select and execute a behavior for the given state, returning its name.
    ///
    /// `state` is a DetectionState value ("NO_TARGET" | "CANDIDATE" |
    /// "CONFIRMED" | "LOST"). `target_cx` is the target centroid x in pixels
    /// (or None when there is no tracked target).
    #[pyo3(signature = (state, target_cx = None))]
    fn plan(&mut self, state: &str, target_cx: Option<f64>) -> String {
        let behavior = if state == "CONFIRMED" && target_cx.is_some() {
            "orient_toward_target"
        } else if state == "NO_TARGET" || state == "LOST" {
            "scan"
        } else {
            // CANDIDATE (or CONFIRMED with no centroid): hold position while
            // verification is pending.
            "stop"
        };
        self.execute(behavior, target_cx);
        behavior.to_string()
    }

    fn emergency_stop(&mut self) {
        self.execute("emergency_stop", None);
    }

    // Motor-state passthrough for telemetry/testing.
    #[getter]
    fn enabled(&self) -> bool {
        self.motor.enabled
    }
    #[getter]
    fn left_speed(&self) -> f64 {
        self.motor.left_speed
    }
    #[getter]
    fn right_speed(&self) -> f64 {
        self.motor.right_speed
    }
}

impl BehaviorPlanner {
    fn execute(&mut self, behavior: &str, target_cx: Option<f64>) {
        if self.current_behavior != behavior {
            eprintln!("behavior {} -> {}", self.current_behavior, behavior);
        }
        self.current_behavior = behavior.to_string();

        let speed = self.default_speed;
        match behavior {
            "patrol" => self.motor.set_speeds(speed, speed),
            "scan" => self.motor.set_speeds(speed, -speed), // rotate in place
            "orient_toward_target" => {
                let (left, right) = self.orient_speeds(target_cx, speed);
                self.motor.set_speeds(left, right);
            }
            "stop" => self.motor.stop(),
            "emergency_stop" => self.motor.emergency_stop(),
            _ => {}
        }
    }

    /// Proportional rotation to center the target horizontally.
    fn orient_speeds(&self, target_cx: Option<f64>, speed: f64) -> (f64, f64) {
        match target_cx {
            None => (0.0, 0.0),
            Some(cx) => {
                let half = self.frame_width / 2.0;
                // error in [-1, 1]: negative => target left of center.
                let error = ((cx - half) / half).clamp(-1.0, 1.0);
                let turn = error * speed;
                (turn, -turn)
            }
        }
    }
}

/// The Python module: `import aegis_control`.
#[pymodule]
fn aegis_control(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MotorDriver>()?;
    m.add_class::<BehaviorPlanner>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clamps_to_unit_range() {
        assert_eq!(clamp_unit(2.0), 1.0);
        assert_eq!(clamp_unit(-2.0), -1.0);
        assert_eq!(clamp_unit(0.5), 0.5);
    }

    #[test]
    fn emergency_stop_disables_and_zeroes() {
        let mut m = MotorDriver::new(true, 0.4);
        m.enable();
        m.set_speeds(1.0, 1.0);
        m.emergency_stop();
        assert!(!m.enabled);
        assert_eq!(m.left_speed, 0.0);
        assert_eq!(m.right_speed, 0.0);
    }

    #[test]
    fn sim_enable_arms_driver() {
        let mut m = MotorDriver::new(true, 0.4);
        assert!(!m.enabled);
        m.enable();
        assert!(m.enabled);
    }

    #[test]
    fn planner_orients_on_confirmed_target() {
        let mut p = BehaviorPlanner::new(true, 0.4, 640.0);
        p.enable();
        assert_eq!(p.plan("CONFIRMED", Some(320.0)), "orient_toward_target");
    }

    #[test]
    fn planner_scans_with_no_target() {
        let mut p = BehaviorPlanner::new(true, 0.4, 640.0);
        p.enable();
        assert_eq!(p.plan("NO_TARGET", None), "scan");
        assert_eq!(p.plan("LOST", None), "scan");
    }

    #[test]
    fn planner_stops_on_candidate() {
        let mut p = BehaviorPlanner::new(true, 0.4, 640.0);
        p.enable();
        assert_eq!(p.plan("CANDIDATE", None), "stop");
    }

    #[test]
    fn orient_turns_toward_offcenter_target() {
        let p = BehaviorPlanner::new(true, 0.4, 640.0);
        // Centered target -> no turn.
        assert_eq!(p.orient_speeds(Some(320.0), 0.4), (0.0, 0.0));
        // Target far right -> positive left wheel, negative right wheel.
        let (l, r) = p.orient_speeds(Some(640.0), 0.4);
        assert!(l > 0.0 && r < 0.0);
        assert_eq!(l, -r);
    }

    #[test]
    fn emergency_stop_via_planner_disables() {
        let mut p = BehaviorPlanner::new(true, 0.4, 640.0);
        p.enable();
        p.emergency_stop();
        assert!(!p.enabled());
    }
}
