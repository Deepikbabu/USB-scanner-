"""Non-interactive, validated quarantine operations for the dashboard IPC."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list", "restore", "delete"))
    parser.add_argument("--index", type=int)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.action == "list":
        try:
            entries = json.loads(Path(changed.QUARANTINE_LOG).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            entries = []
        print(json.dumps(entries or [], default=str))
        return 0
    if not args.index or not args.confirm:
        print(json.dumps({"ok": False, "error": "index and confirmation are required"}))
        return 2
    ok = (changed.restore_from_quarantine(args.index) if args.action == "restore"
          else changed.delete_quarantine_entry(args.index))
    print(json.dumps({"ok": bool(ok), "action": args.action, "index": args.index}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
