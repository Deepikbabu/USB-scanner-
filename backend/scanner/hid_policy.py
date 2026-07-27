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


def identity_metadata(info: dict[str, Any], interfaces: Sequence[str]) -> dict[str, str]:
    """Return the stable identity fields stored with a trusted HID record."""
    return {
        "identity_fingerprint": device_identity_fingerprint(info, list(interfaces)),
        "identity_quality": identity_quality(info, list(interfaces)),
    }
