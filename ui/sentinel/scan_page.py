import random
import re
import math
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea, QFrame,
                             QLineEdit, QGraphicsOpacityEffect, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QVariantAnimation, QRectF, QPointF, QUrl
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath, QDesktopServices
from theme import theme_manager
from widgets import GlassCard

# Import new widgets from scan_widgets
from scan_widgets import (CircularProgressRing, AnimatedUSBScanner, GlassActionButton, 
                           InventoryCard, ThreatCard, WarningCard, ScanStatsCard, 
                           LogCard, ActivityCard, SuspiciousFilePopup, LogContainerCard)

SCAN_LOGS = [
    "Initializing hardware port listener...",
    "Querying connected descriptors from system buses...",
    "Parsing raw USB descriptor structures...",
    "Validating vendor ID (VID) and product ID (PID)...",
    "Checking layout and keystroke rates for anomalous HID triggers...",
    "Scanning firmware signature fields against database...",
    "Evaluating driver mismatch logs and power draw patterns...",
    "Electrical integrity status: STABLE (5V, 100mA)",
    "Port scan successfully completed. 0 physical threat threats found.",
]

class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(16) # ~60 fps
        self.setFixedSize(36, 36)
        
    def _rotate(self):
        self.angle = (self.angle + 6) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        pen = QPen(QColor(theme_manager.get_color('glass_border')), 3)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        
        accent = QColor(theme_manager.get_color('accent'))
        pen_active = QPen(accent, 3)
        pen_active.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_active)
        painter.drawArc(rect, -self.angle * 16, 120 * 16)

class ModernEmailIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        accent = QColor(theme_manager.get_color('accent'))
        
        bg_glow = QColor(accent.red(), accent.green(), accent.blue(), 25)
        painter.setBrush(QBrush(bg_glow))
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 50), 1.0))
        painter.drawEllipse(QPointF(cx, cy), 20, 20)
        
        path = QPainterPath()
        x, y, w, h = cx - 13, cy - 9, 26, 18
        path.addRoundedRect(QRectF(x, y, w, h), 2, 2)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(theme_manager.get_color('text_primary')), 2))
        painter.drawPath(path)
        
        flap = QPainterPath()
        flap.moveTo(x, y)
        flap.lineTo(cx, cy + 1)
        flap.lineTo(x + w, y)
        painter.drawPath(flap)

class CheckmarkWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.anim_progress = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(20)
        
    def _animate(self):
        self.anim_progress += 0.08
        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.timer.stop()
        self.update()
        
    def reset(self):
        self.anim_progress = 0.0
        self.timer.start(20)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        accent = QColor(theme_manager.get_color('accent'))
        
        bg_glow = QColor(accent.red(), accent.green(), accent.blue(), 30)
        painter.setBrush(QBrush(bg_glow))
        painter.setPen(QPen(accent, 2))
        painter.drawEllipse(QPointF(cx, cy), 20, 20)
        
        path = QPainterPath()
        start_x, start_y = cx - 9, cy - 1
        mid_x, mid_y = cx - 2, cy + 6
        end_x, end_y = cx + 9, cy - 6
        
        if self.anim_progress < 0.4:
            p = self.anim_progress / 0.4
            path.moveTo(start_x, start_y)
            path.lineTo(start_x + (mid_x - start_x) * p, start_y + (mid_y - start_y) * p)
        else:
            p = (self.anim_progress - 0.4) / 0.6
            path.moveTo(start_x, start_y)
            path.lineTo(mid_x, mid_y)
            path.lineTo(mid_x + (end_x - mid_x) * p, mid_y + (end_y - mid_y) * p)
            
        pen = QPen(QColor(theme_manager.get_color('text_primary')), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

class ErrorWarningWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.pulse = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse)
        self.timer.start(30)
        
    def _pulse(self):
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        crimson = QColor(181, 82, 43)
        glow_val = int(25 + 15 * math.sin(self.pulse))
        bg_glow = QColor(crimson.red(), crimson.green(), crimson.blue(), glow_val)
        
        painter.setBrush(QBrush(bg_glow))
        painter.setPen(QPen(crimson, 2))
        painter.drawEllipse(QPointF(cx, cy), 20, 20)
        
        pen = QPen(QColor(theme_manager.get_color('text_primary')), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 2))
        painter.drawPoint(QPointF(cx, cy + 7))

class EmailExportPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emailExportPopup")
        if parent:
            self.resize(parent.size())
            parent.installEventFilter(self)
            
        self.card_scale = 1.0
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(220)
        
        self.scale_anim = QVariantAnimation(self)
        self.scale_anim.setDuration(260)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.scale_anim.setStartValue(0.95)
        self.scale_anim.setEndValue(1.0)
        self.scale_anim.valueChanged.connect(self._on_scale_anim)
        
        self.card = GlassCard(self)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(24, 24, 24, 24)
        self.card_layout.setSpacing(12)
        
        self.stack = QStackedWidget()
        self.card_layout.addWidget(self.stack)
        
        self.setup_input_view()
        self.setup_loading_view()
        self.setup_success_view()
        self.setup_error_view()
        
        self.setStyleSheet_custom()
        theme_manager.theme_changed.connect(self.update_all_widgets)
        
        self.hide()
        
    def setup_input_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("Export Scan Report")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 16px; font-weight: 800; font-family: 'Inter';")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_subtitle = QLabel("Enter an email address to receive the generated scan report.")
        lbl_subtitle.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter';")
        lbl_subtitle.setWordWrap(True)
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.email_icon = ModernEmailIcon()
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@domain.com")
        self.email_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.lbl_helper = QLabel("The scan report will be sent as a PDF attachment.")
        self.lbl_helper.setStyleSheet(f"color: {theme_manager.get_color('text_muted')}; font-size: 10px; font-family: 'Inter';")
        self.lbl_helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_helper.setWordWrap(True)
        
        h_btn = QHBoxLayout()
        h_btn.setSpacing(12)
        h_btn.setContentsMargins(0, 8, 0, 0)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_send = QPushButton("Send Report")
        
        h_btn.addWidget(self.btn_cancel)
        h_btn.addWidget(self.btn_send)
        
        layout.addWidget(self.email_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)
        layout.addWidget(self.email_input)
        layout.addWidget(self.lbl_helper)
        layout.addLayout(h_btn)
        
        self.btn_cancel.clicked.connect(self.close_popup)
        self.btn_send.clicked.connect(self.validate_and_send)
        self.email_input.returnPressed.connect(self.validate_and_send)
        
        self.stack.addWidget(widget)
        
    def setup_loading_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spinner = LoadingSpinner()
        
        lbl_title = QLabel("Sending Report")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 15px; font-weight: 800; font-family: 'Inter';")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_status = QLabel("Generating PDF document and transmitting via secure protocol...")
        lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter';")
        lbl_status.setWordWrap(True)
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_status)
        layout.addStretch()
        
        self.stack.addWidget(widget)
        
    def setup_success_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.checkmark = CheckmarkWidget()
        
        lbl_title = QLabel("Report Sent Successfully")
        lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 16px; font-weight: 800; font-family: 'Inter';")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_success_msg = QLabel("The scan report has been successfully sent to:\nexample@domain.com")
        self.lbl_success_msg.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter';")
        self.lbl_success_msg.setWordWrap(True)
        self.lbl_success_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_success_done = QPushButton("Done")
        self.btn_success_done.clicked.connect(self.close_popup)
        
        layout.addWidget(self.checkmark, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_success_msg)
        layout.addWidget(self.btn_success_done, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.stack.addWidget(widget)
        
    def setup_error_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.error_icon = ErrorWarningWidget()
        
        lbl_title = QLabel("Failed to Send Report")
        lbl_title.setStyleSheet("color: #B5522B; font-size: 16px; font-weight: 800; font-family: 'Inter';")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_error_msg = QLabel("Unable to send the report. Please try again later.")
        lbl_error_msg.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter';")
        lbl_error_msg.setWordWrap(True)
        lbl_error_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h_btn = QHBoxLayout()
        h_btn.setSpacing(12)
        h_btn.setContentsMargins(0, 4, 0, 0)
        
        self.btn_error_close = QPushButton("Close")
        self.btn_error_retry = QPushButton("Retry")
        
        h_btn.addWidget(self.btn_error_close)
        h_btn.addWidget(self.btn_error_retry)
        
        self.btn_error_close.clicked.connect(self.close_popup)
        self.btn_error_retry.clicked.connect(self.validate_and_send)
        
        layout.addWidget(self.error_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_error_msg)
        layout.addLayout(h_btn)
        
        self.stack.addWidget(widget)
        
    def setStyleSheet_custom(self):
        accent = theme_manager.get_color('accent')
        text_primary = theme_manager.get_color('text_primary')
        text_secondary = theme_manager.get_color('text_secondary')
        text_muted = theme_manager.get_color('text_muted')
        btn_bg = theme_manager.get_color('btn_bg')
        btn_hover = theme_manager.get_color('btn_hover')
        glass_border = theme_manager.get_color('glass_border')
        
        # Email Input Field Style (Glassmorphic)
        bg_input = "rgba(255, 255, 255, 8)" if theme_manager.current_theme == "dark" else "rgba(0, 0, 0, 6)"
        bg_input_focus = "rgba(255, 255, 255, 12)" if theme_manager.current_theme == "dark" else "rgba(0, 0, 0, 10)"
        
        input_style = f"""
            QLineEdit {{
                background-color: {bg_input};
                color: {text_primary};
                border: 1px solid {glass_border};
                border-radius: 8px;
                padding: 10px 14px;
                font-family: 'Inter';
                font-size: 12px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
                background-color: {bg_input_focus};
            }}
        """
        self.email_input.setStyleSheet(input_style)
        
        # Cancel / Secondary Buttons Style (Outline / Glass overlay)
        cancel_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {text_primary};
                border: 1px solid {glass_border};
                border-radius: 18px;
                min-height: 36px;
                max-height: 36px;
                padding: 0px 24px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {accent};
            }}
            QPushButton:pressed {{
                background-color: rgba(217, 127, 74, 0.35);
                padding-top: 2px;
            }}
        """
        self.btn_cancel.setStyleSheet(cancel_style)
        self.btn_success_done.setStyleSheet(cancel_style)
        self.btn_error_close.setStyleSheet(cancel_style)
        
        # Primary / Accent Buttons Style (Rust Solid Gradient)
        send_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 180), stop:1 rgba(181, 82, 43, 140));
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 18px;
                min-height: 36px;
                max-height: 36px;
                padding: 0px 24px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 235), stop:1 rgba(181, 82, 43, 195));
                border: 1px solid {accent};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(181, 82, 43, 230), stop:1 rgba(150, 68, 35, 200));
                padding-top: 2px;
            }}
        """
        self.btn_send.setStyleSheet(send_style)
        self.btn_error_retry.setStyleSheet(send_style)

    def update_all_widgets(self):
        self.setStyleSheet_custom()
        self.update()
        self.email_icon.update()
        self.spinner.update()
        self.checkmark.update()
        self.error_icon.update()
        
    def validate_and_send(self):
        email = self.email_input.text().strip()
        
        pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
        if not re.match(pattern, email):
            self.lbl_helper.setText("Please enter a valid email address.")
            self.lbl_helper.setStyleSheet("color: #B5522B; font-size: 11px; font-weight: bold; font-family: 'Inter';")
            return
            
        self.lbl_helper.setText("The scan report will be sent as a PDF attachment.")
        self.lbl_helper.setStyleSheet(f"color: {theme_manager.get_color('text_muted')}; font-size: 10px; font-family: 'Inter';")
        
        self.stack.setCurrentIndex(1) # loading
        
        # Simulate sending duration
        QTimer.singleShot(1600, lambda: self.finish_sending(email))
        
    def finish_sending(self, email):
        if email.lower() == "error@domain.com":
            self.stack.setCurrentIndex(3) # error view
        else:
            self.lbl_success_msg.setText(f"The scan report has been successfully sent to:\n\n{email}")
            self.stack.setCurrentIndex(2) # success view
            self.checkmark.reset()

    def show_popup(self):
        self.email_input.clear()
        self.lbl_helper.setText("The scan report will be sent as a PDF attachment.")
        self.lbl_helper.setStyleSheet(f"color: {theme_manager.get_color('text_muted')}; font-size: 10px; font-family: 'Inter';")
        self.stack.setCurrentIndex(0) # input view
        
        self.show()
        self.raise_()
        
        self.opacity_effect.setOpacity(0.0)
        
        try:
            self.fade_anim.finished.disconnect()
        except:
            pass
            
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
        
        self.scale_anim.start()
        self.email_input.setFocus()
        
    def close_popup(self):
        try:
            self.fade_anim.finished.disconnect()
        except:
            pass
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

    def _on_scale_anim(self, val):
        self.card_scale = val
        self._reposition()
        
    def _reposition(self):
        if self.parent():
            self.resize(self.parent().size())
            card_width = int(410 * self.card_scale)
            card_height = int(320 * self.card_scale)
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
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

