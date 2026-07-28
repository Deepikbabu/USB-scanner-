import math
from PyQt6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTableWidget, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QColor
from theme import theme_manager

def draw_category_vector_icon(painter, category, x, y, size):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    accent = QColor_val = theme_manager.get_color("accent")
    accent_color = QColor(accent_color_str := theme_manager.get_color("accent"))
    painter.setPen(QPen(accent_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    cx, cy = x + size // 2, y + size // 2
    
    if category in ["USB Flash Drive", "Pen Drive"]:
        painter.drawRoundedRect(cx - 8, cy - 14, 16, 28, 4, 4)
        painter.drawRect(cx - 5, cy - 22, 10, 8)
        painter.drawLine(cx - 2, cy - 18, cx - 2, cy - 16)
        painter.drawLine(cx + 2, cy - 18, cx + 2, cy - 16)
    elif category == "External HDD":
        painter.drawRoundedRect(cx - 14, cy - 18, 28, 36, 6, 6)
        painter.drawEllipse(cx - 10, cy - 10, 20, 20)
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)
        painter.drawLine(cx, cy + 10, cx - 3, cy - 1)
    elif category == "External SSD":
        painter.drawRoundedRect(cx - 15, cy - 18, 30, 36, 5, 5)
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(cx - 15, cy - 6, 30, 16), Qt.AlignmentFlag.AlignCenter, "SSD")
        painter.drawLine(cx - 10, cy - 10, cx + 10, cy - 10)
        painter.drawLine(cx - 10, cy + 10, cx + 10, cy + 10)
    elif category == "USB Keyboard":
        painter.drawRoundedRect(cx - 20, cy - 10, 40, 20, 3, 3)
        painter.drawRect(cx - 16, cy - 6, 6, 4)
        painter.drawRect(cx - 7, cy - 6, 6, 4)
        painter.drawRect(cx + 2, cy - 6, 6, 4)
        painter.drawRect(cx + 11, cy - 6, 5, 4)
        painter.drawRect(cx - 16, cy + 1, 32, 4)
    elif category == "USB Mouse":
        painter.drawEllipse(cx - 10, cy - 16, 20, 32)
        painter.drawLine(cx, cy - 16, cx, cy)
        painter.drawRect(cx - 2, cy - 10, 4, 6)
    elif category == "USB-C Device":
        painter.drawRoundedRect(cx - 14, cy - 7, 28, 14, 5, 5)
        painter.drawLine(cx - 8, cy, cx + 8, cy)
    elif category == "HDMI Device":
        path = QPainterPath()
        path.moveTo(cx - 12, cy - 10)
        path.lineTo(cx + 12, cy - 10)
        path.lineTo(cx + 8, cy + 10)
        path.lineTo(cx - 8, cy + 10)
        path.closeSubpath()
        painter.drawPath(path)
        for i in range(4):
            px = cx - 5 + i * 3
            painter.drawLine(px, cy - 6, px, cy - 2)
    elif category == "3.5 mm Audio Device":
        painter.drawArc(cx - 14, cy - 14, 28, 28, 0, 180 * 16)
        painter.drawRoundedRect(cx - 16, cy, 5, 9, 2, 2)
        painter.drawRoundedRect(cx + 11, cy, 5, 9, 2, 2)
    elif category == "SD Card":
        path = QPainterPath()
        path.moveTo(cx - 10, cy - 16)
        path.lineTo(cx + 4, cy - 16)
        path.lineTo(cx + 10, cy - 10)
        path.lineTo(cx + 10, cy + 16)
        path.lineTo(cx - 10, cy + 16)
        path.closeSubpath()
        painter.drawPath(path)
        for i in range(3):
            px = cx - 6 + i * 3
            painter.drawLine(px, cy - 12, px, cy - 7)
    elif category == "Mobile Device":
        painter.drawRoundedRect(cx - 12, cy - 18, 24, 36, 5, 5)
        painter.drawRect(cx - 10, cy - 14, 20, 26)
        painter.drawEllipse(cx - 1, cy - 16, 2, 1)
    else:
        painter.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(cx - 15, cy - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, "?")

