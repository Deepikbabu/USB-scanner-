"""Backend-only USB workflow state machine.

Hardware adapters are injected so this orchestration can be tested without a
real USB device or dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time
from typing import Any, Callable, Iterable


class DeviceState(str, Enum):
    DETECTED = "DETECTED"
    ISOLATED = "ISOLATED"
    CLASSIFIED = "CLASSIFIED"
    SCANNING = "SCANNING"
    AWAITING_DECISION = "AWAITING_DECISION"
    REMEDIATING = "REMEDIATING"
    REVERIFYING = "REVERIFYING"
    RELEASED = "RELEASED"
    BLOCKED = "BLOCKED"
    INCOMPLETE = "INCOMPLETE"


class Verdict(str, Enum):
    CLEAN = "CLEAN"
    TRUSTED = "TRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    DANGEROUS = "DANGEROUS"
    INCOMPLETE = "INCOMPLETE"


@dataclass(slots=True)
class FileSnapshot:
    relative_path: str
    size: int
    mtime_ns: int
    sha256: str | None = None


@dataclass(slots=True)
class WorkflowContext:
    device: dict[str, Any]
    state: DeviceState = DeviceState.DETECTED
    verdict: Verdict | None = None
    files: list[FileSnapshot] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    incident_id: str = ""
    reason: str = ""
    started_at: float = field(default_factory=time.time)


def manifest_changed(before: Iterable[FileSnapshot], after: Iterable[FileSnapshot]) -> bool:
    def key(item: FileSnapshot) -> tuple[Any, ...]:
        return (item.relative_path, item.size, item.mtime_ns, item.sha256)
    return sorted(map(key, before)) != sorted(map(key, after))


def classify_device(device: dict[str, Any]) -> str:
    capabilities = {str(value).lower() for value in device.get("capabilities", [])}
    if not capabilities:
        if device.get("hid"):
            capabilities.add("hid")
        if device.get("storage"):
            capabilities.add("storage")
    if "hid" in capabilities and "storage" in capabilities:
        return "composite_hid_storage"
    if "hid" in capabilities:
        return "hid"
    if "storage" in capabilities:
        return "storage"
    return "unsupported"


class Workflow:
    """Run policy decisions while delegating OS operations to callbacks."""

    def __init__(self, *, isolate: Callable[[dict[str, Any]], bool],
                 scan: Callable[[dict[str, Any], list[FileSnapshot] | None], tuple[list[FileSnapshot], list[dict[str, Any]], bool]],
                 reverify: Callable[[dict[str, Any], list[FileSnapshot]], bool],
                 release: Callable[[dict[str, Any]], bool],
                 remediate: Callable[[dict[str, Any], str, list[dict[str, Any]]], bool] | None = None):
        self.isolate = isolate
        self.scan = scan
        self.reverify = reverify
        self.release = release
        self.remediate = remediate

    def run(self, context: WorkflowContext, *, trusted: bool = False,
            previous_manifest: list[FileSnapshot] | None = None,
            current_manifest: list[FileSnapshot] | None = None,
            engines_current: bool = True,
            decision: str | None = None) -> WorkflowContext:
        if not self.isolate(context.device):
            return self._fail(context, "isolation_failed")
        context.state = DeviceState.ISOLATED
        category = classify_device(context.device)
        context.device["category"] = category
        context.state = DeviceState.CLASSIFIED
        if category == "unsupported":
            return self._fail(context, "unsupported_device")
        if category == "hid":
            return self._fail(context, "hid_requires_dedicated_authorization")
        if category == "composite_hid_storage":
            context.findings.append({"severity": "medium", "reason": "HID+storage composite"})
        reusable = bool(previous_manifest and current_manifest and
                        not manifest_changed(previous_manifest, current_manifest) and engines_current)
        context.state = DeviceState.SCANNING
        files, findings, complete = self.scan(context.device, current_manifest if reusable else None)
        context.files, context.findings = files, context.findings + findings
        if not complete or not engines_current:
            return self._fail(context, "scan_incomplete_or_engines_stale")
        dangerous = any(str(item.get("severity", "")).lower() in {"high", "dangerous", "malware"}
                        for item in context.findings)
        suspicious = bool(context.findings) or category == "composite_hid_storage"
        context.verdict = Verdict.DANGEROUS if dangerous else Verdict.SUSPICIOUS if suspicious else Verdict.TRUSTED if trusted else Verdict.CLEAN
        if context.verdict in {Verdict.DANGEROUS, Verdict.SUSPICIOUS}:
            context.state = DeviceState.AWAITING_DECISION
            if decision not in {"quarantine", "delete", "block"} or self.remediate is None:
                return self._fail(context, "operator_decision_required")
            if decision == "block":
                return self._fail(context, "operator_kept_blocked")
            context.state = DeviceState.REMEDIATING
            if not self.remediate(context.device, decision, context.findings):
                return self._fail(context, "remediation_failed")
            files, findings, complete = self.scan(context.device, None)
            context.files, context.findings = files, findings
            if not complete:
                return self._fail(context, "post_remediation_scan_incomplete")
        context.state = DeviceState.REVERIFYING
        if not self.reverify(context.device, context.files):
            return self._fail(context, "content_or_identity_changed")
        if not self.release(context.device):
            return self._fail(context, "release_failed")
        context.state = DeviceState.RELEASED
        context.verdict = Verdict.TRUSTED if trusted else Verdict.CLEAN
        return context

    @staticmethod
    def _fail(context: WorkflowContext, reason: str) -> WorkflowContext:
        context.reason = reason
        context.state = DeviceState.INCOMPLETE if reason.startswith(("scan_", "content_", "release_")) else DeviceState.BLOCKED
        if context.verdict is None or context.state == DeviceState.INCOMPLETE:
            context.verdict = Verdict.INCOMPLETE
        return context
