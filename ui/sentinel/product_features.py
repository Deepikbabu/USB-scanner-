"""Operator-focused investigation, notification, and navigation surfaces."""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from theme import theme_manager
from widgets import AppButton, AppCard, AppTableWidget, EmptyState, StatusBadge
from asset_pages import PageHeader


def _text(value, fallback="Unavailable"):
    value = str(value or "").strip()
    return value if value else fallback


class OperationsDrawer(QFrame):
    """A persistent investigation surface that does not disrupt page context."""

    closed = pyqtSignal()
    open_history_requested = pyqtSignal()
    notifications_read = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("operationsDrawer")
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self._events = []
        self._current_identity = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        head = QHBoxLayout()
        self.eyebrow = QLabel("INVESTIGATION")
        self.eyebrow.setObjectName("drawerEyebrow")
        close = QPushButton("×")
        close.setProperty("variant", "ghost")
        close.setFixedSize(30, 30)
        close.setAccessibleName("Close investigation panel")
        close.clicked.connect(self.close_drawer)
        head.addWidget(self.eyebrow)
        head.addStretch()
        head.addWidget(close)
        outer.addLayout(head)
        self.title = QLabel("No device selected")
        self.title.setObjectName("drawerTitle")
        self.title.setWordWrap(True)
        outer.addWidget(self.title)
        self.badge = StatusBadge("Unreviewed", tone="neutral")
        outer.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(0, 0, 4, 0)
        self.body.setSpacing(10)
        self.identity = AppCard()
        identity_layout = QVBoxLayout(self.identity)
        identity_layout.setContentsMargins(12, 12, 12, 12)
        self.identity_title = QLabel("DEVICE IDENTITY")
        self.identity_title.setObjectName("drawerSection")
        identity_layout.addWidget(self.identity_title)
        self.identity_fields = QLabel()
        self.identity_fields.setWordWrap(True)
        self.identity_fields.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        identity_layout.addWidget(self.identity_fields)
        self.body.addWidget(self.identity)

        self.risk = AppCard()
        risk_layout = QVBoxLayout(self.risk)
        risk_layout.setContentsMargins(12, 12, 12, 12)
        risk_layout.addWidget(self._section("EXPLAINABLE RISK"))
        self.risk_score = QLabel("0 / 100")
        self.risk_score.setObjectName("drawerRisk")
        self.risk_detail = QLabel("No risk evidence reported.")
        self.risk_detail.setWordWrap(True)
        risk_layout.addWidget(self.risk_score)
        risk_layout.addWidget(self.risk_detail)
        self.body.addWidget(self.risk)

        self.timeline = AppCard()
        timeline_layout = QVBoxLayout(self.timeline)
        timeline_layout.setContentsMargins(12, 12, 12, 12)
        timeline_layout.addWidget(self._section("EVIDENCE TIMELINE"))
        self.timeline_text = QLabel("Waiting for device evidence.")
        self.timeline_text.setWordWrap(True)
        timeline_layout.addWidget(self.timeline_text)
        self.body.addWidget(self.timeline)
        self.body.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.history_button = AppButton("Open full incident history", "primary")
        self.history_button.clicked.connect(self.open_history_requested)
        outer.addWidget(self.history_button)
        self.notification_controls = QWidget()
        controls = QHBoxLayout(self.notification_controls)
        controls.setContentsMargins(0, 0, 0, 0)
        self.notification_filter = QComboBox()
        self.notification_filter.addItems(("All updates", "Unread", "Critical"))
        self.notification_filter.currentTextChanged.connect(self._render_notifications)
        mark_read = AppButton("Mark all read")
        mark_read.clicked.connect(self.notifications_read)
        controls.addWidget(self.notification_filter, 1)
        controls.addWidget(mark_read)
        outer.addWidget(self.notification_controls)
        self.notification_controls.hide()
        self._notification_entries = []
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    @staticmethod
    def _section(value):
        label = QLabel(value)
        label.setObjectName("drawerSection")
        return label

    def open_device(self, device, risk_data=None):
        device = dict(device or {})
        identity = (
            device.get("fingerprint") or device.get("serial")
            or f"{device.get('vid')}:{device.get('pid')}:{device.get('port')}"
        )
        if self._current_identity != identity:
            self._events = []
            self.timeline_text.setText("Waiting for device evidence.")
            self._current_identity = identity
        self.eyebrow.setText("DEVICE INVESTIGATION")
        self.notification_controls.hide()
        self.title.setText(_text(device.get("name"), "Unknown USB device"))
        state = _text(
            device.get("classification") or device.get("usbguard_state"),
            "Unreviewed",
        )
        tone = "danger" if state.upper() in {"BLOCKED", "DANGEROUS"} else (
            "success" if state.upper() in {"CLEAN", "TRUSTED", "ALLOWED"} else "info"
        )
        self.badge.update_badge(state, tone=tone)
        self.identity_fields.setText(
            f"Type        {_text(device.get('category'))}\n"
            f"Maker       {_text(device.get('manufacturer'))}\n"
            f"VID / PID   {_text(device.get('vid'))} / {_text(device.get('pid'))}\n"
            f"Serial      {_text(device.get('serial'))}\n"
            f"Port        {_text(device.get('port'))}\n"
            f"Fingerprint {_text(device.get('fingerprint'))}"
        )
        self.apply_risk(risk_data or device)
        self.open_drawer()

    def apply_risk(self, data):
        data = dict(data or {})
        total = int(data.get("total", data.get("risk_score", data.get("risk", 0))) or 0)
        breakdown = data.get("breakdown") or data.get("risk_breakdown") or {}
        lines = []
        if isinstance(breakdown, dict):
            for reason, score in breakdown.items():
                if reason in {"total", "final_total"}:
                    continue
                if isinstance(score, (int, float)):
                    sign = "+" if score >= 0 else ""
                    lines.append(f"• {str(reason).replace('_', ' ').title()}: {sign}{score}")
                elif score:
                    lines.append(f"• {str(reason).replace('_', ' ').title()}: {score}")
        if not lines:
            lines = ["• Backend has not supplied a factor-level breakdown."]
        self.risk_score.setText(f"{total} / 100")
        self.risk_detail.setText("\n".join(lines))

    def add_event(self, title, detail=""):
        line = f"●  {_text(title)}"
        if detail:
            line += f"\n    {_text(detail)}"
        self._events.append(line)
        self._events = self._events[-8:]
        self.timeline_text.setText("\n\n".join(self._events))

    def show_notifications(self, entries):
        self.eyebrow.setText("NOTIFICATION CENTRE")
        self.title.setText("Security activity")
        self._notification_entries = list(entries)
        unread = sum(not bool(item.get("read")) for item in entries)
        self.badge.update_badge(f"{unread} unread", tone="info")
        self.identity.hide()
        self.risk.hide()
        self.timeline.show()
        self.notification_controls.show()
        self._render_notifications()
        self.open_drawer(reset_sections=False)

    def _render_notifications(self, *_):
        mode = self.notification_filter.currentText()
        entries = self._notification_entries
        if mode == "Unread":
            entries = [item for item in entries if not item.get("read")]
        elif mode == "Critical":
            entries = [item for item in entries if item.get("tone") == "danger"]
        lines = []
        for item in entries[-20:]:
            marker = "●" if not item.get("read") else "○"
            lines.append(
                f"{marker}  {_text(item.get('message'))}\n"
                f"    {_text(item.get('time'), '')} · {str(item.get('tone', 'info')).upper()}"
            )
        self.timeline_text.setText("\n\n".join(lines) or "No matching notifications.")

    def open_drawer(self, reset_sections=True):
        if reset_sections:
            self.identity.show()
            self.risk.show()
            self.timeline_text.setText(
                "\n\n".join(self._events) or "Waiting for device evidence."
            )
        self.setMinimumWidth(350)
        self.setMaximumWidth(350)
        self.show()

    def close_drawer(self):
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self.hide()
        self.closed.emit()

    def _apply_theme(self):
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QFrame#operationsDrawer {{
                background:{c['surface']}; border:0; border-left:1px solid {c['border']};
            }}
            QLabel#drawerEyebrow, QLabel#drawerSection {{
                color:{c['text_muted']}; font-size:9px; font-weight:800;
                letter-spacing:1px;
            }}
            QLabel#drawerTitle {{ color:{c['text_primary']}; font-size:17px; font-weight:800; }}
            QLabel#drawerRisk {{ color:{c['accent']}; font-size:26px; font-weight:800; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background:transparent; border:0; }}
        """)


class CommandPalette(QDialog):
    """Searchable command and entity launcher."""

    command_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick actions")
        self.setModal(True)
        self.resize(560, 420)
        self._commands = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("Search pages, devices, incidents, and actions")
        title.setObjectName("paletteTitle")
        layout.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command…")
        self.search.setAccessibleName("Command search")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.itemActivated.connect(self._activate)
        layout.addWidget(self.results, 1)
        self._apply_theme()

    def set_commands(self, commands):
        self._commands = list(commands)
        self._filter("")

    def _filter(self, query):
        query = str(query).casefold().strip()
        self.results.clear()
        for command_id, title, detail in self._commands:
            haystack = f"{title} {detail}".casefold()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(f"{title}\n{detail}")
            item.setData(Qt.ItemDataRole.UserRole, command_id)
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def _activate(self, item):
        self.command_selected.emit(str(item.data(Qt.ItemDataRole.UserRole)))
        self.accept()

    def open_palette(self):
        self.search.clear()
        self.search.setFocus()
        self.exec()

    def _apply_theme(self):
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QDialog {{ background:{c['bg']}; }}
            QLabel#paletteTitle {{ color:{c['text_primary']};font-size:16px;font-weight:800; }}
            QListWidget {{ background:{c['surface']};color:{c['text_primary']};
                          border:1px solid {c['border']};border-radius:9px;padding:4px; }}
            QListWidget::item {{ min-height:48px;padding:8px;border-radius:6px; }}
            QListWidget::item:selected {{ background:{c['accent_soft']}; }}
        """)


