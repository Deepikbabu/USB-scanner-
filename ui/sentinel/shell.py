"""Reusable, responsive application chrome shared by every Sentinel page."""

import json
from PyQt6.QtCore import (
    QDateTime, QEasingCurve, QPropertyAnimation, QSettings, QTimer, Qt,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from navigation import BottomNavigationBar
from product_features import OperationsDrawer
from theme import theme_manager


class Toast(QFrame):
    """Non-blocking, accessible feedback for backend and user actions."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(360)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 10, 11)
        self.indicator = QLabel("●")
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.close_button = QPushButton("×")
        self.close_button.setProperty("variant", "ghost")
        self.close_button.setFixedSize(28, 28)
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.indicator)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.close_button)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_animated)
        self.hide()

    def present(self, message, tone="info", timeout=4200):
        colors = theme_manager.colors
        token = {"success": "success", "warning": "warning", "danger": "danger"}.get(
            tone, "info"
        )
        self.indicator.setStyleSheet(f"color:{colors[token]};")
        self.message.setText(str(message))
        self.setAccessibleName(f"{tone.title()} notification: {message}")
        self.setStyleSheet(
            f"QFrame#toast{{background:{colors['surface_raised']};"
            f"border:1px solid {colors[token]};border-radius:10px;}}"
        )
        self.adjustSize()
        self.setFixedWidth(360)
        self.parent()._position_toast()
        self.show()
        self.raise_()
        self.setWindowOpacity(1.0)
        self.timer.start(timeout)

    def hide_animated(self):
        if theme_manager.reduced_motion:
            self.hide()
            return
        self.animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.animation.setDuration(180)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.hide)
        self.animation.start()


class ApplicationShell(QWidget):
    def __init__(self, page_stack, parent=None):
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.page_stack = page_stack
        self._auto_collapsed = False
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.navigation = BottomNavigationBar(self)
        root.addWidget(self.navigation)

        content = QWidget(self)
        content.setObjectName("shellContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 0, 18, 18)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_top_bar())
        content_layout.addWidget(self._build_scan_strip())
        content_layout.addWidget(page_stack, 1)
        root.addWidget(content, 1)
        self.operations_drawer = OperationsDrawer(self)
        self.operations_drawer.hide()
        self.operations_drawer.open_history_requested.connect(
            lambda: self.navigation.set_active_tab(4)
        )
        self.operations_drawer.notifications_read.connect(self.mark_notifications_read)
        root.addWidget(self.operations_drawer)
        self._settings = QSettings("BBBS", "USB Security Scanner")
        try:
            self._notifications = json.loads(
                self._settings.value("notifications", "[]")
            )[-50:]
        except (TypeError, ValueError):
            self._notifications = []
        initial_unread = sum(
            not item.get("read") for item in self._notifications
            if isinstance(item, dict)
        )
        self.notification_button.setText(str(initial_unread) if initial_unread else "!")

        self.toast = Toast(self)
        self.navigation.tab_changed.connect(self._select_page)
        self._select_page(0)
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < 1120
        if compact and not self.navigation.collapsed:
            self.navigation.toggle_collapsed()
            self._auto_collapsed = True
        elif self.width() >= 1240 and self._auto_collapsed and self.navigation.collapsed:
            self.navigation.toggle_collapsed()
            self._auto_collapsed = False
        self.section_label.setVisible(self.width() >= 920)
        self.connection_text.setVisible(self.width() >= 820)
        self._position_toast()

    def _position_toast(self):
        if hasattr(self, "toast"):
            drawer_width = (
                self.operations_drawer.maximumWidth()
                if hasattr(self, "operations_drawer")
                and self.operations_drawer.isVisible()
                else 0
            )
            self.toast.move(
                max(12, self.width() - drawer_width - self.toast.width() - 22), 74
            )

    def _build_top_bar(self):
        bar = QFrame(self)
        bar.setObjectName("topBar")
        bar.setFixedHeight(66)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("pageTitle")
        self.menu_button = QPushButton("☰")
        self.menu_button.setProperty("variant", "ghost")
        self.menu_button.setFixedSize(36, 36)
        self.menu_button.setToolTip("Collapse or expand navigation (F10)")
        self.menu_button.setAccessibleName("Toggle navigation sidebar")
        self.menu_button.clicked.connect(self.navigation.toggle_collapsed)
        layout.addWidget(self.menu_button)
        layout.addWidget(self.page_title)
        self.section_label = QLabel(" / SECURITY OPERATIONS")
        self.section_label.setObjectName("sectionLabel")
        layout.addWidget(self.section_label)
        layout.addStretch(1)
        self.connection_dot = QLabel("●")
        self.connection_dot.setObjectName("connectionDot")
        self.connection_text = QLabel("Backend connecting")
        self.connection_text.setObjectName("connectionText")
        layout.addWidget(self.connection_dot)
        layout.addWidget(self.connection_text)
        self.theme_button = QPushButton(
            "Light mode" if theme_manager.current_theme == "dark" else "Dark mode"
        )
        self.theme_button.setProperty("variant", "ghost")
        self.theme_button.setToolTip("Switch application theme")
        self.theme_button.setAccessibleName("Toggle dark and light theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_button)
        self.notification_button = QPushButton("!")
        self.notification_button.setProperty("variant", "ghost")
        self.notification_button.setFixedSize(36, 36)
        self.notification_button.setToolTip("Open incident history")
        self.notification_button.setAccessibleName("Open incident history")
        self.notification_button.clicked.connect(self.show_notification_center)
        layout.addWidget(self.notification_button)
        return bar

    def _build_scan_strip(self):
        strip = QFrame(self)
        strip.setObjectName("scanStrip")
        strip.setFixedHeight(42)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(12, 5, 10, 5)
        layout.setSpacing(10)
        self.scan_indicator = QLabel("●")
        self.scan_title = QLabel("Security scan")
        self.scan_title.setObjectName("scanStripTitle")
        self.scan_detail = QLabel("Preparing device…")
        self.scan_detail.setObjectName("scanStripDetail")
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedSize(190, 8)
        self.scan_percent = QLabel("0%")
        open_button = QPushButton("View scan")
        open_button.setProperty("variant", "ghost")
        open_button.clicked.connect(lambda: self.navigation.set_active_tab(1))
        layout.addWidget(self.scan_indicator)
        layout.addWidget(self.scan_title)
        layout.addWidget(self.scan_detail, 1)
        layout.addWidget(self.scan_progress)
        layout.addWidget(self.scan_percent)
        layout.addWidget(open_button)
        strip.hide()
        self.scan_strip = strip
        return strip

    def begin_scan(self, device_name):
        self.scan_title.setText(str(device_name or "USB device"))
        self.scan_detail.setText("Preparing security analysis…")
        self.scan_progress.setValue(0)
        self.scan_percent.setText("0%")
        self.scan_strip.show()

    def update_scan(self, progress, detail=""):
        value = max(0, min(100, int(progress or 0)))
        self.scan_progress.setValue(value)
        self.scan_percent.setText(f"{value}%")
        if detail:
            self.scan_detail.setText(str(detail))
        self.scan_strip.show()

    def complete_scan(self, verdict="Complete"):
        self.scan_progress.setValue(100)
        self.scan_percent.setText("100%")
        self.scan_detail.setText(f"Analysis complete · {verdict}")
        QTimer.singleShot(7000, self.scan_strip.hide)

    def show_toast(self, message, tone="info", timeout=4200):
        self._notifications.append({
            "message": str(message), "tone": str(tone), "read": False,
            "time": QDateTime.currentDateTime().toString("MMM d · hh:mm"),
        })
        self._notifications = self._notifications[-50:]
        self._settings.setValue("notifications", json.dumps(self._notifications))
        unread = sum(not item.get("read") for item in self._notifications)
        self.notification_button.setText(str(unread) if unread else "!")
        self.toast.present(message, tone, timeout)

    def show_notification_center(self):
        self.operations_drawer.show_notifications(
            getattr(self, "_notifications", [])
        )

    def mark_notifications_read(self):
        for item in self._notifications:
            item["read"] = True
        self._settings.setValue("notifications", json.dumps(self._notifications))
        self.notification_button.setText("!")
        self.operations_drawer.show_notifications(self._notifications)

    def toggle_theme(self):
        theme_manager.set_theme(
            "light" if theme_manager.current_theme == "dark" else "dark"
        )

    def inspect_device(self, device, risk_data=None):
        self.operations_drawer.open_device(device, risk_data)

    def add_evidence_event(self, title, detail=""):
        self.operations_drawer.add_event(title, detail)

    def _select_page(self, index):
        titles = {
            0: "Dashboard", 1: "Live Scan", 2: "Devices",
            3: "Quarantine", 4: "History", 5: "Device Details", 6: "Settings",
            7: "Incident Evidence", 8: "Trust Management",
        }
        self.page_title.setText(titles.get(index, "USB Security Scanner"))

    def set_backend_connected(self, connected):
        self.connection_text.setText("Backend online" if connected else "Backend offline")
        self.connection_dot.setProperty("online", bool(connected))
        self.connection_dot.style().unpolish(self.connection_dot)
        self.connection_dot.style().polish(self.connection_dot)

    def _apply_theme(self):
        c = theme_manager.colors
        if hasattr(self, "theme_button"):
            self.theme_button.setText(
                "Light mode" if theme_manager.current_theme == "dark" else "Dark mode"
            )
        self.setStyleSheet(f"""
            QWidget#shellContent {{ background: {c['bg']}; }}
            QFrame#topBar {{ background: transparent; border: 0; }}
            QLabel#pageTitle {{ color: {c['text_primary']}; font-size: 20px; font-weight: 800; }}
            QLabel#sectionLabel {{ color: {c['text_muted']}; font-size: 9px; font-weight: 700; }}
            QLabel#connectionDot {{ color: {c['warning']}; font-size: 13px; }}
            QLabel#connectionDot[online="true"] {{ color: {c['success']}; }}
            QLabel#connectionText {{ color: {c['text_secondary']}; font-size: 11px; }}
            QFrame#scanStrip {{ background:{c['surface_raised']}; border:1px solid {c['border']};
                               border-radius:8px; margin-bottom:6px; }}
            QFrame#scanStrip QLabel {{ border:0; background:transparent; }}
            QLabel#scanStripTitle {{ color:{c['text_primary']}; font-weight:700; }}
            QLabel#scanStripDetail {{ color:{c['text_secondary']}; }}
        """)
