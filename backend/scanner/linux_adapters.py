"""Fail-closed Linux adapters for USB isolation and storage handling."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

def usbguard_state(device_id: str, allow: bool, timeout: float = 5.0) -> bool:
    from backend.scanner.hid_policy import usbguard_set_state
    return usbguard_set_state(device_id, allow, timeout=timeout)

def deauthorize_sysfs(port: str, authorized: bool = False) -> bool:
    if os.name == "nt" or not port:
        return False
    target = Path("/sys/bus/usb/devices") / port / "authorized"
    try:
        target.write_text("1" if authorized else "0", encoding="ascii")
        return True
    except OSError:
        return False

def mount_read_only(device_node: str, mount_path: str) -> bool:
    mount = shutil.which("mount")
    if not mount or not device_node or not mount_path:
        return False
    Path(mount_path).mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run([mount, "-o", "ro,nosuid,nodev,noexec", device_node, mount_path],
                                capture_output=True, text=True, timeout=20)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def unmount(mount_path: str) -> bool:
    tool = shutil.which("umount")
    if not tool or not mount_path:
        return False
    try:
        result = subprocess.run([tool, mount_path], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def classify_udev_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Classify capabilities conservatively from udev/interface evidence."""
    text = " ".join(str(value).lower() for value in properties.values())
    capabilities: set[str] = set()
    if "hid" in text or properties.get("ID_INPUT"):
        capabilities.add("hid")
    if properties.get("ID_INPUT_KEYBOARD"):
        capabilities.add("keyboard")
    if properties.get("ID_INPUT_MOUSE"):
        capabilities.add("mouse")
    if properties.get("ID_FS_UUID") or properties.get("DEVTYPE") in {"partition", "disk"}:
        capabilities.add("storage")
    if properties.get("ID_MTP_DEVICE") or properties.get("ID_PTP_DEVICE"):
        capabilities.add("mtp")
    if properties.get("ID_NET_NAME"):
        capabilities.add("network")
    category = "composite" if len(capabilities) > 1 else next(iter(capabilities), "unknown")
    return {"category": category, "capabilities": sorted(capabilities),
            "dangerous_composite": "hid" in capabilities and "storage" in capabilities}
