import hashlib
import json
import sqlite3
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.ipc import server as ipc_module
from backend.security import intelligence

TEST_ROOT = Path(__file__).resolve().parent / ".artifacts"
TEST_ROOT.mkdir(exist_ok=True)

class OperatorControlTests(unittest.TestCase):
    def test_audit_ledger_is_hash_chained(self):
        database = TEST_ROOT / "operator-audit-test.db"
        database.unlink(missing_ok=True)
        server = ipc_module.IPCServer.__new__(ipc_module.IPCServer)
        server.database = database
        with sqlite3.connect(database) as db:
            db.execute("""CREATE TABLE audit_log (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
                operator TEXT, action TEXT, target TEXT, reason TEXT,
                outcome TEXT, previous_hash TEXT, entry_hash TEXT UNIQUE)""")
        server._audit("alice", "revoke_trust", "device-1", "Device retired", "REVOKED")
        server._audit("bob", "expire_trust", "device-2", "Contractor access", "EXPIRATION_SET")
        entries = list(reversed(server._audit_entries()))
        previous = "GENESIS"
        for entry in entries:
            self.assertEqual(entry["previous_hash"], previous)
            body = json.dumps({
                "timestamp": entry["timestamp"], "operator": entry["operator"],
                "action": entry["action"], "target": entry["target"],
                "reason": entry["reason"], "outcome": entry["outcome"],
                "previous_hash": entry["previous_hash"],
            }, sort_keys=True, separators=(",", ":"))
            self.assertEqual(
                entry["entry_hash"],
                hashlib.sha256(body.encode("utf-8")).hexdigest(),
            )
            previous = entry["entry_hash"]

    def test_signed_trust_expiration_is_enforced(self):
        store = intelligence.SignedTrustStore.__new__(intelligence.SignedTrustStore)
        record = {"expires_at": time.time() - 1}
        signature = "valid"
        with patch.object(store, "_load_all", return_value={
            "temporary-device": {"record": record, "signature": signature}
        }), patch.object(store, "_sign", return_value=signature):
            value, status = store.get("temporary-device")
        self.assertIsNone(value)
        self.assertEqual(status, "expired")

    def test_trust_mutations_require_audit_fields(self):
        server = ipc_module.IPCServer.__new__(ipc_module.IPCServer)
        result = server._trust_command(
            "revoke_trust", {"identity": "device", "confirm": True}
        )
        self.assertFalse(result["ok"])
        self.assertIn("operator", result["output"])

    def test_incident_assignment_acknowledgement_and_comment_persist(self):
        database = TEST_ROOT / "incident-workflow-test.db"
        database.unlink(missing_ok=True)
        server = ipc_module.IPCServer.__new__(ipc_module.IPCServer)
        server.database = database
        with sqlite3.connect(database) as db:
            db.execute("""CREATE TABLE incident_workflow (
                incident_id TEXT PRIMARY KEY, assigned_to TEXT,
                acknowledged INTEGER, comments TEXT, updated REAL)""")
            db.execute("""CREATE TABLE audit_log (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
                operator TEXT, action TEXT, target TEXT, reason TEXT,
                outcome TEXT, previous_hash TEXT, entry_hash TEXT UNIQUE)""")
        with patch.object(server, "publish"):
            result = server._update_incident_workflow({
                "incident_id": "INC-1", "operator": "analyst",
                "assigned_to": "soc-team", "acknowledged": True,
                "comment": "Investigating attached evidence.",
            })
        self.assertTrue(result["ok"])
        workflow = server._incident_workflow()["INC-1"]
        self.assertEqual(workflow["assigned_to"], "soc-team")
        self.assertTrue(workflow["acknowledged"])
        self.assertEqual(workflow["comments"][0]["operator"], "analyst")


if __name__ == "__main__":
    unittest.main()
