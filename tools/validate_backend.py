#!/usr/bin/env python3
"""Non-destructive backend validation for Raspberry Pi/Linux."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(command):
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=60)
    print(result.stdout, end="")
    if result.returncode:
        print(result.stderr, file=sys.stderr, end="")
        raise RuntimeError(f"validation failed: {' '.join(map(str, command))}")


def main():
    run([sys.executable, "tools/simulate_security_flow.py", "all"])
    from backend.scanner.yara_engine import load_rules, last_load_error
    if not load_rules():
        raise RuntimeError(f"YARA rules failed: {last_load_error()}")
    print("[OK] YARA rules compile")
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    with tempfile.NamedTemporaryFile(suffix=".com") as sample:
        sample.write(eicar); sample.flush()
        result = subprocess.run(["clamscan", "--no-summary", sample.name],
                                text=True, capture_output=True, timeout=30)
        if result.returncode != 1:
            raise RuntimeError(f"ClamAV EICAR detection failed (exit={result.returncode})")
    print("[OK] ClamAV detects EICAR")
    print("[OK] Backend validation suite passed")


if __name__ == "__main__":
    main()
