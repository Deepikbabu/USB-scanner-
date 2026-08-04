"""Backend composition root; deliberately independent of the PyQt dashboard."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.database.connection import SQLiteConnectionFactory
from backend.services.container import ServiceContainer
from backend.scanner.linux_adapters import deauthorize_sysfs, mount_read_only, unmount
from backend.scanner.toctou_verification import snapshot, unchanged
from backend.scanner.workflow import FileSnapshot, Workflow, WorkflowContext


class BackendApplication:
    """Wire policy orchestration to backend services and OS adapters."""

    def __init__(self, database_path: Path) -> None:
        self.services = ServiceContainer(SQLiteConnectionFactory(database_path))
        self.workflow = Workflow(
            isolate=self._isolate,
            scan=self._scan,
            reverify=self._reverify,
            release=self._release,
            remediate=self._remediate,
        )
        self._mount_path: str | None = None

    def process_storage(self, device: dict[str, Any], mount_path: str,
                        previous_manifest: list[FileSnapshot] | None = None,
                        engines_current: bool = True,
                        decision: str | None = None) -> WorkflowContext:
        self._mount_path = mount_path
        context = WorkflowContext(device=dict(device))
        return self.workflow.run(context, previous_manifest=previous_manifest,
                                 current_manifest=snapshot(mount_path, hash_files=False),
                                 engines_current=engines_current, decision=decision)

    @staticmethod
    def _isolate(device: dict[str, Any]) -> bool:
        port = str(device.get("physical_port") or device.get("port") or "")
        if port and not deauthorize_sysfs(port, authorized=False):
            # USBGuard may already provide isolation; absence of sysfs metadata
            # must not turn a safe, already-blocked device into an exception.
            return bool(device.get("already_isolated"))
        return True

    def _scan(self, device: dict[str, Any], cached: list[FileSnapshot] | None):
        if not self._mount_path:
            return [], [{"severity": "incomplete", "reason": "no isolated mount"}], False
        if cached is not None:
            return cached, [], True
        report = self.services.scan_service.scan_mount_path(self._mount_path)
        files = snapshot(self._mount_path, hash_files=True)
        findings = [{"severity": item.category, "path": item.path,
                     "reason": item.reason, "score": item.score_delta}
                    for item in report.high_risk + report.medium_risk]
        return files, findings, True

    def _reverify(self, device: dict[str, Any], expected: list[FileSnapshot]) -> bool:
        return bool(self._mount_path and unchanged(self._mount_path, expected))

    def _release(self, device: dict[str, Any]) -> bool:
        port = str(device.get("physical_port") or device.get("port") or "")
        if port:
            return deauthorize_sysfs(port, authorized=True)
        return True

    def _remediate(self, device: dict[str, Any], action: str,
                   findings: list[dict[str, Any]]) -> bool:
        # File-level quarantine/delete remains delegated to the existing vault
        # API. The workflow intentionally refuses to mutate files implicitly.
        # Do not claim remediation succeeded until the vault adapter is wired.
        # Returning False keeps the device blocked rather than releasing it.
        return False

    def close(self) -> None:
        if self._mount_path:
            unmount(self._mount_path)
            self._mount_path = None
