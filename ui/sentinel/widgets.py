import math
from PyQt6.QtWidgets import QFrame, QWidget, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Hover animation properties
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
        self.setStyleSheet("""
            QLabel, QPushButton, QWidget {
                border: none;
                background-color: transparent;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base rectangle with drawing margin (12px) to prevent clipping when lifted/scaled/shadowed
        margin = 12.0
        base_rect = QRectF(self.rect())
        
        # Compute dynamic lifted and scaled rect
        lift = 4.0 * self._hover_progress
        scale = 1.01 * self._hover_progress
        
        card_rect = base_rect.adjusted(
            margin - scale,
            margin - lift - scale,
            -margin + scale,
            -margin - lift + scale
        )
        
        # Draw soft shadow manually
        # This replaces QGraphicsDropShadowEffect to avoid painter conflicts and boost performance on low-power devices
        shadow_opacity = int(35 + 25 * self._hover_progress)
        for offset in range(1, 6):
            shadow_rect = card_rect.adjusted(-offset * 1.5, -offset * 0.5 + 2.0, offset * 1.5, offset * 1.5 + 3.0)
            opacity = int((shadow_opacity / 5) * (6 - offset))
            painter.setBrush(QBrush(QColor(0, 0, 0, opacity)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shadow_rect, 24.0 + offset, 24.0 + offset)
        
        # Draw background glass (slightly brighter on hover)
        bg_color = theme_manager.get_qcolor('glass_bg')
        
        if self._hover_progress > 0:
            if theme_manager.current_theme == "dark":
                bg_color.setRed(min(255, bg_color.red() + int(10 * self._hover_progress)))
                bg_color.setGreen(min(255, bg_color.green() + int(10 * self._hover_progress)))
                bg_color.setBlue(min(255, bg_color.blue() + int(10 * self._hover_progress)))
                bg_color.setAlpha(min(255, bg_color.alpha() + int(10 * self._hover_progress)))
            else:
                bg_color.setAlpha(min(255, bg_color.alpha() + int(15 * self._hover_progress)))
                
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(card_rect, 24.0, 24.0)
        
        # Dynamic glass reflection (moving diagonal white/light-cyan sheen on hover)
        if self._hover_progress > 0.01:
            sheen_path = QPainterPath()
            sheen_path.addRoundedRect(card_rect, 24.0, 24.0)
            painter.save()
            painter.setClipPath(sheen_path)
            
            # Coordinate sliding based on hover progress
            start_x = card_rect.left() - card_rect.width() * 0.5 + (card_rect.width() * 1.5 * self._hover_progress)
            end_x = start_x + card_rect.width() * 0.3
            
            sheen_grad = QLinearGradient(QPointF(start_x, card_rect.top()), QPointF(end_x, card_rect.bottom()))
            sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            sheen_grad.setColorAt(0.5, QColor(255, 255, 255, int(25 * self._hover_progress)))
            sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(sheen_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(card_rect)
            painter.restore()
            
        # Draw elegant cybernetic semi-transparent cyan border
        accent_color_str = theme_manager.get_color("accent")
        accent = QColor(accent_color_str)
        
        # Base glass border
        glass_border = theme_manager.get_qcolor("glass_border")
        
        # Blend base glass border with growing cyan/accent glow on hover
        border_r = int(glass_border.red() + (accent.red() - glass_border.red()) * 0.4 * self._hover_progress)
        border_g = int(glass_border.green() + (accent.green() - glass_border.green()) * 0.4 * self._hover_progress)
        border_b = int(glass_border.blue() + (accent.blue() - glass_border.blue()) * 0.4 * self._hover_progress)
        border_a = int(glass_border.alpha() + (60 - glass_border.alpha()) * self._hover_progress)
        
        pen_color = QColor(border_r, border_g, border_b, border_a)
        pen = QPen(pen_color, 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card_rect, 24.0, 24.0)

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
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)
        
        self.dot = QWidget()
        self.dot.setFixedSize(6, 6)
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
        
        self.label = QLabel(text.upper())
        self.label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; border: none; background: transparent;")
        
        layout.addWidget(self.dot)
        layout.addWidget(self.label)

    def update_badge(self, text, color):
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
        self.label.setText(text.upper())
        self.label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; border: none; background: transparent;")

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

