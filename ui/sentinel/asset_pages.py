"""Devices, quarantine, and contextual device detail pages."""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from theme import theme_manager
from widgets import AppButton, AppCard, AppTableWidget, EmptyState, StatusBadge


def label(text="", muted=False, size=None, weight=None):
    widget = QLabel(str(text))
    widget.setProperty("muted", muted)
    rules = []
    if size:
        rules.append(f"font-size:{size}px")
    if weight:
        rules.append(f"font-weight:{weight}")
    if rules:
        widget.setStyleSheet(";".join(rules))
    return widget


def format_bytes(value):
    try:
        size = float(value or 0)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


class KpiCard(AppCard):
    def __init__(self, title, value="0", tone="accent", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(4)
        layout.addWidget(label(title, muted=True, size=10, weight=700))
        self.value = label(value, size=22, weight=800)
        self.value.setStyleSheet(
            f"color:{theme_manager.get_color(tone)};font-size:22px;font-weight:800"
        )
        layout.addWidget(self.value)


class PageHeader(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(label(title, size=20, weight=800))
        layout.addWidget(label(subtitle, muted=True, size=11))


class DevicesPage(QWidget):
    """Live device inventory merged with persisted incidents."""

    device_selected = pyqtSignal(dict)

    HEADERS = (
        "Device", "Type", "Status", "Trust", "Verdict", "Serial",
        "Physical port", "Fingerprint", "Last seen",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._incidents = []
        self._connected = {}
        self._visible_records = []
        self._trusted_identities = set()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(11)
        root.addWidget(PageHeader(
            "Device inventory",
            "Connected and previously analyzed USB identities, trust, and verdict state.",
        ))

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.kpi_total = KpiCard("KNOWN DEVICES")
        self.kpi_connected = KpiCard("CONNECTED NOW", tone="success")
        self.kpi_blocked = KpiCard("BLOCKED", tone="danger")
        self.kpi_trusted = KpiCard("TRUSTED", tone="info")
        for card in (self.kpi_total, self.kpi_connected, self.kpi_blocked, self.kpi_trusted):
            metrics.addWidget(card)
        root.addLayout(metrics)

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search device, serial, port, VID:PID or fingerprint…")
        self.search.textChanged.connect(self._apply_filters)
        controls.addWidget(self.search, 1)
        self.status_filter = QComboBox()
        self.status_filter.addItems(("All states", "Connected", "Disconnected", "Blocked"))
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        controls.addWidget(self.status_filter)
        self.verdict_filter = QComboBox()
        self.verdict_filter.addItems(
            ("All verdicts", "CLEAN", "TRUSTED", "SUSPICIOUS", "DANGEROUS", "INCOMPLETE")
        )
        self.verdict_filter.currentTextChanged.connect(self._apply_filters)
        controls.addWidget(self.verdict_filter)
        root.addLayout(controls)

        self.table = AppTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._open_record)
        root.addWidget(self.table, 1)
        self.empty_state = EmptyState(
            "No devices recorded",
            "Connected devices and persisted scan incidents will appear here automatically.",
            "▣",
        )
        root.addWidget(self.empty_state)

        footer = QHBoxLayout()
        self.status = label("0 devices", muted=True, size=10)
        footer.addWidget(self.status)
        footer.addStretch()
        footer.addWidget(label("Double-click a row to inspect identity details", muted=True, size=9))
        root.addLayout(footer)
        self._render()

    @staticmethod
    def _device_record(raw, **overrides):
        source = dict(raw or {}) if isinstance(raw, dict) else {"name": str(raw or "Unknown device")}
        record = {
            "name": source.get("name") or source.get("product") or source.get("device") or "Unknown USB device",
            "type": source.get("category") or source.get("device_type") or "USB device",
            "status": source.get("status") or source.get("state") or "Disconnected",
            "trust": source.get("trust_status") or source.get("trusted") or "Unreviewed",
            "verdict": source.get("verdict") or "INCOMPLETE",
            "serial": source.get("serial") or "Unavailable",
            "port": source.get("physical_port") or source.get("port") or "Unknown",
            "fingerprint": source.get("fingerprint") or source.get("hardware_fingerprint") or "Unavailable",
            "last_seen": source.get("last_scan") or source.get("updated") or "Unknown",
            "vid": source.get("vid") or source.get("vendor_id") or "----",
            "pid": source.get("pid") or source.get("product_id") or "----",
            **source,
        }
        record.update(overrides)
        if isinstance(record["trust"], bool):
            record["trust"] = "Trusted" if record["trust"] else "Unreviewed"
        return record

    def apply_backend_device(self, device):
        record = self._device_record(
            device, status="Connected",
            verdict=device.get("verdict") or "PENDING",
            last_seen="Live",
        )
        identity = str(
            device.get("fingerprint") or device.get("serial")
            or f"{device.get('vid')}:{device.get('pid')}:{device.get('port')}"
        )
        self._connected[identity] = record
        self._apply_filters()

    def apply_backend_state(self, state, detail=""):
        if not self._connected:
            return
        identity = next(reversed(self._connected))
        record = self._connected[identity]
        record["status"] = str(state or "UNKNOWN").title()
        detail_text = str(detail or "").casefold()
        if "keyboard" in detail_text:
            record["type"] = record["category"] = "USB Keyboard"
        elif "mouse" in detail_text:
            record["type"] = record["category"] = "USB Mouse"
        elif "storage" in detail_text:
            record["type"] = record["category"] = "USB Flash Drive"
        if detail:
            record["state_detail"] = detail
        self._apply_filters()

    def apply_backend_incidents(self, incidents):
        records = []
        for incident in incidents or []:
            device = incident.get("device")
            raw = device if isinstance(device, dict) else {"name": device}
            records.append(self._device_record(
                raw,
                status=incident.get("state") or "Disconnected",
                verdict=incident.get("verdict") or "INCOMPLETE",
                last_seen=incident.get("updated") or "Unknown",
                incident_id=incident.get("incident_id"),
                risk=incident.get("risk", 0),
            ))
        self._incidents = records
        self._apply_filters()

    def apply_backend_resources(self, resources):
        """Use backend trust stores for the trusted-device metric and row state."""
        resources = dict(resources or {})
        identities = set()
        signed = resources.get("signed_trust") or []
        for item in signed if isinstance(signed, list) else []:
            identities.add(str(item.get("identity") or "").casefold())
        for store_name in ("trusted_hid", "trusted_storage"):
            store = resources.get(store_name) or {}
            if isinstance(store, dict):
                identities.update(str(key).casefold() for key in store)
        self._trusted_identities = {identity for identity in identities if identity}
        for record in self._records():
            evidence = " ".join(str(record.get(key, "")) for key in (
                "fingerprint", "serial", "vid", "pid", "name",
            )).casefold() + " " + (
                f"{record.get('vid', '')}:{record.get('pid', '')}".casefold()
            )
            if any(identity in evidence or evidence in identity
                   for identity in self._trusted_identities if evidence):
                record["trust"] = "Trusted"
        self._apply_filters()

    def apply_backend_disconnect(self):
        for record in self._connected.values():
            record["status"] = "Disconnected"
            record["last_seen"] = "Just now"
        self._connected.clear()
        self._apply_filters()

    def _records(self):
        records = list(self._connected.values())
        live_keys = {
            str(r.get("fingerprint") or r.get("serial") or r.get("name")).casefold()
            for r in records
        }
        for record in self._incidents:
            key = str(record.get("fingerprint") or record.get("serial") or record.get("name")).casefold()
            if key not in live_keys:
                records.append(record)
        return records

    def _apply_filters(self, *_):
        query = self.search.text().strip().casefold()
        state = self.status_filter.currentText()
        verdict = self.verdict_filter.currentText()
        records = []
        for record in self._records():
            haystack = " ".join(str(value) for value in record.values()).casefold()
            current_state = str(record.get("status", ""))
            if query and query not in haystack:
                continue
            if state != "All states" and state.casefold() not in current_state.casefold():
                continue
            if verdict != "All verdicts" and verdict != str(record.get("verdict", "")).upper():
                continue
            records.append(record)
        self._visible_records = records
        self._render()

    def _render(self):
        records = self._visible_records
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = (
                record["name"], record["type"], record["status"], record["trust"],
                str(record["verdict"]).upper(), record["serial"], record["port"],
                record["fingerprint"], record["last_seen"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row)
                if column == 4:
                    verdict = str(value).upper()
                    token = ("success" if verdict in {"CLEAN", "TRUSTED"} else
                             "danger" if verdict == "DANGEROUS" else
                             "warning" if verdict in {"SUSPICIOUS", "INCOMPLETE"} else
                             "text_secondary")
                    item.setForeground(QBrush(theme_manager.get_qcolor(token)))
                elif column == 2 and "connect" in str(value).casefold():
                    item.setForeground(QBrush(theme_manager.get_qcolor("success")))
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.setVisible(bool(records))
        self.empty_state.setVisible(not records)
        all_records = self._records()
        blocked = sum("block" in str(r.get("status", "")).casefold() for r in all_records)
        trusted_rows = sum(
            str(r.get("trust", "")).casefold() == "trusted"
            or str(r.get("verdict", "")).upper() == "TRUSTED" for r in all_records
        )
        self.kpi_total.value.setText(str(len(all_records)))
        self.kpi_connected.value.setText(str(len(self._connected)))
        self.kpi_blocked.value.setText(str(blocked))
        self.kpi_trusted.value.setText(str(max(trusted_rows, len(self._trusted_identities))))
        self.status.setText(f"{len(records)} of {len(all_records)} devices")

    def _open_record(self, row, column):
        item = self.table.item(row, 0)
        source_index = item.data(Qt.ItemDataRole.UserRole) if item else None
        if isinstance(source_index, int) and source_index < len(self._visible_records):
            self.device_selected.emit(dict(self._visible_records[source_index]))


class QuarantinePage(QWidget):
    """Verified quarantine vault with explicit per-item remediation."""

    restore_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    details_requested = pyqtSignal(int)

    HEADERS = (
        "Filename", "Threat / reason", "Original path", "Quarantined",
        "Size", "Integrity", "Actions",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._visible_items = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(11)
        root.addWidget(PageHeader(
            "Quarantine vault",
            "Isolated files remain non-executable. Restore requires current-engine verification.",
        ))
        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.kpi_total = KpiCard("QUARANTINED FILES", tone="warning")
        self.kpi_size = KpiCard("VAULT STORAGE", "0 B")
        self.kpi_verified = KpiCard("INTEGRITY VERIFIED", tone="success")
        self.kpi_attention = KpiCard("NEEDS ATTENTION", tone="danger")
        for card in (self.kpi_total, self.kpi_size, self.kpi_verified, self.kpi_attention):
            metrics.addWidget(card)
        root.addLayout(metrics)

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search filename, original path, hash or threat…")
        self.search.textChanged.connect(self._apply_filters)
        controls.addWidget(self.search, 1)
        self.integrity_filter = QComboBox()
        self.integrity_filter.addItems(("All integrity states", "Verified", "Needs attention"))
        self.integrity_filter.currentTextChanged.connect(self._apply_filters)
        controls.addWidget(self.integrity_filter)
        root.addLayout(controls)

        self.table = AppTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.cellDoubleClicked.connect(self._show_details)
        root.addWidget(self.table, 1)
        self.empty_state = EmptyState(
            "Quarantine is empty",
            "Files isolated by YARA, ClamAV, hash, or policy findings will appear here.",
            "♢",
        )
        root.addWidget(self.empty_state)
        self.status = label("0 quarantined files", muted=True, size=10)
        root.addWidget(self.status)
        self._render()

    @staticmethod
    def _normalize_item(item, index):
        raw = dict(item or {})
        checks_present = any(
            key in raw for key in ("hash_verified", "source_removed", "execute_disabled")
        )
        verified = bool(raw.get("integrity_verified")) if "integrity_verified" in raw else all(bool(raw.get(key)) for key in (
            "hash_verified", "source_removed", "execute_disabled",
        )) if checks_present else bool(raw.get("verified", raw.get("integrity") in {"Verified", "Intact"}))
        return {
            **raw,
            # The production quarantine API is deliberately one-based.
            "backend_index": int(raw.get("backend_index", raw.get("index", index + 1))),
            "name": raw.get("original_name") or raw.get("name") or raw.get("filename") or "Unknown file",
            "reason": raw.get("reason") or raw.get("threat_type") or raw.get("threat") or "Security finding",
            "original_path": raw.get("original_path") or raw.get("path") or "Unavailable",
            "timestamp": raw.get("timestamp") or raw.get("quarantine_time") or raw.get("created_at") or "Unknown",
            "size": raw.get("size", raw.get("file_size", 0)),
            "verified": verified,
            "sha256": raw.get("sha256") or raw.get("hash") or "Unavailable",
        }

    def apply_backend_resources(self, resources):
        items = resources.get("quarantine", []) if isinstance(resources, dict) else []
        self.set_items(items)

    def apply_backend_report(self, data):
        quarantine = data.get("quarantine") or {}
        items = quarantine.get("items", []) if isinstance(quarantine, dict) else quarantine
        # Canonical report evidence may contain only vault paths. Detailed
        # records arrive from the authoritative resources snapshot.
        items = [item for item in items if isinstance(item, dict)]
        if items:
            known = {
                (item.get("quarantine_path"), item.get("sha256")) for item in self._items
            }
            merged = list(self._items)
            for item in items:
                key = (item.get("quarantine_path"), item.get("sha256"))
                if key not in known:
                    merged.append(item)
            self.set_items(merged)

    def apply_backend_event(self, item):
        self.apply_backend_report({"quarantine": {"items": [item]}})

    def set_items(self, items):
        self._items = [self._normalize_item(item, index) for index, item in enumerate(items or [])]
        self._apply_filters()

    def _apply_filters(self, *_):
        query = self.search.text().strip().casefold()
        integrity = self.integrity_filter.currentText()
        visible = []
        for item in self._items:
            haystack = " ".join(str(value) for value in item.values()).casefold()
            if query and query not in haystack:
                continue
            if integrity == "Verified" and not item["verified"]:
                continue
            if integrity == "Needs attention" and item["verified"]:
                continue
            visible.append(item)
        self._visible_items = visible
        self._render()

    def _render(self):
        items = self._visible_items
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = (
                item["name"], item["reason"], item["original_path"], item["timestamp"],
                format_bytes(item["size"]), "Verified" if item["verified"] else "Needs attention",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, item["backend_index"])
                if column == 5:
                    cell.setForeground(QBrush(theme_manager.get_qcolor(
                        "success" if item["verified"] else "danger"
                    )))
                self.table.setItem(row, column, cell)
            host = QWidget()
            actions = QHBoxLayout(host)
            actions.setContentsMargins(2, 1, 2, 1)
            actions.setSpacing(4)
            view = AppButton("View", "ghost")
            restore = AppButton("Restore")
            delete = AppButton("Delete", "danger")
            index = item["backend_index"]
            view.clicked.connect(lambda checked=False, value=index: self.details_requested.emit(value))
            restore.clicked.connect(lambda checked=False, value=index: self.restore_requested.emit(value))
            delete.clicked.connect(lambda checked=False, value=index: self.delete_requested.emit(value))
            for button in (view, restore, delete):
                button.setMinimumHeight(28)
                actions.addWidget(button)
            self.table.setCellWidget(row, 6, host)
        self.table.resizeColumnsToContents()
        self.table.setVisible(bool(items))
        self.empty_state.setVisible(not items)
        total_size = sum(float(item.get("size") or 0) for item in self._items)
        verified = sum(bool(item["verified"]) for item in self._items)
        self.kpi_total.value.setText(str(len(self._items)))
        self.kpi_size.value.setText(format_bytes(total_size))
        self.kpi_verified.value.setText(str(verified))
        self.kpi_attention.value.setText(str(len(self._items) - verified))
        self.status.setText(f"{len(items)} of {len(self._items)} quarantined files")

    def _show_details(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.details_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))


class DeviceDetailsPage(QWidget):
    """Context page populated by a selection from Devices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(12)
        root.addWidget(PageHeader(
            "Device details", "Hardware identity, trust evidence, and latest security state."
        ))
        self.summary = AppCard()
        summary_layout = QVBoxLayout(self.summary)
        self.device_name = label("No device selected", size=18, weight=800)
        self.device_state = StatusBadge("Unavailable", tone="neutral")
        summary_layout.addWidget(self.device_name)
        summary_layout.addWidget(self.device_state, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.summary)
        self.table = AppTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(("Property", "Value"))
        root.addWidget(self.table, 1)
        self.empty_state = EmptyState(
            "Select a device", "Double-click a device in Device Inventory to inspect it.", "▣"
        )
        root.addWidget(self.empty_state)
        self.apply_backend_device({})

    def apply_backend_device(self, device):
        device = dict(device or {})
        self.device_name.setText(device.get("name") or "No device selected")
        state = str(device.get("status") or device.get("usbguard_state") or "Unavailable")
        tone = "success" if state.upper() in {"CONNECTED", "ALLOWED", "TRUSTED"} else "neutral"
        self.device_state.update_badge(state, tone=tone)
        fields = (
            ("Manufacturer", device.get("manufacturer") or device.get("vendor")),
            ("Category", device.get("category") or device.get("type")),
            ("VID:PID", f"{device.get('vid', '----')}:{device.get('pid', '----')}"),
            ("Serial number", device.get("serial")),
            ("Physical port", device.get("physical_port") or device.get("port")),
            ("Fingerprint", device.get("fingerprint") or device.get("hardware_fingerprint")),
            ("Trust", device.get("trust") or device.get("trust_status")),
            ("Verdict", device.get("verdict")),
            ("Filesystem", device.get("file_system")),
            ("Capacity", device.get("capacity")),
            ("Last seen", device.get("last_seen") or device.get("last_scan")),
        )
        available = [(name, value) for name, value in fields if value not in (None, "")]
        self.table.setRowCount(len(available))
        for row, (name, value) in enumerate(available):
            self.table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setVisible(bool(available))
        self.empty_state.setVisible(not available)
