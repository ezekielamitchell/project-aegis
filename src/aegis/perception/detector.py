"""Object detection wrapper around YOLOv8n (Ultralytics).

In simulation mode, detections are synthesized from the frame's bright region so
the pipeline is exercised end-to-end without loading a model. On hardware, the
Ultralytics model is loaded lazily on first use.
"""

from __future__ import annotations

import logging

from aegis.types import Detection

log = logging.getLogger(__name__)

DEFAULT_MODEL = "yolov8n.pt"


class Detector:
    def __init__(
        self,
        confidence_threshold: float = 0.55,
        target_class: str = "person",
        simulation_mode: bool = True,
        model_path: str = DEFAULT_MODEL,
    ):
        self.confidence_threshold = confidence_threshold
        self.target_class = target_class
        self.simulation_mode = simulation_mode
        self.model_path = model_path
        self._model = None

    def _load_model(self):
        if self._model is None:
            from ultralytics import YOLO  # lazy: heavy import

            log.info("Loading YOLO model: %s", self.model_path)
            self._model = YOLO(self.model_path)
        return self._model

    def detect(self, frame) -> list[Detection]:
        """Run detection on a frame and return detections above threshold."""
        if self.simulation_mode:
            return self._synthetic_detect(frame)
        return self._model_detect(frame)

    def _model_detect(self, frame) -> list[Detection]:
        model = self._load_model()
        results = model(frame, verbose=False)
        detections: list[Detection] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                conf = float(box.conf[0])
                cls_name = names[int(box.cls[0])]
                if conf < self.confidence_threshold:
                    continue
                if self.target_class and cls_name != self.target_class:
                    continue
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                detections.append(
                    Detection(class_name=cls_name, confidence=conf, bbox=(x1, y1, x2, y2))
                )
        return detections

    def _synthetic_detect(self, frame) -> list[Detection]:
        """Derive a detection from the brightest contiguous column region."""
        import numpy as np

        gray = frame.mean(axis=2)
        ys, xs = np.where(gray > 128)
        if xs.size == 0:
            return []
        bbox = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
        return [Detection(class_name=self.target_class, confidence=0.9, bbox=bbox)]
