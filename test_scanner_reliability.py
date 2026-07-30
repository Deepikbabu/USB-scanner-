"""Regression checks for fail-closed scan and cancellation contracts."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.security.intelligence import (SignedTrustStore, canonical_hash,
                                            device_identity_fingerprint, identity_quality,
                                            incident_verdict, interface_fingerprint,
                                            manifest_fingerprint)
from backend.ipc.server import IPCServer
from backend.scanner.lifecycle import LifecycleRegistry
from backend.notifications.email_templates import incident_message
from tools.validate_consistency import validate


class ReliabilityContractTests(unittest.TestCase):
    def test_identity_quality_reflects_available_hardware_evidence(self) -> None:
        info = {"vid": "1234", "pid": "5678", "serial": "ABC", "usbguard_hash": "hash"}
        self.assertEqual(identity_quality(info, ["03:01:02"]), "STRONG")
        self.assertEqual(identity_quality({**info, "serial": "Unknown"}, ["03:01:02"]), "MEDIUM")
        self.assertEqual(identity_quality({"vid": "1234", "pid": "5678"}, []), "WEAK")

    def test_descriptor_or_interface_change_changes_identity(self) -> None:
        info = {"vid": "1234", "pid": "5678", "serial": "ABC", "usbguard_hash": "hash-a"}
        first = device_identity_fingerprint(info, ["03:01:02"])
        self.assertNotEqual(first, device_identity_fingerprint({**info, "usbguard_hash": "hash-b"}, ["03:01:02"]))
        self.assertNotEqual(first, device_identity_fingerprint(info, ["03:01:01"]))

    def test_duplicate_devices_with_different_serials_do_not_collide(self) -> None:
        base = {"vid": "1234", "pid": "5678", "usbguard_hash": "same"}
        self.assertNotEqual(
            device_identity_fingerprint({**base, "serial": "ONE"}, ["03:01:02"]),
            device_identity_fingerprint({**base, "serial": "TWO"}, ["03:01:02"]),
        )

    def test_storage_manifest_changes_are_detected(self) -> None:
        original = [{"relative_path": "a.txt", "size": 3, "sha256": "aaa"}]
        changed = [{"relative_path": "a.txt", "size": 4, "sha256": "bbb"}]
        self.assertNotEqual(manifest_fingerprint(original), manifest_fingerprint(changed))

    def test_quarantine_tamper_hash_mismatch_is_detectable(self) -> None:
        original = b"trusted quarantine bytes"
        self.assertNotEqual(canonical_hash(original.decode()), canonical_hash((original + b"!").decode()))

    def test_ipc_ping_response(self) -> None:
        server = IPCServer()
        response = server._command({"protocol": 1, "request_id": "test", "command": "ping", "data": {}})
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["data"]["status"], "ONLINE")

    def test_snapshot_exposes_runtime_identity(self) -> None:
        snapshot = IPCServer().snapshot()
        self.assertEqual(snapshot["runtime"]["api_schema_version"], 2)
        self.assertTrue(snapshot["runtime"]["build_id"])
        self.assertTrue(snapshot["runtime"]["project_root"])

    def test_lifecycle_detects_reenumeration_and_lock(self) -> None:
        registry = LifecycleRegistry()
        session = registry.session("1-1.2")
        self.assertFalse(session.observe_identity("046d:c077"))
        self.assertTrue(session.observe_identity("046d:c534"))
        session.lock("identity changed")
        self.assertTrue(session.blocked)
        self.assertEqual(session.re_enumeration_count, 1)
        self.assertEqual(registry.snapshot("1-1.2")["incident_id"], session.incident_id)

    def test_report_identity_and_verdict_are_consistent(self) -> None:
        import json
        from pathlib import Path
        report = Path(".consistency-test.json")
        report.write_text(json.dumps({"verdict": "DANGEROUS", "incident_id": "inc-1",
                                      "device": {"incident_id": "inc-1"}, "risk_breakdown": {}}), encoding="utf-8")
        try:
            self.assertEqual(validate(str(report), "inc-1", "DANGEROUS"), (True, "consistent"))
            self.assertNotEqual(validate(str(report), "inc-2", "DANGEROUS")[0], True)
            with self.assertRaises(ValueError):
                incident_message("inc-2", "DANGEROUS", str(report))
        finally:
            report.unlink(missing_ok=True)

    def test_incomplete_always_wins(self) -> None:
        self.assertEqual(incident_verdict(allowed=True, incomplete=True), "INCOMPLETE")
        self.assertEqual(incident_verdict(allowed=False, incomplete=True, malware=True), "INCOMPLETE")

    def test_malware_is_never_clean_after_remediation(self) -> None:
        self.assertEqual(
            incident_verdict(allowed=True, malware=True, remediated=True),
            "DANGEROUS",
        )

    def test_blocked_without_malware_is_suspicious(self) -> None:
        self.assertEqual(incident_verdict(allowed=False), "SUSPICIOUS")

    def test_trusted_requires_allowed_device(self) -> None:
        self.assertEqual(incident_verdict(allowed=True, trusted=True), "TRUSTED")
        self.assertNotEqual(incident_verdict(allowed=False, trusted=True), "TRUSTED")


class ProductionScannerAvailabilityTests(unittest.TestCase):
    def test_production_scanner_import_is_explicitly_linux_dependent(self) -> None:
        try:
            import changed  # noqa: F401
        except ImportError as exc:
            self.skipTest(f"Linux scanner dependency unavailable: {exc}")

    def test_verified_empty_filesystem_has_complete_coverage(self) -> None:
        try:
            import changed
        except ImportError as exc:
            self.skipTest(f"Linux scanner dependency unavailable: {exc}")
        mount = "/verified-empty-volume"
        with patch.object(changed.os, "walk", return_value=iter([(mount, [], [])])), \
                patch.object(changed.os.path, "isdir", return_value=True), \
                patch.object(changed.os, "access", return_value=True):
            device = {}
            risk, malware, *_ = changed.scan_storage(mount, device)
        self.assertEqual(risk, 0)
        self.assertFalse(malware)
        self.assertFalse(device["scan_coverage"]["incomplete"])
        self.assertTrue(device["scan_coverage"]["empty_filesystem_verified"])

    def test_directory_enumeration_error_is_fail_closed(self) -> None:
        try:
            import changed
        except ImportError as exc:
            self.skipTest(f"Linux scanner dependency unavailable: {exc}")

        def failed_walk(_path, onerror=None):
            if onerror:
                onerror(PermissionError("denied"))
            return iter(())

        device = {}
        mount = "/unreadable-volume"
        with patch.object(changed.os, "walk", side_effect=failed_walk):
            risk, malware, *_ = changed.scan_storage(mount, device)
        self.assertGreaterEqual(risk, 15)
        self.assertFalse(malware)
        self.assertTrue(device["scan_coverage"]["incomplete"])
        self.assertFalse(device["scan_coverage"]["enumeration_complete"])


if __name__ == "__main__":
    unittest.main()
