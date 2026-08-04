"""In-memory recipient store for the running scanner session."""
from __future__ import annotations
import re
import uuid
_current_recipient: str | None = None
_session_id = uuid.uuid4().hex

def set_session_recipient(email: str) -> bool:
    value = str(email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return False
    global _current_recipient
    _current_recipient = value
    print(f"[SESSION] Recipient set: {value}")
    return True

def get_session_recipient() -> str | None:
    return _current_recipient

def get_session_id() -> str:
    return _session_id

def clear_session_recipient() -> None:
    global _current_recipient
    _current_recipient = None
