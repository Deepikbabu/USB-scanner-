"""Device session and incident lifecycle primitives."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.reports.incident import incident_id


@dataclass(slots=True)
class DeviceSession:
    port: str
    incident_id: str = field(init=False)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    detected_monotonic: float = field(default_factory=time.monotonic)
    connected: bool = True
    blocked: bool = False
    findings: list[str] = field(default_factory=list)
    identities: list[str] = field(default_factory=list)
    re_enumeration_count: int = 0
    blocked_monotonic: float | None = None
    enforcement_latency_ms: float | None = None

    def __post_init__(self) -> None:
        self.incident_id = incident_id(self.port)

    def lock(self, reason: str) -> None:
        self.blocked = True
        self.blocked_monotonic = self.blocked_monotonic or time.monotonic()
        if reason not in self.findings:
            self.findings.append(reason)

    def observe_identity(self, identity: str) -> bool:
        changed = bool(self.identities and self.identities[-1] != identity)
        if identity not in self.identities:
            self.identities.append(identity)
        if changed:
            self.re_enumeration_count += 1
        return changed

    def record_enforcement(self) -> float:
        now = time.monotonic()
        self.enforcement_latency_ms = round(max(0.0, now - self.detected_monotonic) * 1000, 1)
        return self.enforcement_latency_ms

    def disconnect(self) -> None:
        self.connected = False


class LifecycleRegistry:
    """Own sessions by physical port and provide one authoritative state map."""

    def __init__(self) -> None:
        self.sessions: dict[str, DeviceSession] = {}
        self.states: dict[str, str] = {}

    def session(self, port: str) -> DeviceSession:
        return self.sessions.setdefault(port, DeviceSession(port))

    def set_state(self, device_id: str, state: str) -> None:
        self.states[str(device_id)] = str(state)

    def snapshot(self, port: str) -> dict[str, Any]:
        item = self.session(port)
        return {
            "port": item.port, "incident_id": item.incident_id,
            "started_at": item.started_at, "connected": item.connected,
            "blocked": item.blocked, "findings": list(item.findings),
            "identities": list(item.identities),
            "re_enumeration_count": item.re_enumeration_count,
            "enforcement_latency_ms": item.enforcement_latency_ms,
        }
