"""Sandbox worker protocol.

Reads one JSON request from stdin and emits one JSON response. The controller
must launch this module through ``scan_worker_sandbox``; direct production
execution is intentionally refused unless USB_SCANNER_WORKER_SANDBOXED=1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from backend.database.connection import SQLiteConnectionFactory
from backend.database.malware_repository import MalwareHashRepository
from backend.scanner.file_scanner import FileScanner

def main() -> int:
    if os.environ.get("USB_SCANNER_WORKER_SANDBOXED") != "1":
        print(json.dumps({"ok": False, "complete": False, "error": "sandbox required"}), flush=True)
        return 78
    try:
        request = json.loads(sys.stdin.readline())
        root = Path(str(request["mount_path"])).resolve()
        if not root.is_dir():
            raise ValueError("scan mount is not a directory")
        database = Path(str(request.get("database_path", "/tmp/usb-scanner-worker.db")))
        scanner = FileScanner(MalwareHashRepository(SQLiteConnectionFactory(database)))
        report = scanner.scan_mount_path(str(root))
        findings = [{"path": item.path, "size": item.size, "reason": item.reason,
                     "severity": item.category, "score": item.score_delta}
                    for item in report.high_risk + report.medium_risk]
        print(json.dumps({"ok": True, "complete": True, "files": report.summary.total_files,
                          "risk_score": report.summary.risk_score, "findings": findings},
                         default=str), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "complete": False, "error": str(exc)}), flush=True)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
