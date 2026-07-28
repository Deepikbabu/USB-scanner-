"""Shared left-hand application navigation."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from theme import theme_manager


class NavButton(QPushButton):
    def __init__(self, label, glyph, page_index, parent=None):
        super().__init__(f"{glyph}   {label}", parent)
        self.page_index = page_index
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self.setProperty("nav", True)
        self.setMinimumHeight(42)


class BottomNavigationBar(QFrame):
    """Compatibility name for the new fixed sidebar navigation."""

    tab_changed = pyqtSignal(int)
    page_changed = tab_changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideNavigation")
        self.setFixedWidth(184)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 14)
        layout.setSpacing(5)

        brand = QLabel("USB SECURITY")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)
        sub = QLabel("SCANNER")
        sub.setObjectName("brandSubLabel")
        layout.addWidget(sub)
        layout.addSpacing(22)

        # Device Details remains a contextual page (index 5), not a primary tab.
        items = [
            ("Dashboard", "DB", 0),
            ("Live Scan", "LS", 1),
            ("Devices", "DV", 2),
            ("Quarantine", "QV", 3),
            ("History", "HI", 4),
            ("Settings", "ST", 6),
        ]
        self.buttons = []
        for label, glyph, page_index in items:
            button = NavButton(label, glyph, page_index, self)
            button.clicked.connect(
                lambda checked=False, index=page_index: self.set_active_tab(index)
            )
            self.buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)

        version = QLabel("SECURE CONSOLE  •  v1")
        version.setObjectName("navFooter")
        layout.addWidget(version)
        self.set_active_tab(0, emit=False)
        self._apply_nav_theme()
        theme_manager.theme_changed.connect(self._apply_nav_theme)

    def handle_click(self, index):
        self.set_active_tab(index)

    def set_active_tab(self, page_index, emit=True):
        for button in self.buttons:
            button.setChecked(button.page_index == page_index)
        if emit:
            self.tab_changed.emit(page_index)

    def _apply_nav_theme(self):
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QFrame#sideNavigation {{
                background: {c['surface']};
                border: 0;
                border-right: 1px solid {c['border']};
            }}
            QLabel#brandLabel {{
                color: {c['text_primary']}; font-size: 13px; font-weight: 800;
                letter-spacing: 0.5px;
            }}
            QLabel#brandSubLabel {{
                color: {c['accent']}; font-size: 9px; font-weight: 800;
                letter-spacing: 2px; margin-left: 25px;
            }}
            QLabel#navFooter {{ color: {c['text_muted']}; font-size: 9px; }}
            QPushButton[nav="true"] {{
                min-height: 42px; padding: 0 12px; text-align: left;
                color: {c['text_secondary']}; background: transparent;
                border: 1px solid transparent; border-radius: 7px; font-weight: 600;
            }}
            QPushButton[nav="true"]:hover {{
                color: {c['text_primary']}; background: {c['surface_hover']};
            }}
            QPushButton[nav="true"]:checked {{
                color: white; background: {c['accent_soft']};
                border-color: {c['accent']};
            }}
        """)
