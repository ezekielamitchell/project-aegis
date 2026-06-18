"""Single-target tracker.

Selects the most salient detection of the target class each frame and exposes
the previous selection so the verification layer can assess geometric stability.
Multi-target tracking is on the roadmap; this keeps a single best target.
"""

from __future__ import annotations

from typing import Optional

from aegis.types import Detection


class Tracker:
    def __init__(self, target_class: str = "person"):
        self.target_class = target_class
        self.previous: Optional[Detection] = None

    def update(self, detections: list[Detection]) -> Optional[Detection]:
        """Pick the highest-confidence target-class detection, if any."""
        candidates = [
            d for d in detections if not self.target_class or d.class_name == self.target_class
        ]
        best = max(candidates, key=lambda d: d.confidence, default=None)
        self.previous = best
        return best

    def reset(self) -> None:
        self.previous = None
