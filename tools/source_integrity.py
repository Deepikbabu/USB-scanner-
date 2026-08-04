"""Reject corrupted Python sources before any backend/service startup."""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", ".git", "__pycache__", ".artifacts", ".scanner_state"}

def check_sources() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in EXCLUDED for part in path.parts):
            continue
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                nul_count = raw.count(b"\x00")
                errors.append(f"{path}: contains {nul_count} NUL byte(s)")
                continue
            ast.parse(raw.decode("utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            errors.append(f"{path}: {exc}")
    return errors

def main() -> int:
    errors = check_sources()
    if errors:
        print("[ERROR] Python source integrity check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("[OK] Python source integrity verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
