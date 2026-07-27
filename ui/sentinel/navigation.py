import math
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QWidget, QGraphicsDropShadowEffect
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QPointF, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath
from theme import theme_manager

class NavIconWidget(QWidget):
    def __init__(self, icon_name, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(32, 32)
        self.color = QColor("#64748b")

    def set_color(self, color):
        self.color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx, cy = 16, 16
        
        if self.icon_name == "dashboard":
            path = QPainterPath()
            path.moveTo(cx, cy - 12)
            path.lineTo(cx + 11, cy - 8)
            path.lineTo(cx + 11, cy + 3)
            path.cubicTo(cx + 11, cy + 9, cx, cy + 13, cx, cy + 13)
            path.cubicTo(cx, cy + 13, cx - 11, cy + 9, cx - 11, cy + 3)
            path.lineTo(cx - 11, cy - 8)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.icon_name == "scan":
            painter.drawEllipse(QRectF(cx - 12.0, cy - 12.0, 24.0, 24.0))
            path = QPainterPath()
            path.moveTo(cx, cy - 7)
            path.lineTo(cx + 3.5, cy)
            path.lineTo(cx, cy + 7)
            path.lineTo(cx - 3.5, cy)
            path.closeSubpath()
            painter.drawPath(path)
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(QRectF(cx - 1.5, cy - 1.5, 3.0, 3.0))
        elif self.icon_name == "history":
            painter.drawArc(cx - 11, cy - 11, 22, 22, -50 * 16, 280 * 16)
            path = QPainterPath()
            path.moveTo(cx + 8, cy - 10)
            path.lineTo(cx + 11, cy - 3)
            path.lineTo(cx + 3, cy - 6)
            path.closeSubpath()
            painter.setBrush(QBrush(self.color))
            painter.drawPath(path)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - 5.5))
            painter.drawLine(QPointF(cx, cy), QPointF(cx + 4.0, cy))
        elif self.icon_name == "settings":
            painter.drawEllipse(QRectF(cx - 5.5, cy - 5.5, 11.0, 11.0))
            for i in range(8):
                angle = i * 45 * math.pi / 180
                x1 = cx + 5.5 * math.cos(angle)
                y1 = cy + 5.5 * math.sin(angle)
                x2 = cx + 11.0 * math.cos(angle)
                y2 = cy + 11.0 * math.sin(angle)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

class NavButton(QPushButton):
    def __init__(self, label, icon_path, index, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(140, 64)
        self.index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_path = icon_path
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 6, 0, 6)
        
        self.icon_widget = NavIconWidget(icon_path, self)
        layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.text_label = QLabel(label)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)
        
        self.hover_anim = QPropertyAnimation(self, b"size")
        self.update_style()
        theme_manager.theme_changed.connect(lambda: self.update_style(self.underMouse()))

    def update_style(self, hovered=False):
        accent = theme_manager.get_color('accent')
        secondary = theme_manager.get_color('text_muted')
        text_primary = theme_manager.get_color('text_primary')
        
        is_active = self.isChecked()
        
        if is_active:
            self.hover_anim.stop()
            self.setFixedSize(140, 64)
            bg = "rgba(217, 127, 74, 0.15)"
            border = f"1px solid {accent}"
            color = text_primary
            icon_color = QColor(accent)
        elif hovered:
            bg_col = "0,0,0" if theme_manager.current_theme == "light" else "255,255,255"
            bg = f"rgba({bg_col}, 15)"
            border = f"0.5px solid rgba({bg_col}, 40)"
            color = text_primary
            icon_color = QColor(text_primary)
        else:
            bg = "transparent"
            border = "none"
            color = secondary
            icon_color = QColor(secondary)

        self.setStyleSheet(f"QPushButton {{ background: {bg}; border: {border}; border-radius: 32px; }}")
        self.text_label.setStyleSheet(f"QLabel {{ font-size: 10px; font-weight: 900; color: {color}; background: transparent; border: none; letter-spacing: 0.5px; }}")
        self.icon_widget.set_color(icon_color)

    def enterEvent(self, event):
        if not self.isChecked():
            self.update_style(hovered=True)
            self.hover_anim.stop()
            self.hover_anim.setDuration(200)
            self.hover_anim.setEndValue(QSize(140, 68))
            self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.isChecked():
            self.update_style(hovered=False)
            self.hover_anim.stop()
            self.hover_anim.setDuration(200)
            self.hover_anim.setEndValue(QSize(140, 64))
            self.hover_anim.start()
        super().leaveEvent(event)

class BottomNavigationBar(QFrame):
    tab_changed = pyqtSignal(int)
    page_changed = tab_changed # Alias for 100% compatibility with any calling code

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedSize(620, 84)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 12, 0)
        self.layout.setSpacing(10)
        self.buttons = []
        
        nav_items = [
            ("Dashboard", "dashboard"), 
            ("Scan", "scan"), 
            ("History", "history"), 
            ("Settings", "settings")
        ]
        
        for i, (text, icon_name) in enumerate(nav_items):
            btn = NavButton(text, icon_name, i, self)
            btn.clicked.connect(lambda checked, idx=i: self.handle_click(idx))
            self.buttons.append(btn)
            self.layout.addWidget(btn)
            
        self.set_active_tab(0)
        self._apply_nav_theme()
        theme_manager.theme_changed.connect(self._apply_nav_theme)

    def handle_click(self, index):
        self.set_active_tab(index)

    def set_active_tab(self, idx):
        for i, btn in enumerate(self.buttons):
            btn.blockSignals(True)
            btn.setChecked(i == idx)
            btn.blockSignals(False)
            btn.update_style()
        self.tab_changed.emit(idx)

    def _apply_nav_theme(self):
        if theme_manager.current_theme == "light":
            self.setStyleSheet("QFrame { background: rgba(255, 255, 255, 210); border: 1px solid rgba(0, 0, 0, 15); border-radius: 42px; }")
        else:
            self.setStyleSheet("QFrame { background: rgba(13, 13, 13, 180); border: 1px solid rgba(255, 255, 255, 20); border-radius: 42px; }")

