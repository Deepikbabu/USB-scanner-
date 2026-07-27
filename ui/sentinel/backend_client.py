"""Qt client for the privileged USB scanner service.

The UI never scans or authorizes hardware itself.  It consumes newline-delimited
JSON events from the root service and may only answer an already pending action.
"""
import json
import os
import socket
import threading
import time
import uuid

from PyQt6.QtCore import QObject, pyqtSignal


class BackendClient(QObject):
    message_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool, str)

    def __init__(self, socket_path=None, parent=None):
        super().__init__(parent)
        self.socket_path = socket_path or os.environ.get(
            "USB_SCANNER_SOCKET", "/run/usb-scanner/backend.sock"
        )
        self._running = False
        self._socket = None
        self._send_lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._run, daemon=True, name="dashboard-ipc-client").start()

    def stop(self):
        self._running = False
        sock, self._socket = self._socket, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def command(self, command, data=None):
        frame = {"protocol": 1, "request_id": uuid.uuid4().hex,
                 "command": command, "data": data or {}}
        encoded = (json.dumps(frame) + "\n").encode("utf-8")
        with self._send_lock:
            if not self._socket:
                return False
            try:
                self._socket.sendall(encoded)
                return True
            except OSError:
                return False

    def submit_decision(self, action_id, decision):
        return self.command("submit_decision", {
            "action_id": action_id, "decision": decision
        })

    def recover_hid(self):
        """Request recovery of connected trusted HID devices."""
        return self.command("recover_hid")

    def list_quarantine(self):
        return self.command("list_quarantine")

    def restore_quarantine(self, index):
        return self.command("restore_quarantine", {"index": index, "confirm": True})

    def delete_quarantine(self, index):
        return self.command("delete_quarantine", {"index": index, "confirm": True})


    def _run(self):
        while self._running:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self.socket_path)
                sock.settimeout(1.0)
                self._socket = sock
                self.connection_changed.emit(True, self.socket_path)
                self.command("get_snapshot")
                self._receive(sock)
            except OSError as exc:
                if self._running:
                    self.connection_changed.emit(False, str(exc))
            finally:
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                self._socket = None
            if self._running:
                time.sleep(2)

    def _receive(self, sock):
        buffer = b""
        last_heartbeat = time.monotonic()
        while self._running and self._socket is sock:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                if time.monotonic() - last_heartbeat >= 10:
                    if not self.command("ping"):
                        return
                    last_heartbeat = time.monotonic()
                continue
            if not chunk:
                return
            last_heartbeat = time.monotonic()
            buffer += chunk
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                try:
                    self.message_received.emit(json.loads(raw.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
