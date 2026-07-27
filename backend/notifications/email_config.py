from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("USB_SCANNER_EMAIL_CONFIG", "/etc/usb-scanner/email.env"))


def _bool(value: str | None, default=False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool = False
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    recipients: tuple[str, ...] = ()
    tls: bool = True
    ssl: bool = False
    timeout: int = 15
    max_attachment_mb: int = 10

    @property
    def ready(self) -> bool:
        return bool(self.enabled and self.host and self.sender and self.recipients)


def load_email_config(path: Path = CONFIG_PATH) -> EmailConfig:
    values: dict[str, str] = {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    except OSError:
        return EmailConfig()
    try:
        port = int(values.get("SMTP_PORT", "587"))
        timeout = int(values.get("SMTP_TIMEOUT", "15"))
        max_mb = int(values.get("EMAIL_MAX_ATTACHMENT_MB", "10"))
    except ValueError:
        return EmailConfig()
    recipients = tuple(item.strip() for item in values.get("EMAIL_TO", "").split(",") if item.strip())
    return EmailConfig(
        enabled=_bool(values.get("EMAIL_ENABLED")), host=values.get("SMTP_HOST", ""),
        port=port, username=values.get("SMTP_USERNAME", ""),
        password=values.get("SMTP_PASSWORD", ""),
        sender=values.get("EMAIL_FROM", values.get("SMTP_USERNAME", "")),
        recipients=recipients, tls=_bool(values.get("SMTP_TLS"), True),
        ssl=_bool(values.get("SMTP_SSL"), port == 465), timeout=max(5, timeout),
        max_attachment_mb=max(1, max_mb),
    )
