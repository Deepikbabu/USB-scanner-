"""Structured, single-line JSON observability for scanner operations."""
from __future__ import annotations
import json
import logging
import time
from typing import Any

logger = logging.getLogger("usb_scanner")

def event(name: str, **fields: Any) -> None:
    payload = {"ts": time.time(), "event": name, **fields}
    logger.info(json.dumps(payload, sort_keys=True, default=str))

class Timer:
    def __init__(self, name: str, **fields: Any):
        self.name, self.fields, self.started = name, fields, time.monotonic()
    def finish(self, **fields: Any) -> float:
        duration = time.monotonic() - self.started
        event(self.name, duration_seconds=round(duration, 6), **self.fields, **fields)
        return duration
