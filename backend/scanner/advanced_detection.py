"""Content-based detection primitives used by the storage scanner.

All detectors are bounded and return evidence.  They deliberately do not
declare a file malicious on their own; the policy/risk layer decides that.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import mimetypes
import re
import struct
import zipfile
from pathlib import Path
from typing import Any

MAGIC = ((b"MZ", "application/vnd.microsoft.portable-executable"),
         (b"\x7fELF", "application/x-executable"),
         (b"%PDF-", "application/pdf"),
         (b"PK\x03\x04", "application/zip"),
         (b"\xd0\xcf\x11\xe0", "application/vnd.ms-office"))

def detect_mime(data: bytes, name: str = "") -> str:
    for signature, mime in MAGIC:
        if data.startswith(signature):
            return mime
    return mimetypes.guess_type(name)[0] or "application/octet-stream"

def parse_executable(data: bytes) -> dict[str, Any] | None:
    if data.startswith(b"MZ"):
        result: dict[str, Any] = {"format": "PE", "machine": None, "sections": 0}
        if len(data) >= 0x40:
            pe = struct.unpack_from("<I", data, 0x3C)[0]
            if pe + 24 <= len(data) and data[pe:pe + 4] == b"PE\0\0":
                result["machine"], result["sections"] = struct.unpack_from("<HH", data, pe + 4)
                result["has_signature"] = b"WIN_CERTIFICATE" in data
        return result
    if data.startswith(b"\x7fELF") and len(data) >= 20:
        return {"format": "ELF", "class": 32 if data[4] == 1 else 64,
                "endianness": "little" if data[5] == 1 else "big",
                "machine": struct.unpack_from("<H" if data[5] == 1 else ">H", data, 18)[0]}
    return None

def office_macro_evidence(data: bytes) -> list[str]:
    if not (data.startswith(b"PK\x03\x04") or data.startswith(b"\xd0\xcf\x11\xe0")):
        return []
    lower = data.lower()
    return ["VBA macro stream present"] if any(x in lower for x in (b"vba", b"macros", b"vba_project")) else []

def pdf_evidence(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF-"):
        return []
    lower = data[:16 * 1024 * 1024].lower()
    findings = []
    if b"/javascript" in lower or b"/js" in lower:
        findings.append("PDF JavaScript present")
    if b"/embeddedfile" in lower or b"/filespec" in lower:
        findings.append("PDF embedded object present")
    return findings

def archive_evidence(data: bytes, max_entries: int = 10000) -> list[str]:
    if not data.startswith(b"PK\x03\x04"):
        return []
    findings = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()[:max_entries]
            if len(archive.infolist()) > max_entries:
                findings.append("Archive entry limit exceeded")
            expanded = sum(max(0, item.file_size) for item in infos)
            if expanded > 1 * 1024 * 1024 * 1024:
                findings.append("Archive expansion exceeds safety limit")
            if any(Path(item.filename).is_absolute() or ".." in Path(item.filename).parts for item in infos):
                findings.append("Archive contains path traversal entry")
    except (OSError, zipfile.BadZipFile):
        findings.append("Malformed archive")
    return findings

def fuzzy_hash(data: bytes) -> str:
    """Portable similarity seed; optional TLSH/ssdeep can replace this value."""
    return hashlib.sha256(data[:1024 * 1024]).hexdigest()[:32]

def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts if count)

def analyze_content(data: bytes, name: str = "") -> dict[str, Any]:
    executable = parse_executable(data)
    evidence = office_macro_evidence(data) + pdf_evidence(data) + archive_evidence(data)
    return {"mime": detect_mime(data, name), "executable": executable,
            "evidence": evidence, "fuzzy_hash": fuzzy_hash(data),
            "entropy": round(entropy(data), 3)}
