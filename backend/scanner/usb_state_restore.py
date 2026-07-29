"""Transactional restoration of pre-existing trusted USB input state.

This module never enables arbitrary ports. It restores only HID instances that
were working before scanner enforcement or that still match a signed trust
record, and it preserves explicitly dangerous physical-port sessions.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from backend.scanner.hid_policy import authorize_sysfs, usbguard_set_state
from backend.security.intelligence import (
    SignedTrustStore, device_identity_fingerprint, hardware_fingerprint,
    interface_fingerprint,
)

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = Path(os.environ.get("USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"))
FALLBACK_ROOT = ROOT / ".scanner_state"


def state_path() -> Path:
    try:
        STATE_ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
        return STATE_ROOT / "usb_startup_state.json"
    except OSError:
        FALLBACK_ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
        return FALLBACK_ROOT / "usb_startup_state.json"


def _list_devices(timeout=5.0) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["usbguard", "list-devices"], capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    devices = []
    for line in result.stdout.splitlines():
        head = re.match(
            r'\s*(\d+):\s*(\w+).*?\bid\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})',
            line,
        )
        if not head:
            continue
        interfaces = re.findall(
            r"\b([0-9a-fA-F]{2}):[0-9a-fA-F*]{2}:[0-9a-fA-F*]{2}\b", line
        )
        field = lambda name: (
            re.search(rf'\b{name}\s+"([^"]*)"', line).group(1)
            if re.search(rf'\b{name}\s+"([^"]*)"', line) else ""
        )
        device_id, state, vid, pid = head.groups()
        devices.append({
            "usbguard_id": device_id, "state": state.lower(),
            "vid": vid.lower(), "pid": pid.lower(),
            "vid_pid": f"{vid.lower()}:{pid.lower()}",
            "serial": field("serial"), "name": field("name"),
            "port": field("via-port"), "hash": field("hash"),
            "interfaces": sorted(value.lower() for value in interfaces),
        })
    return devices


def _sysfs_authorized(port: str) -> bool | None:
    if not re.fullmatch(r"[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?", str(port or "")):
        return None
    path = Path("/sys/bus/usb/devices") / str(port) / "authorized"
    try:
        return path.read_text(encoding="ascii").strip() == "1" if path.exists() else None
    except OSError:
        return None


def capture_startup_state() -> dict[str, Any]:
    """Persist the HID state before scanner-specific enforcement begins."""
    entries = []
    for device in _list_devices():
        if "03" not in device["interfaces"]:
            continue
        device["sysfs_authorized"] = _sysfs_authorized(device["port"])
        device["was_working"] = (
            device["state"] in {"allow", "allowed"}
            and device["sysfs_authorized"] is not False
        )
        entries.append(device)
    payload = {
        "schema": 1, "captured_at": time.time(), "clean_shutdown": False,
        "hid_devices": entries,
    }
    target = state_path()
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    if os.name != "nt":
        target.chmod(0o600)
    return payload


def _same_device(saved: dict[str, Any], current: dict[str, Any]) -> bool:
    if saved.get("vid_pid") != current.get("vid_pid"):
        return False
    saved_serial = str(saved.get("serial") or "")
    current_serial = str(current.get("serial") or "")
    if saved_serial and current_serial and saved_serial != current_serial:
        return False
    saved_hash = str(saved.get("hash") or "")
    current_hash = str(current.get("hash") or "")
    if saved_hash and current_hash and saved_hash != current_hash:
        return False
    return sorted(saved.get("interfaces") or []) == sorted(current.get("interfaces") or [])


def _signed_trust_verified(device: dict[str, Any]) -> bool:
    record, status = SignedTrustStore().get(f"hid:{device.get('vid_pid')}")
    if status != "verified" or not record:
        return False
    info = {
        "vid": device.get("vid"), "pid": device.get("pid"),
        "serial": device.get("serial") or "Unknown", "vendor": "Unknown",
        "model": device.get("name") or "USB HID", "usbguard_hash": device.get("hash"),
    }
    interfaces = device.get("interfaces") or []
    return bool(
        record.get("hardware_fingerprint") == hardware_fingerprint(info, interfaces)
        and record.get("interface_fingerprint") == interface_fingerprint(interfaces)
        and (
            not record.get("identity_fingerprint")
            or record.get("identity_fingerprint")
            == device_identity_fingerprint(info, interfaces)
        )
    )


def restore_startup_state(preserve_blocked_ports=None) -> dict[str, Any]:
    """Restore eligible HID devices and mark the transaction clean."""
    preserve = {str(value) for value in (preserve_blocked_ports or []) if value}
    target = state_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {"hid_devices": []}
    saved_entries = list(payload.get("hid_devices") or [])
    restored, preserved, failed = [], [], []
    for current in _list_devices():
        if "03" not in current["interfaces"]:
            continue
        if current.get("port") in preserve:
            preserved.append(current.get("vid_pid"))
            continue
        saved = next(
            (entry for entry in saved_entries if entry.get("was_working")
             and _same_device(entry, current)), None
        )
        eligible = bool(saved) or _signed_trust_verified(current)
        if not eligible:
            preserved.append(current.get("vid_pid"))
            continue
        guard_ok = usbguard_set_state(str(current["usbguard_id"]), True)
        sysfs_ok = (
            authorize_sysfs(str(current["port"]), True)
            if current.get("port") else True
        )
        if guard_ok and sysfs_ok:
            restored.append(current.get("vid_pid"))
        else:
            failed.append(current.get("vid_pid"))
    payload.update({
        "clean_shutdown": True, "restored_at": time.time(),
        "restored": restored, "preserved_blocked": preserved, "failed": failed,
    })
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"restored": restored, "preserved_blocked": preserved, "failed": failed}


def recover_unclean_shutdown() -> dict[str, Any]:
    """Restore safe HID state left by a previous interrupted service run."""
    target = state_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"restored": [], "preserved_blocked": [], "failed": []}
    if payload.get("clean_shutdown") is False:
        return restore_startup_state()
    return {"restored": [], "preserved_blocked": [], "failed": []}
