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


def queue_incident_email(incident_id: str, verdict: str,
                         json_report: str | None, pdf_report: str | None) -> bool:
    if verdict not in {"SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}:
        return False
    subject, body = incident_message(incident_id, verdict, json_report)
    attachments = [value for value in (pdf_report, json_report) if value]
    from .session_state import get_session_recipient
    recipient = get_session_recipient()
    if not recipient:
        print("[EMAIL] No recipient set for this session — skipping send")
        return False
    return get_queue().enqueue(f"incident:{incident_id}", incident_id, verdict,
                               subject, body, attachments, recipient=recipient)


def queue_operational_email(event_key: str, subject: str, body: str) -> bool:
    return get_queue().enqueue(f"operational:{event_key}", event_key, "OPERATIONAL",
                               subject, body, [])