class IncidentDetailsPage(QWidget):
    """Complete operator-readable view over persisted incident evidence."""
    back_requested = pyqtSignal()
    workflow_update_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(10)
        navigation = QHBoxLayout()
        back = AppButton("← Back to History")
        back.clicked.connect(self.back_requested)
        navigation.addWidget(back)
        navigation.addStretch()
        root.addLayout(navigation)
        root.addWidget(PageHeader(
            "Incident evidence",
            "Decision trace, risk factors, device identity, and persisted scanner evidence.",
        ))
        summary = AppCard()
        summary_layout = QHBoxLayout(summary)
        self.title = QLabel("No incident selected")
        self.title.setObjectName("incidentTitle")
        self.status = StatusBadge("Unavailable", tone="neutral")
        self.risk = QLabel("Risk —")
        summary_layout.addWidget(self.title, 1)
        summary_layout.addWidget(self.risk)
        summary_layout.addWidget(self.status)
        root.addWidget(summary)
        workflow = AppCard(); workflow_layout = QVBoxLayout(workflow)
        workflow_layout.addWidget(self._workflow_title())
        workflow_controls = QHBoxLayout()
        self.assignee = QLineEdit(); self.assignee.setPlaceholderText("Assign to operator")
        assign = AppButton("Assign"); assign.clicked.connect(self._assign)
        self.acknowledged = QCheckBox("Acknowledged")
        self.acknowledged.toggled.connect(self._acknowledge)
        workflow_controls.addWidget(self.assignee,1); workflow_controls.addWidget(assign)
        workflow_controls.addWidget(self.acknowledged); workflow_layout.addLayout(workflow_controls)
        comment_controls=QHBoxLayout(); self.comment=QLineEdit(); self.comment.setPlaceholderText("Add investigation comment…")
        add_comment=AppButton("Add comment","primary"); add_comment.clicked.connect(self._comment)
        comment_controls.addWidget(self.comment,1); comment_controls.addWidget(add_comment)
        workflow_layout.addLayout(comment_controls)
        self.comments=QLabel("No operator comments."); self.comments.setWordWrap(True)
        workflow_layout.addWidget(self.comments); root.addWidget(workflow)
        self.table = AppTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(("Evidence", "Value"))
        root.addWidget(self.table, 1)
        self.empty = EmptyState(
            "Select an incident",
            "Double-click a History row to open its complete evidence record.",
            "◷",
        )
        root.addWidget(self.empty)

    def apply_incident(self, incident, report=None):
        incident = dict(incident or {})
        report = dict(report or {})
        evidence = {**incident, **report}
        incident_id = str(evidence.get("incident_id") or "Unavailable")
        self.current_incident_id = incident_id
        device = evidence.get("device") if isinstance(evidence.get("device"), dict) else {}
        name = (
            device.get("name") or evidence.get("device_name")
            or evidence.get("device") or "Unknown USB device"
        )
        verdict = str(evidence.get("verdict") or "INCOMPLETE").upper()
        risk = int(
            evidence.get("total_risk", evidence.get("risk", evidence.get("risk_score", 0)))
            or 0
        )
        self.title.setText(f"{name} · {incident_id}")
        self.risk.setText(f"Risk {risk}/100")
        tone = "success" if verdict in {"CLEAN", "TRUSTED"} else (
            "danger" if verdict in {"DANGEROUS", "BLOCKED"} else "warning"
        )
        self.status.update_badge(verdict, tone=tone)
        rows = [
            ("Incident ID", incident_id),
            ("Timestamp", evidence.get("timestamp") or evidence.get("updated")),
            ("Final verdict", verdict),
            ("Final state", evidence.get("state")),
            ("Risk score", f"{risk}/100"),
            ("Device", name),
            ("Manufacturer", device.get("manufacturer") or device.get("vendor")),
            ("VID:PID", f"{device.get('vid', '----')}:{device.get('pid', '----')}"),
            ("Serial", device.get("serial")),
            ("Fingerprint", device.get("fingerprint") or device.get("hardware_fingerprint")),
            ("Files scanned", evidence.get("files_scanned") or evidence.get("files")),
            ("Threats", evidence.get("threat_count") or evidence.get("threats")),
            ("Quarantined", evidence.get("quarantine_count") or evidence.get("quarantined")),
            ("PDF evidence", evidence.get("pdf_path")),
            ("JSON evidence", evidence.get("json_path")),
        ]
        breakdown = evidence.get("risk_breakdown") or {}
        if isinstance(breakdown, dict):
            for key, value in breakdown.items():
                rows.append((f"Risk · {str(key).replace('_', ' ').title()}", value))
        findings = evidence.get("findings") or evidence.get("threat_details") or []
        for index, finding in enumerate(findings[:30], 1):
            rows.append((f"Finding {index}", finding))
        rows = [(key, value) for key, value in rows if value not in (None, "", [], {})]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row, (key, value) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)

    @staticmethod
    def _workflow_title():
        title=QLabel("INCIDENT OWNERSHIP AND RESPONSE")
        title.setObjectName("drawerSection")
        return title

    def _incident_id(self):
        return getattr(self,"current_incident_id","")

    def _assign(self):
        if self._incident_id() and self.assignee.text().strip():
            self.workflow_update_requested.emit(
                self._incident_id(), {"assigned_to":self.assignee.text().strip()}
            )

    def _acknowledge(self, checked):
        if self._incident_id():
            self.workflow_update_requested.emit(
                self._incident_id(), {"acknowledged":bool(checked)}
            )

    def _comment(self):
        text=self.comment.text().strip()
        if self._incident_id() and text:
            self.workflow_update_requested.emit(self._incident_id(),{"comment":text})
            self.comment.clear()

    def apply_workflow(self, workflow):
        workflow=dict(workflow or {})
        self.assignee.setText(str(workflow.get("assigned_to") or ""))
        self.acknowledged.blockSignals(True)
        self.acknowledged.setChecked(bool(workflow.get("acknowledged")))
        self.acknowledged.blockSignals(False)
        comments=workflow.get("comments") or []
        self.comments.setText("\n".join(
            f"• {item.get('operator','Operator')}: {item.get('text','')}"
            for item in comments[-8:]
        ) or "No operator comments.")


