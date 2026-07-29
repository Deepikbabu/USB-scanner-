"""Render deterministic offscreen UI screenshots for layout regression review."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "ui" / "sentinel")]

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtTest import QTest
from backend_client import BackendClient

BackendClient.start = lambda self: None
from main_sys import MainWindow
from theme import theme_manager


def populate(window):
    device = {
        "name": "SanDisk Ultra Fit 128GB", "category": "USB Flash Drive",
        "vid": "0781", "pid": "5583", "serial": "4C530001",
        "port": "USB 3.0 (Port 2)", "fingerprint": "7C5F-A821-9E40-5811",
        "file_system": "exFAT", "capacity": "119.2 GB",
    }
    window.apply_event({"event": "device_detected", "incident_id": "render-1", "data": device})
    window.apply_event({"event": "device_state", "incident_id": "render-1",
                        "data": {"state": "SCANNING", "detail": "Read-only isolation mount verified"}})
    window.apply_event({"event": "backend_ready",
                        "data": {"usbguard": True, "yara": True, "clamav": True, "root": True}})
    window.apply_event({"event": "scan_progress", "incident_id": "render-1",
                        "data": {"progress": 67, "message": "Scanning document.pdf",
                                 "files": "79,452 / 118,321", "speed": "85.7 files/s",
                                 "elapsed": "06:48", "remaining": "03:17"}})
    window.apply_event({"event": "finding_detected", "incident_id": "render-1",
                        "data": {"severity": "HIGH", "finding": "YARA: suspicious executable",
                                 "path": "/media/usb/setup_old.exe", "engine": "YARA"}})
    window.apply_event({"event": "risk_updated", "incident_id": "render-1",
                        "data": {"total": 75, "final_total": 75}})
    incidents = [
        {"incident_id": f"incident-{n}", "device": f"USB Device {n}",
         "state": "COMPLETED", "verdict": verdict, "risk": risk,
         "updated": f"2026-07-{28-n:02d} 10:{n:02d}"}
        for n, (verdict, risk) in enumerate((
            ("CLEAN", 5), ("DANGEROUS", 80), ("TRUSTED", 0),
            ("SUSPICIOUS", 45), ("INCOMPLETE", 20),
        ))
    ]
    quarantine = [{
        "original_name": "setup_old.exe", "reason": "YARA match",
        "original_path": "/media/usb/setup_old.exe", "timestamp": "2026-07-28 10:18",
        "size": 2048000, "sha256": "abc123", "integrity_verified": True,
    }]
    resources = {
        "quarantine": quarantine,
        "trusted_hid": {"046d:c534": "Logitech receiver"},
        "trusted_storage": {},
        "signed_trust": [{
            "identity": "046d:c534:receiver-01", "status": "Trusted",
            "record": {"type": "HID", "source": "Signed trust store",
                       "scope": "Exact hardware identity"},
        }],
        "reports": [{
            "incident_id": "INC-1004", "verdict": "DANGEROUS",
            "total_risk": 75, "files_scanned": 118321, "threat_count": 1,
            "risk_breakdown": {"malware_detection": 45, "unknown_device": 15,
                               "suspicious_executable": 15},
            "findings": ["YARA: suspicious executable · /media/usb/setup_old.exe"],
        }],
        "email_status": {"enabled": True, "ready": True},
        "metrics": {"incidents": 5, "files_scanned": 2453712,
                    "threats_found": 3, "quarantined_files": 1},
    }
    window.apply_snapshot({"recent_events": [], "pending_actions": [],
                           "incidents": incidents, "resources": resources,
                           "system_status": {"usbguard": True, "yara": True,
                                             "clamav": True, "root": True}})
    incident = next((item for item in incidents if item["incident_id"] == "INC-1004"), incidents[0])
    window.page_incident_details.apply_incident(
        incident, resources["reports"][0]
    )


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families() and os.name == "nt":
        for font_path in (
            Path(r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\seguisym.ttf"),
            Path(r"C:\Windows\Fonts\arial.ttf"),
        ):
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
    theme_manager.apply(app)
    output = ROOT / ".artifacts" / "ui-renders"
    output.mkdir(parents=True, exist_ok=True)
    print("Creating window", flush=True)
    window = MainWindow()
    window.shell.set_backend_connected(True)
    print("Populating backend-shaped state", flush=True)
    populate(window)
    page_names = (
        "dashboard", "live-scan", "devices", "quarantine", "history",
        "device-details", "settings", "incident-evidence", "trust-management",
    )
    for width, height in ((1366, 768), (1920, 1080)):
        window.resize(width, height)
        print(f"Showing {width}x{height}", flush=True)
        window.show()
        QTest.qWait(700)
        for index, name in enumerate(page_names):
            print(f"Rendering {name}", flush=True)
            window.pages_stack.setCurrentIndex(index)
            window.shell._select_page(index)
            window.nav_bar.set_active_tab(index, emit=False)
            app.processEvents()
            target = output / f"{name}-{width}x{height}.png"
            if not window.grab().save(str(target), "PNG"):
                raise RuntimeError(f"Could not render {target}")
    window.resize(1024, 680)
    if not window.nav_bar.collapsed:
        window.nav_bar.toggle_collapsed()
    QTest.qWait(320)
    window.pages_stack.setCurrentIndex(0)
    window.shell._select_page(0)
    window.nav_bar.set_active_tab(0, emit=False)
    app.processEvents()
    target = output / "dashboard-collapsed-1024x680.png"
    if not window.grab().save(str(target), "PNG"):
        raise RuntimeError(f"Could not render {target}")
    window.backend.stop()
    window.close()
    print(f"Rendered {len(page_names) * 2 + 1} screenshots to {output}")


if __name__ == "__main__":
    main()
