"""Backend-only validation for destructive remediation decisions."""
from __future__ import annotations

import hashlib
import hmac
import os
import time

ALLOWED_ACTIONS = frozenset({"quarantine", "delete", "block", "cancel"})

def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def validate_action(action: str, *, expected_action: str | None = None,
                    token: str | None = None, expected_token: str | None = None,
                    expires_at: float | None = None, path: str | None = None,
                    expected_sha256: str | None = None,
                    typed_confirmation: str | None = None) -> tuple[bool, str]:
    if action not in ALLOWED_ACTIONS:
        return False, "unsupported_action"
    if expected_action and action != expected_action:
        return False, "action_mismatch"
    if expires_at is not None and time.time() > expires_at:
        return False, "action_expired"
    if expected_token and not token or expected_token and not hmac.compare_digest(str(token), str(expected_token)):
        return False, "invalid_confirmation_token"
    if action == "delete" and typed_confirmation != "DELETE":
        return False, "typed_confirmation_required"
    if path and expected_sha256:
        try:
            if not hmac.compare_digest(sha256_file(path), expected_sha256):
                return False, "file_changed"
        except OSError:
            return False, "file_unavailable"
    return True, "ok"
