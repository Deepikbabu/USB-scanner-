from __future__ import annotations

import json
import hashlib
import os
import sqlite3
import threading
import time
from pathlib import Path

from .email_config import load_email_config
from .email_sender import send_message

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(os.environ.get("USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"))
FALLBACK = ROOT / ".scanner_state"
RETRY_DELAYS = (10, 30, 120, 600)


class EmailQueue:
    def __init__(self) -> None:
        try:
            STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.state = STATE
        except OSError:
            FALLBACK.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.state = FALLBACK
        self.db = self.state / "email_delivery.db"
        self.spool = self.state / "email-spool"
        self.spool.mkdir(mode=0o700, exist_ok=True)
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS delivery (
                delivery_key TEXT PRIMARY KEY, incident_id TEXT, verdict TEXT,
                status TEXT, attempts INTEGER, next_attempt REAL, created REAL,
                updated REAL, last_error TEXT, spool_path TEXT)""")
        if os.name != "nt":
            self.db.chmod(0o600)

    def _connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def enqueue(self, delivery_key: str, incident_id: str, verdict: str,
                subject: str, body: str, attachments: list[str] | None = None) -> bool:
        config = load_email_config()
        if not config.enabled:
            return False
        if not config.ready:
            raise RuntimeError("email is enabled but SMTP host, sender, or recipients are incomplete")
        now = time.time()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT status FROM delivery WHERE delivery_key=?", (delivery_key,)).fetchone()
            if existing and existing[0] in {"QUEUED", "RETRYING", "SENT"}:
                return False
            recent = connection.execute(
                "SELECT COUNT(*) FROM delivery WHERE created>=?", (now - 600,)).fetchone()[0]
            if recent >= 10:
                return False
            spool_name = hashlib.sha256(delivery_key.encode()).hexdigest() + ".json"
            spool_path = self.spool / spool_name
            temporary = spool_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"subject": subject, "body": body,
                                             "attachments": attachments or [],
                                             "recipients": list(config.recipients)}), encoding="utf-8")
            if os.name != "nt":
                temporary.chmod(0o600)
            temporary.replace(spool_path)
            connection.execute("REPLACE INTO delivery VALUES (?,?,?,?,?,?,?,?,?,?)", (
                delivery_key, incident_id, verdict, "QUEUED", 0, now, now, now, "", str(spool_path)))
        self.start()
        return True

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, name="email-delivery", daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while not self._stop.wait(2):
            config = load_email_config()
            if not config.ready:
                continue
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT delivery_key,attempts,spool_path FROM delivery "
                    "WHERE status IN ('QUEUED','RETRYING') AND next_attempt<=? "
                    "ORDER BY created LIMIT 1", (time.time(),)).fetchone()
            if not row:
                continue
            key, attempts, spool_path = row
            try:
                payload = json.loads(Path(spool_path).read_text(encoding="utf-8"))
                send_message(config, payload["subject"], payload["body"], payload.get("attachments"),
                             payload.get("recipients"))
                self._set_result(key, "SENT", attempts + 1, 0, "")
                Path(spool_path).unlink(missing_ok=True)
            except Exception as exc:
                attempts += 1
                if attempts > len(RETRY_DELAYS):
                    self._set_result(key, "FAILED", attempts, 0, str(exc))
                else:
                    self._set_result(key, "RETRYING", attempts,
                                     time.time() + RETRY_DELAYS[attempts - 1], str(exc))

    def _set_result(self, key, status, attempts, next_attempt, error):
        with self._connect() as connection:
            connection.execute("UPDATE delivery SET status=?,attempts=?,next_attempt=?,updated=?,last_error=? "
                               "WHERE delivery_key=?",
                               (status, attempts, next_attempt, time.time(), error[:1000], key))
            row = connection.execute("SELECT incident_id,verdict FROM delivery WHERE delivery_key=?", (key,)).fetchone()
        if row:
            try:
                from backend.ipc import publish_event
                publish_event("email_delivery_updated", {
                    "status": status, "attempts": attempts, "error": error[:1000],
                    "verdict": row[1],
                }, row[0])
            except Exception:
                pass

    def retry_failed(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("UPDATE delivery SET status='QUEUED',attempts=0,next_attempt=?,last_error='' "
                                        "WHERE status='FAILED'", (time.time(),))
            count = cursor.rowcount
        self.start()
        return count

    def status(self) -> list[tuple]:
        with self._connect() as connection:
            return connection.execute("SELECT incident_id,verdict,status,attempts,updated,last_error "
                                      "FROM delivery ORDER BY created DESC LIMIT 50").fetchall()
