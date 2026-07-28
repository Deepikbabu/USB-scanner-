"""Backend-driven security operations dashboard."""

from collections import deque

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QLineF, QPropertyAnimation, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient, QBrush
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QTableWidgetItem, QVBoxLayout, QWidget, QGraphicsOpacityEffect,
)

from theme import theme_manager
from widgets import AppButton, AppCard, AppTableWidget, EmptyState, StatusBadge


def _label(text="", muted=False, size=None, weight=None):
    label = QLabel(str(text))
    label.setProperty("muted", muted)
    rules = []
    if size:
        rules.append(f"font-size:{size}px")
    if weight:
        rules.append(f"font-weight:{weight}")
    if rules:
        label.setStyleSheet(";".join(rules))
    return label


class TrendChart(QWidget):
    """Small dependency-free risk chart suitable for Raspberry Pi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0] * 7
        self.reveal = 1.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(650)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._animate)
        self.setMinimumHeight(175)

    def set_values(self, values):
        self.values = list(values[-7:]) or [0]
        self.animation.stop(); self.animation.setStartValue(0.0); self.animation.setEndValue(1.0); self.animation.start()

    def _animate(self, value):
        self.reveal = float(value); self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(12, 14, -12, -22)
        border = theme_manager.get_qcolor("border")
        for step in range(4):
            y = rect.top() + rect.height() * step / 3
            painter.setPen(QPen(border, 1))
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
        if len(self.values) < 2:
            return
        high = max(max(self.values), 1)
        path = QPainterPath()
        for index, value in enumerate(self.values):
            x = rect.left() + rect.width() * index / (len(self.values) - 1)
            y = rect.bottom() - (float(value) / high) * rect.height() * self.reveal
            path.moveTo(x, y) if index == 0 else path.lineTo(x, y)
        fill = QPainterPath(path)
        fill.lineTo(rect.right(), rect.bottom()); fill.lineTo(rect.left(), rect.bottom()); fill.closeSubpath()
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        accent = theme_manager.get_qcolor("accent"); soft = QColor(accent); soft.setAlpha(65)
        clear = QColor(accent); clear.setAlpha(0)
        gradient.setColorAt(0, soft); gradient.setColorAt(1, clear)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(gradient)); painter.drawPath(fill)
        painter.setPen(QPen(theme_manager.get_qcolor("accent"), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class DeviceVisual(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.category = "USB device"
        self.setFixedSize(72, 72)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.pulse_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.pulse_animation.setDuration(1400); self.pulse_animation.setStartValue(.82)
        self.pulse_animation.setEndValue(1.0); self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.start()

    def set_category(self, category):
        self.category = category or "USB device"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent=theme_manager.get_qcolor("accent"); glow=QColor(accent); glow.setAlpha(34)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(glow); painter.drawEllipse(QRectF(4,4,64,64))
        painter.setPen(QPen(accent,2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); painter.setBrush(Qt.BrushStyle.NoBrush)
        category=self.category.casefold()
        if "keyboard" in category:
            painter.drawRoundedRect(QRectF(10,22,52,30),5,5)
            for row in range(3):
                for col in range(6): painter.drawRoundedRect(QRectF(15+col*7.2,27+row*7,4.5,3.5),.8,.8)
        elif "mouse" in category:
            painter.drawRoundedRect(QRectF(23,10,27,49),13,13)
            painter.drawLine(QLineF(36.5,10,36.5,30)); painter.drawLine(QLineF(31,22,42,22))
        else:
            painter.drawRoundedRect(QRectF(23,18,26,39),5,5)
            painter.drawRect(QRectF(28,10,16,8))
            painter.drawLine(QLineF(32,12,32,16)); painter.drawLine(QLineF(40,12,40,16))


class MetricCard(AppCard):
    def __init__(self, title, value="0", accent="accent", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)
        self.title = _label(title, muted=True, size=10, weight=700)
        self.value = _label(value, size=23, weight=800)
        self.value.setStyleSheet(
            f"color:{theme_manager.get_color(accent)};font-size:23px;font-weight:800"
        )
        self.delta = _label("Waiting for live data", muted=True, size=9)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.delta)

    def set_value(self, value, detail=None):
        self.value.setText(str(value))
        if detail is not None:
            self.delta.setText(str(detail))


class LastScanSummaryCard(AppCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        layout.addWidget(_label("LAST SCAN SUMMARY", muted=True, size=10, weight=800))
        self.fields = {}
        for key, title in (
            ("files", "Files scanned"), ("threats", "Threats found"),
            ("risk_score", "Risk score"), ("status", "Final verdict"),
        ):
            row = QHBoxLayout()
            row.addWidget(_label(title, muted=True, size=10))
            row.addStretch()
            value = _label("—", size=11, weight=700)
            self.fields[key] = value
            row.addWidget(value)
            layout.addLayout(row)

    def reset(self):
        for value in self.fields.values():
            value.setText("—")

    def update_scan(self, data):
        self.fields["files"].setText(str(data.get("files", data.get("total_files", 0))))
        self.fields["threats"].setText(str(data.get("threats", 0)))
        risk = data.get("risk_score", data.get("risk", data.get("total")))
        if risk is not None:
            self.fields["risk_score"].setText(f"{risk}/100")
        status = data.get("status", data.get("verdict"))
        if status is not None:
            self.fields["status"].setText(str(status).upper())


class NotificationCenter(AppCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = deque(maxlen=8)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(_label("RECENT ACTIVITY", muted=True, size=10, weight=800))
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(3)
        layout.addLayout(self.list_layout)
        self.empty = _label("No live security events yet", muted=True, size=10)
        self.list_layout.addWidget(self.empty)

    def add_log(self, message):
        self.entries.appendleft(str(message))
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for entry in self.entries:
            label = _label(entry, muted=True, size=10)
            label.setWordWrap(True)
            self.list_layout.addWidget(label)

    def set_activity_status(self, status):
        self.add_log(status)

    def add_timeline_event(self, time_str, event_text):
        self.add_log(f"{time_str}  {event_text}")


class DashboardPage(QWidget):
    retry_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected_device = None
        self._incidents = []
        self._risk_values = deque([0] * 7, maxlen=7)
        self.detection_timer = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(12)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.lbl_status = _label("Security overview", size=20, weight=800)
        self.lbl_subtitle = _label("Waiting for the security engine", muted=True, size=11)
        heading.addWidget(self.lbl_status)
        heading.addWidget(self.lbl_subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.btn_retry = AppButton("Retry backend", "primary")
        self.btn_retry.clicked.connect(self.retry_requested)
        self.btn_retry.hide()
        header.addWidget(self.btn_retry)
        root.addLayout(header)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.metric_devices = MetricCard("DEVICES SCANNED")
        self.metric_files = MetricCard("FILES SCANNED")
        self.metric_threats = MetricCard("THREATS FOUND", accent="danger")
        self.metric_quarantine = MetricCard("FILES QUARANTINED", accent="warning")
        for index, card in enumerate((
            self.metric_devices, self.metric_files, self.metric_threats,
            self.metric_quarantine,
        )):
            metrics.addWidget(card, 0, index)
        root.addLayout(metrics)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        trend_card = AppCard()
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(16, 14, 16, 12)
        title_row = QHBoxLayout()
        title_row.addWidget(_label("RISK TREND", muted=True, size=10, weight=800))
        title_row.addStretch()
        title_row.addWidget(_label("RECENT INCIDENTS", muted=True, size=9))
        trend_layout.addLayout(title_row)
        self.risk_chart = TrendChart()
        trend_layout.addWidget(self.risk_chart)
        middle.addWidget(trend_card, 3)

        device_card = AppCard()
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(16, 14, 16, 14)
        device_layout.addWidget(_label("CURRENT DEVICE", muted=True, size=10, weight=800))
        device_head = QHBoxLayout()
        self.usb_visualizer = DeviceVisual()
        device_head.addWidget(self.usb_visualizer)
        device_text = QVBoxLayout()
        self.lbl_device_name = _label("No device connected", size=14, weight=700)
        self.lbl_device_meta = _label("USB monitoring is active", muted=True, size=10)
        self.device_badge = StatusBadge("Waiting", tone="neutral")
        device_text.addWidget(self.lbl_device_name)
        device_text.addWidget(self.lbl_device_meta)
        device_text.addWidget(self.device_badge, alignment=Qt.AlignmentFlag.AlignLeft)
        device_head.addLayout(device_text, 1)
        device_layout.addLayout(device_head)
        self.lbl_threat_level = _label("Risk level: —", muted=True, size=11, weight=700)
        device_layout.addWidget(self.lbl_threat_level)
        middle.addWidget(device_card, 2)
        root.addLayout(middle, 1)

        lower = QHBoxLayout()
        lower.setSpacing(10)
        self.notification_center = NotificationCenter()
        self.last_scan_card = LastScanSummaryCard()
        lower.addWidget(self.notification_center, 3)
        lower.addWidget(self.last_scan_card, 2)
        root.addLayout(lower)

        # Compatibility control: retained for validators, never shown.
        self.btn_trigger = QPushButton("Simulate")
        self.btn_trigger.hide()

    @staticmethod
    def _category_from_state(state, detail, current):
        detail_text = str(detail or "").lower()
        if "keyboard" in detail_text:
            return "USB Keyboard"
        if "mouse" in detail_text:
            return "USB Mouse"
        if "storage" in detail_text:
            return "USB Flash Drive"
        return current or "USB device"

    def apply_backend_incidents(self, incidents):
        self._incidents = list(incidents or [])
        devices = set()
        for number, incident in enumerate(self._incidents):
            device = incident.get("device")
            serial = device.get("serial") if isinstance(device, dict) else device
            devices.add(str(incident.get("incident_id") or serial or number))
        files = sum(int(i.get("files", i.get("total_files", 0)) or 0) for i in self._incidents)
        threats = sum(int(i.get("threats", 0) or 0) for i in self._incidents)
        quarantined = sum(int(i.get("quarantine_count", 0) or 0) for i in self._incidents)
        risks = [int(i.get("risk_score", i.get("risk", 0)) or 0) for i in self._incidents[-7:]]
        self.metric_devices.set_value(len(devices), "Persisted incidents")
        self.metric_files.set_value(f"{files:,}", "Persisted scan evidence")
        self.metric_threats.set_value(threats, "Confirmed findings")
        self.metric_quarantine.set_value(quarantined, "Isolated files")
        self.risk_chart.set_values(risks or [0])

    def apply_backend_resources(self, resources):
        """Apply authoritative totals derived from persisted report evidence."""
        metrics = dict((resources or {}).get("metrics") or {})
        if metrics:
            self.metric_devices.set_value(metrics.get("incidents", 0), "Persisted reports")
            self.metric_files.set_value(
                f"{int(metrics.get('files_scanned', 0) or 0):,}", "Persisted scan evidence"
            )
            self.metric_threats.set_value(metrics.get("threats_found", 0), "Persisted findings")
            self.metric_quarantine.set_value(
                metrics.get("quarantined_files", 0), "Current vault contents"
            )

    def apply_backend_device(self, device):
        self.connected_device = dict(device or {})
        name = self.connected_device.get("name", "Unknown USB device")
        category = self.connected_device.get("category", "USB device")
        self.lbl_device_name.setText(name)
        self.lbl_device_meta.setText(
            f"{category}  •  {self.connected_device.get('vid', '----')}:"
            f"{self.connected_device.get('pid', '----')}"
        )
        self.usb_visualizer.set_category(category)
        self.device_badge.update_badge("Connected", tone="info")
        self.notification_center.add_log(f"Device detected: {name}")

    def apply_backend_state(self, state, detail=""):
        state_text = str(state or "UNKNOWN").upper()
        category = self._category_from_state(
            state_text, detail,
            self.connected_device.get("category") if self.connected_device else None,
        )
        if self.connected_device is not None:
            self.connected_device["category"] = category
            self.connected_device["usbguard_state"] = state_text
        self.usb_visualizer.set_category(category)
        tone = "success" if state_text in {"ALLOWED", "TRUSTED", "CLEAN"} else (
            "danger" if state_text in {"BLOCKED", "DANGEROUS"} else "info"
        )
        self.device_badge.update_badge(state_text, tone=tone)
        if detail:
            self.lbl_device_meta.setText(str(detail))
        self.notification_center.add_log(f"Device state: {state_text}")

    def apply_backend_risk(self, data):
        risk = int(data.get("total", data.get("risk_score", 0)) or 0)
        self._risk_values.append(risk)
        self.risk_chart.set_values(list(self._risk_values))
        level = "DANGEROUS" if risk >= 70 else "HIGH" if risk >= 40 else "MEDIUM" if risk >= 20 else "LOW"
        self.lbl_threat_level.setText(f"Risk level: {level}  •  {risk}/100")
        self.last_scan_card.fields["risk_score"].setText(f"{risk}/100")

    def apply_backend_finding(self, data):
        finding = data.get("finding") or data.get("reason") or "Security finding"
        self.metric_threats.set_value(
            int(self.metric_threats.value.text().replace(",", "") or 0) + 1,
            "Live finding detected",
        )
        self.notification_center.add_log(str(finding))

    def apply_backend_scan_complete(self, data):
        self.last_scan_card.update_scan(data)
        self.metric_files.set_value(f"{int(data.get('files', 0) or 0):,}", "Latest scan")

    def apply_backend_report(self, data):
        verdict = str(data.get("verdict", "INCOMPLETE")).upper()
        payload = dict(data)
        payload["status"] = verdict
        payload.setdefault("risk_score", data.get("total", 0))
        self.last_scan_card.update_scan(payload)
        tone = "success" if verdict in {"CLEAN", "TRUSTED"} else (
            "danger" if verdict == "DANGEROUS" else "warning"
        )
        self.device_badge.update_badge(verdict, tone=tone)
        self.lbl_threat_level.setText(
            f"{verdict}  •  {self.last_scan_card.fields['risk_score'].text()}"
        )
        self.notification_center.add_log(f"Incident report ready: {verdict}")

    def apply_backend_disconnect(self):
        self.connected_device = None
        self.lbl_device_name.setText("No device connected")
        self.lbl_device_meta.setText("USB monitoring is active")
        self.device_badge.update_badge("Waiting", tone="neutral")
        self.usb_visualizer.set_category("USB device")

    # Compatibility hooks used by older page code.
    def detect_new_device(self, device):
        self.apply_backend_device(device)

    def reset_to_idle(self, logged_eject_device=None):
        self.apply_backend_disconnect()

    def on_scan_completed(self, scan_data):
        self.apply_backend_scan_complete(scan_data)

    def start_simulated_detection_timer(self, delay_ms):
        return None

    def update_styles(self):
        self.update()