class ReportPreviewDialog(QDialog):
    """Embedded PDF preview with a metadata fallback when QtPdf is unavailable."""
    def __init__(self, report, parent=None):
        super().__init__(parent); self.setWindowTitle("Incident report preview"); self.resize(900,700)
        layout=QVBoxLayout(self); report=dict(report or {})
        path=Path(str(report.get("pdf_path") or ""))
        loaded=False
        if path.is_file():
            try:
                from PyQt6.QtPdf import QPdfDocument
                from PyQt6.QtPdfWidgets import QPdfView
                document=QPdfDocument(self); document.load(str(path))
                viewer=QPdfView(); viewer.setDocument(document)
                viewer.setPageMode(QPdfView.PageMode.MultiPage)
                self._document=document; layout.addWidget(viewer,1); loaded=True
            except (ImportError,RuntimeError):
                loaded=False
        if not loaded:
            fallback=QLabel(
                "Embedded PDF rendering is unavailable on this platform.\n\n"
                f"Incident: {report.get('incident_id','Unavailable')}\n"
                f"Verdict: {report.get('verdict','Unavailable')}\n"
                f"Risk: {report.get('risk',report.get('total_risk','—'))}\n"
                f"Report: {path if path else 'No PDF generated'}"
            )
            fallback.setWordWrap(True); fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fallback,1)
        close=AppButton("Close","primary"); close.clicked.connect(self.accept)
        layout.addWidget(close,0,Qt.AlignmentFlag.AlignRight)


