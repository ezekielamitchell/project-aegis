"""Camera frame source.

In simulation mode a synthetic frame generator is used so the full pipeline can
run on any machine without a camera. On hardware, OpenCV's VideoCapture is used.
"""

from __future__ import annotations

import logging
from typing import Iterator, Optional

log = logging.getLogger(__name__)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480


class CameraSource:
    """Yields frames as numpy arrays (H, W, 3) in BGR order.

    Acts as a context manager so the capture device is released cleanly.
    """

    def __init__(self, camera_index: int = 0, simulation_mode: bool = True):
        self.camera_index = camera_index
        self.simulation_mode = simulation_mode
        self._capture = None
        self._sim_t = 0

    def __enter__(self) -> "CameraSource":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self) -> None:
        if self.simulation_mode:
            log.info("CameraSource running in simulation mode")
            return
        import cv2  # lazy: only needed on hardware

        self._capture = cv2.VideoCapture(self.camera_index)
        if not self._capture.isOpened():
            raise RuntimeError(f"Could not open camera index {self.camera_index}")
        log.info("CameraSource opened camera index %d", self.camera_index)

    def read(self) -> Optional["object"]:
        """Return a single frame, or None if no frame is available."""
        if self.simulation_mode:
            return self._synthetic_frame()
        if self._capture is None:
            raise RuntimeError("Camera not opened; call open() first")
        ok, frame = self._capture.read()
        return frame if ok else None

    def frames(self) -> Iterator["object"]:
        while True:
            frame = self.read()
            if frame is None:
                break
            yield frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _synthetic_frame(self):
        """Generate a deterministic moving-box frame for simulation/testing."""
        import numpy as np

        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        # A box that drifts horizontally so the tracker/verifier have signal.
        x = 100 + (self._sim_t * 5) % (FRAME_WIDTH - 200)
        frame[180:300, x : x + 80] = 200
        self._sim_t += 1
        return frame
