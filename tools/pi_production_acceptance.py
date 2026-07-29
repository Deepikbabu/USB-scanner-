#!/usr/bin/env python3
"""Read-only Raspberry Pi production acceptance checks.

Run on the deployed Pi:
    sudo .venv/bin/python3 tools/pi_production_acceptance.py
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOCKET = Path(os.environ.get("USB_SCANNER_SOCKET", "/run/usb-scanner/backend.sock"))
STATE = Path(os.environ.get("USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"))


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def ipc_snapshot():
    if not hasattr(socket, "AF_UNIX") or not SOCKET.exists():
        return False, "Unix socket unavailable"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect(str(SOCKET))
            client.sendall(b'{"protocol":1,"request_id":"acceptance","command":"get_snapshot","data":{}}\n')
            payload = b""
            while b"\n" not in payload:
                payload += client.recv(65536)
        response = json.loads(payload.split(b"\n", 1)[0])
        return response.get("status") == "ok", response.get("data", {})
    except (OSError, ValueError) as exc:
        return False, str(exc)


def main():
    checks = []

    def add(name, ok, detail):
        checks.append((name, bool(ok), str(detail)))

    machine = platform.machine().lower()
    add("Raspberry Pi architecture", machine in {"aarch64", "arm64", "armv7l"}, machine)
    add("Root acceptance session", os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        "root" if hasattr(os, "geteuid") and os.geteuid() == 0 else "run with sudo")
    for binary in ("usbguard", "clamscan", "freshclam", "yara", "findmnt", "lsusb"):
        add(f"Executable · {binary}", bool(shutil.which(binary)), shutil.which(binary) or "missing")
    ok, detail = command("systemctl", "is-active", "usb-scanner.service")
    add("Scanner service active", ok and detail == "active", detail)
    ok, detail = command("systemctl", "is-active", "usbguard")
    add("USBGuard active", ok and detail == "active", detail)
    ok, detail = command("usbguard", "list-devices")
    add("USBGuard responding", ok, detail[:180])
    add("Backend socket permissions", SOCKET.exists() and os.access(SOCKET, os.R_OK | os.W_OK),
        str(SOCKET))
    ok, detail = ipc_snapshot()
    add("IPC authoritative snapshot", ok, "snapshot received" if ok else detail)
    usage = shutil.disk_usage(STATE if STATE.exists() else ROOT)
    free_gib = usage.free / 1024 ** 3
    add("Free evidence storage", free_gib >= 1.0, f"{free_gib:.2f} GiB free")
    display = os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")
    add("Desktop display session", bool(display), display or "not visible to this shell")
    reports = ROOT / "reports"
    quarantine = ROOT / "quarantine"
    add("Reports directory writable", reports.exists() and os.access(reports, os.W_OK), reports)
    add("Quarantine directory protected",
        quarantine.exists() and not bool(quarantine.stat().st_mode & 0o002), quarantine)

    print("USB Scanner · Raspberry Pi production acceptance")
    print("=" * 56)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    failed = [name for name, ok, _ in checks if not ok]
    print(f"\nResult: {len(checks)-len(failed)}/{len(checks)} checks passed")
    if failed:
        print("Failed gates: " + ", ".join(failed))
        return 1
    print("Static production gates passed. Complete the physical USB test matrix next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