class TrustManagementPage(QWidget):
    """Auditable trust inventory without inventing unsupported mutations."""
    trust_action_requested = pyqtSignal(str, str)
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(10)
        navigation = QHBoxLayout()
        back = AppButton("← Back to Settings")
        back.clicked.connect(self.back_requested)
        navigation.addWidget(back)
        navigation.addStretch()
        root.addLayout(navigation)
        root.addWidget(PageHeader(
            "Trust management",
            "Signed HID and storage identities accepted by the backend policy.",
        ))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search trusted identity, device type, or source…")
        self.search.textChanged.connect(self._render)
        controls = QHBoxLayout()
        controls.addWidget(self.search, 1)
        self.expire_button = AppButton("Set 24h expiration")
        self.rescan_button = AppButton("Require rescan")
        self.revoke_button = AppButton("Revoke trust", "danger")
        for button in (self.expire_button, self.rescan_button, self.revoke_button):
            button.setEnabled(False)
            controls.addWidget(button)
        self.expire_button.clicked.connect(lambda:self._emit_action("expire_trust"))
        self.rescan_button.clicked.connect(lambda:self._emit_action("require_trust_rescan"))
        self.revoke_button.clicked.connect(lambda:self._emit_action("revoke_trust"))
        root.addLayout(controls)
        self.table = AppTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ("Identity", "Type", "Status", "Source", "Policy scope")
        )
        self.table.itemSelectionChanged.connect(self._selection_changed)
        root.addWidget(self.table, 1)
        self.empty = EmptyState(
            "No trust records",
            "Trusted identities will appear when the signed backend stores contain records.",
            "◇",
        )
        root.addWidget(self.empty)
        self.status = QLabel("0 signed trust records")
        self.status.setProperty("muted", True)
        root.addWidget(self.status)
        self._records = []

    def _selected_identity(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.text() if item else ""

    def _selection_changed(self):
        enabled = bool(self._selected_identity())
        for button in (self.expire_button, self.rescan_button, self.revoke_button):
            button.setEnabled(enabled)

    def _emit_action(self, action):
        identity = self._selected_identity()
        if identity:
            self.trust_action_requested.emit(action, identity)

    def apply_backend_resources(self, resources):
        resources = dict(resources or {})
        records = []
        signed = resources.get("signed_trust") or []
        if isinstance(signed, dict):
            signed = [{"identity": key, "record": value} for key, value in signed.items()]
        for item in signed:
            record = item.get("record") if isinstance(item.get("record"), dict) else item
            records.append({
                "identity": item.get("identity") or record.get("identity"),
                "type": record.get("type") or record.get("category") or "USB identity",
                "status": item.get("status") or record.get("status") or "Trusted",
                "source": record.get("source") or "Signed trust store",
                "scope": record.get("scope") or "Exact hardware identity",
            })
        for source, title in (
            ("trusted_hid", "HID trust store"), ("trusted_storage", "Storage trust store")
        ):
            store = resources.get(source) or {}
            iterable = store.items() if isinstance(store, dict) else enumerate(store)
            for identity, record in iterable:
                record = record if isinstance(record, dict) else {}
                if any(str(item["identity"]) == str(identity) for item in records):
                    continue
                records.append({
                    "identity": identity,
                    "type": record.get("type") or source.replace("trusted_", "").upper(),
                    "status": "Trusted", "source": title,
                    "scope": record.get("scope") or "Exact hardware identity",
                })
        self._records = records
        self._render()

    def _render(self, *_):
        query = self.search.text().strip().casefold()
        visible = [
            record for record in self._records
            if not query or query in " ".join(str(v) for v in record.values()).casefold()
        ]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(visible))
        for row, record in enumerate(visible):
            for column, key in enumerate(("identity", "type", "status", "source", "scope")):
                self.table.setItem(row, column, QTableWidgetItem(str(record.get(key) or "—")))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.setVisible(bool(visible))
        self.empty.setVisible(not visible)
        self.status.setText(f"{len(visible)} of {len(self._records)} signed trust records")
