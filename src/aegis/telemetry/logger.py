"""Session logger — writes newline-delimited JSON records to disk.

Each record is one event (a frame's outcome, a state transition, or a metrics
snapshot). JSONL keeps logs append-only and easy to analyze post-mission.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

log = logging.getLogger(__name__)


class SessionLogger:
    def __init__(self, log_dir: str = "data", enabled: bool = True):
        self.enabled = enabled
        self.log_dir = log_dir
        self._fh = None
        self.path: Optional[str] = None

    def __enter__(self) -> "SessionLogger":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self) -> None:
        if not self.enabled:
            return
        os.makedirs(self.log_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(self.log_dir, f"session_{stamp}.jsonl")
        self._fh = open(self.path, "a")
        log.info("logging session to %s", self.path)

    def log(self, event: str, **fields: Any) -> None:
        if not self.enabled or self._fh is None:
            return
        record = {"ts": time.time(), "event": event, **fields}
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
