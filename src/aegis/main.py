"""AEGIS main entrypoint — perception-to-action pipeline.

    Camera -> Detector -> Tracker -> TemporalFilter -> BehaviorPlanner -> Motor
                                                              |
                                                          Telemetry

Run with:  python -m aegis.main --config configs/default.yaml
"""

from __future__ import annotations

import argparse
import logging
import signal
import time

from aegis.config import Config
from aegis.control import BehaviorPlanner
from aegis.perception import CameraSource, Detector, Tracker
from aegis.telemetry import MqttClient, SessionLogger
from aegis.verification import TemporalFilter

log = logging.getLogger("aegis")


def build_pipeline(cfg: Config):
    camera = CameraSource(camera_index=cfg.camera_index, simulation_mode=cfg.simulation_mode)
    detector = Detector(
        confidence_threshold=cfg.confidence_threshold,
        target_class=cfg.target_class,
        simulation_mode=cfg.simulation_mode,
    )
    tracker = Tracker(target_class=cfg.target_class)
    verifier = TemporalFilter(
        required_consecutive_frames=cfg.required_consecutive_frames,
        max_missed_frames=cfg.max_missed_frames,
        max_centroid_drift=cfg.max_centroid_drift,
    )
    # The Rust BehaviorPlanner owns its MotorDriver; motion planning + motor
    # output + e-stop all run in the crate.
    planner = BehaviorPlanner(
        simulation_mode=cfg.simulation_mode,
        default_speed=cfg.motor_speed_default,
    )
    return camera, detector, tracker, verifier, planner


def run(cfg: Config, max_frames: int | None = None) -> None:
    camera, detector, tracker, verifier, planner = build_pipeline(cfg)

    mqtt = MqttClient(
        enabled=cfg.mqtt_enabled,
        host=cfg.mqtt_host,
        port=cfg.mqtt_port,
        topic=cfg.mqtt_topic,
    )

    stop_requested = {"flag": False}

    def handle_signal(signum, frame):
        log.warning("signal %d received — requesting shutdown", signum)
        stop_requested["flag"] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    with camera, SessionLogger(log_dir=cfg.log_dir, enabled=cfg.telemetry_enabled) as session:
        mqtt.connect()
        planner.enable()
        try:
            frame_idx = 0
            while not stop_requested["flag"]:
                if max_frames is not None and frame_idx >= max_frames:
                    break

                t0 = time.perf_counter()
                frame = camera.read()
                if frame is None:
                    log.info("no frame — ending run")
                    break

                detections = detector.detect(frame)
                target = tracker.update(detections)
                state = verifier.update(target)
                target_cx = target.centroid[0] if target else None
                behavior = planner.plan(state.value, target_cx)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                record = {
                    "frame": frame_idx,
                    "state": state.value,
                    "behavior": behavior,
                    "n_detections": len(detections),
                    "confidence": round(target.confidence, 3) if target else None,
                    "fp_rate": round(verifier.false_positive_rate, 3),
                    "latency_ms": round(latency_ms, 2),
                }
                session.log("frame", **record)
                mqtt.publish(record)
                if cfg.debug:
                    log.info("%s", record)

                frame_idx += 1
        finally:
            planner.emergency_stop()
            mqtt.disconnect()
            log.info(
                "run complete: %d frames, fp_rate=%.3f",
                frame_idx,
                verifier.false_positive_rate,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS patrol pipeline")
    parser.add_argument("--config", default="configs/default.yaml", help="path to config YAML")
    parser.add_argument(
        "--max-frames", type=int, default=None, help="stop after N frames (useful for sim/testing)"
    )
    args = parser.parse_args()

    cfg = Config.load(args.config)
    logging.basicConfig(
        level=logging.DEBUG if cfg.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("AEGIS starting (simulation_mode=%s)", cfg.simulation_mode)
    run(cfg, max_frames=args.max_frames)


if __name__ == "__main__":
    main()
