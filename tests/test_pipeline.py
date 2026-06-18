"""Smoke tests for config, control, and the end-to-end simulation pipeline."""

from aegis.config import Config
from aegis.control import Behavior, BehaviorPlanner, MotorDriver
from aegis.main import run


def test_config_defaults_and_unknown_keys_ignored():
    cfg = Config.from_dict({"camera_index": 2, "not_a_real_key": 123})
    assert cfg.camera_index == 2
    assert cfg.simulation_mode is True


def test_motor_driver_safe_by_default():
    motor = MotorDriver(simulation_mode=True)
    assert motor.enabled is False
    # Commands before enable() should not move anything.
    motor.set_speeds(1.0, 1.0)
    motor.enable()
    motor.set_speeds(2.0, -2.0)  # out of range -> clamped
    assert motor.left_speed == 1.0
    assert motor.right_speed == -1.0


def test_emergency_stop_disables_driver():
    motor = MotorDriver(simulation_mode=True)
    motor.enable()
    motor.emergency_stop()
    assert motor.enabled is False
    assert motor.left_speed == 0.0


def test_planner_orients_on_confirmed_target():
    planner = BehaviorPlanner(simulation_mode=True, default_speed=0.4)
    planner.enable()
    # target centroid x = 320 (frame center) -> confirmed target -> orient
    assert planner.plan("CONFIRMED", 320.0) == Behavior.ORIENT_TOWARD_TARGET


def test_planner_scans_with_no_target():
    planner = BehaviorPlanner(simulation_mode=True)
    planner.enable()
    assert planner.plan("NO_TARGET", None) == Behavior.SCAN


def test_planner_stops_while_candidate_pending():
    planner = BehaviorPlanner(simulation_mode=True)
    planner.enable()
    assert planner.plan("CANDIDATE", None) == Behavior.STOP


def test_planner_orients_toward_offcenter_target():
    planner = BehaviorPlanner(simulation_mode=True, default_speed=0.4)
    planner.enable()
    planner.plan("CONFIRMED", 640.0)  # far right of a 640px frame
    assert planner.left_speed > 0.0
    assert planner.right_speed < 0.0


def test_simulation_pipeline_runs():
    cfg = Config(simulation_mode=True, telemetry_enabled=False)
    # Should complete without hardware and without raising.
    run(cfg, max_frames=20)
