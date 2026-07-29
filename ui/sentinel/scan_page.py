"""Focused, backend-driven live scan workspace."""

from pathlib import Path
import os
import re
from collections import deque

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QProgressBar, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from theme import theme_manager
from widgets import AppButton, AppCard, AppTableWidget, StatusBadge


def _label(text="", muted=False, size=None, weight=None):
    label = QLabel(str(text))
    label.setProperty("muted", muted)
    style = []
    if size:
        style.append(f"font-size:{size}px")
    if weight:
        style.append(f"font-weight:{weight}")
    if style:
        label.setStyleSheet(";".join(style))
    return label


class ScanRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(420); self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._set_animated_value)
        self.setFixedSize(170, 170)

    def setValue(self, value):
        target=max(0,min(100,int(value or 0))); self.animation.stop()
        self.animation.setStartValue(float(self.value)); self.animation.setEndValue(float(target)); self.animation.start()

    def _set_animated_value(self,value):
        self.value=float(value); self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(13, 13, -13, -13)
        pen = QPen(theme_manager.get_qcolor("border"), 12)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        pen.setColor(theme_manager.get_qcolor("accent"))
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, int(-self.value * 360 * 16 / 100))
        painter.setPen(theme_manager.get_qcolor("text_primary"))
        font = painter.font()
        font.setPixelSize(31)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self.value)}%")


class ThroughputChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = deque([0.0] * 24, maxlen=24)
        self.setMinimumSize(160, 70)
        self.setAccessibleName("Real-time scan throughput chart")

    def add_value(self, value):
        self.values.append(max(0.0, float(value or 0)))
        self.update()

    def reset(self):
        self.values = deque([0.0] * 24, maxlen=24)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(5, 7, -5, -7)
        painter.setPen(QPen(theme_manager.get_qcolor("border"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        high = max(max(self.values), 1.0)
        points = []
        for index, value in enumerate(self.values):
            x = rect.left() + rect.width() * index / max(len(self.values) - 1, 1)
            y = rect.bottom() - rect.height() * value / high
            points.append((x, y))
        painter.setPen(QPen(theme_manager.get_qcolor("accent"), 2))
        for first, second in zip(points, points[1:]):
            painter.drawLine(
                QPointF(first[0], first[1]), QPointF(second[0], second[1])
            )


class InventoryCard(AppCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(_label("SCAN INVENTORY", muted=True, size=10, weight=800))
        grid = QGridLayout()
        self.items = {}
        for index, name in enumerate(("Files", "Folders", "Executables", "Archives", "Hidden")):
            title = _label(name, muted=True, size=9)
            value = _label("0", size=15, weight=800)
            self.items[name] = {"label": value, "title": title}
            grid.addWidget(title, index // 3 * 2, index % 3)
            grid.addWidget(value, index // 3 * 2 + 1, index % 3)
        layout.addLayout(grid)

    def update_inventory(self, data):
        mapping = {
            "Files": "files", "Folders": "folders", "Executables": "executables",
            "Archives": "archives", "Hidden": "hidden",
        }
        for title, key in mapping.items():
            self.items[title]["label"].setText(str(data.get(key, 0)))


class ThreatCard(AppCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addWidget(_label("RISK ASSESSMENT", muted=True, size=10, weight=800))
        self.lbl_level = _label("LOW", size=20, weight=800)
        self.lbl_malware_name = _label("No findings reported", size=11, weight=700)
        self.lbl_malware_location = _label("Live engine findings will appear below", muted=True, size=9)
        self.lbl_recommendation = _label("Waiting for backend risk analysis", muted=True, size=10)
        self.lbl_recommendation.setWordWrap(True)
        layout.addWidget(self.lbl_level)
        layout.addWidget(self.lbl_malware_name)
        layout.addWidget(self.lbl_malware_location)
        layout.addWidget(self.lbl_recommendation)


class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_progress = 0
        self.latest_report_path = None
        self.findings = []
        self.backend_logs = []
        self.scan_timer = QTimer(self)  # Compatibility only; never starts simulation.
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(10)

        header = AppCard()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        device_text = QVBoxLayout()
        self.lbl_status = _label("Waiting for a USB device", size=19, weight=800)
        self.lbl_scan_info = _label(
            "The backend will start analysis when an eligible device is connected.",
            muted=True, size=10,
        )
        device_text.addWidget(self.lbl_status)
        device_text.addWidget(self.lbl_scan_info)
        header_layout.addLayout(device_text, 1)
        self.scan_badge = StatusBadge("Idle", tone="neutral")
        header_layout.addWidget(self.scan_badge)
        root.addWidget(header)
        self.phase_label = _label(
            "01  ISOLATE   ·   02  INVENTORY   ·   03  ANALYZE   ·   04  REMEDIATE   ·   05  REPORT",
            muted=True, size=9, weight=700,
        )
        self.phase_label.setAccessibleName("Scan phase timeline")
        root.addWidget(self.phase_label)

        overview = QHBoxLayout()
        overview.setSpacing(10)
        progress_card = AppCard()
        progress_layout = QHBoxLayout(progress_card)
        progress_layout.setContentsMargins(20, 16, 20, 16)
        self.progress_ring = ScanRing()
        progress_layout.addWidget(self.progress_ring)
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(26)
        metrics.setVerticalSpacing(8)
        self.metric_labels = {}
        for index, (key, title) in enumerate((
            ("files", "Files scanned"), ("speed", "Scan speed"),
            ("elapsed", "Elapsed time"), ("remaining", "Estimated remaining"),
        )):
            metrics.addWidget(_label(title, muted=True, size=9), index, 0)
            value = _label("—", size=11, weight=700)
            self.metric_labels[key] = value
            metrics.addWidget(value, index, 1)
        progress_layout.addLayout(metrics, 1)
        chart_host = QVBoxLayout()
        chart_host.addWidget(_label("LIVE THROUGHPUT", muted=True, size=9, weight=800))
        self.throughput_chart = ThroughputChart()
        chart_host.addWidget(self.throughput_chart)
        progress_layout.addLayout(chart_host)
        overview.addWidget(progress_card, 3)

        engines = AppCard()
        engine_layout = QVBoxLayout(engines)
        engine_layout.setContentsMargins(16, 14, 16, 14)
        engine_layout.addWidget(_label("SECURITY ENGINES", muted=True, size=10, weight=800))
        self.engine_badges = {}
        for engine in ("USBGuard", "YARA", "ClamAV", "Hash database"):
            row = QHBoxLayout()
            row.addWidget(_label(engine, size=10, weight=600))
            row.addStretch()
            badge = StatusBadge("Waiting", tone="neutral")
            self.engine_badges[engine.lower()] = badge
            row.addWidget(badge)
            engine_layout.addLayout(row)
        overview.addWidget(engines, 2)
        root.addLayout(overview)

        self.coverage = QProgressBar()
        self.coverage.setRange(0, 100)
        self.coverage.setValue(0)
        self.coverage.setTextVisible(True)
        self.coverage.setFormat("Scan coverage  %p%")
        root.addWidget(self.coverage)

        lower = QHBoxLayout()
        lower.setSpacing(10)
        findings_card = AppCard()
        findings_layout = QVBoxLayout(findings_card)
        findings_layout.setContentsMargins(16, 14, 16, 14)
        finding_head = QHBoxLayout()
        finding_head.addWidget(_label("LIVE FINDINGS", muted=True, size=10, weight=800))
        finding_head.addStretch()
        self.lbl_finding_count = _label("0 findings", muted=True, size=9)
        finding_head.addWidget(self.lbl_finding_count)
        findings_layout.addLayout(finding_head)
        self.findings_table = AppTableWidget(0, 4)
        self.findings_table.setHorizontalHeaderLabels(("Severity", "Finding", "File", "Engine"))
        findings_layout.addWidget(self.findings_table)
        lower.addWidget(findings_card, 3)

        right = QVBoxLayout()
        self.inventory_card = InventoryCard()
        self.threat_card = ThreatCard()
        right.addWidget(self.inventory_card)
        right.addWidget(self.threat_card)
        lower.addLayout(right, 2)
        root.addLayout(lower, 1)

        self.quarantine_card = AppCard()
        quarantine_layout = QHBoxLayout(self.quarantine_card)
        quarantine_layout.setContentsMargins(16, 10, 16, 10)
        quarantine_layout.addWidget(_label("QUARANTINE", muted=True, size=10, weight=800))
        self.lbl_quarantine_status = _label("No quarantine action", size=10, weight=700)
        quarantine_layout.addWidget(self.lbl_quarantine_status, 1)
        self.quarantine_card.hide()
        root.addWidget(self.quarantine_card)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_report = AppButton("Open latest report")
        self.btn_report.setEnabled(False)
        self.btn_report.clicked.connect(self.open_latest_report)
        actions.addWidget(self.btn_report)
        self.btn_cancel = AppButton("Cancel scan", "danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setToolTip("Cancellation is unavailable until supported by the backend")
        self.btn_cancel.hide()
        actions.addWidget(self.btn_cancel)
        root.addLayout(actions)

    def begin_backend_scan(self, device):
        self.clear_logs_and_warnings()
        self.scan_progress = 0
        self.progress_ring.setValue(0)
        self.coverage.setValue(0)
        self.throughput_chart.reset()
        self._set_phase(1)
        name = device.get("name", "Unknown USB device")
        meta = f"{device.get('category', 'USB device')}  •  {device.get('serial', 'Serial unavailable')}"
        self.lbl_status.setText(name)
        self.lbl_scan_info.setText(meta)
        self.scan_badge.update_badge("Preparing", tone="info")

    def apply_backend_progress(self, data):
        self.scan_progress = int(data.get("progress", self.scan_progress) or 0)
        self.progress_ring.setValue(self.scan_progress)
        self.coverage.setValue(self.scan_progress)
        self.scan_badge.update_badge("Scanning", tone="info")
        self.lbl_scan_info.setText(str(data.get("message") or "Security analysis in progress"))
        for key in ("files", "speed", "elapsed", "remaining"):
            if key in data:
                self.metric_labels[key].setText(str(data[key]))
        speed_match = re.search(r"[\d.]+", str(data.get("speed", "0")))
        if speed_match:
            self.throughput_chart.add_value(float(speed_match.group(0)))
        self._set_phase(2 if self.scan_progress < 15 else 3 if self.scan_progress < 90 else 4)

    def apply_backend_scan_complete(self, data):
        inventory = dict(data.get("inventory") or {})
        inventory.setdefault("files", data.get("files", 0))
        self.inventory_card.update_inventory(inventory)
        self.metric_labels["files"].setText(str(inventory.get("files", 0)))
        self.lbl_scan_info.setText("Scan complete; consolidating final evidence and verdict.")
        self.scan_badge.update_badge("Consolidating", tone="warning")
        self._set_phase(5)

    def _set_phase(self, active):
        names = ("ISOLATE", "INVENTORY", "ANALYZE", "REMEDIATE", "REPORT")
        parts = []
        for index, name in enumerate(names, 1):
            marker = "●" if index == active else "✓" if index < active else "○"
            parts.append(f"{marker} {index:02d} {name}")
        self.phase_label.setText("   ·   ".join(parts))

    def apply_backend_state(self, state, detail=""):
        state_text = str(state or "UNKNOWN").upper()
        tone = "danger" if state_text in {"BLOCKED", "DANGEROUS"} else (
            "success" if state_text in {"ALLOWED", "TRUSTED", "CLEAN"} else "info"
        )
        self.scan_badge.update_badge(state_text, tone=tone)
        if detail:
            self.lbl_scan_info.setText(str(detail))

    def apply_backend_engines(self, data):
        aliases = {
            "usbguard": ("usbguard",), "yara": ("yara",),
            "clamav": ("clamav",), "hash database": ("database", "hash_database", "hash"),
        }
        for name, keys in aliases.items():
            value = next((data[k] for k in keys if k in data), None)
            ready = value is True or str(value).upper() in {"READY", "ONLINE", "OK", "TRUE"}
            self.engine_badges[name].update_badge(
                "Ready" if ready else "Unavailable", tone="success" if ready else "warning"
            )

    def apply_backend_storage_status(self, data):
        path = data.get("pdf_path") or data.get("report_path")
        if path:
            self.latest_report_path = str(path)
            self.btn_report.setEnabled(True)

    def apply_backend_finding(self, data):
        finding = str(data.get("finding") or data.get("reason") or "Security finding")
        severity = str(data.get("severity") or data.get("level") or "UNKNOWN").upper()
        path = str(data.get("path") or data.get("file") or "—")
        engine = str(data.get("engine") or "Scanner")
        self.findings.append(dict(data))
        row = self.findings_table.rowCount()
        self.findings_table.insertRow(row)
        for column, value in enumerate((severity, finding, path, engine)):
            self.findings_table.setItem(row, column, QTableWidgetItem(value))
        self.lbl_finding_count.setText(f"{len(self.findings)} finding{'s' if len(self.findings) != 1 else ''}")
        self.threat_card.lbl_malware_name.setText(finding)
        self.threat_card.lbl_malware_location.setText(path)

    def apply_backend_risk(self, data):
        total = int(data.get("total", data.get("risk_score", 0)) or 0)
        post = int(data.get("final_total", total) or 0)
        level = "CRITICAL" if total >= 70 else "HIGH" if total >= 40 else "MEDIUM" if total >= 20 else "LOW"
        self.threat_card.lbl_level.setText(f"{level}  •  {total}/100")
        self.threat_card.lbl_recommendation.setText(
            f"Original risk: {total}/100  •  post-remediation score: {post}/100"
        )

    def clear_quarantine_evidence(self):
        self.quarantine_card.hide()
        self.lbl_quarantine_status.setText("No quarantine action")

    def apply_quarantine_event(self, entry):
        verified = all(bool(entry.get(key)) for key in (
            "hash_verified", "source_removed", "execute_disabled",
        )) if any(key in entry for key in ("hash_verified", "source_removed", "execute_disabled")) else bool(entry.get("verified"))
        name = entry.get("original_name") or entry.get("name") or "Quarantined file"
        self.lbl_quarantine_status.setText(
            f"{name}  •  {'VERIFIED' if verified else 'INTEGRITY CHECK REQUIRED'}"
        )
        self.quarantine_card.show()

    def apply_report_quarantine(self, data):
        quarantine = data.get("quarantine") or {}
        items = quarantine.get("items", []) if isinstance(quarantine, dict) else quarantine
        items = [item for item in items if isinstance(item, dict)]
        if items:
            self.apply_quarantine_event(items[-1])

    def complete_backend_scan(self, data):
        verdict = str(data.get("verdict", "INCOMPLETE")).upper()
        tone = "success" if verdict in {"CLEAN", "TRUSTED"} else (
            "danger" if verdict == "DANGEROUS" else "warning"
        )
        self.lbl_status.setText(f"Scan result: {verdict}")
        self.lbl_scan_info.setText("Final report and evidence are ready.")
        self.scan_badge.update_badge(verdict, tone=tone)
        self.apply_backend_storage_status(data)

    def open_latest_report(self):
        if self.latest_report_path and Path(self.latest_report_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(self.latest_report_path)))

    def start_scan(self):
        self.lbl_scan_info.setText("Waiting for the backend to start an authorized scan.")

    def add_log_card(self, message):
        # Operational logs must never inflate security-finding metrics.
        self.backend_logs.append(str(message))
        self.backend_logs = self.backend_logs[-100:]
        self.lbl_scan_info.setText(str(message))

    def add_warning(self, title, description, level):
        self.apply_backend_finding(
            {"severity": level, "finding": title, "path": description, "engine": "Policy"}
        )

    def popup_suspicious(self, name, path, reason):
        self.apply_backend_finding(
            {"severity": "HIGH", "finding": reason, "path": path, "engine": name}
        )

    def clear_logs_and_warnings(self):
        self.findings.clear()
        self.backend_logs.clear()
        self.findings_table.setRowCount(0)
        self.lbl_finding_count.setText("0 findings")
        self.inventory_card.update_inventory({})
        self.threat_card.lbl_level.setText("LOW")
        self.threat_card.lbl_malware_name.setText("No findings reported")
        self.threat_card.lbl_malware_location.setText("Live engine findings will appear below")
        self.threat_card.lbl_recommendation.setText("Waiting for backend risk analysis")
        self.clear_quarantine_evidence()

    def update_styles(self):
        self.update()
