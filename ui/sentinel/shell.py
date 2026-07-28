"""Reusable application chrome shared by every Sentinel page."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from navigation import BottomNavigationBar
from theme import theme_manager


class ApplicationShell(QWidget):
    def __init__(self, page_stack, parent=None):
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.page_stack = page_stack
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
        content_layout.addWidget(page_stack, 1)
        root.addWidget(content, 1)

        self.navigation.tab_changed.connect(self._select_page)
        self._select_page(0)
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    def _build_top_bar(self):
        bar = QFrame(self)
        bar.setObjectName("topBar")
        bar.setFixedHeight(66)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("pageTitle")
        layout.addWidget(self.page_title)
        layout.addStretch(1)
        self.connection_dot = QLabel("●")
        self.connection_dot.setObjectName("connectionDot")
        self.connection_text = QLabel("Backend connecting")
        self.connection_text.setObjectName("connectionText")
        layout.addWidget(self.connection_dot)
        layout.addWidget(self.connection_text)
        self.notification_button = QPushButton("!")
        self.notification_button.setProperty("variant", "ghost")
        self.notification_button.setFixedSize(36, 36)
        self.notification_button.setToolTip("Notifications")
        self.notification_button.clicked.connect(
            lambda: self.navigation.set_active_tab(4)
        )
        layout.addWidget(self.notification_button)
        return bar

    def _select_page(self, index):
        titles = {
            0: "Dashboard", 1: "Live Scan", 2: "Devices",
            3: "Quarantine", 4: "History", 5: "Device Details", 6: "Settings",
        }
        self.page_title.setText(titles.get(index, "USB Security Scanner"))

    def set_backend_connected(self, connected):
        self.connection_text.setText("Backend online" if connected else "Backend offline")
        self.connection_dot.setProperty("online", bool(connected))
        self.connection_dot.style().unpolish(self.connection_dot)
        self.connection_dot.style().polish(self.connection_dot)

    def _apply_theme(self):
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QWidget#shellContent {{ background: {c['bg']}; }}
            QFrame#topBar {{ background: transparent; border: 0; }}
            QLabel#pageTitle {{ color: {c['text_primary']}; font-size: 20px; font-weight: 800; }}
            QLabel#connectionDot {{ color: {c['warning']}; font-size: 13px; }}
            QLabel#connectionDot[online="true"] {{ color: {c['success']}; }}
            QLabel#connectionText {{ color: {c['text_secondary']}; font-size: 11px; }}
        """)
