"""Temporal verification — the core contribution of AEGIS.

A single detection frame never triggers a behavioral response. A detection must
persist for `required_consecutive_frames` with geometrically stable bounding-box
position before the target is CONFIRMED. Once confirmed, the target stays
confirmed until it is missing for `max_missed_frames`, at which point it is LOST.

State machine:

    NO_TARGET --detect--> CANDIDATE --N stable frames--> CONFIRMED
        ^                     |                              |
        |                  (no detect)                   (missing > max)
        +---------------------+------------------------------> LOST --> NO_TARGET

This suppresses transient false positives (single-frame flickers, unstable
boxes) without adding latency beyond the verification window.
"""

from __future__ import annotations

from typing import Optional

from aegis.types import Detection, DetectionState

FRAME_WIDTH = 640  # reference width for normalizing centroid drift


class TemporalFilter:
    def __init__(
        self,
        required_consecutive_frames: int = 4,
        max_missed_frames: int = 8,
        max_centroid_drift: float = 0.15,
        frame_width: int = FRAME_WIDTH,
    ):
        self.required_consecutive_frames = required_consecutive_frames
        self.max_missed_frames = max_missed_frames
        self.max_centroid_drift = max_centroid_drift
        self.frame_width = frame_width

        self.state = DetectionState.NO_TARGET
        self._consecutive = 0
        self._missed = 0
        self._last: Optional[Detection] = None

        # Session counters for metrics (false positive rate, etc.).
        self.total_detections = 0
        self.unverified_candidates = 0

    def _is_stable(self, current: Detection) -> bool:
        """True if `current` is close enough to the last detection to be the
        same target (bounding-box geometry stability check)."""
        if self._last is None:
            return True
        cx, _ = current.centroid
        lx, _ = self._last.centroid
        drift = abs(cx - lx) / float(self.frame_width)
        return drift <= self.max_centroid_drift

    def update(self, detection: Optional[Detection]) -> DetectionState:
        """Feed one frame's tracked detection (or None) and return the state."""
        if detection is not None:
            self.total_detections += 1

        if detection is None:
            return self._on_no_detection()
        return self._on_detection(detection)

    def _on_detection(self, detection: Detection) -> DetectionState:
        self._missed = 0

        if self.state == DetectionState.CONFIRMED:
            self._last = detection
            return self.state

        if self._is_stable(detection):
            self._consecutive += 1
        else:
            # Unstable geometry — restart the count, this looks like a flicker.
            self._consecutive = 1
            self.unverified_candidates += 1

        self._last = detection

        if self._consecutive >= self.required_consecutive_frames:
            self.state = DetectionState.CONFIRMED
        else:
            if self.state != DetectionState.CANDIDATE:
                self.unverified_candidates += 1
            self.state = DetectionState.CANDIDATE
        return self.state

    def _on_no_detection(self) -> DetectionState:
        if self.state == DetectionState.CONFIRMED:
            self._missed += 1
            if self._missed > self.max_missed_frames:
                self.state = DetectionState.LOST
                self._reset_tracking()
            return self.state

        # Not confirmed and nothing detected: drop any pending candidate.
        self._reset_tracking()
        self.state = DetectionState.NO_TARGET
        return self.state

    def _reset_tracking(self) -> None:
        self._consecutive = 0
        self._missed = 0
        self._last = None

    @property
    def false_positive_rate(self) -> float:
        """Unverified candidates / total detections (0.0 if no detections)."""
        if self.total_detections == 0:
            return 0.0
        return self.unverified_candidates / self.total_detections
