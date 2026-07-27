from .dashboard import DashboardPage, COLORS, GlassCard, StatusBadge
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class PlaceholderPage(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 120)
        card = GlassCard()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(40, 60, 40, 60)
        cv.setSpacing(20)
        icon_lbl = QLabel("◎")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size: 80px; color: {COLORS['accent']}; border: none;")
        cv.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: 900; border: none;")
        cv.addWidget(title_lbl)
        status = StatusBadge("Coming Soon", COLORS['accent'])
        cv.addWidget(status, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()

class ScanPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("Scanning Interface", "Analyze connected USB devices", parent)

class HistoryPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("Scan History", "Previous scan records", parent)

class SettingsPage(PlaceholderPage):
    def __init__(self, parent=None):
        super().__init__("Settings", "Application preferences", parent)
