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
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QLineEdit, QMainWindow, QProgressBar, QTextEdit, QWidget, QPushButton

SOCKET = os.environ.get("USB_SCANNER_SOCKET", "/run/usb-scanner/backend.sock")

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
    @staticmethod
    def open_report(path):
        if path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def apply(self, message):
        data = message.get("data", message)
        if message.get("event"):
            event = message.get("event"); payload = message.get("data", {}) or {}
            self.log.append(f"{event}: {json.dumps(payload, default=str)}")
            if event == "device_state": self.values["state"].setText(str(payload.get("state", "-")))
            if event == "scan_progress":
                self.progress.setValue(int(payload.get("progress", 0)))
                self.values["files"].setText(str(payload.get("files", "-")))
            if event in {"report_ready", "incident_completed"}:
                self.values["verdict"].setText(str(payload.get("verdict", "-")))
                self.progress.setValue(100)
                for button, key, label in ((self.pdf, "pdf_path", "Open PDF report"),
                                           (self.json, "json_path", "Open JSON report")):
                    path = payload.get(key)
                    button.setProperty("path", path)
                    button.setText(label if path else f"{label} unavailable")
                    button.setEnabled(bool(path))
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

def main():
    app = QApplication(sys.argv); window = Window(); window.show(); raise SystemExit(app.exec())

if __name__ == "__main__": main()
