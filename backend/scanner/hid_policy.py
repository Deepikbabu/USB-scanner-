"""Linux HID authorization and identity policy primitives.

This module is intentionally side-effect-limited: callers explicitly request
USBGuard or sysfs changes and receive a boolean result.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from backend.security.intelligence import device_identity_fingerprint, identity_quality


PORT_PATTERN = re.compile(r"[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?")


def authorize_sysfs(port: str, authorized: bool) -> bool:
    """Set and verify kernel USB authorization for a validated port."""
    if not port or not PORT_PATTERN.fullmatch(port):
        return False
    path = Path("/sys/bus/usb/devices") / port / "authorized"
    try:
        if not path.exists():
            return False
        path.write_text("1" if authorized else "0", encoding="ascii")
        return path.read_text(encoding="ascii").strip() == ("1" if authorized else "0")
    except OSError:
        return False


def usbguard_set_state(device_id: str, allow: bool, timeout: float = 10.0) -> bool:
    """Authorize or block one USBGuard instance."""
    if not str(device_id).isdigit():
        return False
    action = "allow-device" if allow else "block-device"
    try:
        result = subprocess.run(
            ["usbguard", action, str(device_id)],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def recover_trusted_hid(trusted_vid_pids: set[str], timeout: float = 3.0) -> list[str]:
    """Allow only trusted keyboard/mouse VID:PID devices after a crash.

    USBGuard output is treated as untrusted text; unknown devices are never
    changed. This is safe to call from service startup/ExecStopPost.
    """
    recovered = []
    try:
        result = subprocess.run(["usbguard", "list-devices"], capture_output=True,
                                text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return recovered
    for line in result.stdout.splitlines():
        match = re.match(r"\s*(\d+):.*? id ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})", line)
        if not match:
            continue
        device_id, vid, pid = match.groups(); key = f"{vid.lower()}:{pid.lower()}"
        if key in {str(v).lower() for v in trusted_vid_pids} and usbguard_set_state(device_id, True):
            recovered.append(device_id)
    return recovered


def identity_metadata(info: dict[str, Any], interfaces: Sequence[str]) -> dict[str, str]:
    """Return the stable identity fields stored with a trusted HID record."""
    return {
        "identity_fingerprint": device_identity_fingerprint(info, list(interfaces)),
        "identity_quality": identity_quality(info, list(interfaces)),
    }
