from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .email_config import EmailConfig


def send_message(config: EmailConfig, subject: str, body: str,
                 attachments: list[str] | None = None) -> None:
    if not config.ready:
        raise RuntimeError("email is disabled or configuration is incomplete")
    message = EmailMessage()
    message["Subject"], message["From"] = subject, config.sender
    message["To"] = ", ".join(config.recipients)
    message.set_content(body)
    limit = config.max_attachment_mb * 1024 * 1024
    for value in attachments or []:
        path = Path(value)
        if not path.is_file() or path.stat().st_size > limit:
            continue
        mime, _ = mimetypes.guess_type(path.name)
        main, sub = (mime or "application/octet-stream").split("/", 1)
        message.add_attachment(path.read_bytes(), maintype=main, subtype=sub, filename=path.name)
    server_cls = smtplib.SMTP_SSL if config.ssl else smtplib.SMTP
    with server_cls(config.host, config.port, timeout=config.timeout) as server:
        if config.tls and not config.ssl:
            server.starttls()
        if config.username:
            server.login(config.username, config.password)
        server.send_message(message)