class GlassCard(QFrame):
    """Shared application card retained under its legacy public name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        self._hover_progress = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._handle_anim)
        
        self.update_style()
        theme_manager.theme_changed.connect(self.update_style)

    def _handle_anim(self, value):
        self._hover_progress = value
        self.update()

    def enterEvent(self, event):
        self.anim.setDirection(QVariantAnimation.Direction.Forward)
        if self.anim.state() != QVariantAnimation.State.Running:
            self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.setDirection(QVariantAnimation.Direction.Backward)
        if self.anim.state() != QVariantAnimation.State.Running:
            self.anim.start()
        super().leaveEvent(event)

    def update_style(self):
        self.setStyleSheet("QFrame#glassCard { background: transparent; border: none; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        card_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg_color = theme_manager.get_qcolor(
            "surface_hover" if self._hover_progress > 0.5 else "surface"
        )
        painter.setBrush(QBrush(bg_color))
        border = theme_manager.get_qcolor(
            "accent" if self._hover_progress > 0.75 else "border"
        )
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(card_rect, 12.0, 12.0)

class GlassProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassProgressBar")
        self.value = 0
        self.setFixedHeight(8)
        # Prevent stylesheets from overriding custom painting
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def setValue(self, val):
        self.value = val
        self.update()
        # Ensure parent chain is repainted for semi-transparent widgets
        p = self.parent()
        while p:
            p.update()
            p = p.parent()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        bg_color = QColor(255, 255, 255, 35) if theme_manager.current_theme == "dark" else QColor(15, 23, 42, 25)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(self.rect())
        painter.drawRoundedRect(rect, 4.0, 4.0)
        
        if self.value > 0:
            fill_width = rect.width() * (min(100.0, max(0.0, self.value)) / 100.0)
            if fill_width > 0:
                fill_rect = QRectF(0, 0, fill_width, rect.height())
                accent = QColor(theme_manager.get_color("accent"))
                
                gradient = QLinearGradient(0, 0, rect.width(), 0)
                gradient.setColorAt(0, accent)
                gradient.setColorAt(1, QColor(0, 229, 255, 200) if theme_manager.current_theme == "dark" else QColor(0, 180, 216, 200))
                
                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(fill_rect, 4.0, 4.0)

class StatusBadge(QWidget):
    SEMANTIC_COLORS = {
        "success": "success", "clean": "success", "trusted": "success",
        "warning": "warning", "suspicious": "warning", "incomplete": "warning",
        "danger": "danger", "dangerous": "danger", "blocked": "danger",
        "info": "info", "scanning": "info", "neutral": "text_secondary",
    }

    def __init__(self, text, color=None, parent=None, tone=None):
        super().__init__(parent)
        self.setObjectName("statusBadge")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 3, 9, 3)
        layout.setSpacing(6)
        
        self.dot = QWidget()
        self.dot.setFixedSize(6, 6)
        self.label = QLabel(text.upper())
        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        self.update_badge(text, color=color, tone=tone)

    def update_badge(self, text, color=None, tone=None):
        key = tone or str(text).lower()
        token = self.SEMANTIC_COLORS.get(key, "text_secondary")
        color = color or theme_manager.get_color(token)
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
        self.label.setText(text.upper())
        self.setStyleSheet(
            f"QWidget#statusBadge {{ background: {theme_manager.get_color('surface_raised')};"
            f" border: 1px solid {theme_manager.get_color('border')}; border-radius: 10px; }}"
            f" QLabel {{ color: {color}; font-size: 9px; font-weight: 800;"
            " letter-spacing: 0.6px; border: none; background: transparent; }}"
        )


class AppButton(QPushButton):
    """Button with a consistent semantic variant."""

    def __init__(self, text="", variant="secondary", parent=None):
        super().__init__(text, parent)
        self.setProperty("variant", variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class AppTableWidget(QTableWidget):
    """Standard table behavior shared by all data-heavy pages."""

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(44)
        self.horizontalHeader().setStretchLastSection(True)


class EmptyState(QFrame):
    """Reusable honest empty/loading/error state for page content."""

    def __init__(self, title="No data yet", message="", icon="◇", parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(7)
        self.icon = QLabel(icon)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message = QLabel(message)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        layout.addWidget(self.icon)
        layout.addWidget(self.title)
        layout.addWidget(self.message)
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    def set_content(self, title, message="", icon=None):
        self.title.setText(title)
        self.message.setText(message)
        if icon is not None:
            self.icon.setText(icon)

    def _apply_theme(self):
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QFrame#emptyState {{ background: {c['surface']}; border: 1px dashed {c['border']};
                                border-radius: 10px; }}
            QFrame#emptyState QLabel {{ background: transparent; border: 0; }}
        """)
        self.icon.setStyleSheet(f"color: {c['accent']}; font-size: 28px;")
        self.title.setStyleSheet(f"color: {c['text_primary']}; font-size: 14px; font-weight: 700;")
        self.message.setStyleSheet(f"color: {c['text_secondary']}; font-size: 11px;")


