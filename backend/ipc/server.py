from __future__ import annotations

import json
import hashlib
import os
import queue
import socket
import sqlite3
import threading
import time
import uuid
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any

try:
    import grp
except ImportError:  # Allows protocol tests on non-Linux development hosts.
    grp = None

PROTOCOL_VERSION = 1
DEFAULT_SOCKET = Path(os.environ.get("USB_SCANNER_SOCKET", "/run/usb-scanner/backend.sock"))
STATE_ROOT = Path(os.environ.get("USB_SCANNER_STATE_DIR", "/var/lib/usb-scanner"))
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class IPCServer:
    def __init__(self) -> None:
        self.socket_path = DEFAULT_SOCKET
        self.state_root = STATE_ROOT
        self.clients: set[socket.socket] = set()
        self.clients_lock = threading.Lock()
        self.recent = deque(maxlen=250)
        self.active: dict[str, dict[str, Any]] = {}
        self.completed_incidents: dict[str, float] = {}
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.system_status: dict[str, Any] = {}
        self.action_responses: dict[str, queue.Queue[str]] = {}
        self.running = False
        self.server_socket: socket.socket | None = None
        self._prepare_state()

    def _prepare_state(self) -> None:
        try:
            self.state_root.mkdir(parents=True, mode=0o750, exist_ok=True)
        except OSError:
            self.state_root = Path(__file__).resolve().parents[2] / ".scanner_state"
            self.state_root.mkdir(parents=True, mode=0o750, exist_ok=True)
        self.database = self.state_root / "dashboard_state.db"
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY, timestamp REAL, event TEXT,
                incident_id TEXT, payload TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp DESC)")
            db.execute("""CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY, state TEXT, verdict TEXT,
                device TEXT, risk INTEGER, updated REAL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT,
                severity TEXT, finding TEXT, path TEXT, timestamp REAL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS reports (
                incident_id TEXT PRIMARY KEY, verdict TEXT, pdf_path TEXT,
                json_path TEXT, updated REAL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS actions (
                action_id TEXT PRIMARY KEY, status TEXT, payload TEXT, updated REAL)""")
        if os.name != "nt":
            self.database.chmod(0o640)

    def start(self) -> None:
        if self.running or not hasattr(socket, "AF_UNIX"):
            return
        self.socket_path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)
        try:
            self.socket_path.unlink(missing_ok=True)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(self.socket_path))
            try:
                if grp is not None:
                    os.chown(self.socket_path, 0, grp.getgrnam("usb-scanner").gr_gid)
            except (KeyError, PermissionError, OSError): pass
            os.chmod(self.socket_path, 0o660)
            server.listen(8)
            server.settimeout(1)
        except OSError as exc:
            print(f"[IPC] Dashboard socket unavailable: {exc}")
            return
        self.server_socket, self.running = server, True
        threading.Thread(target=self._accept_loop, daemon=True, name="dashboard-ipc").start()
        self.publish("backend_connection", {"status": "ONLINE", "socket": str(self.socket_path)})

    def _accept_loop(self) -> None:
        while self.running and self.server_socket:
            try:
                client, _ = self.server_socket.accept()
                client.settimeout(1)
                with self.clients_lock:
                    self.clients.add(client)
                threading.Thread(target=self._client_loop, args=(client,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _client_loop(self, client: socket.socket) -> None:
        buffer = b""
        try:
            while self.running:
                try:
                    chunk = client.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    try:
                        request = json.loads(raw.decode("utf-8"))
                        response = self._command(request)
                    except Exception as exc:
                        response = {"protocol": 1, "status": "error", "error": str(exc)}
                    # Serialize command replies with asynchronous broadcasts so
                    # two JSON frames can never interleave on one stream.
                    with self.clients_lock:
                        client.sendall((json.dumps(response, default=str) + "\n").encode())
        finally:
            with self.clients_lock:
                self.clients.discard(client)
            try: client.close()
            except OSError: pass

    def _command(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("request_id")
        command = request.get("command")
        if request.get("protocol", 1) != PROTOCOL_VERSION:
            return {"protocol": 1, "request_id": request_id, "status": "error",
                    "error": "unsupported protocol"}
        if command == "get_snapshot":
            data = self.snapshot()
        elif command == "get_history":
            data = {"events": self.history(int(request.get("data", {}).get("limit", 200)))}
        elif command == "submit_decision":
            values = request.get("data", {})
            accepted = self.submit_action(str(values.get("action_id", "")), str(values.get("decision", "")))
            return {"protocol": 1, "request_id": request_id,
                    "status": "accepted" if accepted else "rejected"}
        elif command == "ping":
            data = {"status": "ONLINE", "time": time.time()}
        elif command == "recover_hid":
            # Recovery is delegated to the signed-fingerprint verifier. The
            # dashboard cannot directly authorize arbitrary USB devices.
            project_root = Path(__file__).resolve().parents[2]
            script = project_root / "tools" / "hid_trust.py"
            try:
                result = subprocess.run(
                    [os.environ.get("PYTHON", sys.executable), str(script), "recover"],
                    cwd=project_root, capture_output=True, text=True, timeout=30,
                )
                data = {"ok": result.returncode == 0,
                        "output": (result.stdout or result.stderr).strip()}
            except (OSError, subprocess.TimeoutExpired) as exc:
                data = {"ok": False, "output": str(exc)}
        elif command in {"list_quarantine", "restore_quarantine", "delete_quarantine"}:
            project_root = Path(__file__).resolve().parents[2]
            script = project_root / "tools" / "quarantine_api.py"
            values = request.get("data") or {}
            action = command.replace("_quarantine", "")
            args = [sys.executable, str(script), action]
            if values.get("index") is not None:
                args.extend(["--index", str(values["index"])])
            if values.get("confirm"):
                args.append("--confirm")
            try:
                result = subprocess.run(args, cwd=project_root, capture_output=True,
                                        text=True, timeout=90)
                data = {"ok": result.returncode == 0, "action": action,
                        "output": (result.stdout or result.stderr).strip()}
            except (OSError, subprocess.TimeoutExpired) as exc:
                data = {"ok": False, "output": str(exc)}
        else:
            return {"protocol": 1, "request_id": request_id, "status": "error",
                    "error": "unknown command"}
        return {"protocol": 1, "request_id": request_id, "status": "ok", "data": data}

    def publish(self, event: str, data: dict[str, Any] | None = None,
                incident_id: str | None = None) -> dict[str, Any]:
        payload = {"protocol": 1, "event_id": f"evt-{uuid.uuid4().hex}",
                   "event": event, "timestamp": time.time(),
                   "incident_id": incident_id, "data": data or {}}
        self.recent.append(payload)
        key = incident_id or (data or {}).get("device_id")
        if key and event in {"device_state", "scan_progress", "risk_updated", "device_detected"} and str(key) not in self.completed_incidents:
            device_key = str((data or {}).get("device_id", ""))
            if incident_id and device_key and device_key != str(incident_id):
                self.active.pop(device_key, None)
            current = self.active.setdefault(str(key), {})
            combined_data = dict(current.get("data", {}))
            combined_data.update(data or {})
            current.update(payload)
            current["data"] = combined_data
        if event == "incident_completed" and key:
            self.active.pop(str(key), None)
            self.completed_incidents[str(key)] = payload["timestamp"]
            if len(self.completed_incidents) > 5000:
                oldest = min(self.completed_incidents, key=self.completed_incidents.get)
                self.completed_incidents.pop(oldest, None)
        if event == "backend_ready":
            self.system_status = dict(data or {})
        try:
            with sqlite3.connect(self.database) as db:
                db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
                    payload["event_id"], payload["timestamp"], event,
                    incident_id, json.dumps(payload, default=str)))
                db.execute("DELETE FROM events WHERE event_id IN (SELECT event_id FROM events "
                           "ORDER BY timestamp DESC LIMIT -1 OFFSET 5000)")
                if incident_id and event == "device_state":
                    db.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET "
                               "state=excluded.state,device=excluded.device,updated=excluded.updated", (
                        incident_id, (data or {}).get("state", ""), "",
                        (data or {}).get("device_id", ""), 0, payload["timestamp"]))
                elif incident_id and event == "risk_updated":
                    db.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET "
                               "risk=excluded.risk,updated=excluded.updated", (
                        incident_id, "", "", "", int((data or {}).get("total", 0)), payload["timestamp"]))
                elif incident_id and event == "finding_detected":
                    db.execute("INSERT INTO findings(incident_id,severity,finding,path,timestamp) VALUES (?,?,?,?,?)", (
                        incident_id, (data or {}).get("severity", ""), (data or {}).get("finding", ""),
                        (data or {}).get("path", ""), payload["timestamp"]))
                elif incident_id and event == "report_ready":
                    db.execute("REPLACE INTO reports VALUES (?,?,?,?,?)", (
                        incident_id, (data or {}).get("verdict", ""), (data or {}).get("pdf_path", ""),
                        (data or {}).get("json_path", ""), payload["timestamp"]))
                    db.execute("INSERT INTO incidents VALUES (?,?,?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET "
                               "verdict=excluded.verdict,updated=excluded.updated", (
                        incident_id, "COMPLETED", (data or {}).get("verdict", ""), "", 0, payload["timestamp"]))
        except sqlite3.Error:
            pass
        encoded = (json.dumps(payload, default=str) + "\n").encode()
        with self.clients_lock:
            dead = []
            for client in self.clients:
                try: client.sendall(encoded)
                except OSError: dead.append(client)
            for client in dead:
                self.clients.discard(client)
        return payload

    def snapshot(self) -> dict[str, Any]:
        return {"protocol": 1, "backend": "ONLINE", "system_status": self.system_status,
                "active_incidents": list(self.active.values()),
                "pending_actions": list(self.pending_actions.values()),
                "recent_events": list(self.recent), "resources": self._resources(),
                "incidents": self._incidents(),
                "generated_at": time.time()}

    def _incidents(self) -> list[dict[str, Any]]:
        try:
            with sqlite3.connect(self.database) as db:
                rows = db.execute(
                    "SELECT incident_id,state,verdict,device,risk,updated "
                    "FROM incidents ORDER BY updated DESC LIMIT 250"
                ).fetchall()
            return [{"incident_id": row[0], "state": row[1], "verdict": row[2],
                     "device": row[3], "risk": row[4], "updated": row[5]}
                    for row in rows]
        except sqlite3.Error:
            return []

    def _resources(self) -> dict[str, Any]:
        def load(path, default):
            try: return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): return default
        def safe_int(value):
            try: return int(value or 0)
            except (TypeError, ValueError): return 0
        raw_quarantine = load(PROJECT_ROOT / "quarantine" / "quarantine_log.json", [])
        quarantine = []
        for raw_entry in raw_quarantine if isinstance(raw_quarantine, list) else []:
            entry = dict(raw_entry or {})
            vault_path = Path(entry.get("quarantine_path") or (
                PROJECT_ROOT / "quarantine" / str(entry.get("quarantined_name", ""))
            ))
            digest = None
            try:
                hasher = hashlib.sha256()
                with vault_path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
                entry["size"] = vault_path.stat().st_size
                entry["execute_disabled"] = (vault_path.stat().st_mode & 0o111) == 0
            except OSError:
                entry["size"] = 0
                entry["execute_disabled"] = False
            entry["vault_present"] = digest is not None
            entry["integrity_verified"] = bool(
                digest and entry.get("sha256") and digest == entry.get("sha256")
                and entry["execute_disabled"]
            )
            quarantine.append(entry)
        hid = load(PROJECT_ROOT / "whitelist.json", {})
        storage = load(PROJECT_ROOT / "storage_whitelist.json", {})
        signed_trust = []
        try:
            from backend.security.intelligence import SignedTrustStore
            store = SignedTrustStore()
            wrapped_records = load(store.records_path, {})
            for identity in sorted(wrapped_records):
                record, status = store.get(identity)
                raw_record = wrapped_records.get(identity, {}).get("record", {})
                signed_trust.append({"identity": identity, "status": status,
                                     "record": record or raw_record})
        except Exception:
            pass
        reports = []
        for path in sorted((PROJECT_ROOT / "reports").glob("incident_*.json"), reverse=True):
            payload = load(path, {})
            device = payload.get("device") if isinstance(payload.get("device"), dict) else {}
            coverage = payload.get("scan_coverage")
            if not isinstance(coverage, dict):
                coverage = device.get("scan_coverage", {}) if isinstance(device.get("scan_coverage"), dict) else {}
            inventory = device.get("file_inventory", {}) if isinstance(device.get("file_inventory"), dict) else {}
            findings = payload.get("findings", payload.get("flags", []))
            findings = findings if isinstance(findings, list) else []
            malicious = payload.get("malicious_files", [])
            malicious = malicious if isinstance(malicious, list) else []
            breakdown = payload.get("risk_breakdown", {})
            breakdown = breakdown if isinstance(breakdown, dict) else {}
            report_id = payload.get("incident_id") or device.get("incident_id") or path.stem
            verdict = str(payload.get("verdict", payload.get("decision", "INCOMPLETE"))).upper()
            pdf_path = path.with_suffix(".pdf")
            threat_count = len(malicious)
            if not malicious and verdict in {"SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}:
                threat_count = len(findings)
            reports.append({
                "incident_id": report_id,
                "verdict": verdict,
                "json_path": str(path),
                "pdf_path": str(pdf_path) if pdf_path.exists() else "",
                "timestamp": payload.get("timestamp", ""),
                "device": device,
                "files": safe_int(inventory.get("files", coverage.get("total_files", 0))),
                "threats": threat_count,
                "risk": safe_int(payload.get("total_risk", breakdown.get("total", 0))),
                "quarantine_count": len(payload.get("quarantine_paths", []) or []),
            })
        deliveries = []
        email_status = {"enabled": False, "ready": False}
        try:
            from backend.notifications.email_config import load_email_config
            email_config = load_email_config()
            email_status = {"enabled": email_config.enabled, "ready": email_config.ready}
        except Exception:
            pass
        email_db = self.state_root / "email_delivery.db"
        try:
            with sqlite3.connect(email_db) as db:
                deliveries = [{"incident_id": row[0], "verdict": row[1], "status": row[2],
                               "attempts": row[3], "updated": row[4], "error": row[5]}
                              for row in db.execute("SELECT incident_id,verdict,status,attempts,updated,last_error "
                                                    "FROM delivery ORDER BY created DESC LIMIT 100")]
        except sqlite3.Error: pass
        metrics = {
            "incidents": len(reports),
            "files_scanned": sum(report["files"] for report in reports),
            "threats_found": sum(report["threats"] for report in reports),
            "quarantined_files": len(quarantine),
        }
        return {"quarantine": quarantine, "trusted_hid": hid, "trusted_storage": storage,
                "signed_trust": signed_trust, "reports": reports[:100],
                "email_deliveries": deliveries, "email_status": email_status,
                "metrics": metrics}

    def history(self, limit=200) -> list[dict[str, Any]]:
        try:
            with sqlite3.connect(self.database) as db:
                rows = db.execute("SELECT payload FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [json.loads(row[0]) for row in rows]
        except (sqlite3.Error, json.JSONDecodeError):
            return []

    def register_action(self, title: str, device: str, summary: str,
                        options: dict[str, tuple[str, str]], default: str, timeout: int) -> str:
        action_id = f"action-{uuid.uuid4().hex}"
        choices, seen = [], set()
        for key, (result, label) in options.items():
            if result in seen or not key.isdigit(): continue
            seen.add(result); choices.append({"id": result, "key": key, "label": label})
        action = {"action_id": action_id, "title": title, "device": device, "summary": summary,
                  "options": choices, "safe_default": default, "expires_at": time.time() + timeout}
        self.pending_actions[action_id] = action
        self.action_responses[action_id] = queue.Queue(maxsize=1)
        self.publish("user_action_required", action)
        with sqlite3.connect(self.database) as db:
            db.execute("REPLACE INTO actions VALUES (?,?,?,?)",
                       (action_id, "PENDING", json.dumps(action), time.time()))
        return action_id

    def wait_action(self, action_id: str, timeout: float) -> str | None:
        response = self.action_responses.get(action_id)
        if not response: return None
        try: return response.get(timeout=timeout)
        except queue.Empty: return None

    def submit_action(self, action_id: str, decision: str) -> bool:
        action, response = self.pending_actions.get(action_id), self.action_responses.get(action_id)
        if not action or not response or time.time() > action["expires_at"]:
            return False
        allowed = {item["id"] for item in action["options"]}
        if decision not in allowed: return False
        try: response.put_nowait(decision)
        except queue.Full: return False
        self.pending_actions.pop(action_id, None)
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE actions SET status='RESOLVED',updated=? WHERE action_id=?", (time.time(), action_id))
        self.publish("action_resolved", {"action_id": action_id, "decision": decision})
        return True

    def finish_action(self, action_id: str, decision: str, expired=False) -> None:
        existed = self.pending_actions.pop(action_id, None)
        self.action_responses.pop(action_id, None)
        if existed:
            with sqlite3.connect(self.database) as db:
                db.execute("UPDATE actions SET status=?,updated=? WHERE action_id=?",
                           ("EXPIRED" if expired else "RESOLVED", time.time(), action_id))
            self.publish("action_expired" if expired else "action_resolved",
                         {"action_id": action_id, "decision": decision})


_SERVER: IPCServer | None = None
_LOCK = threading.Lock()


def get_ipc_server() -> IPCServer:
    global _SERVER
    with _LOCK:
        if _SERVER is None: _SERVER = IPCServer()
        return _SERVER


def publish_event(event: str, data: dict[str, Any] | None = None,
                  incident_id: str | None = None) -> dict[str, Any]:
    return get_ipc_server().publish(event, data, incident_id)
