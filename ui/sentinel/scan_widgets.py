import sys
import random
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea, QFrame, 
                             QGridLayout, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF, QVariantAnimation, QEasingCurve, QDateTime, QPropertyAnimation
from PyQt6.QtGui import QPainter, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QColor
from theme import theme_manager
from widgets import GlassCard

class GreenCheckIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.anim_progress = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.valueChanged.connect(self._on_anim)
        self.anim.start()

    def _on_anim(self, val):
        self.anim_progress = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        
        # Circle background
        bg_color = QColor("#D97F4A")
        bg_color.setAlpha(max(0, min(255, int(35 + 220 * self.anim_progress))))
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)
        
        # Checkmark line
        if self.anim_progress > 0.2:
            pen = QPen(QColor("#ffffff"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            p = QPainterPath()
            p.moveTo(rect.left() + rect.width() * 0.3, rect.top() + rect.height() * 0.5)
            p.lineTo(rect.left() + rect.width() * 0.45, rect.top() + rect.height() * 0.65)
            p.lineTo(rect.left() + rect.width() * 0.7, rect.top() + rect.height() * 0.35)
            painter.drawPath(p)

class GlassActionButton(QPushButton):
    def __init__(self, text, icon_type, parent=None):
        super().__init__(text, parent)
        self.icon_type = icon_type  # "document", "shield", "refresh"
        self.setMinimumSize(120, 36)
        self.setMaximumSize(180, 40)
        self._hover_progress = 0.0
        self._press_progress = 0.0
        
        # Hover animation
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(200)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.valueChanged.connect(self._on_hover_anim)
        
        # Press animation
        self.press_anim = QVariantAnimation(self)
        self.press_anim.setDuration(100)
        self.press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.press_anim.valueChanged.connect(self._on_press_anim)
        
    def _on_hover_anim(self, val):
        self._hover_progress = val
        self.update()
        
    def _on_press_anim(self, val):
        self._press_progress = val
        self.update()
        
    def enterEvent(self, event):
        self.hover_anim.setDirection(QVariantAnimation.Direction.Forward)
        if self.hover_anim.state() != QVariantAnimation.State.Running:
            self.hover_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.hover_anim.setDirection(QVariantAnimation.Direction.Backward)
        if self.hover_anim.state() != QVariantAnimation.State.Running:
            self.hover_anim.start()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        self.press_anim.setDirection(QVariantAnimation.Direction.Forward)
        if self.press_anim.state() != QVariantAnimation.State.Running:
            self.press_anim.start()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.press_anim.setDirection(QVariantAnimation.Direction.Backward)
        if self.press_anim.state() != QVariantAnimation.State.Running:
            self.press_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        scale = 1.0 + (0.03 * self._hover_progress) - (0.05 * self._press_progress)
        
        painter.save()
        painter.translate(width / 2.0, height / 2.0)
        painter.scale(scale, scale)
        painter.translate(-width / 2.0, -height / 2.0)
        
        rect = QRectF(2, 2, width - 4, height - 4)
        radius = height / 2.0 - 2.0
        
        accent_color = QColor(theme_manager.get_color("accent"))
        
        bg_color = QColor(255, 255, 255, 12) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 10)
        hover_bg = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(30 * self._hover_progress))
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        if self._hover_progress > 0:
            painter.setBrush(QBrush(hover_bg))
            painter.drawRoundedRect(rect, radius, radius)
            
        if self._hover_progress > 0:
            glow_pen = QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(120 * self._hover_progress)), 1.5)
            painter.setPen(glow_pen)
        else:
            border_color = QColor(255, 255, 255, 30) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 25)
            painter.setPen(QPen(border_color, 1.0))
            
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        
        text = self.text()
        font = QFont("Inter", 9, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        
        text_x = (width - text_width) / 2.0
        text_y = (height + fm.ascent() - fm.descent()) / 2.0
        
        text_color = QColor(theme_manager.get_color("text_primary"))
        if self._hover_progress > 0:
            text_color = QColor(
                int(text_color.red() * (1 - self._hover_progress) + accent_color.red() * self._hover_progress),
                int(text_color.green() * (1 - self._hover_progress) + accent_color.green() * self._hover_progress),
                int(text_color.blue() * (1 - self._hover_progress) + accent_color.blue() * self._hover_progress)
            )
        painter.setPen(QPen(text_color))
        painter.drawText(QPointF(text_x, text_y), text)
        
        painter.restore()

class CircularProgressRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(40, 40)
        self.value = 0.0
        self.display_value = 0.0
        self.blue_glow_active = False
        self.draw_check = False
        
        # Pulse animation
        self.pulse = 0.0
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start(30)

        # Smooth value transition animation
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(800)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_value)

    def setValue(self, val):
        self.value = float(val)
        if self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()
        self.anim.setStartValue(self.display_value)
        self.anim.setEndValue(self.value)
        self.anim.start()

    def _on_anim_value(self, val):
        self.display_value = val
        self.update()

    def set_blue_glow(self, active):
        self.blue_glow_active = active
        self.update()

    def set_draw_check(self, draw):
        self.draw_check = draw
        self.update()

    def _update_pulse(self):
        self.pulse = (self.pulse + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        thickness = max(4.0, min(w, h) * 0.08)
        
        # Margins to prevent clipping of the pen stroke width
        margin = thickness / 2.0 + 2.0
        draw_rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        
        is_dark = (theme_manager.current_theme == "dark")
        
        # Draw dynamic glass fill background
        inner_bg = QColor(255, 255, 255, 8) if is_dark else QColor(0, 0, 0, 5)
        painter.setBrush(QBrush(inner_bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(draw_rect)
        
        # Background Track
        track_color = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 12)
        bg_pen = QPen(track_color, thickness)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(draw_rect)
        
        # Draw Progress Arc
        val_pct = 100.0 if self.draw_check else self.display_value
        if val_pct > 0.001:
            angle = (val_pct / 100.0) * 360.0
            
            # Subtle glow effect underneath the main arc
            glow_color = QColor("#C98A5E") if self.blue_glow_active else QColor(theme_manager.get_color("accent"))
            glow_opacity = int(45 + 15 * math.sin(self.pulse))
            glow_color.setAlpha(max(0, min(255, glow_opacity)))
            glow_pen = QPen(glow_color, thickness + 2.5)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(draw_rect, 90 * 16, int(-angle * 16))
            
            # Main Foreground Arc
            main_color = QColor("#C98A5E") if self.blue_glow_active else QColor(theme_manager.get_color("accent"))
            gradient = QLinearGradient(draw_rect.topLeft(), draw_rect.bottomRight())
            gradient.setColorAt(0, main_color)
            gradient.setColorAt(1, QColor("#B5522B"))
            
            arc_pen = QPen(QBrush(gradient), thickness)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(draw_rect, 90 * 16, int(-angle * 16))
            
        # Draw inside percentage text - perfectly centered and styled
        text_color = QColor(theme_manager.get_color("text_primary"))
        painter.setPen(QPen(text_color))
        
        # Proportional crisp typography size
        font_size = int(min(w, h) * 0.18)
        font = QFont("JetBrains Mono", font_size, QFont.Weight.ExtraBold)
        painter.setFont(font)
        
        display_val = 100 if self.draw_check else int(val_pct)
        text = f"{display_val}%"
        
        # Draw precisely inside the full widget bounds to ensure perfect alignment
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

class AnimatedUSBScanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(210, 210)
        self.angle = 0.0
        self.wave_pos = 0.0
        self.wave_direction = 1
        self.pulse = 0.0
        self.particles = []
        self.scanning = False
        
        # Circular Progress Ring properties
        self.value = 0.0
        self.display_value = 0.0
        self.blue_glow_active = False
        self.draw_check = False
        
        # Checkmark transition animation
        self.check_anim_progress = 0.0
        self.check_anim = QVariantAnimation(self)
        self.check_anim.setDuration(450)
        self.check_anim.setStartValue(0.0)
        self.check_anim.setEndValue(1.0)
        self.check_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.check_anim.valueChanged.connect(self._on_check_anim)
        
        # Progress value transition animation
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(800)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_value)
        
        for _ in range(16):
            self.particles.append({
                'x': random.uniform(-60, 60),
                'y': random.uniform(-60, 60),
                'speed': random.uniform(0.6, 1.6),
                'size': random.uniform(1.5, 3.5),
                'angle': random.uniform(0, 2 * math.pi)
            })
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

    def setValue(self, val):
        self.value = float(val)
        if self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()
        self.anim.setStartValue(self.display_value)
        self.anim.setEndValue(self.value)
        self.anim.start()

    def _on_anim_value(self, val):
        self.display_value = val
        self.update()

    def set_blue_glow(self, active):
        self.blue_glow_active = active
        self.update()

    def set_draw_check(self, draw):
        self.draw_check = draw
        if draw:
            self.check_anim.setStartValue(self.check_anim_progress)
            self.check_anim.setEndValue(1.0)
            self.check_anim.start()
        else:
            self.check_anim_progress = 0.0
        self.update()

    def _on_check_anim(self, val):
        self.check_anim_progress = val
        self.update()

    def set_scanning(self, active):
        self.scanning = active

    def update_animation(self):
        if self.scanning:
            self.angle = (self.angle + 1.8) % 360
            self.wave_pos += self.wave_direction * 0.025
            if self.wave_pos >= 1.0:
                self.wave_pos = 1.0
                self.wave_direction = -1
            elif self.wave_pos <= 0.0:
                self.wave_pos = 0.0
                self.wave_direction = 1
                
            for p in self.particles:
                p['x'] += math.cos(p['angle']) * p['speed']
                p['y'] += math.sin(p['angle']) * p['speed']
                if p['x']**2 + p['y']**2 > 70**2:
                    p['x'] = 0
                    p['y'] = 0
                    p['angle'] = random.uniform(0, 2 * math.pi)
        else:
            self.angle = (self.angle + 0.3) % 360
            
        self.pulse = (self.pulse + 0.05) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect_widget = QRectF(self.rect())
        center = rect_widget.center()
        cx, cy = center.x(), center.y()
        
        accent = QColor(theme_manager.get_color("accent"))
        text_primary = QColor(theme_manager.get_color("text_primary"))
        
        # --- DRAW CORE PROGRESS RING (Surrounding everything) ---
        rect_ring = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        thickness = 8.0
        draw_rect = rect_ring.adjusted(thickness/2, thickness/2, -thickness/2, -thickness/2)
        
        # Background Track
        bg_pen = QPen(QColor(255, 255, 255, 12) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 12), thickness)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(draw_rect)
        
        # Draw Progress Arc
        if self.display_value > 0 or self.draw_check:
            val_pct = 100.0 if self.draw_check else self.display_value
            angle = (val_pct / 100.0) * 360.0
            
            # Glow Effect under Arc
            glow_color = QColor("#C98A5E") if self.blue_glow_active else QColor(accent)
            glow_opacity = int(40 + 15 * math.sin(self.pulse))
            glow_color.setAlpha(max(0, min(255, glow_opacity)))
            glow_pen = QPen(glow_color, thickness + 4.0)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(draw_rect, 90 * 16, int(-angle * 16))
            
            # Main Foreground Arc
            main_color = QColor("#C98A5E") if self.blue_glow_active else QColor(accent)
            gradient = QLinearGradient(draw_rect.topLeft(), draw_rect.bottomRight())
            gradient.setColorAt(0, main_color)
            gradient.setColorAt(1, QColor("#8A6455"))
            
            arc_pen = QPen(QBrush(gradient), thickness)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(draw_rect, 90 * 16, int(-angle * 16))
            
        # --- DRAW USB SCANNER OR CHECKMARK TRANSITION ---
        scan_opacity = 1.0 - self.check_anim_progress
        
        if scan_opacity > 0.001:
            # Ambient Pulse Glow inside
            glow_alpha = int((40 + 20 * math.sin(self.pulse)) * scan_opacity)
            if self.scanning:
                glow_alpha = int((75 + 30 * math.sin(self.pulse * 1.5)) * scan_opacity)
            glow_color = QColor(accent)
            glow_color.setAlpha(max(0, min(255, glow_alpha)))
            
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, 54.0, 54.0)
            
            # Draw central USB connector icon
            usb_color = QColor(text_primary)
            usb_color.setAlpha(max(0, min(255, int(255 * scan_opacity))))
            painter.setPen(QPen(usb_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw USB details
            hx, hy = int(cx - 15), int(cy - 24)
            painter.drawRoundedRect(hx, hy, 30, 24, 4, 4)
            painter.drawRect(int(cx - 9), int(cy - 20), 5, 5)
            painter.drawRect(int(cx + 4), int(cy - 20), 5, 5)
            painter.drawRect(int(cx - 18), int(cy), 36, 14)
            painter.drawLine(int(cx), int(cy + 14), int(cx), int(cy + 32))
            
            # Rotating outer scanning dashed ring (just inside the progress ring)
            ring_color = QColor(accent)
            ring_color.setAlpha(max(0, min(255, int(180 * scan_opacity))))
            ring_pen = QPen(ring_color, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(ring_pen)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self.angle)
            painter.drawEllipse(QPointF(0, 0), 76.0, 76.0)
            painter.restore()
            
            if self.scanning:
                # Moving scan wave
                wave_y = cy - 35 + (self.wave_pos * 70)
                wave_grad = QLinearGradient(cx - 55, wave_y, cx + 55, wave_y)
                laser_color = QColor(accent)
                laser_color.setAlpha(int(190 * scan_opacity))
                transparent_color = QColor(accent)
                transparent_color.setAlpha(0)
                wave_grad.setColorAt(0, transparent_color)
                wave_grad.setColorAt(0.5, laser_color)
                wave_grad.setColorAt(1, transparent_color)
                
                laser_pen = QPen(QBrush(wave_grad), 3)
                painter.setPen(laser_pen)
                painter.drawLine(int(cx - 60), int(wave_y), int(cx + 60), int(wave_y))
                
                # Flowing particles
                painter.setPen(Qt.PenStyle.NoPen)
                for p in self.particles:
                    part_color = QColor(accent)
                    dist = math.sqrt(p['x']**2 + p['y']**2)
                    alpha = int(240 * (1.0 - dist / 70.0) * scan_opacity)
                    part_color.setAlpha(max(0, min(255, alpha)))
                    painter.setBrush(QBrush(part_color))
                    painter.drawEllipse(QPointF(cx + p['x'], cy + p['y']), p['size'], p['size'])

        # Draw checkmark transition on completion
        if self.check_anim_progress > 0.001:
            # Smoothly fade in rust circle
            rust_color = QColor("#D97F4A")
            bg_opacity = int(255 * self.check_anim_progress)
            rust_color.setAlpha(max(0, min(255, bg_opacity)))
            
            painter.setBrush(QBrush(rust_color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            circle_radius = 42.0 * self.check_anim_progress
            painter.drawEllipse(QPointF(cx, cy), circle_radius, circle_radius)
            
            if self.check_anim_progress > 0.2:
                pen = QPen(QColor("#ffffff"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
                p = QPainterPath()
                p.moveTo(cx - 15 * self.check_anim_progress, cy)
                p.lineTo(cx - 3 * self.check_anim_progress, cy + 12 * self.check_anim_progress)
                p.lineTo(cx + 15 * self.check_anim_progress, cy - 12 * self.check_anim_progress)
                painter.drawPath(p)
                


class DeviceInfoCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        
        lbl_title = QLabel("DEVICE INFORMATION")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(lbl_title)
        
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        
        self.fields = {}
        field_names = [
            ("Device Name", "USB Mass Storage"),
            ("Manufacturer", "Kingston Technology"),
            ("Vendor ID", "0x0951"),
            ("Product ID", "0x1666"),
            ("Serial Number", "SN-928A-BD283"),
            ("USB Version", "USB 3.2 Gen 2"),
            ("Capacity", "64 GB"),
            ("File System", "exFAT"),
            ("Classification", "Secure Storage")
        ]
        
        for idx, (name, val) in enumerate(field_names):
            row = idx // 2
            col = (idx % 2) * 2
            
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter'; font-weight: 500;")
            
            lbl_val = QLabel(val)
            lbl_val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 11px; font-family: 'JetBrains Mono'; font-weight: 600;")
            
            self.fields[name] = lbl_val
            
            self.grid.addWidget(lbl_name, row, col)
            self.grid.addWidget(lbl_val, row, col + 1)
            
        layout.addLayout(self.grid)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
    def fade_in(self):
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(500)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def update_field(self, name, val):
        if name in self.fields:
            self.fields[name].setText(val)

class InventoryCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        
        lbl_title = QLabel("FILE INVENTORY")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(lbl_title)
        
        self.items = {}
        item_configs = [
            ("Files", 1250),
            ("Folders", 220),
            ("Executables", 15),
            ("Archives", 8),
            ("Hidden", 2)
        ]
        
        for name, target in item_configs:
            h_layout = QHBoxLayout()
            
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 12px; font-family: 'Inter';")
            
            lbl_count = QLabel("0")
            lbl_count.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 14px; font-family: 'JetBrains Mono'; font-weight: 700;")
            
            h_layout.addWidget(lbl_name)
            h_layout.addStretch()
            h_layout.addWidget(lbl_count)
            
            layout.addLayout(h_layout)
            self.items[name] = {
                'label': lbl_count,
                'target': target,
                'current': 0
            }
            
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
            
    def start_animation(self, duration=3000):
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(duration)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self._on_anim_update)
        self.anim.start()
        
    def _on_anim_update(self, progress):
        for name, data in self.items.items():
            val = int(data['target'] * progress)
            data['label'].setText(str(val))

    def update_inventory(self, inventory):
        values = inventory or {}
        key_map = {"Files": "files", "Folders": "folders", "Executables": "executables",
                   "Archives": "archives", "Hidden": "hidden"}
        for label, key in key_map.items():
            value = values.get(key)
            self.items[label]["label"].setText(str(value) if value is not None else "—")

    def reset_live(self):
        for data in self.items.values():
            data["label"].setText("—")

class ThreatCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        
        self.lbl_title = QLabel("ENDPOINT THREAT REPORT")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        h_score_layout = QHBoxLayout()
        h_score_layout.setSpacing(16)
        h_score_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.risk_ring = CircularProgressRing()
        self.risk_ring.setFixedSize(90, 90)
        h_score_layout.addWidget(self.risk_ring)
        
        v_level_layout = QVBoxLayout()
        v_level_layout.setSpacing(4)
        v_level_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_level = QLabel("SAFE")
        self.lbl_level.setStyleSheet("color: #D97F4A; font-size: 18px; font-weight: 800; font-family: 'Inter';")
        self.lbl_recommendation = QLabel("No anomalies detected. Device signature matches trusted definitions.")
        self.lbl_recommendation.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter';")
        self.lbl_recommendation.setWordWrap(True)
        
        v_level_layout.addWidget(self.lbl_level)
        v_level_layout.addWidget(self.lbl_recommendation)
        h_score_layout.addLayout(v_level_layout, 1)
        
        layout.addLayout(h_score_layout)
        
        # Malware detection area (hidden by default)
        self.malware_widget = QWidget()
        self.malware_widget.setObjectName("malwareWidget")
        malware_layout = QVBoxLayout(self.malware_widget)
        malware_layout.setContentsMargins(12, 12, 12, 12)
        malware_layout.setSpacing(6)
        self.malware_widget.setStyleSheet(f"""
            QWidget#malwareWidget {{
                background-color: rgba(181, 82, 43, 15);
                border: none;
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background-color: transparent;
            }}
        """)
        
        self.lbl_malware_title = QLabel("DETECTION TRACE:")
        self.lbl_malware_title.setStyleSheet("color: #B5522B; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_malware_name = QLabel("Threat Name: Trojan.Generic")
        self.lbl_malware_name.setStyleSheet("color: #ffffff; font-size: 11px; font-family: 'JetBrains Mono'; font-weight: 700;")
        self.lbl_malware_location = QLabel("Location: E:\\Downloads\\setup.exe")
        self.lbl_malware_location.setStyleSheet("color: #a1a1aa; font-size: 11px; font-family: 'JetBrains Mono';")
        self.lbl_malware_location.setWordWrap(True)
        
        malware_layout.addWidget(self.lbl_malware_title)
        malware_layout.addWidget(self.lbl_malware_name)
        malware_layout.addWidget(self.lbl_malware_location)
        
        layout.addWidget(self.malware_widget)
        self.malware_widget.hide()
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
    def update_threat_report(self, score, level, rec, malware_name=None, malware_loc=None):
        self.risk_ring.setValue(score)
        self.lbl_level.setText(level)
        self.lbl_recommendation.setText(rec)
        
        if level == "SAFE":
            self.lbl_level.setStyleSheet("color: #D97F4A; font-size: 18px; font-weight: 800; font-family: 'Inter';")
            self.malware_widget.hide()
        elif level == "LOW":
            self.lbl_level.setStyleSheet("color: #C98A5E; font-size: 18px; font-weight: 800; font-family: 'Inter';")
            self.malware_widget.hide()
        elif level == "MEDIUM":
            self.lbl_level.setStyleSheet("color: #C98A5E; font-size: 18px; font-weight: 800; font-family: 'Inter';")
            # Preserve a live detection trace when the following risk event is
            # describing remediation. A new scan explicitly resets this card.
            if malware_name and malware_loc:
                self.lbl_malware_name.setText(f"Threat Name: {malware_name}")
                self.lbl_malware_location.setText(f"Location: {malware_loc}")
                self.malware_widget.show()
        else: # HIGH / CRITICAL
            self.lbl_level.setStyleSheet("color: #B5522B; font-size: 18px; font-weight: 800; font-family: 'Inter';")
            if malware_name:
                self.lbl_malware_name.setText(f"Threat Name: {malware_name}")
                self.lbl_malware_location.setText(f"Location: {malware_loc or 'Not supplied by scanner'}")
                self.malware_widget.show()
 
class WarningCard(QWidget):
    def __init__(self, title, description, risk_level="MEDIUM", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        color_map = {
            "SAFE": "#D97F4A",
            "LOW": "#C98A5E",
            "MEDIUM": "#C98A5E",
            "HIGH": "#B5522B"
        }
        color = color_map.get(risk_level, "#C98A5E")
        
        bg_color = "rgba(0, 0, 0, 40)" if theme_manager.current_theme == 'dark' else "rgba(255, 255, 255, 120)"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {color}55;
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        self.lbl_icon = QLabel("●")
        self.lbl_icon.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 900; margin-left: 4px; margin-right: 4px;")
        layout.addWidget(self.lbl_icon)
        
        v_layout = QVBoxLayout()
        v_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 11px; font-weight: 800; font-family: 'Inter';")
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-family: 'Inter';")
        lbl_desc.setWordWrap(True)
        
        v_layout.addWidget(lbl_title)
        v_layout.addWidget(lbl_desc)
        
        layout.addLayout(v_layout, 1)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(400)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

class ScanStatsCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 16, 32, 16)
        layout.setSpacing(16)
        
        self.threats_block = QVBoxLayout()
        self.threats_block.setSpacing(2)
        self.threats_block.addStretch(1)
        lbl_threat_title = QLabel("THREATS DETECTED")
        lbl_threat_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; border: none; background: transparent;")
        self.lbl_threat_val = QLabel("0")
        self.lbl_threat_val.setStyleSheet("color: #D97F4A; font-size: 24px; font-weight: 800; font-family: 'JetBrains Mono'; border: none; background: transparent;")
        self.threats_block.addWidget(lbl_threat_title)
        self.threats_block.addWidget(self.lbl_threat_val)
        self.threats_block.addStretch(1)
        layout.addLayout(self.threats_block)
        
        layout.addSpacing(20)  # Gentle spacing instead of harsh line separator
        
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(24)
        
        # Column 1: ELAPSED
        elapsed_col = QVBoxLayout()
        elapsed_col.setSpacing(2)
        elapsed_col.addStretch(1)
        lbl_elapsed_title = QLabel("ELAPSED")
        lbl_elapsed_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-family: 'Inter'; font-weight: 700; border: none; background: transparent;")
        self.lbl_elapsed_val = QLabel("00:00")
        self.lbl_elapsed_val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 13px; font-family: 'JetBrains Mono'; font-weight: 700; border: none; background: transparent;")
        elapsed_col.addWidget(lbl_elapsed_title)
        elapsed_col.addWidget(self.lbl_elapsed_val)
        elapsed_col.addStretch(1)
        
        # Column 2: REMAINING
        remaining_col = QVBoxLayout()
        remaining_col.setSpacing(2)
        remaining_col.addStretch(1)
        lbl_remaining_title = QLabel("REMAINING")
        lbl_remaining_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-family: 'Inter'; font-weight: 700; border: none; background: transparent;")
        self.lbl_remaining_val = QLabel("00:00")
        self.lbl_remaining_val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 13px; font-family: 'JetBrains Mono'; font-weight: 700; border: none; background: transparent;")
        remaining_col.addWidget(lbl_remaining_title)
        remaining_col.addWidget(self.lbl_remaining_val)
        remaining_col.addStretch(1)
        
        # Column 3: SPEED
        speed_col = QVBoxLayout()
        speed_col.setSpacing(2)
        speed_col.addStretch(1)
        lbl_speed_title = QLabel("SPEED")
        lbl_speed_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-family: 'Inter'; font-weight: 700; border: none; background: transparent;")
        self.lbl_speed_val = QLabel("0 MB/s")
        self.lbl_speed_val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 13px; font-family: 'JetBrains Mono'; font-weight: 700; border: none; background: transparent;")
        speed_col.addWidget(lbl_speed_title)
        speed_col.addWidget(self.lbl_speed_val)
        speed_col.addStretch(1)
        
        self.stats_layout.addLayout(elapsed_col, 1)
        self.stats_layout.addLayout(remaining_col, 1)
        self.stats_layout.addLayout(speed_col, 1)
        
        layout.addLayout(self.stats_layout, 1)
        
    def set_threats(self, count):
        self.lbl_threat_val.setText(str(count))
        if count > 0:
            self.lbl_threat_val.setStyleSheet("color: #B5522B; font-size: 24px; font-weight: 800; font-family: 'JetBrains Mono'; border: none; background: transparent;")
            self.pulse_anim = QVariantAnimation(self)
            self.pulse_anim.setDuration(300)
            self.pulse_anim.setStartValue(1.0)
            self.pulse_anim.setEndValue(1.3)
            self.pulse_anim.valueChanged.connect(self._on_pulse_threat)
            self.pulse_anim.start()
        else:
            self.lbl_threat_val.setStyleSheet("color: #D97F4A; font-size: 24px; font-weight: 800; font-family: 'JetBrains Mono'; border: none; background: transparent;")
            
    def _on_pulse_threat(self, scale):
        font = QFont("JetBrains Mono", int(18 * scale), QFont.Weight.Bold)
        self.lbl_threat_val.setFont(font)
        
    def update_stats(self, elapsed_sec, remaining_sec, speed_mbs):
        m_el, s_el = divmod(int(elapsed_sec), 60)
        m_rem, s_rem = divmod(int(remaining_sec), 60)
        
        self.lbl_elapsed_val.setText(f"{m_el:02d}:{s_el:02d}")
        self.lbl_remaining_val.setText(f"{m_rem:02d}:{s_rem:02d}" if remaining_sec > 0 else "00:00")
        self.lbl_speed_val.setText(f"{speed_mbs} MB/s")

class LogCard(QWidget):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        bg_color = "rgba(255, 255, 255, 15)" if theme_manager.current_theme == 'dark' else "rgba(0, 0, 0, 8)"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        # Sleek terminal chevron
        self.lbl_chevron = QLabel("»")
        self.lbl_chevron.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-size: 11px; font-family: 'JetBrains Mono'; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(self.lbl_chevron)
        
        # Message
        self.lbl_message = QLabel(message)
        self.lbl_message.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 11px; font-family: 'JetBrains Mono'; border: none; background: transparent;")
        self.lbl_message.setWordWrap(True)
        layout.addWidget(self.lbl_message, 1)
        
        # Timestamp
        self.lbl_time = QLabel(QDateTime.currentDateTime().toString("hh:mm:ss"))
        self.lbl_time.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-family: 'JetBrains Mono'; border: none; background: transparent;")
        layout.addWidget(self.lbl_time)
        
        # Fade-in Animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(400)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

class LogContainerCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        
        self.lbl_title = QLabel("SCAN LOG TRACE")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        self.logs_scroll = QScrollArea()
        self.logs_scroll.setWidgetResizable(True)
        self.logs_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.logs_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.logs_content = QWidget()
        self.logs_content.setStyleSheet("background: transparent;")
        self.logs_layout = QVBoxLayout(self.logs_content)
        self.logs_layout.setContentsMargins(0, 0, 0, 0)
        self.logs_layout.setSpacing(6)
        self.logs_layout.addStretch()
        self.logs_scroll.setWidget(self.logs_content)
        
        # ScrollBar styling
        self.logs_scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 40);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 70);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        layout.addWidget(self.logs_scroll)
        
    def update_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")

class ActivityCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(10)
        
        lbl_title = QLabel("ACTIVITY TIMELINE")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(lbl_title)
        
        self.stages = [
            "Reading Device",
            "Checking Firmware",
            "Inspecting Archives",
            "Hidden File Detection",
            "Autorun Detection",
            "Malware Scan",
            "Risk Score Calculation"
        ]
        
        self.items = []
        for stage in self.stages:
            h_layout = QHBoxLayout()
            h_layout.setSpacing(10)
            
            lbl_dot = QLabel("●")
            lbl_dot.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 12px;")
            
            lbl_name = QLabel(stage)
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter'; font-weight: 500;")
            
            h_layout.addWidget(lbl_dot)
            h_layout.addWidget(lbl_name)
            h_layout.addStretch()
            
            layout.addLayout(h_layout)
            self.items.append({
                'dot': lbl_dot,
                'name': lbl_name,
                'status': 'pending' # pending, scanning, completed
            })
            
    def set_stage_status(self, stage_idx, status):
        if stage_idx < 0 or stage_idx >= len(self.items):
            return
            
        item = self.items[stage_idx]
        item['status'] = status
        
        accent = theme_manager.get_color("accent")
        if status == 'completed':
            item['dot'].setText("✔")
            item['dot'].setStyleSheet("color: #D97F4A; font-size: 11px; font-weight: 900;")
            item['name'].setStyleSheet("color: #D97F4A; font-size: 11px; font-family: 'Inter'; font-weight: 600;")
        elif status == 'scanning':
            item['dot'].setText("●")
            item['dot'].setStyleSheet(f"color: {accent}; font-size: 12px;")
            item['name'].setStyleSheet(f"color: {accent}; font-size: 11px; font-family: 'Inter'; font-weight: 700;")
        else: # pending
            item['dot'].setText("●")
            item['dot'].setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 12px;")
            item['name'].setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter'; font-weight: 500;")

    def reset(self):
        for idx in range(len(self.items)):
            self.set_stage_status(idx, 'pending')

class SuspiciousFilePopup(QWidget):
    action_taken = pyqtSignal(str) # 'keep' or 'isolate'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("suspiciousPopup")
        if parent:
            self.resize(parent.size())
            parent.installEventFilter(self)
            
        self.card = GlassCard(self)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(32, 32, 32, 32)
        self.card_layout.setSpacing(16)
        
        lbl_title = QLabel("SUSPICIOUS FILE DETECTED")
        lbl_title.setStyleSheet("color: #B5522B; font-size: 13px; font-weight: 900; font-family: 'Inter'; letter-spacing: 1.5px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addWidget(lbl_title)
        
        self.lbl_filename = QLabel("File: invoice.pdf.exe")
        self.lbl_filename.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 14px; font-weight: 700; font-family: 'Inter';")
        self.lbl_filename.setWordWrap(True)
        self.card_layout.addWidget(self.lbl_filename)
        
        self.lbl_filepath = QLabel("Path: E:\\invoice.pdf.exe")
        self.lbl_filepath.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'JetBrains Mono';")
        self.lbl_filepath.setWordWrap(True)
        self.card_layout.addWidget(self.lbl_filepath)
        
        self.lbl_reason = QLabel("Reason: Double extension detected (pdf.exe). High likelihood of masquerading malware.")
        self.lbl_reason.setStyleSheet("color: #C98A5E; font-size: 11px; font-family: 'Inter'; font-weight: 600;")
        self.lbl_reason.setWordWrap(True)
        self.card_layout.addWidget(self.lbl_reason)
        
        h_btn = QHBoxLayout()
        h_btn.setSpacing(12)
        
        self.btn_keep = QPushButton("KEEP")
        self.btn_isolate = QPushButton("ISOLATE")
        
        h_btn.addWidget(self.btn_keep)
        h_btn.addWidget(self.btn_isolate)
        self.card_layout.addLayout(h_btn)
        
        self.btn_keep.clicked.connect(self._on_keep)
        self.btn_isolate.clicked.connect(self._on_isolate)
        
        self.setStyleSheet_custom()
        theme_manager.theme_changed.connect(self.setStyleSheet_custom)
        
        self.hide()
        
    def setStyleSheet_custom(self):
        self.btn_keep.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('btn_bg')};
                color: {theme_manager.get_color('text_primary')};
                border: 1px solid {theme_manager.get_color('glass_border')};
                border-radius: 18px;
                min-height: 36px;
                max-height: 36px;
                padding: 0px 24px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.get_color('btn_hover')};
                border: 1px solid {theme_manager.get_color('accent')};
            }}
        """)
        self.btn_isolate.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(181, 82, 43, 0.8), stop:1 rgba(181, 82, 43, 0.55));
                color: #ffffff;
                border: 1px solid rgba(181, 82, 43, 0.8);
                border-radius: 18px;
                min-height: 36px;
                max-height: 36px;
                padding: 0px 24px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B5522B, stop:1 #964423);
                border: 1px solid #ffffff44;
            }}
        """)
        
    def show_popup(self, filename, filepath, reason):
        self.lbl_filename.setText(f"File: {filename}")
        self.lbl_filepath.setText(f"Path: {filepath}")
        self.lbl_reason.setText(f"Reason: {reason}")
        self.show()
        self.raise_()
        self._reposition()
        
    def _reposition(self):
        if self.parent():
            self.resize(self.parent().size())
            card_width, card_height = 360, 260
            self.card.setGeometry(
                int((self.width() - card_width) / 2),
                int((self.height() - card_height) / 2),
                card_width,
                card_height
            )
            
    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == event.Type.Resize:
            self._reposition()
        return super().eventFilter(obj, event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
    def _on_keep(self):
        self.action_taken.emit("keep")
        self.hide()
        
    def _on_isolate(self):
        self.action_taken.emit("isolate")
        self.hide()
