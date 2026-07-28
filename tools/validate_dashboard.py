"""Headless smoke validation for the real-service Sentinel dashboard."""
import os
import json
import socket
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ui" / "sentinel"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from backend_client import BackendClient
from backend.security.intelligence import incident_verdict, risk_breakdown

# Do not create a reconnect thread during an offline validation run.
BackendClient.start = lambda self: None
from main_sys import MainWindow


def main():
    confirmed = risk_breakdown(storage=10, malware=70)
    assert confirmed["total"] >= 70 and confirmed["severity"] == "CRITICAL"
    assert incident_verdict(allowed=True, malware=True, remediated=True,
                            total_risk=confirmed["total"]) == "DANGEROUS"
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    # The dashboard now exposes Dashboard, Live Scan, Devices, Quarantine,
    # History, Device Details, and Settings. Keep the validator tolerant of
    # future additive pages while requiring all core views.
    assert window.pages_stack.count() >= 7
    assert not window.page_scan.scan_timer.isActive(), "simulated scan timer is active"
    timer = getattr(window.page_dashboard, "detection_timer", None)
    assert timer is None or not timer.isActive(), "simulated device timer is active"
    assert not window.page_dashboard.btn_trigger.isVisible(), "simulation control is visible"
    expanded_width = window.nav_bar.maximumWidth()
    window.nav_bar.toggle_collapsed()
    QTest.qWait(300)
    assert window.nav_bar.collapsed
    assert window.nav_bar.maximumWidth() < expanded_width
    window.nav_bar.toggle_collapsed()
    QTest.qWait(300)

    # Verify the exact action structure emitted by IPCServer, including replay.
    captured_actions = []
    window.show_action_required = lambda action: captured_actions.append(action)
    ipc_action = {
        "action_id": "action-validation", "title": "Choose handling",
        "device": "Validation USB", "summary": "Device remains blocked",
        "options": [{"id": "scan", "key": "1", "label": "Scan device"},
                    {"id": "block", "key": "2", "label": "Keep blocked"}],
        "safe_default": "block",
    }
    stale_action = dict(ipc_action)
    stale_action["action_id"] = "expired-validation"
    window.apply_snapshot({
                           "recent_events": [{"event": "user_action_required",
                                              "data": stale_action}],
                           "pending_actions": [ipc_action],
                           "incidents": [], "system_status": {}, "resources": {}})
    assert captured_actions == [ipc_action]
    assert window.decision_choices(ipc_action) == [
        ("scan", "Scan device"), ("block", "Keep blocked")]

    device = {"name": "Validation USB", "vid": "1234", "pid": "5678",
              "category": "Mass Storage"}
    window.apply_event({"event": "device_detected", "incident_id": "validation",
                        "data": device})
    window.apply_event({"event": "device_state", "incident_id": "validation",
                        "data": {"state": "CLASSIFIED", "detail": "keyboard"}})
    assert window.page_dashboard.connected_device["category"] == "USB Keyboard"
    assert window.page_dashboard.usb_visualizer.category == "USB Keyboard"
    window.apply_event({"event": "scan_progress", "incident_id": "validation",
                        "data": {"progress": 42, "message": "ClamAV scan"}})
    window.apply_event({"event": "finding_detected", "incident_id": "validation",
                        "data": {"severity": "HIGH", "finding": "Validation finding"}})
    window.apply_event({"event": "risk_updated", "incident_id": "validation",
                        "data": {"total": 80, "final_total": 0, "remediated": True,
                                 "original": {"hardware": 0, "trust": 0, "interface": 0,
                                              "behavior": 0, "storage": 10, "nvd": 0,
                                              "malware": 70}}})
    window.apply_event({"event": "scan_complete", "incident_id": "validation",
                        "data": {"files": 125, "threats": 1,
                                 "inventory": {"files": 125, "folders": 12,
                                               "executables": 3, "archives": 2, "hidden": 1}}})
    assert "consolidating" in window.page_scan.lbl_scan_info.text().lower()
    assert window.page_scan.inventory_card.items["Files"]["label"].text() == "125"
    assert window.page_dashboard.last_scan_card.fields["files"].text() == "125"
    assert window.page_dashboard.last_scan_card.fields["threats"].text() == "1"
    assert window.page_dashboard.last_scan_card.fields["risk_score"].text() == "80/100"
    quarantine_event = {"original_name": "bad.exe", "original_path": "/media/usb/bad.exe",
                        "quarantine_path": "/vault/bad.exe", "sha256": "abc123",
                        "reason": "YARA match", "verified": True,
                        "hash_verified": True, "source_removed": True,
                        "execute_disabled": True}
    window.apply_event({"event": "quarantine_updated", "incident_id": "validation",
                        "data": quarantine_event})
    assert not window.page_scan.quarantine_card.isHidden()
    assert "VERIFIED" in window.page_scan.lbl_quarantine_status.text()
    assert "post-remediation score: 0" in window.page_scan.threat_card.lbl_recommendation.text()
    assert "Validation finding" in window.page_scan.threat_card.lbl_malware_name.text()
    assert "DANGEROUS" in window.page_dashboard.lbl_threat_level.text()
    window.apply_event({"event": "report_ready", "incident_id": "validation",
                        "data": {"verdict": "DANGEROUS", "pdf_path": "/tmp/report.pdf",
                                 "quarantine": ["/vault/bad.exe"]}})
    assert window.page_scan.scan_progress == 42
    assert window.page_dashboard.connected_device["name"] == "Validation USB"
    assert "DANGEROUS" in window.page_scan.lbl_status.text()
    assert window.page_dashboard.last_scan_card.fields["status"].text() == "DANGEROUS"
    # A newly opened dashboard must recover an active scan even if its initial
    # events have rolled out of the recent-event buffer.
    window.page_dashboard.apply_backend_disconnect()
    window.apply_snapshot({
        "recent_events": [], "pending_actions": [], "incidents": [],
        "resources": {}, "system_status": {},
        "active_incidents": [{
            "incident_id": "active-validation",
            "data": {"incident_id": "active-validation", "name": "Active USB",
                     "vid": "1111", "pid": "2222", "state": "SCANNING",
                     "detail": "classified as storage", "progress": 61,
                     "message": "Scanning active.bin"},
        }],
    })
    assert window.page_dashboard.connected_device["name"] == "Active USB"
    assert window.page_scan.scan_progress == 61
    window.apply_event({"event": "log", "data": {"message": "Live backend log"}})
    window.apply_event({"event": "backend_ready", "data": {"Linux": "READY"}})
    window.apply_event({"event": "action_resolved",
                        "data": {"action_id": "action-validation", "decision": "block"}})
    window.apply_event({"event": "incident_completed", "incident_id": "validation",
                        "data": {"verdict": "SUSPICIOUS", "pdf_path": "/tmp/report.pdf"}})

    resources = {
        "trusted_hid": {"046d:c534": "Logitech receiver"},
        "trusted_storage": {},
        "quarantine": [{"original_name": "bad.exe", "reason": "YARA match",
                        "original_path": "/media/usb/bad.exe",
                        "quarantine_path": "/vault/bad.exe", "sha256": "abc"}],
        "email_status": {"enabled": True, "ready": True},
        "email_deliveries": [{"incident_id": "validation", "status": "SENT", "attempts": 1}],
        "reports": [{"incident_id": "validation", "verdict": "SUSPICIOUS",
                     "pdf_path": "/tmp/report.pdf", "json_path": "/tmp/report.json"}],
    }
    window.page_settings.apply_backend_status({"Linux": "READY"}, resources)
    assert len(window.page_settings.trusted_dynamic) == 1
    assert len(window.page_settings.quarantine_dynamic) == 1
    assert "1 FILE" in window.page_settings.lbl_quarantine_title.text()
    assert window.page_settings.email_status_row.lbl_val.text() == "READY"
    assert window.page_settings.latest_report_path == "/tmp/report.pdf"
    window.page_settings.apply_resource_event(
        "email_delivery_updated", {"status": "SENT"}
    )
    assert window.page_settings.email_status_row.lbl_val.text() == "SENT"

    # Verify that BackendClient serializes a command as the server expects.
    left, right = socket.socketpair()
    transport = BackendClient()
    transport._socket = left
    assert transport.command("submit_decision", {"action_id": "a", "decision": "block"})
    frame = json.loads(right.recv(4096).decode().strip())
    assert frame["protocol"] == 1 and frame["command"] == "submit_decision"
    assert frame["data"]["decision"] == "block"
    left.close(); right.close(); transport._socket = None
    window.apply_event({"event": "device_state", "incident_id": "validation",
                        "data": {"state": "DISCONNECTED", "detail": "physical device removed"}})
    assert window.page_dashboard.connected_device is None
    window.backend.stop()
    window.close()
    app.processEvents()
    print("Sentinel dashboard live-backend mapping validation: PASS")


if __name__ == "__main__":
    main()
