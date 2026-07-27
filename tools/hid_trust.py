"""Interactive USBGuard/HID trust administration for Raspberry Pi Linux."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.security.intelligence import (SignedTrustStore, device_identity_fingerprint,
                                            identity_quality,
                                            hardware_fingerprint, interface_fingerprint)
WHITELIST = ROOT / "whitelist.json"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=15)


def parse_devices() -> list[dict[str, object]]:
    result = run("usbguard", "list-devices")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "usbguard list-devices failed")
    devices = []
    for line in result.stdout.splitlines():
        head = re.match(r"\s*(\d+):\s+(\w+).*?\bid\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})", line)
        if not head:
            continue
        interfaces = re.findall(r"\b([0-9a-fA-F]{2}):[0-9a-fA-F*]{2}:[0-9a-fA-F*]{2}\b", line)
        if "03" not in {item.lower() for item in interfaces}:
            continue
        name_match = re.search(r'name\s+"([^"]*)"', line)
        serial_match = re.search(r'serial\s+"([^"]*)"', line)
        port_match = re.search(r'via-port\s+"([^"]*)"', line)
        hash_match = re.search(r'hash\s+"([^"]*)"', line)
        devices.append({
            "usbguard_id": head.group(1), "state": head.group(2).lower(),
            "vid_pid": head.group(3).lower(),
            "name": name_match.group(1) if name_match else "Unknown HID",
            "serial": serial_match.group(1) if serial_match else "",
            "port": port_match.group(1) if port_match else "",
            "hash": hash_match.group(1) if hash_match else "",
            "interfaces": interfaces, "line": line,
        })
    return devices


def load_whitelist() -> dict[str, str]:
    try:
        data = json.loads(WHITELIST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_whitelist(data: dict[str, str]) -> None:
    WHITELIST.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    sudo_uid, sudo_gid = os.environ.get("SUDO_UID"), os.environ.get("SUDO_GID")
    if sudo_uid and sudo_gid:
        os.chown(WHITELIST, int(sudo_uid), int(sudo_gid))


def choose(items: list[dict[str, object]], title: str) -> dict[str, object] | None:
    print(f"\n{title}\n" + "=" * len(title))
    if not items:
        print("No matching HID devices were found.")
        return None
    for index, item in enumerate(items, 1):
        print(f"[{index}] {item['name']}")
        print(f"    State      : {item['state']}")
        print(f"    VID:PID    : {item['vid_pid']}")
        print(f"    Port       : {item['port'] or 'unknown'}")
        print(f"    Serial     : {item['serial'] or 'not provided'}")
        print(f"    Interfaces : {' '.join(item['interfaces'])}")
        print(f"    Hash       : {item['hash'] or 'not provided'}")
    while True:
        value = input("\nSelect a device number, or 0 to cancel: ").strip()
        if value == "0":
            return None
        if value.isdigit() and 1 <= int(value) <= len(items):
            return items[int(value) - 1]
        print("Invalid selection.")


def permanent_allow(device_id: str) -> None:
    result = run("usbguard", "allow-device", "--permanent", device_id)
    if result.returncode:
        result = run("usbguard", "allow-device", device_id, "--permanent")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "USBGuard permanent allow failed")


def authorize_sysfs_port(port: str) -> bool:
    """Re-enable a trusted HID port previously disabled through sysfs."""
    if not port or not re.fullmatch(r"[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?", port):
        return False
    path = Path("/sys/bus/usb/devices") / port / "authorized"
    try:
        if path.exists():
            path.write_text("1", encoding="ascii")
            return True
    except OSError as exc:
        print(f"[WARN] Could not reauthorize sysfs port {port}: {exc}")
    return False


def sysfs_authorized(port: str) -> bool | None:
    """Read the kernel authorization state for a USB port."""
    if not port or not re.fullmatch(r"[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?", port):
        return None
    path = Path("/sys/bus/usb/devices") / port / "authorized"
    try:
        return path.read_text(encoding="ascii").strip() == "1" if path.exists() else None
    except OSError:
        return None


def trust() -> int:
    item = choose(parse_devices(), "HID TRUST MANAGEMENT")
    if not item:
        return 0
    print("\nWARNING: Trusting a HID allows it to send keyboard/mouse input after reboot.")
    confirmation = input(f"Type TRUST to authorize {item['name']!r}: ").strip()
    if confirmation != "TRUST":
        print("Cancelled; device remains unchanged.")
        return 0
    permanent_allow(str(item["usbguard_id"]))
    whitelist = load_whitelist()
    whitelist[str(item["vid_pid"])] = str(item["name"])
    save_whitelist(whitelist)
    info = {"vid": str(item["vid_pid"]).split(":", 1)[0],
            "pid": str(item["vid_pid"]).split(":", 1)[1],
            "serial": item["serial"] or "Unknown", "vendor": "Unknown",
            "model": item["name"], "usbguard_hash": item["hash"]}
    SignedTrustStore().put(f"hid:{item['vid_pid']}", {
        "kind": "hid", "vid_pid": item["vid_pid"], "name": item["name"],
        "hardware_fingerprint": hardware_fingerprint(info, item["interfaces"]),
        "interface_fingerprint": interface_fingerprint(item["interfaces"]),
        "identity_fingerprint": device_identity_fingerprint(info, item["interfaces"]),
        "identity_quality": identity_quality(info, item["interfaces"]),
        "enrolled_at": __import__("datetime").datetime.now().isoformat(),
    })
    print(f"[OK] Trusted HID saved: {item['vid_pid']} {item['name']}")
    print("The device is authorized now and will remain trusted after reboot.")
    return 0


def remove_matching_rules(vid_pid: str) -> None:
    result = run("usbguard", "list-rules")
    for line in result.stdout.splitlines():
        match = re.match(r"\s*(\d+):", line)
        if match and f" id {vid_pid} " in f" {line.lower()} ":
            removed = run("usbguard", "remove-rule", match.group(1))
            if removed.returncode:
                print(f"[WARN] Could not remove USBGuard rule {match.group(1)}: {removed.stderr.strip()}")


def untrust() -> int:
    whitelist = load_whitelist()
    current = {str(item["vid_pid"]): item for item in parse_devices()}
    items = []
    for vid_pid, name in sorted(whitelist.items()):
        item = dict(current.get(vid_pid, {}))
        item.update({"vid_pid": vid_pid, "name": name, "state": item.get("state", "not connected"),
                     "port": item.get("port", ""), "serial": item.get("serial", ""),
                     "interfaces": item.get("interfaces", ["03:*:*"]), "hash": item.get("hash", "")})
        items.append(item)
    item = choose(items, "REMOVE HID TRUST")
    if not item:
        return 0
    if input(f"Type REMOVE to untrust {item['name']!r}: ").strip() != "REMOVE":
        print("Cancelled.")
        return 0
    vid_pid = str(item["vid_pid"])
    whitelist.pop(vid_pid, None)
    save_whitelist(whitelist)
    SignedTrustStore().remove(f"hid:{vid_pid}")
    remove_matching_rules(vid_pid)
    for device in parse_devices():
        if device["vid_pid"] == vid_pid:
            run("usbguard", "block-device", str(device["usbguard_id"]))
    print(f"[OK] Trust removed for {vid_pid}. Connected instances were blocked.")
    return 0


def list_hid() -> int:
    trusted = load_whitelist()
    print("\nUSBGuard HID devices\n====================")
    for item in parse_devices():
        project_trust = "TRUSTED" if item["vid_pid"] in trusted else "UNTRUSTED"
        kernel_state = sysfs_authorized(str(item["port"]))
        kernel_label = "AUTHORIZED" if kernel_state else "BLOCKED" if kernel_state is False else "UNKNOWN"
        print(f"{item['usbguard_id']:>3}  {str(item['state']).upper():<7} {project_trust:<9} "
              f"{item['vid_pid']}  {item['name']}  port={item['port']}  kernel={kernel_label}")
    return 0


def repair() -> int:
    trusted = load_whitelist()
    repaired = 0
    for item in parse_devices():
        if item["vid_pid"] not in trusted:
            continue
        record, status = SignedTrustStore().get(f"hid:{item['vid_pid']}")
        info = {"vid": str(item["vid_pid"]).split(":", 1)[0],
                "pid": str(item["vid_pid"]).split(":", 1)[1],
                "serial": item["serial"] or "Unknown", "vendor": "Unknown",
                "model": item["name"], "usbguard_hash": item["hash"]}
        current_hardware = hardware_fingerprint(info, item["interfaces"])
        current_interfaces = interface_fingerprint(item["interfaces"])
        if (status != "verified" or
                record.get("hardware_fingerprint") != current_hardware or
                record.get("interface_fingerprint") != current_interfaces or
                (record.get("identity_fingerprint") and
                 record.get("identity_fingerprint") != device_identity_fingerprint(info, item["interfaces"]))):
            run("usbguard", "block-device", str(item["usbguard_id"]))
            print(f"[BLOCKED] Trusted HID fingerprint verification failed: {item['vid_pid']}")
            continue
        result = run("usbguard", "allow-device", str(item["usbguard_id"]))
        if result.returncode:
            print(f"[WARN] Could not authorize trusted HID: {result.stderr.strip()}")
            continue
        port = str(item.get("port", ""))
        if port and not authorize_sysfs_port(port):
            print(f"[WARN] USBGuard allowed {item['vid_pid']}, but sysfs port {port} remains unauthorized")
        repaired += 1
        print(f"[OK] Authorized trusted HID: {item['vid_pid']} {item['name']}")
    print(f"Repair complete: {repaired} connected trusted HID device(s) authorized.")
    return 0


def rescan() -> int:
    trusted = load_whitelist()
    items = [item for item in parse_devices() if item["vid_pid"] in trusted]
    item = choose(items, "VERIFY TRUSTED HID FINGERPRINT")
    if not item:
        return 0
    record, status = SignedTrustStore().get(f"hid:{item['vid_pid']}")
    info = {"vid": str(item["vid_pid"]).split(":", 1)[0],
            "pid": str(item["vid_pid"]).split(":", 1)[1],
            "serial": item["serial"] or "Unknown", "vendor": "Unknown",
            "model": item["name"], "usbguard_hash": item["hash"]}
    matches = (status == "verified" and
               record.get("hardware_fingerprint") == hardware_fingerprint(info, item["interfaces"]) and
               record.get("interface_fingerprint") == interface_fingerprint(item["interfaces"]) and
               (not record.get("identity_fingerprint") or
                record.get("identity_fingerprint") == device_identity_fingerprint(info, item["interfaces"])))
    if not matches:
        run("usbguard", "block-device", str(item["usbguard_id"]))
        print("[BLOCKED] Fingerprint changed or signed trust is invalid. Revoke and enroll manually after review.")
        return 1
    print(f"[OK] Trusted HID fingerprint verified: {item['vid_pid']}")
    return 0


def rollback() -> int:
    confirmation = input("Type ROLLBACK to restore the previous trust records: ").strip()
    if confirmation != "ROLLBACK":
        print("Cancelled; trust records were not changed.")
        return 1
    ok = SignedTrustStore().rollback()
    print("[OK] Trust records rolled back." if ok else "[ERROR] No usable trust backup found.")
    return 0 if ok else 1


def main() -> int:
    if os.geteuid() != 0:
        print("Run this command with sudo.", file=sys.stderr)
        return 2
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    actions = {"list": list_hid, "trust": trust, "approve": trust,
               "untrust": untrust, "revoke": untrust,
               "repair": repair, "recover": repair, "rescan": rescan,
               "rollback": rollback}
    if action not in actions:
        print("Usage: hid_trust.py [list|approve|revoke|rescan|repair|recover|rollback]", file=sys.stderr)
        return 2
    return actions[action]()


if __name__ == "__main__":
    raise SystemExit(main())
