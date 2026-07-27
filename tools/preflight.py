"""Raspberry Pi/Linux runtime checks performed before the UI starts."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(name: str, ready: bool, detail: str = "") -> bool:
    state = "READY" if ready else "FAILED"
    print(f"{name:<18} {state}{' - ' + detail if detail else ''}")
    return ready


def main() -> int:
    results = []
    results.append(check("Linux", sys.platform.startswith("linux")))
    writable_paths = [
        ("Project reports", ROOT / "reports"),
        ("Quarantine", ROOT / "quarantine"),
        ("IPC runtime", Path("/run/usb-scanner")),
    ]
    for label, path in writable_paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
            results.append(check(label, os.access(path, os.W_OK), str(path)))
        except OSError as exc:
            results.append(check(label, False, f"{path}: {exc}"))
    results.append(check("udev", Path("/sys/bus/usb").exists() and Path("/proc/mounts").exists()))
    results.append(check("Mount tools", bool(shutil.which("mount") and shutil.which("umount"))))
    usbguard = shutil.which("usbguard")
    usbguard_active = False
    if usbguard:
        status = subprocess.run(["systemctl", "is-active", "usbguard"], capture_output=True, text=True)
        usbguard_active = status.returncode == 0
    results.append(check("USBGuard", usbguard_active, "pre-authorization isolation unavailable" if not usbguard_active else ""))
    try:
        import pyudev  # noqa: F401
        results.append(check("pyudev", True))
    except Exception as exc:
        results.append(check("pyudev", False, str(exc)))
    try:
        from backend.scanner.yara_engine import last_load_error, load_rules
        rules = load_rules()
        results.append(check("YARA rules", rules is not None, last_load_error() or ""))
    except Exception as exc:
        results.append(check("YARA rules", False, str(exc)))
    daemon_socket = any(Path(path).exists() for path in (
        "/run/clamav/clamd.ctl", "/var/run/clamav/clamd.ctl", "/run/clamd.scan/clamd.sock"
    ))
    scanner = shutil.which("clamdscan") if daemon_socket else None
    scanner = scanner or shutil.which("clamscan")
    clam_ok = False
    detail = "not installed"
    if scanner:
        try:
            # clamscan reports the engine/database version without depending on
            # a responsive daemon socket.
            version_tool = shutil.which("clamscan") or scanner
            result = subprocess.run([version_tool, "--version"], capture_output=True, text=True, timeout=10)
            clam_ok = result.returncode == 0
            detail = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr) else scanner
        except subprocess.TimeoutExpired:
            clam_ok = False
            detail = "version check timed out"
    results.append(check("ClamAV", clam_ok, detail))
    try:
        from backend.security.intelligence import NVDClient, SignedTrustStore
        trust = SignedTrustStore()
        migrated = trust.migrate_legacy()
        if migrated:
            print(f"Trust migration     READY - upgraded {migrated} legacy record(s)")
        results.append(check("Signed trust", trust.key_path.exists(), str(trust.directory)))
        results.append(check("Trust permissions", trust.key_path.stat().st_mode & 0o077 == 0,
                             "trust key must not be group/world accessible"))
        nvd = NVDClient()
        print(f"NVD enrichment     READY - {'API key configured' if nvd.api_key else 'anonymous/cached mode'}")
    except Exception as exc:
        results.append(check("Intelligence", False, str(exc)))
    try:
        from backend.notifications.email_config import CONFIG_PATH, load_email_config
        email = load_email_config()
        if email.ready:
            print(f"Email notifications READY - {email.host}:{email.port} -> {len(email.recipients)} recipient(s)")
        elif email.enabled:
            print(f"Email notifications FAILED - incomplete configuration in {CONFIG_PATH}")
            results.append(False)
        else:
            print("Email notifications OPTIONAL - disabled")
    except Exception as exc:
        results.append(check("Email", False, str(exc)))
    from db_init import ensure_database
    results.append(check("Malware database", Path(ensure_database()).exists()))
    if os.geteuid() != 0:
        print("Root enforcement   DEGRADED - UI is unprivileged; backend will use sudo")
    else:
        print("Root enforcement   READY")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
