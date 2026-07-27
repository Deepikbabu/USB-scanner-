"""List or remove trusted storage fingerprints."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.security.intelligence import SignedTrustStore

path = ROOT / "storage_whitelist.json"
try:
    records = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    records = {}

action = sys.argv[1] if len(sys.argv) >= 2 else "list"
if action == "list":
    print("Trusted storage fingerprints")
    print("============================")
    for index, (vid_pid, record) in enumerate(sorted(records.items()), 1):
        print(f"[{index}] {vid_pid} {record.get('label', '')}")
        print(f"    Serial      : {record.get('serial', 'Unknown')}")
        print(f"    Fingerprint : {record.get('fingerprint', 'missing')}")
        print(f"    Trusted at  : {record.get('trusted_at', 'unknown')}")
    if not records:
        print("No trusted storage devices.")
elif action in {"forget", "revoke", "rescan"}:
    keys = list(sorted(records))
    for index, key in enumerate(keys, 1):
        print(f"[{index}] {key} {records[key].get('label', '')}")
    choice = input(f"Select a record to {action}, or 0 to cancel: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        key = keys[int(choice) - 1]
        record = records[key]
        identity = f"storage:{key}:{record.get('serial', 'Unknown')}"
        if action == "rescan":
            record["force_rescan"] = True
            path.write_text(json.dumps(records, indent=4) + "\n", encoding="utf-8")
            SignedTrustStore().put(identity, record)
            print(f"[OK] Full rescan required on next connection: {key}")
        else:
            records.pop(key)
            path.write_text(json.dumps(records, indent=4) + "\n", encoding="utf-8")
            SignedTrustStore().remove(identity)
            print(f"[OK] Storage trust removed: {key}")
    else:
        print("Cancelled.")
elif action == "approve":
    print("Storage approval is performed only after a complete clean scan.")
    print("Connect the device, run the scanner, and choose STORE when prompted.")
else:
    raise SystemExit("Usage: storage_trust.py [list|approve|revoke|rescan]")
