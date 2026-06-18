"""Shared data types used across AEGIS modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DetectionState(str, Enum):
    """States emitted by the temporal verification layer."""

    NO_TARGET = "NO_TARGET"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    LOST = "LOST"


@dataclass(frozen=True)
class Detection:
    """A single bounding-box detection from the perception layer.

    bbox is (x1, y1, x2, y2) in pixel coordinates.
    """

    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)
