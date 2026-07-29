#!/usr/bin/env python3
"""Administrative entry point for transactional USB state recovery."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.scanner.usb_state_restore import (
    capture_startup_state, recover_unclean_shutdown, restore_startup_state,
)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "capture":
        result = capture_startup_state()
    elif action == "recover":
        result = recover_unclean_shutdown()
    elif action == "restore":
        result = restore_startup_state()
    else:
        raise SystemExit("Usage: usb_state_admin.py [capture|recover|restore]")
    print(json.dumps(result, indent=2, default=str))
    return 1 if result.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
