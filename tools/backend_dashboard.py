"""Minimal backend-only status dashboard.

This intentionally has no USB or filesystem authority. It only displays
newline-delimited backend events and asks the existing backend for a snapshot.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QLineEdit, QMainWindow, QProgressBar, QTextEdit, QWidget, QPushButton, QMessageBox

# Production socket path is fixed for normal dashboard use. Custom socket
# overrides are intentionally not required to launch the dashboard.
SOCKET = "/run/usb-scanner/backend.sock"

class Client(QObject):
    message = pyqtSignal(dict)
    connection = pyqtSignal(str)
    def __init__(self):
        super().__init__(); self.running = True; self.sock = None
    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
    def command(self, command, data):
        if not self.sock: return False
        try:
            self.sock.sendall((json.dumps({"protocol": 1, "command": command,
                                           "request_id": "dashboard-action", "data": data}) + "\n").encode())
            return True
        except OSError:
            return False
    def submit_decision(self, action_id, decision, token):
        return self.command("submit_decision", {"action_id": action_id,
                                                   "decision": decision,
                                                   "confirmation_token": token})
    def _run(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(SOCKET); self.sock = sock
                self.connection.emit("ONLINE")
                sock.sendall((json.dumps({"protocol": 1, "command": "get_snapshot",
                                           "request_id": "dashboard"}) + "\n").encode())
                buffer = b""
                while self.running:
                    chunk = sock.recv(65536)
                    if not chunk: break
                    buffer += chunk
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        try: self.message.emit(json.loads(raw.decode()))
                        except (UnicodeDecodeError, json.JSONDecodeError): pass
            except OSError as exc:
                self.connection.emit(f"OFFLINE: {exc}")
            finally:
                if self.sock:
                    try: self.sock.close()
                    except OSError: pass
                self.sock = None
            time.sleep(2)

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("USB Scanner Backend Status"); self.resize(820, 560)
        root = QWidget(); grid = QGridLayout(root); self.setCentralWidget(root)
        self.values = {}
        fields = ["connection", "state", "device", "fingerprint", "files", "scanned",
                  "failed", "skipped", "coverage", "verdict", "email"]
        for row, field in enumerate(fields):
            grid.addWidget(QLabel(field.replace("_", " ").title() + ":"), row, 0)
            value = QLabel("-"); value.setTextInteractionFlags(value.textInteractionFlags())
            self.values[field] = value; grid.addWidget(value, row, 1)
        self.progress = QProgressBar(); grid.addWidget(self.progress, 11, 0, 1, 2)
        self.email_input = QLineEdit(); self.email_input.setPlaceholderText("Notification email address")
        self.email_save = QPushButton("Use email for this session")
        self.email_save.clicked.connect(self.save_email)
        grid.addWidget(self.email_input, 12, 0); grid.addWidget(self.email_save, 12, 1)
        self.pdf = QPushButton("PDF report unavailable"); self.pdf.setEnabled(False)
        self.json = QPushButton("JSON report unavailable"); self.json.setEnabled(False)
        self.pdf.clicked.connect(lambda: self.open_report(self.pdf.property("path")))
        self.json.clicked.connect(lambda: self.open_report(self.json.property("path")))
        grid.addWidget(self.pdf, 13, 0); grid.addWidget(self.json, 13, 1)
        self.log = QTextEdit(); self.log.setReadOnly(True); grid.addWidget(self.log, 14, 0, 1, 2)
        self.client = Client(); self.client.message.connect(self.apply); self.client.connection.connect(self.set_connection)
        self.client.start()
    def set_connection(self, state): self.values["connection"].setText(state)
    def save_email(self):
        address = self.email_input.text().strip()
        if self.client.command("set_email_recipient", {"email": address}):
            self.log.append(f"Email recipient submitted to backend: {address}")
        else:
            self.log.append("Email recipient could not be submitted: backend offline")
    def apply_normalized(self, payload):
        if not isinstance(payload, dict): return
        report = payload.get("report") if isinstance(payload.get("report"), dict) else payload
        if report is not payload:
            payload = {**payload, **report}
        coverage = payload.get("scan_coverage") if isinstance(payload.get("scan_coverage"), dict) else payload
        aliases = {
            "files": ("files_discovered", "total_files", "files"),
            "scanned": ("files_scanned", "processed_files", "fully_scanned_files"),
            "failed": ("files_failed", "failed_files", "timed_out_files"),
            "skipped": ("files_skipped", "skipped_files"),
        }
        for field, names in aliases.items():
            for name in names:
                if name in coverage:
                    self.values[field].setText(str(coverage[name])); break
        # Some backend events use ``total``/``processed`` and some use the
        # explicit names above.  Accept both so the dashboard remains a view
        # of the backend rather than depending on one event version.
        fallback_aliases = {
            "files": ("total", "count"),
            "scanned": ("processed", "scanned"),
            "failed": ("failed",),
            "skipped": ("skipped",),
        }
        for field, names in fallback_aliases.items():
            if self.values[field].text() == "-":
                for name in names:
                    if name in coverage:
                        self.values[field].setText(str(coverage[name])); break
        complete = coverage.get("scan_complete")
        if complete is None and "incomplete" in coverage:
            complete = not bool(coverage.get("incomplete"))
        if complete is not None:
            self.values["coverage"].setText("COMPLETE" if complete else "INCOMPLETE")
        elif coverage.get("total_files", coverage.get("total")) is not None:
            total = int(coverage.get("total_files", coverage.get("total")) or 0)
            scanned = int(coverage.get("processed_files", coverage.get("processed", coverage.get("fully_scanned_files", 0))) or 0)
            self.values["coverage"].setText(f"{(scanned / total * 100):.1f}%" if total else "100%")
        verdict = payload.get("verdict")
        if verdict: self.values["verdict"].setText(str(verdict))
        email = payload.get("email_status")
        if isinstance(email, dict):
            self.values["email"].setText(str(email.get("status") or ("READY" if email.get("ready") else "NOT CONFIGURED")))
        elif email: self.values["email"].setText(str(email))
        elif payload.get("status") and (payload.get("recipient") or payload.get("email")):
            self.values["email"].setText(str(payload.get("status")))
        for button, key, label in ((self.pdf, "pdf_path", "Open PDF report"),
                                   (self.json, "json_path", "Open JSON report")):
            path = payload.get(key)
            if path:
                button.setProperty("path", path); button.setText(label); button.setEnabled(True)
    @staticmethod
    def open_report(path):
        if path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def apply(self, message):
        data = message.get("data", message)
        if message.get("event") == "user_action_required":
            self.show_action(message.get("data", {}) or {})
            return
        if message.get("event"):
            event = message.get("event"); payload = message.get("data", {}) or {}
            self.log.append(f"{event}: {json.dumps(payload, default=str)}")
            if event == "device_state": self.values["state"].setText(str(payload.get("state", "-")))
            if event in {"device", "device_classified", "device_state"}:
                device = payload.get("device") if isinstance(payload.get("device"), dict) else payload
                self.values["device"].setText(str(device.get("name") or device.get("model") or device.get("manufacturer") or "-"))
                self.values["fingerprint"].setText(str(device.get("hardware_fingerprint") or device.get("fingerprint") or "-"))
            if event == "scan_progress":
                self.progress.setValue(int(payload.get("progress", payload.get("percent", 0)) or 0))
                self.apply_normalized(payload)
            if event in {"email_queued", "email_delivery", "email_status"}:
                self.apply_normalized(payload)
            if event in {"report_ready", "incident_completed"}:
                self.values["verdict"].setText(str(payload.get("verdict", "-")))
                self.progress.setValue(100)
                for button, key, label in ((self.pdf, "pdf_path", "Open PDF report"),
                                           (self.json, "json_path", "Open JSON report")):
                    path = payload.get(key)
                    button.setProperty("path", path)
                    button.setText(label if path else f"{label} unavailable")
                    button.setEnabled(bool(path))
                self.apply_normalized(payload)
        device = data.get("device") if isinstance(data, dict) else None
        if isinstance(device, dict):
            self.values["device"].setText(str(device.get("name") or device.get("model") or "-"))
            self.values["fingerprint"].setText(str(device.get("hardware_fingerprint") or "-"))
        coverage = data.get("scan_coverage", {}) if isinstance(data, dict) else {}
        if isinstance(coverage, dict):
            self.values["files"].setText(str(coverage.get("total_files", "-")))
            self.values["scanned"].setText(str(coverage.get("processed_files", coverage.get("fully_scanned_files", "-"))))
            self.values["failed"].setText(str(coverage.get("files_failed", coverage.get("failed_files", "-"))))
            self.values["skipped"].setText(str(coverage.get("files_skipped", "-")))
            complete = coverage.get("scan_complete")
            self.values["coverage"].setText("COMPLETE" if complete is True else "INCOMPLETE" if complete is False else "-")
        email = data.get("email_status") if isinstance(data, dict) else None
        if isinstance(email, dict): self.values["email"].setText("READY" if email.get("ready") else "NOT CONFIGURED")
        self.apply_normalized(data)

    def show_action(self, action):
        options = action.get("options") or []
        box = QMessageBox(self)
        box.setWindowTitle(str(action.get("title", "USB action required")))
        box.setText(f"{action.get('summary', '')}\n\nThe device remains isolated until you choose.")
        buttons = {}
        for item in options:
            if not isinstance(item, dict): continue
            button = box.addButton(str(item.get("label") or item.get("id")), QMessageBox.ButtonRole.AcceptRole)
            buttons[button] = str(item.get("id"))
        box.exec()
        clicked = box.clickedButton()
        decision = buttons.get(clicked, str(action.get("safe_default") or "block"))
        token = str(action.get("confirmation_token") or "")
        self.log.append(f"Submitting backend decision: {decision}")
        if not self.client.submit_decision(str(action.get("action_id", "")), decision, token):
            self.log.append("Decision could not be submitted; backend safe default remains active.")

def main():
    app = QApplication(sys.argv); window = Window(); window.show(); raise SystemExit(app.exec())

if __name__ == "__main__": main()