AppCard = GlassCard

class AnimatedUSBWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 120)
        self.pulse = 0
        self.flow = 0
        self.connected = False
        self.category = "Unknown Device"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

    def set_connected(self, connected, category="Unknown Device"):
        self.connected = connected
        self.category = category
        self.update()

    def update_animation(self):
        self.pulse = (self.pulse + 0.05) % (2 * math.pi)
        self.flow = (self.flow + (0.04 if self.connected else 0.02)) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        center = rect.center() 
        cx, cy = center.x(), center.y()
        
        accent = QColor(theme_manager.get_color("accent"))
        
        glow_alpha = int(35 + 20 * math.sin(self.pulse))
        if self.connected:
            glow_alpha = int(60 + 25 * math.sin(self.pulse * 1.5))
        glow_alpha = max(0, min(255, glow_alpha))
        glow_color = QColor(accent)
        glow_color.setAlpha(glow_alpha)
        
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 42.0, 42.0)
        
        if self.connected:
            draw_category_vector_icon(painter, self.category, int(cx - 20), int(cy - 20), 40)
            
            pen_ring = QPen(accent, 1, Qt.PenStyle.DashLine)
            painter.setPen(pen_ring)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, 50.0, 50.0)
            
            particle_angle = self.flow * 2 * math.pi
            px = cx + 50 * math.cos(particle_angle)
            py = cy + 50 * math.sin(particle_angle)
            painter.setBrush(QBrush(accent))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), 4.0, 4.0)
        else:
            pen_color = QColor(accent)
            pen_color.setAlpha(180)
            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            
            head_x, head_y = int(cx - 15), int(cy - 22)
            painter.drawRoundedRect(head_x, head_y, 30, 24, 4, 4)
            painter.drawRect(int(cx - 9), int(cy - 28), 6, 6)
            painter.drawRect(int(cx + 3), int(cy - 28), 6, 6)
            
            path = QPainterPath()
            path.moveTo(cx, cy + 4)
            path.cubicTo(cx, cy + 22, cx + 22, cy + 34, cx, cy + 46)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            
            light_pos = path.pointAtPercent(self.flow)
            painter.setBrush(QBrush(accent))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(light_pos, 3.5, 3.5)

class CircularRiskRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.angle = 0
        self.threat_active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(30)

    def update_angle(self):
        self.angle = (self.angle + 2) % 360
        self.update()

    def set_threat(self, threat):
        self.threat_active = threat
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        
        accent = QColor(theme_manager.get_color("accent"))
        if self.threat_active:
            accent = QColor("#B5522B")
            
        glass_border = QColor(theme_manager.get_color("glass_border"))
        if glass_border.alpha() == 0:
            glass_border = QColor(255, 255, 255, 25)
            
        painter.setPen(QPen(glass_border, 2.5))
        painter.drawEllipse(rect)
        
        pen = QPen(accent, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, int(-self.angle * 16), 110 * 16)
        
        painter.setPen(QPen(QColor(theme_manager.get_color("text_primary"))))
        painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        text = "100%" if self.threat_active else "0%"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
