from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPointF, QDateTime
from theme import theme_manager
from widgets import GlassCard, StatusBadge, draw_category_vector_icon
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath
import math

class HistoryItemWidget(QFrame):
    def __init__(self, device, timestamp, status, parent=None):
        super().__init__(parent)
        self.device = device
        self.setFixedHeight(64)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)
        
        # We draw the icon in a custom painter box on the left
        self.icon_box = QWidget()
        self.icon_box.setFixedSize(40, 40)
        self.icon_box.paintEvent = self.paint_icon
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.lbl_name = QLabel(device['name'])
        self.lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self.lbl_meta = QLabel(f"VID: {device['vid']} | PID: {device['pid']} | {timestamp}")
        self.lbl_meta.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; background: transparent; border: none;")
        
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_meta)
        
        badge_color = theme_manager.get_color("accent") if status == "ALLOWED" else theme_manager.get_color("text_secondary")
        self.badge = StatusBadge(status, badge_color)
        
        layout.addWidget(self.icon_box)
        layout.addLayout(info_layout, 1)
        layout.addWidget(self.badge)
        
        self.update_style()
        theme_manager.theme_changed.connect(self.update_style)

    def paint_icon(self, event):
        painter = QPainter(self.icon_box)
        draw_category_vector_icon(painter, self.device['category'], 0, 0, 40)

    def update_style(self):
        bg = "rgba(255, 255, 255, 6)" if theme_manager.current_theme == "dark" else "rgba(15, 23, 42, 6)"
        border = theme_manager.get_color("glass_border")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 0.5px solid {border};
                border-radius: 12px;
            }}
        """)
        self.lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self.lbl_meta.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; background: transparent; border: none;")
        
        # Update badge dynamically
        badge_color = theme_manager.get_color("accent") if self.badge.label.text() == "ALLOWED" else theme_manager.get_color("text_secondary")
        self.badge.update_badge(self.badge.label.text(), badge_color)

class ScanAnalyticsGraph(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(250)
        self.setMouseTracking(True)
        
        # Raw chart data
        self.days, self.scores, self.devices, self.results = [], [], [], []
        
        self.hovered_index = -1
        self.animation_progress = 0.0
        
        # Grow timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(20)
        
    def animate(self):
        if self.animation_progress < 1.0:
            self.animation_progress = min(1.0, self.animation_progress + 0.04)
            self.update()
        else:
            self.timer.stop()
            
    def mouseMoveEvent(self, event):
        pos = event.position()
        
        # Base rectangle of the visible card (accounts for 12px glass card margin)
        margin = 12.0
        lift = 5.0 * self._hover_progress if hasattr(self, "_hover_progress") else 0.0
        scale = 1.02 * self._hover_progress if hasattr(self, "_hover_progress") else 0.0
        
        base_rect = QRectF(self.rect())
        card_rect = base_rect.adjusted(
            margin - scale,
            margin - lift - scale,
            -margin + scale,
            -margin - lift + scale
        )
        
        # Dimensions inside the visible card
        left_padding = 48
        right_padding = 24
        top_padding = 64
        bottom_padding = 36
        
        chart_left = card_rect.left() + left_padding
        chart_right = card_rect.right() - right_padding
        chart_top = card_rect.top() + top_padding
        chart_bottom = card_rect.bottom() - bottom_padding
        
        w = chart_right - chart_left
        h = chart_bottom - chart_top
        if w <= 0 or h <= 0:
            return
            
        x_step = w / 6.0
        
        # Check if near any data point
        closest_idx = -1
        min_dist = 25.0  # Pixels radius
        
        for i in range(7):
            cx = chart_left + i * x_step
            cy = chart_bottom - (h * (self.scores[i] / 100.0))
            dist = math.hypot(pos.x() - cx, pos.y() - cy)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
                
        if closest_idx != self.hovered_index:
            self.hovered_index = closest_idx
            self.update()
            
    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()

    def paintEvent(self, event):
        # Draw GlassCard base background & border
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base rectangle of the visible card (accounts for 12px glass card margin)
        margin = 12.0
        lift = 5.0 * self._hover_progress if hasattr(self, "_hover_progress") else 0.0
        scale = 1.02 * self._hover_progress if hasattr(self, "_hover_progress") else 0.0
        
        base_rect = QRectF(self.rect())
        card_rect = base_rect.adjusted(
            margin - scale,
            margin - lift - scale,
            -margin + scale,
            -margin - lift + scale
        )
        
        # Dimensions inside the visible card
        left_padding = 48
        right_padding = 24
        top_padding = 64
        bottom_padding = 36
        
        chart_left = card_rect.left() + left_padding
        chart_right = card_rect.right() - right_padding
        chart_top = card_rect.top() + top_padding
        chart_bottom = card_rect.bottom() - bottom_padding
        
        w = chart_right - chart_left
        h = chart_bottom - chart_top
        if w <= 0 or h <= 0:
            return
            
        x_step = w / 6.0
        base_y = chart_bottom
        
        # Title and Subtitle (perfectly aligned with the other card titles at left margin + 18)
        painter.setPen(QPen(QColor(theme_manager.get_color("text_primary"))))
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(int(card_rect.left() + 18), int(card_rect.top() + 22), "SCAN ANALYTICS")
        
        painter.setPen(QPen(QColor(theme_manager.get_color("text_secondary"))))
        painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
        painter.drawText(int(card_rect.left() + 18), int(card_rect.top() + 35), "USB Security Activity Overview")
        
        # Draw horizontal faint guidelines at Y=50 and Y=100
        grid_pen = QPen(QColor(255, 255, 255, 12) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 8), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.drawLine(int(chart_left), int(chart_top + h/2), int(chart_right), int(chart_top + h/2))
        painter.drawLine(int(chart_left), int(chart_top), int(chart_right), int(chart_top))
        
        # Draw Y-axis labels (positioned to the left of chart_left)
        painter.setPen(QPen(QColor(theme_manager.get_color("text_secondary"))))
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.drawText(QRect(int(card_rect.left()), int(chart_top - 8), int(left_padding - 6), 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "100")
        painter.drawText(QRect(int(card_rect.left()), int(chart_top + h/2 - 8), int(left_padding - 6), 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "50")
        painter.drawText(QRect(int(card_rect.left()), int(chart_bottom - 8), int(left_padding - 6), 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "0")
        
        # Draw X-axis labels (days)
        days_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day_lbl in enumerate(days_short):
            cx = chart_left + i * x_step
            painter.drawText(QRect(int(cx - 20), int(chart_bottom + 6), 40, 16), Qt.AlignmentFlag.AlignCenter, day_lbl)
            
        # Map raw data points
        points = []
        for i in range(7):
            cx = chart_left + i * x_step
            cy = base_y - (h * (self.scores[i] / 100.0))
            points.append(QPointF(cx, cy))
            
        # Construct animated spline points
        anim_points = []
        for p in points:
            ay = base_y - (base_y - p.y()) * self.animation_progress
            anim_points.append(QPointF(p.x(), ay))
            
        # Catmull-Rom Smooth Spline Path Construction
        path = QPainterPath()
        path.moveTo(anim_points[0])
        for i in range(6):
            p0 = anim_points[max(0, i-1)]
            p1 = anim_points[i]
            p2 = anim_points[i+1]
            p3 = anim_points[min(6, i+2)]
            
            tension = 0.25
            cp1x = p1.x() + (p2.x() - p0.x()) * tension
            cp1y = p1.y() + (p2.y() - p0.y()) * tension
            
            cp2x = p2.x() - (p3.x() - p1.x()) * tension
            cp2y = p2.y() - (p3.y() - p1.y()) * tension
            
            path.cubicTo(cp1x, cp1y, cp2x, cp2y, p2.x(), p2.y())
            
        # Draw vertical gradient fill under spline path
        fill_path = QPainterPath(path)
        fill_path.lineTo(anim_points[-1].x(), base_y)
        fill_path.lineTo(anim_points[0].x(), base_y)
        fill_path.closeSubpath()
        
        accent_hex = theme_manager.get_color("accent")
        accent_color = QColor(accent_hex)
        
        fill_grad = QLinearGradient(0, chart_top, 0, base_y)
        fill_grad.setColorAt(0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 45))
        fill_grad.setColorAt(1, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
        painter.fillPath(fill_path, QBrush(fill_grad))
        
        # Draw smooth line
        line_pen = QPen(accent_color, 2.2)
        painter.setPen(line_pen)
        painter.drawPath(path)
        
        # Draw glowing point nodes
        for idx, p in enumerate(anim_points):
            is_hovered = (idx == self.hovered_index)
            r = 6.0 if is_hovered else 3.5
            
            # Glow halo
            glow = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 80 if is_hovered else 40)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(p, r + 4, r + 4)
            
            # Inner circle
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(accent_color, 1.5))
            painter.drawEllipse(p, r, r)
            
        # Draw elegant hover tooltip
        if self.hovered_index != -1:
            p = anim_points[self.hovered_index]
            day = self.days[self.hovered_index]
            score = self.scores[self.hovered_index]
            dev = self.devices[self.hovered_index]
            res = self.results[self.hovered_index]
            
            tw = 160
            th = 85
            
            tx = p.x() + 15
            if tx + tw > card_rect.right() - 8:
                tx = p.x() - tw - 15
            ty = p.y() - th - 15
            if ty < card_rect.top() + 8:
                ty = p.y() + 15
                 
            tooltip_rect = QRectF(tx, ty, tw, th)
            
            painter.save()
            # Glass container with subtle theme accent border
            painter.setPen(QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 120), 1))
            tooltip_bg = QColor(13, 13, 13, 230) if theme_manager.current_theme == "dark" else QColor(255, 255, 255, 230)
            painter.setBrush(QBrush(tooltip_bg))
            painter.drawRoundedRect(tooltip_rect, 10.0, 10.0)
            
            # Content Text
            painter.setPen(QPen(QColor(theme_manager.get_color("text_primary"))))
            
            # Day title
            painter.setFont(QFont("Inter", 8, QFont.Weight.ExtraBold))
            painter.drawText(int(tx + 10), int(ty + 20), f"{day.upper()}")
            
            # Device Name
            painter.setPen(QPen(QColor(theme_manager.get_color("text_secondary"))))
            painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
            painter.drawText(int(tx + 10), int(ty + 38), f"Device: {dev}")
            
            # Risk Score
            score_clr = theme_manager.get_color("accent")
            painter.setPen(QPen(QColor(score_clr)))
            painter.setFont(QFont("Inter", 9, QFont.Weight.ExtraBold))
            painter.drawText(int(tx + 10), int(ty + 56), f"Risk Score: {score}")
            
            # Result
            painter.setPen(QPen(QColor(theme_manager.get_color("text_secondary"))))
            painter.setFont(QFont("Inter", 8, QFont.Weight.Normal))
            painter.drawText(int(tx + 10), int(ty + 72), f"Status: {res}")
            
            painter.restore()

class StatIconWidget(QWidget):
    def __init__(self, icon_type, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(36, 36)
        self.update_styles()
        theme_manager.theme_changed.connect(self.update_styles)
        
    def update_styles(self):
        self.accent_hex = theme_manager.get_color("accent")
        self.accent_color = QColor(self.accent_hex)
        self.text_sec_color = QColor(theme_manager.get_color("text_secondary"))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clean background (no filled color block or background container)
        # This completely resolves "dont use multiple colour and colour blocks"
        
        # Draw vector icon with standard theme text_secondary color for a sleek, modern, cohesive look
        # This perfectly aligns with "looks too old and is very colourful change those icons and sync with the ui theme"
        painter.setPen(QPen(self.text_sec_color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        
        if self.icon_type == "total_scans":
            # Sleek modern magnifying glass scan icon
            painter.drawEllipse(QPointF(cx - 3, cy - 3), 6, 6)
            painter.drawLine(QPointF(cx + 1.2, cy + 1.2), QPointF(cx + 8, cy + 8))
        elif self.icon_type == "devices":
            # Modern thin laptop outline
            painter.drawRoundedRect(QRectF(cx - 9, cy - 6, 18, 10), 2, 2)
            painter.drawLine(QPointF(cx - 12, cy + 5), QPointF(cx + 12, cy + 5))
            painter.drawLine(QPointF(cx - 2, cy + 4), QPointF(cx + 2, cy + 4))
        elif self.icon_type == "threats":
            # Minimalist elegant triangle alert icon
            path = QPainterPath()
            path.moveTo(cx, cy - 9)
            path.lineTo(cx - 9, cy + 7)
            path.lineTo(cx + 9, cy + 7)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(cx, cy - 3), QPointF(cx, cy + 1))
            painter.drawPoint(QPointF(cx, cy + 4))
        elif self.icon_type == "blocked":
            # Sleek lock / closed loop shield icon
            path = QPainterPath()
            path.moveTo(cx, cy - 9)
            path.lineTo(cx + 7, cy - 9)
            path.lineTo(cx + 7, cy - 1)
            path.quadTo(cx + 7, cy + 6, cx, cy + 9)
            path.quadTo(cx - 7, cy + 6, cx - 7, cy - 1)
            path.lineTo(cx - 7, cy - 9)
            path.closeSubpath()
            painter.drawPath(path)
            # Modern inner shield core
            painter.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 3))
        elif self.icon_type == "avg_risk":
            # Modern trending-up minimalist line chart arrow
            painter.drawLine(QPointF(cx - 8, cy + 6), QPointF(cx - 3, cy + 1))
            painter.drawLine(QPointF(cx - 3, cy + 1), QPointF(cx + 2, cy - 3))
            painter.drawLine(QPointF(cx + 2, cy - 3), QPointF(cx + 8, cy - 8))
            painter.drawLine(QPointF(cx + 3, cy - 8), QPointF(cx + 8, cy - 8))
            painter.drawLine(QPointF(cx + 8, cy - 8), QPointF(cx + 8, cy - 3))
        elif self.icon_type == "clean_rate":
            # Beautiful sleek checkmark in a thin circle
            painter.drawEllipse(QPointF(cx, cy), 8, 8)
            # Thin checkmark
            painter.drawLine(QPointF(cx - 3.5, cy), QPointF(cx - 1, cy + 2.5))
            painter.drawLine(QPointF(cx - 1, cy + 2.5), QPointF(cx + 4, cy - 3))

class StatCard(GlassCard):
    def __init__(self, title, target_val, prefix="", suffix="", icon_type="total_scans", parent=None):
        super().__init__(parent)
        self.title = title
        self.target_val = target_val
        self.current_val = 0.0 if isinstance(target_val, float) else 0
        self.prefix = prefix
        self.suffix = suffix
        
        self.setFixedHeight(84)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(26, 16, 26, 16)
        layout.setSpacing(10)
        
        self.icon_widget = StatIconWidget(icon_type)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_num = QLabel(f"{self.prefix}0{self.suffix}")
        self.lbl_num.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 800; font-size: 20px; background: transparent; border: none;")
        
        self.lbl_desc = QLabel(self.title.upper())
        self.lbl_desc.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;")
        
        info_layout.addWidget(self.lbl_num)
        info_layout.addWidget(self.lbl_desc)
        
        layout.addWidget(self.icon_widget)
        layout.addLayout(info_layout, 1)
        
        self.update_styles()
        theme_manager.theme_changed.connect(self.update_styles)
        
        # Anim timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.increment)
        self.anim_timer.start(20)
        
    def update_styles(self):
        self.lbl_num.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 800; font-size: 20px; background: transparent; border: none;")
        self.lbl_desc.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;")

    def increment(self):
        if isinstance(self.target_val, float):
            step = self.target_val / 25.0
            if self.current_val < self.target_val:
                self.current_val = min(self.target_val, self.current_val + step)
                self.lbl_num.setText(f"{self.prefix}{self.current_val:.1f}{self.suffix}")
            else:
                self.anim_timer.stop()
        else:
            step = max(1, int(self.target_val / 25))
            if self.current_val < self.target_val:
                self.current_val = min(self.target_val, self.current_val + step)
                self.lbl_num.setText(f"{self.prefix}{self.current_val}{self.suffix}")
            else:
                self.anim_timer.stop()

class DoughnutPainter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(20)
        
    def animate(self):
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + 0.04)
            self.update()
        else:
            self.timer.stop()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        accent_hex = theme_manager.get_color("accent")
        accent_color = QColor(accent_hex)
        
        slices = [
            (0.60, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 255)),
            (0.20, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180)),
            (0.15, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 120)),
            (0.05, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 60))
        ]
        
        start_angle = 90 * 16
        total_sweep = 360 * self.progress
        pen_width = 16
        
        bg_color = QColor(255, 255, 255, 15) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 10)
        painter.setPen(QPen(bg_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(rect)
        
        for pct, color in slices:
            sweep = -int(pct * total_sweep * 16)
            pen = QPen(color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, start_angle, sweep)
            start_angle += sweep
            
        painter.setPen(QPen(QColor(theme_manager.get_color("text_secondary"))))
        painter.setFont(QFont("Inter", 9, QFont.Weight.ExtraBold))
        text_rect = rect.adjusted(14, 14, -14, -14)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "RISK\nRATIO")

class DoughnutChartWidget(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(340)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)
        
        lbl_title = QLabel("RISK LEVEL DISTRIBUTION")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent;")
        main_layout.addWidget(lbl_title)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        self.chart_paint = DoughnutPainter()
        self.chart_paint.setFixedSize(140, 140)
        content_layout.addWidget(self.chart_paint)
        
        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(10)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.legend_items = []
        slices_data = [
            ("Safe", "60%", 255),
            ("Low Risk", "20%", 180),
            ("Medium Risk", "15%", 120),
            ("High Threat", "5%", 60)
        ]
        
        for name, pct, alpha in slices_data:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(8)
            
            dot = QLabel()
            dot.setFixedSize(8, 8)
            
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: 500; background: transparent;")
            
            lbl_val = QLabel(pct)
            lbl_val.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 700; background: transparent;")
            
            item_layout.addWidget(dot)
            item_layout.addWidget(lbl_name)
            item_layout.addStretch()
            item_layout.addWidget(lbl_val)
            
            legend_layout.addLayout(item_layout)
            self.legend_items.append((dot, lbl_name, lbl_val, alpha))
            
        content_layout.addLayout(legend_layout, 1)
        main_layout.addLayout(content_layout)
        self.update_styles()
        
    def update_styles(self):
        accent_hex = theme_manager.get_color("accent")
        accent_color = QColor(accent_hex)
        for dot, lbl_name, lbl_val, alpha in self.legend_items:
            dot.setStyleSheet(f"background-color: rgba({accent_color.red()}, {accent_color.green()}, {accent_color.blue()}, {alpha}); border-radius: 4px; border: none;")
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: 500; background: transparent;")
            lbl_val.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 700; background: transparent;")
        self.chart_paint.update()

class DeviceBarItem(QWidget):
    def __init__(self, name, count, max_count, parent=None):
        super().__init__(parent)
        self.name = name
        self.count = count
        self.max_count = max_count
        self.progress = 0.0
        
        self.setFixedHeight(28)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        lbl_row = QHBoxLayout()
        lbl_row.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_name = QLabel(self.name)
        self.lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: 500; background: transparent;")
        
        self.lbl_val = QLabel(str(self.count))
        self.lbl_val.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: 700; background: transparent;")
        
        lbl_row.addWidget(self.lbl_name)
        lbl_row.addStretch()
        lbl_row.addWidget(self.lbl_val)
        
        layout.addLayout(lbl_row)
        
        self.bar = QWidget()
        self.bar.setFixedHeight(5)
        self.bar.paintEvent = self.paint_bar
        layout.addWidget(self.bar)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.grow)
        self.timer.start(20)
        
    def grow(self):
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + 0.04)
            self.bar.update()
        else:
            self.timer.stop()
            
    def paint_bar(self, event):
        painter = QPainter(self.bar)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.bar.rect())
        bg_color = QColor(255, 255, 255, 15) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 10)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 2.5, 2.5)
        
        fill_pct = (self.count / self.max_count) * self.progress
        fill_width = rect.width() * fill_pct
        if fill_width > 0:
            fill_rect = QRectF(0, 0, fill_width, rect.height())
            accent = QColor(theme_manager.get_color("accent"))
            
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0, accent)
            grad.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 120))
            
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fill_rect, 2.5, 2.5)
            
    def update_styles(self):
        self.lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: 500; background: transparent;")
        self.lbl_val.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: 700; background: transparent;")
        self.bar.update()

class HorizontalBarChartWidget(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(340)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)
        
        lbl_title = QLabel("DEVICES SCANNED")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent;")
        layout.addWidget(lbl_title)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        # Custom ScrollBar style
        self.scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 40);
                border-radius: 3px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 4, 12, 4)
        self.scroll_layout.setSpacing(12)
        
        device_data = [
            ("USB Flash Drive", 40),
            ("External HDD", 15),
            ("SSD", 12),
            ("USB-C Device", 18),
            ("Keyboard", 8),
            ("Mouse", 7),
            ("HDMI", 4),
            ("Phone", 9)
        ]
        
        device_data.sort(key=lambda x: x[1], reverse=True)
        max_count = max([x[1] for x in device_data])
        
        self.items = []
        for name, count in device_data:
            item = DeviceBarItem(name, count, max_count)
            self.scroll_layout.addWidget(item)
            self.items.append(item)
            
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
    def update_styles(self):
        for item in self.items:
            item.update_styles()

class TimelineItem(QWidget):
    def __init__(self, time_str, device_name, status, parent=None):
        super().__init__(parent)
        self.time_str = time_str
        self.device_name = device_name
        self.status = status
        self.status_color = theme_manager.get_color("accent")
        self.opacity = 0.0
        
        self.setFixedHeight(36)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(36, 0, 12, 0)
        layout.setSpacing(12)
        
        self.lbl_time = QLabel(self.time_str)
        self.lbl_time.setFixedWidth(45)
        self.lbl_time.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: bold; background: transparent;")
        
        self.lbl_device = QLabel(self.device_name)
        self.lbl_device.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: 600; background: transparent;")
        
        self.lbl_status = QLabel(self.status.upper())
        self.lbl_status.setStyleSheet(f"""
            QLabel {{
                color: {self.status_color};
                background: transparent;
                border: none;
                padding: 0px;
                font-family: 'Inter';
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
            }}
        """)
        
        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_device, 1)
        layout.addWidget(self.lbl_status)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.fade_in)
        
    def trigger_animation(self, delay_ms):
        QTimer.singleShot(delay_ms, self.anim_timer.start)
        self.anim_timer.setInterval(20)
        
    def fade_in(self):
        if self.opacity < 1.0:
            self.opacity = min(1.0, self.opacity + 0.05)
            self.update()
        else:
            self.anim_timer.stop()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        line_color = QColor(255, 255, 255, 15) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 10)
        painter.setPen(QPen(line_color, 1.5))
        painter.drawLine(18, 0, 18, self.height())
        
        node_color = QColor(self.status_color)
        node_color.setAlpha(int(255 * self.opacity))
        
        glow = QColor(self.status_color)
        glow.setAlpha(int(45 * self.opacity))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(18 - 6, self.height() // 2 - 6, 12, 12)
        
        painter.setBrush(QBrush(node_color))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawEllipse(18 - 4, self.height() // 2 - 4, 8, 8)
        
    def update_styles(self):
        self.status_color = theme_manager.get_color("accent")
        self.lbl_time.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: bold; background: transparent;")
        self.lbl_device.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: 600; background: transparent;")
        self.lbl_status.setStyleSheet(f"""
            QLabel {{
                color: {self.status_color};
                background: transparent;
                border: none;
                padding: 0px;
                font-family: 'Inter';
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
            }}
        """)
        self.update()

class TimelineWidget(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(230)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(6)
        
        lbl_title = QLabel("RECENT SCAN ACTIVITY")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent;")
        layout.addWidget(lbl_title)
        
        self.items_container = QWidget()
        self.items_container.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(4)
        
        events = []
        
        self.items = []
        for idx, (time_str, name, status) in enumerate(events):
            item = TimelineItem(time_str, name, status)
            self.items_layout.addWidget(item)
            self.items.append(item)
            item.trigger_animation(idx * 150)
            
        layout.addWidget(self.items_container)
        
    def update_styles(self):
        for item in self.items:
            item.update_styles()

class QuickSummaryWidget(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(230)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(10)
        
        lbl_title = QLabel("QUICK ANALYTICS SUMMARY")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent;")
        layout.addWidget(lbl_title)
        
        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(8)
        metrics_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        metrics = [("Most Active Device", "UNAVAILABLE"), ("Highest Risk Device", "UNAVAILABLE"),
                   ("Avg Scan Duration", "UNAVAILABLE"), ("DB Updates", "UNAVAILABLE"),
                   ("Last Audit Time", "UNAVAILABLE")]
        
        self.labels = []
        for label, val in metrics:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            lbl_key = QLabel(label)
            lbl_key.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-weight: 500; background: transparent;")
            
            lbl_val = QLabel(val)
            lbl_val.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 700; background: transparent;")
            
            row_layout.addWidget(lbl_key)
            row_layout.addStretch()
            row_layout.addWidget(lbl_val)
            
            metrics_layout.addLayout(row_layout)
            self.labels.append((lbl_key, lbl_val))
            
            if label != metrics[-1][0]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                line.setStyleSheet(f"background-color: rgba(255, 255, 255, 10); max-height: 1px; border: none;")
                metrics_layout.addWidget(line)
                
        layout.addLayout(metrics_layout)
        
    def update_styles(self):
        for key_lbl, val_lbl in self.labels:
            key_lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-weight: 500; background: transparent;")
            val_lbl.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 700; background: transparent;")

class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout of the page is a ScrollArea for beautiful responsive scrolling (perfect for Pi 7-inch)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.main_scroll.setStyleSheet("background: transparent; border: none;")
        
        # Premium scroll bar
        self.main_scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 50);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 80);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        self.page_content = QWidget()
        self.page_content.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self.page_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        self.main_scroll.setWidget(self.page_content)
        main_layout.addWidget(self.main_scroll)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(4)
        
        lbl_welcome = QLabel("ENDPOINT ACTIVITY LOGS")
        lbl_welcome.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px;")
        self.lbl_status = QLabel("System Incident History")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        
        header_layout.addWidget(lbl_welcome)
        header_layout.addWidget(self.lbl_status)
        layout.addLayout(header_layout)
        
        # ==========================================
        # SCAN ANALYTICS DASHBOARD (TOP SECTION)
        # ==========================================
        
        # 1. Main Interactive Line Graph
        self.analytics_graph = ScanAnalyticsGraph()
        layout.addWidget(self.analytics_graph)
        
        # 2. Six Compact Summary Statistics Cards (Grid of 2 columns, 3 rows for perfect 7-inch screen ratio)
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        
        self.card_total_scans = StatCard("Total Scans", 0, icon_type="total_scans")
        self.card_devices = StatCard("Devices Scanned", 0, icon_type="devices")
        self.card_threats = StatCard("Threats Detected", 0, icon_type="threats")
        self.card_blocked = StatCard("Threats Blocked", 0, icon_type="blocked")
        self.card_avg_risk = StatCard("Average Risk", 0, suffix="%", icon_type="avg_risk")
        self.card_clean_rate = StatCard("Clean Scan Rate", 0, suffix="%", icon_type="clean_rate")
        
        self.stats_grid.addWidget(self.card_total_scans, 0, 0)
        self.stats_grid.addWidget(self.card_devices, 0, 1)
        self.stats_grid.addWidget(self.card_threats, 1, 0)
        self.stats_grid.addWidget(self.card_blocked, 1, 1)
        self.stats_grid.addWidget(self.card_avg_risk, 2, 0)
        self.stats_grid.addWidget(self.card_clean_rate, 2, 1)
        
        layout.addLayout(self.stats_grid)
        
        # 3. Second Analytics Group: Doughnut Distribution & Horizontal Device Bar Chart (Stacked vertically for perfect responsive layout)
        self.doughnut_chart = DoughnutChartWidget()
        self.bar_chart = HorizontalBarChartWidget()
        
        layout.addWidget(self.doughnut_chart)
        layout.addWidget(self.bar_chart)
        
        # 4. Timeline & Quick Summary (Stacked vertically)
        self.timeline = TimelineWidget()
        self.quick_summary = QuickSummaryWidget()
        
        layout.addWidget(self.timeline)
        layout.addWidget(self.quick_summary)
        
        # Label to separate dashboard from pre-existing incident list card
        self.lbl_list_title = QLabel("DETAILED ENDPOINT EVENT LOG")
        self.lbl_list_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px; margin-top: 10px;")
        layout.addWidget(self.lbl_list_title)
        
        # ==========================================
        # EXISTING LOG HISTORY PANEL
        # ==========================================
        self.card = GlassCard()
        self.scroll_layout = QVBoxLayout(self.card)
        self.scroll_layout.setContentsMargins(32, 32, 32, 32)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(self.card)
        
        # Seed initial historic records (Preserved exact initial states!)
        self.add_log_entry({
            "name": "Kingston DataTraveler",
            "category": "USB Flash Drive",
            "vid": "0x0930",
            "pid": "0x6545"
        }, "2026-07-02 22:15:30", "ALLOWED")
        
        self.add_log_entry({
            "name": "Logitech MX Master 3",
            "category": "USB Mouse",
            "vid": "0x046D",
            "pid": "0xC52B"
        }, "2026-07-02 21:04:12", "ALLOWED")
        
        self.add_log_entry({
            "name": "Anomalous Keystroke Payload USB",
            "category": "USB Keyboard",
            "vid": "0x04D9",
            "pid": "0x1702"
        }, "2026-07-02 18:22:45", "BLOCKED")
        
        theme_manager.theme_changed.connect(self.update_styles)

    def update_styles(self):
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        self.lbl_list_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px; margin-top: 10px;")
        
        self.analytics_graph.update()
        self.doughnut_chart.update()
        self.doughnut_chart.chart_paint.update()
        self.bar_chart.update()
        self.bar_chart.update_styles()
        self.timeline.update()
        self.timeline.update_styles()
        self.quick_summary.update()
        self.quick_summary.update_styles()
        
        for i in range(self.stats_grid.count()):
            widget = self.stats_grid.itemAt(i).widget()
            if hasattr(widget, 'update_styles'):
                widget.update_styles()

    def add_log_entry(self, device, timestamp, status):
        widget = HistoryItemWidget(device, timestamp, status)
        self.scroll_layout.insertWidget(0, widget) # New logs at top

    def apply_backend_incidents(self, incidents):
        incidents = incidents or []
        risks = [int(item.get("risk", 0) or 0) for item in incidents]
        verdicts = [str(item.get("verdict", "")).upper() for item in incidents]
        blocked = sum(v in {"BLOCKED", "DANGEROUS", "SUSPICIOUS"} for v in verdicts)
        clean = sum(v in {"CLEAN", "TRUSTED"} for v in verdicts)
        values = {
            self.card_total_scans: len(incidents), self.card_devices: len(incidents),
            self.card_threats: sum(r > 0 for r in risks), self.card_blocked: blocked,
            self.card_avg_risk: round(sum(risks) / len(risks)) if risks else 0,
            self.card_clean_rate: round(clean * 100 / len(incidents)) if incidents else 0,
        }
        for card, value in values.items():
            card.anim_timer.stop(); card.target_val = value; card.current_val = value
            card.lbl_num.setText(f"{card.prefix}{value}{card.suffix}")
