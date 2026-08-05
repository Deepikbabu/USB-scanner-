from __future__ import annotations

import threading

from .email_queue import EmailQueue
from .email_templates import incident_message

_queue: EmailQueue | None = None
_lock = threading.Lock()


def get_queue() -> EmailQueue:
    global _queue
    with _lock:
        if _queue is None:
            _queue = EmailQueue()
        return _queue


def start_email_worker() -> None:
    get_queue().start()

def assign_session_recipient(recipient: str) -> int:
    from .session_state import get_session_id
    return get_queue().assign_recipient(recipient, get_session_id())


def queue_incident_email(incident_id: str, verdict: str,
                         json_report: str | None, pdf_report: str | None) -> bool:
    # A session recipient requested reports for this scan.  Queue clean and
    # trusted reports as well as incidents; the recipient controls delivery,
    # while the report still contains the final verdict.
    if verdict not in {"CLEAN", "TRUSTED", "SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}:
        return False
    subject, body = incident_message(incident_id, verdict, json_report)
    attachments = [value for value in (pdf_report, json_report) if value]
    from .session_state import get_session_recipient
    recipient = get_session_recipient()
    if not recipient:
        print("[EMAIL] No recipient set for this session — report pending recipient")
        return get_queue().enqueue(f"incident:{incident_id}", incident_id, verdict,
                                   subject, body, attachments, recipient=None)
    return get_queue().enqueue(f"incident:{incident_id}", incident_id, verdict,
                               subject, body, attachments, recipient=recipient)


def queue_operational_email(event_key: str, subject: str, body: str) -> bool:
    return get_queue().enqueue(f"operational:{event_key}", event_key, "OPERATIONAL",
                               subject, body, [])
