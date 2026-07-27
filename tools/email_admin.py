#!/usr/bin/env python3
from __future__ import annotations

import getpass
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.notifications.email_config import CONFIG_PATH, load_email_config
from backend.notifications.email_queue import EmailQueue
from backend.notifications.email_sender import send_message
from backend.notifications.manager import queue_operational_email


def require_root():
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("Run this command with sudo.")


def safe(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("configuration values cannot contain newlines")
    return value.strip()


def configure() -> None:
    require_root()
    host = safe(input("SMTP host: "))
    port = safe(input("SMTP port [587]: ") or "587")
    username = safe(input("SMTP username/email: "))
    password = safe(getpass.getpass("SMTP password/application password: "))
    sender = safe(input(f"From address [{username}]: ") or username)
    recipients = safe(input("Recipient email(s), comma separated: "))
    ssl = port == "465"
    tls_answer = safe(input("Use STARTTLS? [Y/n]: ") or "y").lower()
    if not host or not sender or not recipients:
        raise SystemExit("SMTP host, sender, and at least one recipient are required.")
    try:
        parsed_port = int(port)
        if not 1 <= parsed_port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("SMTP port must be a number from 1 to 65535.")
    CONFIG_PATH.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    content = "\n".join((
        "EMAIL_ENABLED=true", f"SMTP_HOST={host}", f"SMTP_PORT={port}",
        f"SMTP_USERNAME={username}", f"SMTP_PASSWORD={password}",
        f"EMAIL_FROM={sender}", f"EMAIL_TO={recipients}",
        f"SMTP_TLS={'true' if tls_answer in {'y','yes'} and not ssl else 'false'}",
        f"SMTP_SSL={'true' if ssl else 'false'}", "SMTP_TIMEOUT=15",
        "EMAIL_MAX_ATTACHMENT_MB=10", "",
    ))
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(CONFIG_PATH)
    CONFIG_PATH.chmod(0o600)
    print(f"[OK] Protected email configuration written to {CONFIG_PATH}")


def set_enabled(enabled: bool) -> None:
    require_root()
    try:
        lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise SystemExit("Configure email first with --configure-email.")
    replacement = f"EMAIL_ENABLED={'true' if enabled else 'false'}"
    had_setting = any(line.startswith("EMAIL_ENABLED=") for line in lines)
    lines = [replacement if line.startswith("EMAIL_ENABLED=") else line for line in lines]
    if not had_setting:
        lines.insert(0, replacement)
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CONFIG_PATH.chmod(0o600)
    print(f"[OK] Email notifications {'enabled' if enabled else 'disabled'}.")


def test_email() -> None:
    config = load_email_config()
    if not config.ready:
        raise SystemExit("Email is disabled or incomplete. Run --configure-email first.")
    try:
        send_message(config, "USB Scanner email test",
                     f"Email delivery test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}.")
    except Exception as exc:
        raise SystemExit(f"SMTP test failed: {type(exc).__name__}: {exc}")
    print("[OK] SMTP authentication and test delivery succeeded.")


def status() -> None:
    config = load_email_config()
    print(f"Configuration : {CONFIG_PATH}")
    print(f"File exists   : {CONFIG_PATH.exists()}")
    print(f"Enabled       : {config.enabled}")
    print(f"Ready         : {config.ready}")
    print(f"SMTP          : {config.host or 'not configured'}:{config.port}")
    print(f"Sender        : {config.sender or 'not configured'}")
    print(f"Recipients    : {', '.join(config.recipients) or 'not configured'}")
    print(f"Transport     : {'implicit TLS' if config.ssl else 'STARTTLS' if config.tls else 'plain SMTP'}")
    if not config.enabled:
        print("Action         : run sudo ./run.sh --configure-email")
    elif not config.ready:
        print("Action         : configuration is incomplete; run --configure-email again")
    print("\nRecent deliveries")
    for incident, verdict, state, attempts, updated, error in EmailQueue().status():
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated))
        print(f"{stamp} {state:<9} attempts={attempts} {verdict:<12} {incident}")
        if error:
            print(f"  error: {error}")


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "configure": configure()
    elif action == "test": test_email()
    elif action == "status": status()
    elif action == "enable": set_enabled(True)
    elif action == "disable": set_enabled(False)
    elif action == "retry": print(f"[OK] Queued {EmailQueue().retry_failed()} failed delivery record(s).")
    elif action == "service-failure":
        queue_operational_email(
            f"service-failure-{int(time.time() // 300)}",
            "CRITICAL: USB Scanner service failed",
            "The USB Scanner systemd service entered a failed state. Systemd will attempt recovery. "
            "Review: journalctl -u usb-scanner --since '-10 minutes'",
        )
        print("[OK] Service failure notification queued.")
    else: raise SystemExit("Usage: email_admin.py [configure|test|status|enable|disable|retry]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
