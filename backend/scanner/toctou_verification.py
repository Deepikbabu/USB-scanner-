"""Release-time storage manifest verification."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
from typing import Iterable
from backend.scanner.workflow import FileSnapshot, manifest_changed

def snapshot(root: str | Path, hash_files: bool = True) -> list[FileSnapshot]:
    base = Path(root)
    result: list[FileSnapshot] = []
    for path in sorted((p for p in base.rglob("*") if p.is_file()), key=lambda p: str(p)):
        try:
            stat = path.stat()
            digest = None
            if hash_files:
                digest_hash = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest_hash.update(chunk)
                digest = digest_hash.hexdigest()
            result.append(FileSnapshot(str(path.relative_to(base)), stat.st_size, stat.st_mtime_ns, digest))
        except OSError:
            continue
    return result

def unchanged(root: str | Path, expected: Iterable[FileSnapshot]) -> bool:
    return not manifest_changed(list(expected), snapshot(root, hash_files=True))