class ScanPage(QWidget):
    scan_completed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(4)
        
        lbl_welcome = QLabel("CYBER RECONNAISSANCE SCANNER")
        lbl_welcome.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px;")
        self.lbl_status = QLabel("Deep Physical Scanning Engine")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        
        header_layout.addWidget(lbl_welcome)
        header_layout.addWidget(self.lbl_status)
        layout.addLayout(header_layout)
        
        # Main Glass Card body layout
        self.card = GlassCard()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        # 1. Current Device Status
        self.lbl_scan_info = QLabel("Initiate deep scan to audit all low-level communication registers on USB endpoints.")
        self.lbl_scan_info.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 13px;")
        self.lbl_scan_info.setWordWrap(True)
        card_layout.addWidget(self.lbl_scan_info)
        
        # Hidden log box to retain 100% backward compatibility with other scripts referencing self.log_box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.hide()
        card_layout.addWidget(self.log_box)
        
        # 2. Large USB Scanning Animation (Unified with progress ring around it)
        self.usb_scanner = AnimatedUSBScanner()
        card_layout.addWidget(self.usb_scanner, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 3. Circular progress bar reference mapped directly to unified scanner to preserve all backward compatibility
        self.progress_bar = self.usb_scanner
        
        # 4. Live Scan Stages (Activity timeline)
        self.activity_card = ActivityCard()
        card_layout.addWidget(self.activity_card)
        
        # 5. File Inventory Card
        self.inventory_card = InventoryCard()
        card_layout.addWidget(self.inventory_card)
        
        # 6. Threat summary / Detection Card
        self.threat_card = ThreatCard()
        card_layout.addWidget(self.threat_card)

        # Verified quarantine evidence from the backend (never simulated).
        self.quarantine_card = GlassCard()
        quarantine_layout = QVBoxLayout(self.quarantine_card)
        quarantine_layout.setContentsMargins(24, 20, 24, 20)
        quarantine_layout.setSpacing(8)
        self.lbl_quarantine_title = QLabel("VERIFIED QUARANTINE")
        self.lbl_quarantine_title.setStyleSheet(
            f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; "
            "font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;"
        )
        self.lbl_quarantine_status = QLabel("No files quarantined in this incident.")
        self.lbl_quarantine_status.setWordWrap(True)
        self.lbl_quarantine_status.setStyleSheet(
            f"color: {theme_manager.get_color('text_secondary')}; font-size: 12px; font-family: 'Inter';"
        )
        self.quarantine_rows_layout = QVBoxLayout()
        self.quarantine_rows_layout.setSpacing(6)
        quarantine_layout.addWidget(self.lbl_quarantine_title)
        quarantine_layout.addWidget(self.lbl_quarantine_status)
        quarantine_layout.addLayout(self.quarantine_rows_layout)
        card_layout.addWidget(self.quarantine_card)
        self.quarantine_rows = []
        self.quarantine_card.hide()

        self.storage_status_card = GlassCard()
        storage_layout = QVBoxLayout(self.storage_status_card)
        storage_layout.setContentsMargins(24, 18, 24, 18)
        title = QLabel("STORAGE SECURITY STATUS")
        title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800;")
        self.lbl_storage_mount = QLabel("Mount: NOT CONNECTED")
        self.lbl_storage_isolation = QLabel("Isolation: UNKNOWN")
        self.lbl_storage_coverage = QLabel("Coverage: not available")
        self.lbl_storage_engines = QLabel("Engines: not available")
        self.lbl_storage_verdict = QLabel("Verdict: pending")
        self.lbl_storage_quarantine = QLabel("Quarantine: none")
        for label in (self.lbl_storage_mount, self.lbl_storage_isolation, self.lbl_storage_coverage,
                      self.lbl_storage_engines, self.lbl_storage_verdict, self.lbl_storage_quarantine):
            label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 12px;")
            storage_layout.addWidget(label)
        storage_layout.insertWidget(0, title)
        card_layout.addWidget(self.storage_status_card)
        
        # Dynamic Warning Banners Area
        self.warnings_container = QWidget()
        self.warnings_container.setStyleSheet("background: transparent;")
        self.warnings_layout = QVBoxLayout(self.warnings_container)
        self.warnings_layout.setContentsMargins(0, 0, 0, 0)
        self.warnings_layout.setSpacing(8)
        card_layout.addWidget(self.warnings_container)
        
        # 7. Risk Score Card / Estimated Scan Stats (Elapsed, Remaining, Speed, Threats)
        self.stats_card = ScanStatsCard()
        card_layout.addWidget(self.stats_card)
        
        # 9. Device Activity Logs scroll container
        self.log_container = LogContainerCard()
        self.logs_scroll = self.log_container.logs_scroll
        self.logs_layout = self.log_container.logs_layout
        self.log_container.setMinimumHeight(240)
        card_layout.addWidget(self.log_container)
        
        # 10. Post Scan Actions / Launch button
        self.btn_scan = QPushButton("LAUNCH SYSTEM AUDIT")
        self.btn_scan.setText("WAITING FOR PHYSICAL USB DEVICE")
        self.btn_scan.setEnabled(False)
        card_layout.addWidget(self.btn_scan, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Post Scan Actions container (Export, Quarantine, Scan again)
        self.post_scan_widget = QWidget()
        post_scan_layout = QHBoxLayout(self.post_scan_widget)
        post_scan_layout.setContentsMargins(0, 0, 0, 0)
        post_scan_layout.setSpacing(12)
        
        self.btn_export = GlassActionButton("EXPORT REPORT", "document")
        self.btn_quarantine = GlassActionButton("QUARANTINE FILES", "shield")
        self.btn_again = GlassActionButton("SCAN AGAIN", "refresh")
        self.btn_again.setEnabled(False)
        
        post_scan_layout.addWidget(self.btn_export)
        post_scan_layout.addWidget(self.btn_quarantine)
        post_scan_layout.addWidget(self.btn_again)
        card_layout.addWidget(self.post_scan_widget)
        self.post_scan_widget.hide()
        
        # Wrap the GlassCard inside a premium transparent QScrollArea to ensure a smooth, unified page scroll flow
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 60);
                min-height: 30px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 90);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        self.scroll_area.setWidget(self.card)
        layout.addWidget(self.scroll_area, 1)
        
        # Floating Suspicious File Popup (Absolute position over this widget)
        self.popup = SuspiciousFilePopup(self)
        
        # Floating Email Export Popup
        self.email_popup = EmailExportPopup(self)
        # Reports and configured email delivery are generated by the backend.
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.open_latest_report)
        self.btn_quarantine.setEnabled(False)
        self.latest_pdf_path = ""
        self.latest_json_path = ""
        
        # Scan Timers setup
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.advance_scan)
        self.scan_progress = 0
        self.log_idx = 0
        
        # Seconds tracker for elapsed & remaining
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats_timer)
        self.elapsed_seconds = 0
        self.threat_count = 0
        
        # Trigger flags to avoid duplicate pops
        self._trigger_double_ext = False
        self._trigger_hidden = False
        self._trigger_autorun = False
        self._trigger_malware = False
        
        theme_manager.theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        accent = theme_manager.get_color('accent')
        text_primary = theme_manager.get_color('text_primary')
        
        # Main Launch Audit Button Style
        btn_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 180), stop:1 rgba(181, 82, 43, 140));
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 20px;
                min-height: 40px;
                max-height: 40px;
                padding: 0px 32px;
                font-family: 'Inter';
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 1.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 235), stop:1 rgba(181, 82, 43, 195));
                border: 1px solid rgba(217, 127, 74, 255);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(181, 82, 43, 230), stop:1 rgba(150, 68, 35, 200));
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: rgba(128, 128, 128, 30);
                color: rgba(255, 255, 255, 60);
                border: 1px solid rgba(255, 255, 255, 10);
            }}
        """
        self.btn_scan.setStyleSheet(btn_style)
        
        # Update custom action buttons
        self.btn_export.update()
        self.btn_quarantine.update()
        self.btn_again.update()
        
        # Update logs container theme styling
        self.log_container.update_styles()

    def begin_backend_scan(self, device):
        self.scan_timer.stop()
        self.stats_timer.stop()
        self.scan_progress = 0
        self.threat_count = 0
        self.clear_logs_and_warnings()
        self.activity_card.reset()
        self.inventory_card.reset_live()
        self.clear_quarantine_evidence()
        self.progress_bar.setValue(0)
        self.progress_bar.set_draw_check(False)
        self.progress_bar.set_blue_glow(False)
        self.usb_scanner.set_scanning(True)
        self.lbl_status.setText("Live backend analysis")
        self.lbl_scan_info.setText(
            f"{device.get('name', 'USB device')} is isolated while YARA, ClamAV, fingerprint and policy checks run."
        )
        self.btn_scan.setText("BACKEND SCAN IN PROGRESS")
        self.add_log_card("Physical device event received from security service")
        self.post_scan_widget.hide()

    def apply_backend_progress(self, data):
        progress = int(data.get("progress", data.get("percent", 0)) or 0)
        progress = max(0, min(100, progress))
        self.scan_progress = progress
        self.progress_bar.setValue(progress)
        message = data.get("message") or data.get("stage") or f"Analysis progress: {progress}%"
        self.lbl_scan_info.setText(str(message))
        self.add_log_card(str(message))
        self.update_backend_timeline(progress)

    def update_backend_timeline(self, progress):
        """Animate real stages without invoking the supplied fake findings."""
        active = min(6, max(0, int(progress / 15)))
        for index in range(7):
            if index < active:
                self.activity_card.set_stage_status(index, "completed")
            elif index == active and progress < 100:
                self.activity_card.set_stage_status(index, "scanning")

    def apply_backend_scan_complete(self, data):
        self.scan_timer.stop(); self.stats_timer.stop()
        self.usb_scanner.set_scanning(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Security scan complete")
        threats = int(data.get("threats", 0) or 0)
        files = int(data.get("files", 0) or 0)
        self.threat_count = threats
        self.stats_card.set_threats(threats)
        self.inventory_card.update_inventory(data.get("inventory", {}))
        self.lbl_scan_info.setText(
            f"Scanned {files} files; {threats} threats. Consolidating PDF and JSON evidence…"
        )
        self.add_log_card("Security engines completed; report consolidation is running")
        for index in range(7):
            self.activity_card.set_stage_status(index, "completed")

    def apply_backend_state(self, state, detail=""):
        label = str(state or "UNKNOWN").replace("_", " ").title()
        self.lbl_status.setText(label)
        if detail:
            self.lbl_scan_info.setText(str(detail))
            self.add_log_card(f"{label}: {detail}")
        if str(state).upper() in {"DISCONNECTED", "REMOVED", "DEVICE REMOVED DURING ANALYSIS"}:
            self.scan_timer.stop(); self.stats_timer.stop()
            self.usb_scanner.set_scanning(False)

    def apply_backend_engines(self, data):
        """Display authoritative engine/isolation readiness from the backend."""
        engines = ", ".join(
            f"{name.upper()}: {'READY' if bool(data.get(name)) else 'UNAVAILABLE'}"
            for name in ("yara", "clamav", "usbguard") if name in data
        )
        if engines:
            self.lbl_storage_engines.setText(f"Engines: {engines}")
            self.add_log_card(f"Backend readiness — {engines}")

    def apply_backend_storage_status(self, data):
        coverage = data.get("scan_coverage") or {}
        mount = data.get("mount_path") or data.get("mount")
        if mount:
            self.lbl_storage_mount.setText(f"Mount: {mount}")
        self.lbl_storage_isolation.setText(
            "Isolation: " + ("VERIFIED" if data.get("isolation_verified") else "BLOCKED/UNKNOWN")
        )
        if coverage:
            self.lbl_storage_coverage.setText(
                f"Coverage: {coverage.get('fully_scanned_files', coverage.get('scanned_files', 0))}/"
                f"{coverage.get('total_files', 0)} files"
            )
        if data.get("verdict"):
            self.lbl_storage_verdict.setText(f"Verdict: {data['verdict']}")
        quarantine = data.get("quarantine_paths") or data.get("quarantine") or []
        self.lbl_storage_quarantine.setText(f"Quarantine: {len(quarantine)} item(s)")

    def apply_backend_finding(self, data):
        severity = str(data.get("severity", "INFO")).upper()
        finding = str(data.get("finding") or data.get("message") or "Security finding")
        path = str(data.get("path") or "")
        self.threat_count += 1 if severity in {"MEDIUM", "HIGH", "CRITICAL", "DANGEROUS"} else 0
        self.stats_card.set_threats(self.threat_count)
        self.add_log_card(f"[{severity}] {finding}{': ' + path if path else ''}")
        if severity in {"MEDIUM", "HIGH", "CRITICAL", "DANGEROUS"}:
            self.add_warning(finding, path or "Reported by backend security engine", severity)
            score = max(int(data.get("risk", 0) or 0), self.threat_count * 10)
            self.threat_card.update_threat_report(
                min(100, score), "HIGH" if severity in {"HIGH", "CRITICAL", "DANGEROUS"} else "MEDIUM",
                "Threat detected by the backend. Awaiting quarantine/block decision.",
                finding, path,
            )

    def apply_backend_risk(self, data):
        score = int(data.get("total", data.get("score", 0)) or 0)
        level = (
            "HIGH" if score >= 60 else
            "MEDIUM" if data.get("remediated") or score >= 25 else "SAFE"
        )
        original = data.get("original") or data.get("original_risk") or data
        final = data.get("final") or data
        categories = ("hardware", "trust", "interface", "behavior", "storage", "nvd", "malware")
        breakdown = ", ".join(f"{key.title()} {original.get(key, 0)}" for key in categories)
        remediation = " Quarantine verified; post-remediation score: " + str(data.get("final_total", 0)) + "." if data.get("remediated") else ""
        self.threat_card.update_threat_report(
            score, level, f"Original evidence: {breakdown}.{remediation}"
        )

    def clear_quarantine_evidence(self):
        for row in self.quarantine_rows:
            self.quarantine_rows_layout.removeWidget(row)
            row.deleteLater()
        self.quarantine_rows.clear()
        self.quarantine_card.hide()

    def apply_quarantine_event(self, entry):
        self.quarantine_card.show()
        sha = str(entry.get("sha256") or "")
        original = str(entry.get("original_path") or "Unknown source")
        vault = str(entry.get("quarantine_path") or "Unknown vault path")
        verified = bool(
            entry.get("verified") and entry.get("hash_verified")
            and entry.get("source_removed") and entry.get("execute_disabled")
            and sha and vault
        )
        self.lbl_quarantine_status.setText(
            "VERIFIED: backend copied the file, compared SHA-256, removed the source, and disabled execution."
            if verified else "INCOMPLETE: quarantine integrity evidence is missing. Device remains blocked."
        )
        row = QLabel(
            f"{entry.get('original_name', 'Threat file')}\nOriginal: {original}\nVault: {vault}\n"
            f"SHA-256: {sha or 'missing'}\nIntegrity: {'VERIFIED' if verified else 'INCOMPLETE'}\n"
            f"Reason: {entry.get('reason', 'Security-engine detection')}"
        )
        row.setWordWrap(True)
        row.setStyleSheet(
            f"color: {theme_manager.get_color('text_primary')}; background: rgba(181,82,43,15); "
            "border: none; border-radius: 8px; padding: 10px; font-family: 'JetBrains Mono'; font-size: 10px;"
        )
        self.quarantine_rows_layout.addWidget(row)
        self.quarantine_rows.append(row)

    def apply_report_quarantine(self, data):
        device = data.get("device") if isinstance(data.get("device"), dict) else {}
        records = device.get("quarantine_records") or []
        if records and not self.quarantine_rows:
            for record in records:
                self.apply_quarantine_event(record)

    def complete_backend_scan(self, data):
        self.scan_timer.stop(); self.stats_timer.stop()
        self.usb_scanner.set_scanning(False)
        self.progress_bar.setValue(100)
        self.progress_bar.set_blue_glow(True)
        self.progress_bar.set_draw_check(True)
        verdict = str(data.get("verdict", "COMPLETE"))
        self.lbl_status.setText(f"Analysis complete — {verdict}")
        paths = [p for p in (data.get("pdf_path"), data.get("json_path")) if p]
        self.latest_pdf_path = str(data.get("pdf_path") or "")
        self.latest_json_path = str(data.get("json_path") or "")
        self.lbl_scan_info.setText("Report ready" + (": " + " | ".join(paths) if paths else "."))
        self.btn_scan.setText("WAITING FOR NEXT PHYSICAL USB DEVICE")
        self.btn_scan.show()
        self.post_scan_widget.show()
        self.btn_export.setText("OPEN PDF REPORT")
        self.btn_export.setEnabled(bool(self.latest_pdf_path))
        self.btn_quarantine.hide()
        self.btn_again.hide()

    def open_latest_report(self):
        path = self.latest_pdf_path or self.latest_json_path
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.lbl_scan_info.setText(
                f"Report file is unavailable at: {path or 'no report path received'}"
            )

    def start_scan(self):
        self.log_box.clear()
        self.scan_progress = 0
        self.log_idx = 0
        self.progress_bar.setValue(0)
        self.lbl_scan_info.setText("Audit running. Processing deep peripheral verification metrics...")
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("SCANNING IN PROGRESS...")
        
        # Reset tracker metrics
        self.threat_count = 0
        self.elapsed_seconds = 0
        self._trigger_double_ext = False
        self._trigger_hidden = False
        self._trigger_autorun = False
        self._trigger_malware = False
        
        self.clear_logs_and_warnings()
        self.activity_card.reset()
        self.threat_card.update_threat_report(0, "SAFE", "No anomalies detected. Device signature matches trusted definitions.")
        
        self.btn_scan.show()
        self.post_scan_widget.hide()
        
        # Visual resets
        self.usb_scanner.set_scanning(True)
        self.inventory_card.start_animation(4000)
        self.progress_bar.set_blue_glow(False)
        self.progress_bar.set_draw_check(False)
        self.lbl_status.setText("Deep Physical Scanning Engine")
        
        # Progress and completion are authoritative backend events. Do not
        # advance a synthetic local scan while the service is working.
        self.scan_timer.stop()
        self.stats_timer.stop()

    def advance_scan(self):
        return
        if self.scan_progress >= 100:
            self.scan_progress = 100
            self.progress_bar.setValue(100)
            
            # Stop basic scan timers
            self.scan_timer.stop()
            self.stats_timer.stop()
            
            # Stop scan scanner loop
            self.usb_scanner.set_scanning(False)
            
            # 16. Scan Completion Animation Phase
            self.progress_bar.set_blue_glow(True)
            self.lbl_scan_info.setText("Completing post-processing integrity verification...")
            
            # Write remainder of base logs
            while self.log_idx < len(SCAN_LOGS):
                msg = f"[{self.scan_progress}%] {SCAN_LOGS[self.log_idx]}"
                self.log_box.append(msg)
                self.add_log_card(SCAN_LOGS[self.log_idx])
                self.log_idx += 1
                
            # Play a timed delay transition checkmark (800ms)
            QTimer.singleShot(900, self.finish_scan_animation)
            return
            
        self.progress_bar.setValue(self.scan_progress)
        self.update_timeline_and_alerts(self.scan_progress)
        
        # Output logs proportionally
        expected_log_idx = int((self.scan_progress / 100.0) * len(SCAN_LOGS))
        while self.log_idx <= expected_log_idx and self.log_idx < len(SCAN_LOGS):
            msg = f"[{self.scan_progress}%] {SCAN_LOGS[self.log_idx]}"
            self.log_box.append(msg)
            self.add_log_card(SCAN_LOGS[self.log_idx])
            self.log_idx += 1

    def update_timeline_and_alerts(self, progress):
        # Update stage highlights based on progress boundaries
        if progress < 15:
            self.activity_card.set_stage_status(0, 'scanning')
        elif progress < 30:
            self.activity_card.set_stage_status(0, 'completed')
            self.activity_card.set_stage_status(1, 'scanning')
        elif progress < 45:
            self.activity_card.set_stage_status(1, 'completed')
            self.activity_card.set_stage_status(2, 'scanning')
            
            # 12. Double Extension Warning at ~32%
            if not self._trigger_double_ext:
                self._trigger_double_ext = True
                self.add_warning("Double Extension Detected", "invoice.pdf.exe masquerading as document.", "MEDIUM")
                self.popup_suspicious("invoice.pdf.exe", "E:\\invoice.pdf.exe", "Double extension detected (pdf.exe). High likelihood of masquerading malware.")
                self.threat_count += 1
                self.stats_card.set_threats(self.threat_count)
                
        elif progress < 60:
            self.activity_card.set_stage_status(2, 'completed')
            self.activity_card.set_stage_status(3, 'scanning')
            
            # 11. Hidden File Detection Warning at ~48%
            if not self._trigger_hidden:
                self._trigger_hidden = True
                self.add_warning("Hidden File Detected", "Risk Increased due to hidden system binary .hidden.exe.", "MEDIUM")
                self.threat_count += 1
                self.stats_card.set_threats(self.threat_count)
                
        elif progress < 75:
            self.activity_card.set_stage_status(3, 'completed')
            self.activity_card.set_stage_status(4, 'scanning')
            
            # 13. Autorun Execution Warning at ~64%
            if not self._trigger_autorun:
                self._trigger_autorun = True
                self.add_warning("Potential Auto-Execution Detected", "autorun.inf detected pointing to untrusted payload.", "HIGH")
                self.threat_count += 1
                self.stats_card.set_threats(self.threat_count)
                
        elif progress < 90:
            self.activity_card.set_stage_status(4, 'completed')
            self.activity_card.set_stage_status(5, 'scanning')
            
            # 15. Malware Detection at ~80%
            if not self._trigger_malware:
                self._trigger_malware = True
                self.threat_count += 1
                self.stats_card.set_threats(self.threat_count)
                self.threat_card.update_threat_report(
                    68, "HIGH", 
                    "Severe risk. Active malicious signature trace found. Quarantine recommended.",
                    "Trojan.Generic", "E:\\Downloads\\setup.exe"
                )
                
        elif progress < 100:
            self.activity_card.set_stage_status(5, 'completed')
            self.activity_card.set_stage_status(6, 'scanning')

    def finish_scan_animation(self):
        # Trigger completed look
        self.progress_bar.set_draw_check(True)
        self.lbl_status.setText("Scan Complete")
        self.lbl_scan_info.setText("Reconnaissance scan finalized. Host endpoints audit complete.")
        
        # Complete all activity items
        for idx in range(7):
            self.activity_card.set_stage_status(idx, 'completed')
            
        # Swap main buttons
        self.btn_scan.hide()
        self.post_scan_widget.show()
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("LAUNCH SYSTEM AUDIT")
        
        # Emit scan completed details with accurate counters
        self.scan_completed.emit({
            "date": "Today",
            "files": 1250,
            "threats": self.threat_count,
            "duration": f"{self.elapsed_seconds} sec"
        })

    def update_stats_timer(self):
        if self.scan_progress > 0 and self.scan_progress < 100:
            self.elapsed_seconds += 1
            rate = self.scan_progress / self.elapsed_seconds if self.elapsed_seconds > 0 else 0.1
            remaining = int((100 - self.scan_progress) / rate) if rate > 0 else 8
            self.stats_card.update_stats(self.elapsed_seconds, remaining, 0)

    def add_log_card(self, message):
        card = LogCard(message)
        # Add before the layout spacer
        self.logs_layout.insertWidget(self.logs_layout.count() - 1, card)
        QTimer.singleShot(40, lambda: self.logs_scroll.verticalScrollBar().setValue(
            self.logs_scroll.verticalScrollBar().maximum()
        ))

    def add_warning(self, title, description, level):
        card = WarningCard(title, description, level)
        self.warnings_layout.addWidget(card)

    def popup_suspicious(self, name, path, reason):
        self.popup.show_popup(name, path, reason)

    def clear_logs_and_warnings(self):
        # Clear log list
        for i in reversed(range(self.logs_layout.count())):
            item = self.logs_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        # Clear warning banner cards
        for i in reversed(range(self.warnings_layout.count())):
            item = self.warnings_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        self.stats_card.set_threats(0)
        self.stats_card.update_stats(0, 0, 0)
