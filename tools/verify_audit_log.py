#!/usr/bin/env python3
"""Verify the dashboard operator audit ledger hash chain."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from pathlib import Path

DATABASE = Path(os.environ.get(
    "USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"
)) / "dashboard_state.db"


def main():
    with sqlite3.connect(DATABASE) as db:
        rows = db.execute(
            "SELECT timestamp,operator,action,target,reason,outcome,"
            "previous_hash,entry_hash FROM audit_log ORDER BY sequence"
        ).fetchall()
    previous = "GENESIS"
    for index, row in enumerate(rows, 1):
        timestamp, operator, action, target, reason, outcome, linked, digest = row
        if linked != previous:
            raise SystemExit(f"Audit chain broken at entry {index}: previous hash mismatch")
        body = json.dumps({
            "timestamp": timestamp, "operator": operator, "action": action,
            "target": target, "reason": reason, "outcome": outcome,
            "previous_hash": linked,
        }, sort_keys=True, separators=(",", ":"))
        calculated = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if calculated != digest:
            raise SystemExit(f"Audit chain broken at entry {index}: content mismatch")
        previous = digest
    print(f"Audit ledger verified: {len(rows)} entries")


if __name__ == "__main__":
    main()
