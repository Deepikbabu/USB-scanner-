"""Quarantine vault integrity and record helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_records(log_path: str | Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(Path(log_path).read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str | None:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def integrity_matches(path: str | Path, expected: str | None) -> bool:
    return bool(expected) and sha256_file(path) == str(expected).lower()


def entry_at(records: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if index < 1 or index > len(records):
        return None
    return records[index - 1]
