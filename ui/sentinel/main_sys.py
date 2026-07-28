import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt, QDateTime, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPixmap, QBrush
from theme import theme_manager
from navigation import BottomNavigationBar
from dashboard import DashboardPage
from scan_page import ScanPage
from history import HistoryPage
from settings import SettingsPage
from backend_client import BackendClient
from asset_pages import DevicesPage, QuarantinePage, DeviceDetailsPage

class PremiumBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("premiumBackgroundWidget")
        
        # Build noise pixmap for highly performant, CPU-friendly grain tiling on Raspberry Pi
        self._noise_pixmap = QPixmap(128, 128)
        self._noise_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(self._noise_pixmap)
        for x in range(128):
            for y in range(128):
                # Subtle grain dots
                alpha = random.randint(4, 9)
                painter.setPen(QColor(255, 255, 255, alpha))
                painter.drawPoint(x, y)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        is_dark = (theme_manager.current_theme == "dark")
        
        if is_dark:
            # Smooth radial gradient for Monochrome Rust
            radial = QRadialGradient(w / 2.0, h / 2.2, max(w, h) * 0.95)
            radial.setColorAt(0.0, QColor("#0D0705"))
            radial.setColorAt(0.5, QColor("#150A06"))
            radial.setColorAt(1.0, QColor("#2A1108"))
            painter.fillRect(self.rect(), QBrush(radial))
        else:
            # Base light grey/cream layer
            painter.fillRect(self.rect(), QColor("#FAF8F5"))
            
            # Soft warm cream-ish linear gradient
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor("#F4EEEC"))
            grad.setColorAt(1.0, QColor("#FAF8F5"))
            painter.fillRect(self.rect(), QBrush(grad))
            
            # Soft radial light warm rust glow
            radial = QRadialGradient(w / 2.0, h / 2.2, max(w, h) * 0.7)
            radial.setColorAt(0.0, QColor(217, 127, 74, 10))
            radial.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(self.rect(), QBrush(radial))
            
        # Draw tiled noise grain texture
        painter.save()
        painter.setOpacity(0.35 if is_dark else 0.2)
        brush = QBrush(self._noise_pixmap)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        painter.restore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Security Detector && Terminal Sandbox")
        self.resize(800, 600)
        
        # Central Widget & Main Layout
        self.central_widget = PremiumBackgroundWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
        # Pages Stack
        self.pages_stack = QStackedWidget()
        
        self.page_dashboard = DashboardPage()
        # Dashboard construction is lazy so validation can run before the
        # backend connects; build its widgets before accessing status labels.
        self.page_dashboard.apply_backend_incidents([])
        self.page_scan = ScanPage()
        self.page_history = HistoryPage()
        self.page_settings = SettingsPage()
        self.page_devices = DevicesPage()
        self.page_quarantine = QuarantinePage()
        self.page_device_details = DeviceDetailsPage()
        
        self.pages_stack.addWidget(self.page_dashboard)
        self.pages_stack.addWidget(self.page_scan)
        self.pages_stack.addWidget(self.page_devices)
        self.pages_stack.addWidget(self.page_quarantine)
        self.pages_stack.addWidget(self.page_history)
        self.pages_stack.addWidget(self.page_device_details)
        self.pages_stack.addWidget(self.page_settings)
        
        # Bottom Navigation
        self.nav_bar = BottomNavigationBar()
        
        # Center the navigation bar inside a layout with flexible spacers
        self.nav_container_layout = QHBoxLayout()
        self.nav_container_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_container_layout.addStretch(1)
        self.nav_container_layout.addWidget(self.nav_bar)
        self.nav_container_layout.addStretch(1)
        
        self.main_layout.addWidget(self.pages_stack, 1)
        self.main_layout.addLayout(self.nav_container_layout)
        
        # Connect navigation switching with transition animation
        self.nav_bar.tab_changed.connect(self.switch_page)
        
        # The privileged service is the sole source of device and scan state.
        self._seen_events = set()
        self._shown_actions = set()
        self._active_incident = None
        self.backend = BackendClient(parent=self)
        self.page_dashboard.lbl_status.setText("Loading security engine…")
        self.page_settings.recover_hid_requested.connect(self.recover_trusted_hid)
        self.page_settings.quarantine_restore_requested.connect(self.restore_quarantine)
        self.page_settings.quarantine_delete_requested.connect(self.delete_quarantine)
        self.page_dashboard.retry_requested.connect(self.retry_backend)
        self.page_quarantine.restore_requested.connect(self.restore_quarantine)
        self.page_quarantine.delete_requested.connect(self.delete_quarantine)
        self.page_quarantine.details_requested.connect(self.show_quarantine_details)
        self.backend.connection_changed.connect(self.on_backend_connection)
        self.backend.message_received.connect(self.on_backend_message)
        self.backend.start()
        
        self.update_theme_styles()
        theme_manager.theme_changed.connect(self.update_theme_styles)

    def recover_trusted_hid(self):
        self.page_settings.lbl_hid_recovery.setText("Verifying fingerprints and restoring authorized HID devices…")
        if not self.backend.recover_hid():
            self.page_settings.lbl_hid_recovery.setText("Recovery request could not reach the backend.")

    def restore_quarantine(self, index):
        self.page_settings.lbl_status.setText(f"Restoring quarantine item {index}…")
        if not self.backend.restore_quarantine(index):
            self.page_settings.lbl_status.setText("Restore request could not reach the backend.")

    def delete_quarantine(self, index):
        answer = QMessageBox.question(self, "Confirm deletion", "Permanently delete this quarantined item?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.page_settings.lbl_status.setText(f"Deleting quarantine item {index}…")
        if not self.backend.delete_quarantine(index):
            self.page_settings.lbl_status.setText("Delete request could not reach the backend.")

    def show_quarantine_details(self, index):
        item = self.page_quarantine.table.item(index, 0)
        name = item.text() if item else "Unknown item"
        QMessageBox.information(self, "Quarantine details", f"File: {name}\nIntegrity and threat details are available in the final report.")

    def closeEvent(self, event):
        self.backend.stop()
        super().closeEvent(event)

    def on_backend_connection(self, connected, detail):
        if connected:
            self.page_dashboard.btn_retry.hide()
            self.page_dashboard.lbl_subtitle.setText("Security engine online — live event stream")
            self.page_dashboard.lbl_status.setText("Secure Terminal: Monitoring")
        else:
            self.page_dashboard.btn_retry.show()
            self.page_dashboard.lbl_subtitle.setText("Security engine offline — reconnecting")
            self.page_dashboard.lbl_status.setText("Backend unavailable")
            self.page_scan.lbl_scan_info.setText(
                "Waiting for the usb-scanner service. No scan data is being received."
            )
            self.page_dashboard.lbl_status.setText("Backend disconnected — retrying")

    def retry_backend(self):
        self.page_dashboard.btn_retry.setEnabled(False)
        self.page_dashboard.lbl_status.setText('Retrying connection…')
        self.backend.stop(); self.backend.start()
        self.page_dashboard.btn_retry.setEnabled(True)

    def on_backend_message(self, message):
        if message.get("status") == "error" or message.get("event") == "error":
            detail = str(message.get("error") or message.get("message") or "Backend request failed")
            self.page_dashboard.lbl_status.setText("Backend error")
            self.page_dashboard.lbl_subtitle.setText(detail)
            self.page_scan.lbl_scan_info.setText("Backend error — waiting for retry")
            return
        # Command response containing the initial authoritative snapshot.
        if message.get("status") == "ok" and isinstance(message.get("data"), dict):
            snapshot = message["data"]
            if "recent_events" in snapshot:
                self.apply_snapshot(snapshot)
            elif "ok" in snapshot and "output" in snapshot:
                self.page_settings.lbl_hid_recovery.setText(
                    str(snapshot.get("output") or "Recovery completed.")
                )
                self.page_dashboard.notification_center.add_log(
                    "HID recovery: " + ("SUCCESS" if snapshot.get("ok") else "FAILED")
                )
                self.page_scan.add_log_card(
                    "HID recovery result: " + str(snapshot.get("output") or "No backend details")
                )
                if snapshot.get("action") in {"list", "restore", "delete"}:
                    ok=bool(snapshot.get('ok')); action=str(snapshot.get('action')).title(); result=f"{action}: {'SUCCESS' if ok else 'FAILED'}"
                    self.page_settings.lbl_status.setText("Quarantine operation: " + result)
                    self.page_dashboard.notification_center.add_log(result)
                    if not ok: QMessageBox.warning(self, 'Quarantine action failed', str(snapshot.get('output') or result))
                    else: QMessageBox.information(self, 'Quarantine action complete', str(snapshot.get('output') or result))
                    self.backend.command("get_snapshot")
            elif "action" in snapshot:
                self.page_settings.lbl_status.setText(str(snapshot.get("output") or "Quarantine operation completed."))
                self.backend.command("get_snapshot")
            return
        event_id = message.get("event_id")
        if event_id and event_id in self._seen_events:
            return
        if event_id:
            self._seen_events.add(event_id)
        self.apply_event(message)

    def apply_snapshot(self, snapshot):
        # Replaying real persisted events makes a newly opened dashboard current.
        for event in snapshot.get("recent_events", []):
            # Prompts are transient capabilities. Historical/expired action
            # events must never be rendered as live decision dialogs.
            if event.get("event") in {
                "user_action_required", "action_resolved", "action_expired"
            }:
                continue
            self.on_backend_message(event)
        for action in snapshot.get("pending_actions", []):
            self.apply_event({"event": "user_action_required", "data": dict(action)})
        incidents = snapshot.get("incidents", [])
        if hasattr(self.page_dashboard, "apply_backend_incidents"):
            self.page_dashboard.apply_backend_incidents(incidents)
        if hasattr(self.page_history, "apply_backend_incidents"):
            self.page_history.apply_backend_incidents(incidents)
        if hasattr(self.page_settings, "apply_backend_status"):
            self.page_settings.apply_backend_status(
                snapshot.get("system_status", {}), snapshot.get("resources", {})
            )

    @staticmethod
    def normalize_device(data):
        raw = dict(data.get("device", {})) if isinstance(data.get("device"), dict) else dict(data)
        return {
            "name": raw.get("name") or raw.get("product") or raw.get("device_name") or "Unknown USB device",
            "manufacturer": raw.get("manufacturer") or raw.get("vendor") or "Unknown",
            "vid": str(raw.get("vid") or raw.get("vendor_id") or "----"),
            "pid": str(raw.get("pid") or raw.get("product_id") or "----"),
            "serial": str(raw.get("serial") or "Unavailable"),
            "port": str(raw.get("physical_port") or raw.get("port") or "UNKNOWN"),
            "fingerprint": str(raw.get("hardware_fingerprint") or raw.get("identity_fingerprint") or "UNKNOWN"),
            "usbguard_state": str(raw.get("usbguard_state") or "UNKNOWN"),
            "kernel_authorized": raw.get("kernel_authorized"),
            "usb_version": str(raw.get("usb_version") or "Unknown"),
            "category": raw.get("category") or raw.get("device_type") or raw.get("type") or "USB device",
            "classification": raw.get("classification") or "Unknown",
            "capacity": raw.get("capacity", "N/A"), "used_space": raw.get("used_space", "N/A"),
            "free_space": raw.get("free_space", "N/A"), "file_system": raw.get("file_system", "N/A"),
        }

    def apply_event(self, message):
        event = message.get("event", "")
        data = message.get("data", {}) or {}
        incident = message.get("incident_id") or data.get("incident_id")
        if incident:
            self._active_incident = incident
        if event == "device_detected":
            device = self.normalize_device(data)
            self.page_dashboard.apply_backend_device(device)
            self.page_devices.apply_backend_device(device)
            self.page_device_details.apply_backend_device(device)
            self.page_scan.begin_backend_scan(device)
            self.pages_stack.setCurrentIndex(0)
        elif event == "device_state":
            state, detail = data.get("state", "UNKNOWN"), data.get("detail", "")
            self.page_dashboard.apply_backend_state(state, detail)
            self.page_scan.apply_backend_state(state, detail)
            self.page_dashboard.connected_device.update({"usbguard_state": state, "state_detail": detail}) if self.page_dashboard.connected_device else None
            if str(state).upper() in {"DISCONNECTED", "REMOVED"}:
                self.page_dashboard.apply_backend_disconnect()
        elif event == "scan_progress":
            self.page_scan.apply_backend_progress(data)
        elif event == "scan_complete":
            self.page_scan.apply_backend_scan_complete(data)
            self.page_dashboard.apply_backend_scan_complete(data)
        elif event == "finding_detected":
            self.page_scan.apply_backend_finding(data)
            self.page_dashboard.apply_backend_finding(data)
        elif event == "risk_updated":
            self.page_dashboard.apply_backend_risk(data)
            self.page_scan.apply_backend_risk(data)
        elif event == "report_ready":
            self.page_scan.apply_backend_storage_status(data)
            self.page_dashboard.apply_backend_report(data)
            self.page_quarantine.apply_backend_report(data)
            self.page_scan.apply_report_quarantine(data)
            self.page_scan.complete_backend_scan(data)
            device = self.page_dashboard.connected_device or self.normalize_device(data)
            stamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            self.page_history.add_log_entry(device, stamp, str(data.get("verdict", "COMPLETE")))
            self.backend.command("get_snapshot")
        elif event in {"quarantine_updated", "email_delivery_updated", "trust_updated"}:
            self.page_dashboard.notification_center.add_log(
                f"{event.replace('_', ' ').title()}: {data.get('status') or data.get('reason') or 'updated'}"
            )
            self.page_settings.apply_resource_event(event, data)
            if event == "quarantine_updated":
                self.page_scan.apply_quarantine_event(data)
            self.backend.command("get_snapshot")
        elif event == "log":
            self.page_dashboard.notification_center.add_log(str(data.get("message", "Backend update")))
            self.page_scan.add_log_card(str(data.get("message", "Backend update")))
        elif event == "backend_ready":
            self.page_settings.apply_backend_status(data, {})
            self.page_scan.apply_backend_engines(data)
            self.page_dashboard.lbl_status.setText("Secure Terminal: Monitoring")
        elif event == "incident_completed":
            self.page_dashboard.apply_backend_report(data)
            self.page_dashboard.notification_center.add_log("Incident consolidation completed")
            self.backend.command("get_snapshot")
        elif event in {"action_resolved", "action_expired"}:
            self._shown_actions.discard(str(data.get("action_id", "")))
            decision = data.get("decision", "safe default")
            self.page_dashboard.notification_center.add_log(
                f"User action {event.split('_', 1)[1]}: {decision}"
            )
        elif event == "user_action_required":
            self.show_action_required(data)

    @staticmethod
    def decision_choices(action):
        """Normalize both the current IPC list format and legacy dict format."""
        choices, seen = [], set()
        options = action.get("options") or []
        if isinstance(options, dict):
            iterable = []
            for key, value in options.items():
                if isinstance(value, (list, tuple)) and len(value) >= 2:
                    iterable.append({"id": value[0], "key": key, "label": value[1]})
                else:
                    iterable.append({"id": key, "key": key, "label": str(value)})
        else:
            iterable = options
        for item in iterable:
            if not isinstance(item, dict):
                continue
            result = str(item.get("id") or item.get("result") or item.get("key") or "")
            if not result or result in seen:
                continue
            seen.add(result)
            choices.append((result, str(item.get("label") or result.replace("_", " ").title())))
        return choices

    def show_action_required(self, action):
        action_id = action.get("action_id")
        if not action_id or action_id in self._shown_actions:
            return
        self._shown_actions.add(action_id)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("USB scanner — user decision required")
        box.setText(str(action.get("title", "Device decision required")))
        box.setInformativeText(
            f"Device: {action.get('device_name') or action.get('device') or 'Unknown'}\n\n{action.get('summary', '')}\n\n"
            "The device remains blocked until you choose."
        )
        box.setStyleSheet(f"""
            QMessageBox {{ background-color: {theme_manager.get_color('bg')}; }}
            QLabel {{ color: {theme_manager.get_color('text_primary')};
                      font-family: 'Inter'; font-size: 12px; min-width: 440px; }}
            QPushButton {{ background-color: {theme_manager.get_color('accent')}; color: #ffffff;
                           border: none; border-radius: 10px; padding: 10px 18px;
                           font-family: 'Inter'; font-weight: 700; min-width: 260px; min-height: 42px; }}
            QPushButton:hover {{ opacity: 0.92; }}
        """)
        mapping = {}
        labels = set()
        for result, label in self.decision_choices(action):
            label = str(label)
            labels.add(label.casefold())
            button = box.addButton(label, QMessageBox.ButtonRole.AcceptRole)
            button.setMinimumWidth(260)
            button.setMinimumHeight(42)
            mapping[button] = result
        if "keep blocked" not in labels:
            blocked_button = box.addButton("Keep blocked", QMessageBox.ButtonRole.RejectRole)
            blocked_button.setMinimumWidth(260)
            blocked_button.setMinimumHeight(42)
        box.exec()
        decision = mapping.get(
            box.clickedButton(), action.get("safe_default") or action.get("default") or "block"
        )
        sent = self.backend.submit_decision(action_id, decision)
        if sent:
            self.page_dashboard.notification_center.add_log(
                f"Decision submitted: {decision}. Waiting for backend confirmation."
            )
        else:
            self._shown_actions.discard(action_id)
            self.page_dashboard.notification_center.add_log(
                "Decision was not sent because the backend connection is unavailable."
            )

    def switch_page(self, idx):
        target_page = self.pages_stack.widget(idx)
        self.pages_stack.setCurrentIndex(idx)
        
        try:
            from animation import setup_fade_in_animation
            # Trigger standard smooth fade-in entrance transition
            self._fade_anim, self._opacity_effect = setup_fade_in_animation(target_page, 250)
            self._fade_anim.finished.connect(lambda: target_page.setGraphicsEffect(None))
            self._fade_anim.start()
        except (ImportError, ModuleNotFoundError):
            # Fallback if animations.py is not available in the user's workspace
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
            
            opacity_effect = QGraphicsOpacityEffect(target_page)
            target_page.setGraphicsEffect(opacity_effect)
            
            self._fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
            self._fade_anim.setDuration(250)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self._opacity_effect = opacity_effect
            self._fade_anim.finished.connect(lambda: target_page.setGraphicsEffect(None))
            self._fade_anim.start()

    def log_device_authorized(self, device):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.page_history.add_log_entry(device, timestamp, "ALLOWED")

    def log_device_blocked(self, device):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.page_history.add_log_entry(device, timestamp, "BLOCKED")

    def update_theme_styles(self):
        # Trigger repaint on our custom background widget when theme changes
        self.central_widget.update()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
