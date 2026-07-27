"""Read-only USB scanner service health diagnostics."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report(label: str, ok: bool, detail: str = "") -> bool:
    print(f"{label:<22} {'READY' if ok else 'FAILED'}{(' - ' + detail) if detail else ''}")
    return ok


def main() -> int:
    results = []
    if sys.platform.startswith("linux") and shutil.which("systemctl"):
        status = subprocess.run(["systemctl", "is-active", "usb-scanner"], capture_output=True, text=True)
        results.append(report("usb-scanner service", status.returncode == 0, status.stdout.strip() or status.stderr.strip()))
        journal = subprocess.run(["journalctl", "-u", "usb-scanner", "-n", "5", "--no-pager"], capture_output=True, text=True)
        print("\nRecent service log:")
        print(journal.stdout.strip() or journal.stderr.strip() or "(no entries)")
    else:
        results.append(report("systemd", False, "Linux systemd is unavailable"))
    paths = [("IPC socket", Path("/run/usb-scanner/backend.sock")),
             ("Reports", ROOT / "reports"), ("Quarantine", ROOT / "quarantine")]
    for label, path in paths:
        results.append(report(label, path.exists(), str(path)))
    results.append(report("Project root", os.access(ROOT, os.R_OK), str(ROOT)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
