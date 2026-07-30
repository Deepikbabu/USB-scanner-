"""Template-aligned horizontal navigation with native Qt vector icons."""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)

from theme import theme_manager


class NavIcon(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.active = False
        self.setFixedSize(18, 18)

    def set_active(self, active):
        self.active = active
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = theme_manager.get_qcolor("accent" if self.active else "text_secondary")
        painter.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.name == "dashboard":
            for x, y in ((2, 2), (10, 2), (2, 10), (10, 10)):
                painter.drawRoundedRect(QRectF(x, y, 6, 6), 1.4, 1.4)
        elif self.name == "scan":
            painter.drawEllipse(QRectF(2, 2, 11, 11))
            painter.drawLine(QPointF(11, 11), QPointF(16, 16))
        elif self.name == "devices":
            painter.drawRoundedRect(QRectF(5, 1, 8, 12), 1.5, 1.5)
            painter.drawLine(9, 13, 9, 17)
            painter.drawLine(6, 17, 12, 17)
        elif self.name == "quarantine":
            path = QPainterPath()
            path.moveTo(9, 1)
            path.lineTo(15, 4)
            path.lineTo(14, 11)
            path.cubicTo(13, 15, 9, 17, 9, 17)
            path.cubicTo(9, 17, 5, 15, 4, 11)
            path.lineTo(3, 4)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(6, 9, 12, 9)
        elif self.name == "history":
            painter.drawArc(QRectF(2, 2, 14, 14), -45 * 16, 300 * 16)
            painter.drawLine(9, 5, 9, 9)
            painter.drawLine(9, 9, 12, 11)
        elif self.name == "settings":
            painter.drawEllipse(QRectF(6, 6, 6, 6))
            for index in range(8):
                angle = index * math.pi / 4
                painter.drawLine(
                    QPointF(9 + 4 * math.cos(angle), 9 + 4 * math.sin(angle)),
                    QPointF(9 + 7 * math.cos(angle), 9 + 7 * math.sin(angle)),
                )


class NavButton(QPushButton):
    def __init__(self, label, icon_name, page_index, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self.setProperty("nav", True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 0, 9, 0)
        layout.setSpacing(6)
        self.icon = NavIcon(icon_name, self)
        self.text_label = QLabel(label)
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon)
        layout.addWidget(self.text_label)
        self.toggled.connect(self.icon.set_active)

    def set_collapsed(self, collapsed):
        self.text_label.setVisible(not collapsed)


class BottomNavigationBar(QFrame):
    """Compatibility name retained for callers; displayed as top page tabs."""

    tab_changed = pyqtSignal(int)
    page_changed = tab_changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topNavigation")
        self._collapsed = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        items = (
            ("Dashboard", "dashboard", 0),
            ("Live Scan", "scan", 1),
            ("Devices", "devices", 2),
            ("Quarantine", "quarantine", 3),
            ("History", "history", 4),
            ("Settings", "settings", 6),
        )
        self.buttons = []
        for text, icon, index in items:
            button = NavButton(text, icon, index, self)
            button.clicked.connect(
                lambda _checked=False, value=index: self.set_active_tab(value)
            )
            self.buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()
        self.set_active_tab(0, emit=False)
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    @property
    def collapsed(self):
        return self._collapsed

    def toggle_collapsed(self):
        self._collapsed = not self._collapsed
        for button in self.buttons:
            button.set_collapsed(self._collapsed)

    def handle_click(self, index):
        self.set_active_tab(index)

    def set_active_tab(self, page_index, emit=True):
        for button in self.buttons:
            button.setChecked(button.page_index == page_index)
        if emit:
            self.tab_changed.emit(page_index)

    def _apply_theme(self):
        colors = theme_manager.colors
        self.setStyleSheet(f"""
            QFrame#topNavigation {{ background: transparent; border: 0; }}
            QPushButton[nav="true"] {{
                min-height: 42px; max-height: 42px; color: {colors['text_secondary']};
                background: transparent; border: 0;
                border-bottom: 2px solid transparent; border-radius: 0;
            }}
            QPushButton[nav="true"] QLabel {{
                color: {colors['text_secondary']}; background: transparent;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton[nav="true"]:hover {{ background: {colors['surface_hover']}; }}
            QPushButton[nav="true"]:checked {{
                background: transparent; border-bottom: 2px solid {colors['accent']};
            }}
            QPushButton[nav="true"]:checked QLabel {{
                color: {colors['text_primary']}; font-weight: 700;
            }}
        """)
