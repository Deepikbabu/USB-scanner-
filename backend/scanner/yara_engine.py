"""YARA rule loading and scan helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yara
except ImportError:  # pragma: no cover - optional dependency
    yara = None


RULES_PATH = Path(__file__).with_name("yara_rules.yar")
_LAST_LOAD_ERROR: str | None = None


@dataclass(slots=True)
class YaraFinding:
    """Single YARA hit returned by the scanner."""

    rule: str
    issue: str
    risk: int
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _safe_meta_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@lru_cache(maxsize=1)
def load_rules():
    """Compile the bundled YARA rules once and cache the result."""
    global _LAST_LOAD_ERROR
    if yara is None or not RULES_PATH.exists():
        _LAST_LOAD_ERROR = "yara-python is unavailable" if yara is None else f"rules file missing: {RULES_PATH}"
        return None
    try:
        rules = yara.compile(filepath=str(RULES_PATH))
        _LAST_LOAD_ERROR = None
        return rules
    except Exception as exc:
        _LAST_LOAD_ERROR = str(exc)
        return None


def last_load_error() -> str | None:
    """Return the most recent compiler/load failure for diagnostics."""
    return _LAST_LOAD_ERROR


def scan_bytes(data: bytes, file_name: str | None = None) -> list[YaraFinding]:
    """Run YARA rules against an in-memory buffer."""
    rules = load_rules()
    if rules is None or not data:
        return []

    try:
        matches = rules.match(data=data)
    except Exception:
        return []

    findings: list[YaraFinding] = []
    for match in matches:
        meta = {key: _safe_meta_value(value) for key, value in getattr(match, "meta", {}).items()}
        severity_raw = meta.get("severity", 5)
        try:
            risk = int(severity_raw)
        except (TypeError, ValueError):
            risk = 5

        description = meta.get("description") or f"YARA rule matched: {match.rule}"
        if file_name:
            issue = f"YARA hit: {match.rule} on {file_name} - {description}"
        else:
            issue = f"YARA hit: {match.rule} - {description}"

        findings.append(
            YaraFinding(
                rule=match.rule,
                issue=issue,
                risk=risk,
                tags=list(getattr(match, "tags", [])),
                meta=meta,
            )
        )

    return findings
