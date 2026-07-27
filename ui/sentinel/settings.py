from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QButtonGroup, QScrollArea
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QUrl, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QDesktopServices
from theme import theme_manager
from widgets import GlassCard, StatusBadge

class VectorIcon(QWidget):
    def __init__(self, icon_type, parent=None, size=24, color_key="text_secondary"):
        super().__init__(parent)
        self.icon_type = icon_type
        self.size = size
        self.color_key = color_key
        self.rotation_angle = 0
        self.setFixedSize(size, size)
        theme_manager.theme_changed.connect(self.update)
        
    def set_rotation(self, angle):
        self.rotation_angle = angle
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(theme_manager.get_color(self.color_key))
        pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        
        if self.rotation_angle != 0:
            painter.translate(cx, cy)
            painter.rotate(self.rotation_angle)
            painter.translate(-cx, -cy)
            
        if self.icon_type in ["device_sandisk", "device_kingston", "device_flash"]:
            painter.drawRoundedRect(QRectF(cx - 5, cy - 8, 10, 16), 2, 2)
            painter.drawRect(QRectF(cx - 3, cy - 12, 6, 4))
            painter.drawEllipse(QPointF(cx, cy + 4), 1.5, 1.5)
        elif self.icon_type == "device_ssd":
            painter.drawRoundedRect(QRectF(cx - 7, cy - 10, 14, 20), 2, 2)
            painter.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy - 4))
            painter.drawLine(QPointF(cx - 4, cy + 4), QPointF(cx + 4, cy + 4))
        elif self.icon_type == "device_keyboard":
            painter.drawRoundedRect(QRectF(cx - 10, cy - 6, 20, 12), 2, 2)
            painter.drawLine(QPointF(cx - 7, cy - 3), QPointF(cx + 7, cy - 3))
            painter.drawLine(QPointF(cx - 3, cy + 2), QPointF(cx + 3, cy + 2))
        elif self.icon_type == "bell":
            path = QPainterPath()
            path.moveTo(cx - 7, cy + 4)
            path.lineTo(cx + 7, cy + 4)
            path.quadTo(cx + 5, cy - 5, cx, cy - 7)
            path.quadTo(cx - 5, cy - 5, cx - 7, cy + 4)
            painter.drawPath(path)
            painter.drawEllipse(QPointF(cx, cy + 6), 1.5, 1.5)
        elif self.icon_type == "shield":
            path = QPainterPath()
            path.moveTo(cx, cy - 9)
            path.lineTo(cx + 7, cy - 9)
            path.lineTo(cx + 7, cy - 2)
            path.quadTo(cx + 7, cy + 5, cx, cy + 9)
            path.quadTo(cx - 7, cy + 5, cx - 7, cy - 2)
            path.lineTo(cx - 7, cy - 9)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.icon_type == "usb_connection":
            painter.drawEllipse(QPointF(cx, cy + 5), 2, 2)
            painter.drawLine(QPointF(cx, cy + 3), QPointF(cx, cy - 5))
            painter.drawLine(QPointF(cx, cy + 1), QPointF(cx - 4, cy - 2))
            painter.drawLine(QPointF(cx, cy + 1), QPointF(cx + 4, cy - 2))
        elif self.icon_type == "scan_complete":
            painter.drawEllipse(QPointF(cx, cy), 8, 8)
            painter.drawLine(QPointF(cx - 3, cy), QPointF(cx - 1, cy + 2))
            painter.drawLine(QPointF(cx - 1, cy + 2), QPointF(cx + 4, cy - 3))
        elif self.icon_type == "wifi":
            painter.drawEllipse(QPointF(cx, cy + 6), 1.5, 1.5)
            painter.drawArc(QRectF(cx - 4, cy + 2, 8, 8), 45 * 16, 90 * 16)
            painter.drawArc(QRectF(cx - 8, cy - 2, 16, 16), 45 * 16, 90 * 16)
        elif self.icon_type == "globe":
            painter.drawEllipse(QPointF(cx, cy), 8, 8)
            painter.drawLine(QPointF(cx - 8, cy), QPointF(cx + 8, cy))
            painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 8))
        elif self.icon_type == "ethernet":
            painter.drawRoundedRect(QRectF(cx - 8, cy - 5, 16, 10), 1.5, 1.5)
            painter.drawLine(QPointF(cx, cy + 5), QPointF(cx, cy + 7))
            painter.drawLine(QPointF(cx - 4, cy + 7), QPointF(cx + 4, cy + 7))
        elif self.icon_type == "os":
            painter.drawEllipse(QPointF(cx, cy - 4), 2.5, 2.5)
            painter.drawEllipse(QPointF(cx - 3, cy + 1), 3, 3)
            painter.drawEllipse(QPointF(cx + 3, cy + 1), 3, 3)
            painter.drawEllipse(QPointF(cx, cy + 5), 3, 3)
        elif self.icon_type == "cpu":
            painter.drawRect(QRectF(cx - 6, cy - 6, 12, 12))
            painter.drawRect(QRectF(cx - 3, cy - 3, 6, 6))
            for offset in [-3, 3]:
                painter.drawLine(QPointF(cx + offset, cy - 8), QPointF(cx + offset, cy - 6))
                painter.drawLine(QPointF(cx + offset, cy + 6), QPointF(cx + offset, cy + 8))
        elif self.icon_type == "temp":
            painter.drawEllipse(QPointF(cx, cy + 5), 3, 3)
            painter.drawRoundedRect(QRectF(cx - 1.5, cy - 7, 3, 10), 1.5, 1.5)
        elif self.icon_type == "ram":
            painter.drawRect(QRectF(cx - 9, cy - 4, 18, 8))
            for i in range(4):
                painter.drawLine(QPointF(cx - 6 + i * 4, cy + 4), QPointF(cx - 6 + i * 4, cy + 6))
        elif self.icon_type == "storage":
            painter.drawEllipse(QRectF(cx - 7, cy - 6, 14, 4))
            painter.drawEllipse(QRectF(cx - 7, cy - 1, 14, 4))
            painter.drawEllipse(QRectF(cx - 7, cy + 4, 14, 4))
            painter.drawLine(QPointF(cx - 7, cy - 4), QPointF(cx - 7, cy + 6))
            painter.drawLine(QPointF(cx + 7, cy - 4), QPointF(cx + 7, cy + 6))
        elif self.icon_type == "developer":
            painter.drawEllipse(QPointF(cx, cy - 3), 3.5, 3.5)
            painter.drawArc(QRectF(cx - 6, cy + 1, 12, 8), 0, 180 * 16)
        elif self.icon_type == "python":
            painter.drawText(QRectF(cx - 12, cy - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, "</>")
        elif self.icon_type == "refresh":
            painter.drawArc(QRectF(cx - 7, cy - 7, 14, 14), 45 * 16, 270 * 16)
            painter.drawLine(QPointF(cx + 5, cy - 3), QPointF(cx + 5, cy - 7))
            painter.drawLine(QPointF(cx + 5, cy - 7), QPointF(cx + 1, cy - 7))
        elif self.icon_type == "arrow_right":
            painter.drawLine(QPointF(cx - 2, cy - 4), QPointF(cx + 2, cy))
            painter.drawLine(QPointF(cx + 2, cy), QPointF(cx - 2, cy + 4))

class ToggleRow(QFrame):
    def __init__(self, title, description, icon_type=None, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedHeight(64)
        self._is_hovered = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        
        if icon_type:
            self.icon = VectorIcon(icon_type, size=24, color_key="text_secondary")
            layout.addWidget(self.icon)
            
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_desc = QLabel(description)
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_desc)
        
        self.btn_toggle = QPushButton("ENABLED")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(90, 32)
        self.btn_toggle.clicked.connect(self.on_clicked)
        
        layout.addLayout(text_layout, 1)
        layout.addWidget(self.btn_toggle)
        
        self.update_style(hovered=False)
        theme_manager.theme_changed.connect(lambda: self.update_style(hovered=self._is_hovered))

    def on_clicked(self):
        self.btn_toggle.setText("ENABLED" if self.btn_toggle.isChecked() else "DISABLED")
        self.update_style(hovered=self._is_hovered)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update_style(hovered=True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._is_hovered = False
        self.update_style(hovered=False)
        super().leaveEvent(event)

    def update_style(self, hovered=False):
        accent = theme_manager.get_color("accent")
        text_pri = theme_manager.get_color("text_primary")
        text_sec = theme_manager.get_color("text_secondary")
        border = accent if hovered else theme_manager.get_color("glass_border")
        
        if hovered:
            bg = "rgba(217, 127, 74, 20)" if theme_manager.current_theme == "dark" else "rgba(217, 127, 74, 12)"
            if self.icon_type:
                self.icon.color_key = "accent"
        else:
            bg = "rgba(255, 255, 255, 6)" if theme_manager.current_theme == "dark" else "rgba(15, 23, 42, 6)"
            if self.icon_type:
                self.icon.color_key = "text_secondary"
                
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border: 0.5px solid {border}; border-radius: 12px; }}")
        self.lbl_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self.lbl_desc.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 11px; background: transparent; border: none;")
        if self.icon_type:
            self.icon.update()
            
        if self.btn_toggle.isChecked():
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 180), stop:1 rgba(181, 82, 43, 140));
                    color: #ffffff;
                    border-radius: 16px;
                    font-family: 'Inter';
                    font-weight: 800;
                    font-size: 10px;
                    border: 1px solid rgba(255, 255, 255, 25);
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217, 127, 74, 235), stop:1 rgba(181, 82, 43, 195));
                    border: 1px solid rgba(217, 127, 74, 255);
                }}
            """)
        else:
            self.btn_toggle.setStyleSheet(f"QPushButton {{ background: rgba(255, 255, 255, 10); color: {text_sec}; border-radius: 16px; font-family: 'Inter'; font-weight: 800; font-size: 10px; border: 1px solid {theme_manager.get_color('glass_border')}; }} QPushButton:hover {{ background: rgba(255, 255, 255, 20); border: 1px solid rgba(255, 255, 255, 40); }}")

class InfoRow(QFrame):
    def __init__(self, icon_type, label, value=None, show_status_dot=False, show_arrow=False, is_trusted=False, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.show_status_dot = show_status_dot
        self.show_arrow = show_arrow
        self.is_trusted = is_trusted
        self.setFixedHeight(54 if is_trusted else 46)
        self._is_hovered = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(12)
        
        self.icon = VectorIcon(icon_type, size=22 if is_trusted else 18, color_key="text_secondary")
        layout.addWidget(self.icon)
        
        self.lbl_label = QLabel(label)
        layout.addWidget(self.lbl_label)
        
        layout.addStretch(1)
        
        if show_status_dot:
            self.dot = QWidget()
            self.dot.setFixedSize(6, 6)
            self.dot.setStyleSheet("background-color: #D97F4A; border-radius: 3px; border: none;")
            layout.addWidget(self.dot)
            
        if is_trusted:
            self.badge = StatusBadge("TRUSTED", theme_manager.get_color("accent"))
            layout.addWidget(self.badge)
            
        if value is not None:
            self.lbl_val = QLabel(value)
            layout.addWidget(self.lbl_val)
            
        if show_arrow:
            self.arrow = VectorIcon("arrow_right", size=16, color_key="accent")
            layout.addWidget(self.arrow)
            
        self.update_style(hovered=False)
        theme_manager.theme_changed.connect(lambda: self.update_style(hovered=self._is_hovered))

    def add_action_button(self, label, callback):
        button = QPushButton(label)
        button.setFixedHeight(28)
        button.clicked.connect(callback)
        self.layout().addWidget(button)
        return button
        
    def enterEvent(self, event):
        self._is_hovered = True
        self.update_style(hovered=True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._is_hovered = False
        self.update_style(hovered=False)
        super().leaveEvent(event)

    def update_style(self, hovered=False):
        accent = theme_manager.get_color("accent")
        text_pri = theme_manager.get_color("text_primary")
        text_sec = theme_manager.get_color("text_secondary")
        border = accent if hovered else theme_manager.get_color("glass_border")
        
        if hovered:
            bg = "rgba(217, 127, 74, 20)" if theme_manager.current_theme == "dark" else "rgba(217, 127, 74, 12)"
            self.icon.color_key = "accent"
        else:
            bg = "rgba(255, 255, 255, 4)" if theme_manager.current_theme == "dark" else "rgba(15, 23, 42, 4)"
            self.icon.color_key = "text_secondary"
            
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border: 0.5px solid {border}; border-radius: 10px; }}")
        self.lbl_label.setStyleSheet(f"color: {text_pri if self.is_trusted else text_sec}; font-family: 'Inter'; font-size: 12px; font-weight: {700 if self.is_trusted else 500}; background: transparent; border: none;")
        
        if hasattr(self, 'lbl_val'):
            val_color = accent if self.show_status_dot else text_pri
            self.lbl_val.setStyleSheet(f"color: {val_color}; font-family: 'Inter'; font-size: 12px; font-weight: 700; background: transparent; border: none;")
            
        if hasattr(self, 'badge'):
            self.badge.update_badge("TRUSTED", accent)
            
        if hasattr(self, 'arrow'):
            self.arrow.color_key = "accent" if hovered else "text_secondary"
            self.arrow.update()
            
        self.icon.update()

class SettingsPage(QWidget):
    recover_hid_requested = pyqtSignal()
    quarantine_restore_requested = pyqtSignal(int)
    quarantine_delete_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background: rgba(128, 128, 128, 50); min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: rgba(128, 128, 128, 80); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(16)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(4)
        
        lbl_welcome = QLabel("SYSTEM SYSTEM PREFERENCES")
        lbl_welcome.setObjectName("lbl_welcome")
        lbl_welcome.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px;")
        
        self.lbl_status = QLabel("Security settings")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        
        header_layout.addWidget(lbl_welcome)
        header_layout.addWidget(self.lbl_status)
        scroll_layout.addLayout(header_layout)
        
        # 1. Main Security Settings Card (Original settings)
        self.card = GlassCard()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(12)
        
        # Theme Setting
        self.theme_row = QFrame()
        self.theme_row.setFixedHeight(64)
        theme_layout = QHBoxLayout(self.theme_row)
        theme_layout.setContentsMargins(14, 8, 14, 8)
        
        self.lbl_t_title = QLabel("System Style Theme")
        self.lbl_t_desc = QLabel("Set preferred interface style.")
        
        t_text_layout = QVBoxLayout()
        t_text_layout.setSpacing(2)
        t_text_layout.addWidget(self.lbl_t_title)
        t_text_layout.addWidget(self.lbl_t_desc)
        theme_layout.addLayout(t_text_layout, 1)
        
        self.btn_dark = QPushButton("DARK")
        self.btn_dark.setCheckable(True)
        self.btn_light = QPushButton("LIGHT")
        self.btn_light.setCheckable(True)
        
        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.btn_dark)
        self.theme_group.addButton(self.btn_light)
        
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(6)
        theme_btn_layout.addWidget(self.btn_dark)
        theme_btn_layout.addWidget(self.btn_light)
        theme_layout.addLayout(theme_btn_layout)
        
        card_layout.addWidget(self.theme_row)
        
        # Original Toggles
        self.toggle_1 = ToggleRow("Automatic Port Isolation", "Quarantine anomalous USB targets instantly.")
        self.toggle_2 = ToggleRow("Electrical Overcurrent Monitor", "Identify power-surge signature vectors.")
        self.toggle_3 = ToggleRow("Keyboard Rate Throttling", "De-escalate rapid BadUSB physical emulation speeds.")
        self.toggle_4 = ToggleRow("Driver Sandbox Mode", "Launch system classes in container nodes.")
        
        card_layout.addWidget(self.toggle_1)
        card_layout.addWidget(self.toggle_2)
        card_layout.addWidget(self.toggle_3)
        card_layout.addWidget(self.toggle_4)
        
        scroll_layout.addWidget(self.card)
        
        # 2. Trusted Devices Card
        self.card_trusted = GlassCard()
        trusted_layout = QVBoxLayout(self.card_trusted)
        self.trusted_layout = trusted_layout
        trusted_layout.setContentsMargins(32, 32, 32, 32)
        trusted_layout.setSpacing(12)
        
        lbl_trusted_title = QLabel("TRUSTED DEVICES")
        lbl_trusted_title.setObjectName("lbl_trusted_title")
        trusted_layout.addWidget(lbl_trusted_title)
        
        self.dev_sandisk = InfoRow("device_sandisk", "SanDisk Ultra USB 3.0", is_trusted=True)
        self.dev_kingston = InfoRow("device_kingston", "Kingston DataTraveler", is_trusted=True)
        self.dev_samsung = InfoRow("device_ssd", "Samsung T7 SSD", is_trusted=True)
        self.dev_logitech = InfoRow("device_keyboard", "Logitech Keyboard", is_trusted=True)
        
        trusted_layout.addWidget(self.dev_sandisk)
        trusted_layout.addWidget(self.dev_kingston)
        trusted_layout.addWidget(self.dev_samsung)
        trusted_layout.addWidget(self.dev_logitech)
        
        self.link_manage = InfoRow("arrow_right", "Manage Trusted Devices", show_arrow=True, is_trusted=True)
        trusted_layout.addWidget(self.link_manage)
        for sample in (self.dev_sandisk, self.dev_kingston, self.dev_samsung, self.dev_logitech,
                       self.link_manage):
            sample.hide()
        self.trusted_dynamic = []
        self.trusted_empty = InfoRow("shield", "Waiting for backend trust records", "LIVE")
        trusted_layout.addWidget(self.trusted_empty)
        scroll_layout.addWidget(self.card_trusted)
        
        # 3. Quarantine Settings Card
        self.card_quarantine = GlassCard()
        quarantine_layout = QVBoxLayout(self.card_quarantine)
        self.quarantine_layout = quarantine_layout
        quarantine_layout.setContentsMargins(32, 32, 32, 32)
        quarantine_layout.setSpacing(12)
        
        self.lbl_quarantine_title = QLabel("QUARANTINE VAULT")
        self.lbl_quarantine_title.setObjectName("lbl_quarantine_title")
        quarantine_layout.addWidget(self.lbl_quarantine_title)
        
        self.toggle_quarantine = ToggleRow("Automatically Quarantine Threats", "Isolate threats immediately on detection.")
        self.toggle_move = ToggleRow("Move Suspicious Files", "Relocate unverified risk vectors to secure folder.")
        self.toggle_delete = ToggleRow("Delete After Scan", "Permanently discard verified malicious payloads.")
        
        quarantine_layout.addWidget(self.toggle_quarantine)
        quarantine_layout.addWidget(self.toggle_move)
        quarantine_layout.addWidget(self.toggle_delete)
        for control in (self.toggle_quarantine, self.toggle_move, self.toggle_delete):
            control.hide()
        self.quarantine_dynamic = []
        self.quarantine_empty = InfoRow("shield", "Quarantine vault", "No records")
        quarantine_layout.addWidget(self.quarantine_empty)
        scroll_layout.addWidget(self.card_quarantine)
        
        # 4. Notification Settings Card
        self.card_notifications = GlassCard()
        notif_layout = QVBoxLayout(self.card_notifications)
        self.notification_layout = notif_layout
        notif_layout.setContentsMargins(32, 32, 32, 32)
        notif_layout.setSpacing(12)
        
        lbl_notif_title = QLabel("NOTIFICATION SETTINGS")
        lbl_notif_title.setObjectName("lbl_notif_title")
        notif_layout.addWidget(lbl_notif_title)
        
        self.notif_desk = ToggleRow("Desktop Notifications", "Enable real-time OS banner alerts.", "bell")
        self.notif_threat = ToggleRow("Threat Alerts", "Enable high-priority warnings on threat detection.", "shield")
        self.notif_conn = ToggleRow("USB Connection Alerts", "Flash popups when USB devices are attached.", "usb_connection")
        self.notif_scan = ToggleRow("Scan Complete Notification", "Deliver details upon scan finalization.", "scan_complete")
        
        notif_layout.addWidget(self.notif_desk)
        notif_layout.addWidget(self.notif_threat)
        notif_layout.addWidget(self.notif_conn)
        notif_layout.addWidget(self.notif_scan)
        for control in (self.notif_desk, self.notif_threat, self.notif_conn, self.notif_scan):
            control.hide()
        self.email_status_row = InfoRow("bell", "Email delivery", "Waiting for backend", show_status_dot=True)
        self.email_delivery_rows = []
        notif_layout.addWidget(self.email_status_row)
        scroll_layout.addWidget(self.card_notifications)
        
        # 5. Network Information Card
        self.card_network = GlassCard()
        net_layout = QVBoxLayout(self.card_network)
        net_layout.setContentsMargins(32, 32, 32, 32)
        net_layout.setSpacing(12)
        
        lbl_net_title = QLabel("NETWORK INFORMATION")
        lbl_net_title.setObjectName("lbl_network_title")
        net_layout.addWidget(lbl_net_title)
        
        net_layout.addWidget(InfoRow("wifi", "Wi-Fi Status", "Connected", show_status_dot=True))
        net_layout.addWidget(InfoRow("globe", "Network Name", "USB Detector Lab"))
        net_layout.addWidget(InfoRow("ethernet", "IP Address", "192.168.1.105"))
        net_layout.addWidget(InfoRow("ethernet", "MAC Address", "84:7B:57:XX:XX:XX"))
        net_layout.addWidget(InfoRow("globe", "Internet", "Connected", show_status_dot=True))
        scroll_layout.addWidget(self.card_network)
        self.card_network.hide()  # No backend network telemetry is published.
        
        # 6. Raspberry Pi Information Card
        self.card_pi = GlassCard()
        pi_layout = QVBoxLayout(self.card_pi)
        pi_layout.setContentsMargins(32, 32, 32, 32)
        pi_layout.setSpacing(12)
        
        lbl_pi_title = QLabel("RASPBERRY PI INFORMATION")
        lbl_pi_title.setObjectName("lbl_pi_title")
        pi_layout.addWidget(lbl_pi_title)
        
        pi_layout.addWidget(InfoRow("os", "Operating System", "Raspberry Pi OS"))
        pi_layout.addWidget(InfoRow("cpu", "CPU Model", "Broadcom BCM2712"))
        pi_layout.addWidget(InfoRow("temp", "CPU Temperature", "48°C"))
        pi_layout.addWidget(InfoRow("ram", "RAM", "8 GB"))
        pi_layout.addWidget(InfoRow("storage", "Storage", "64 GB"))
        pi_layout.addWidget(InfoRow("python", "Python Version", "3.x"))
        pi_layout.addWidget(InfoRow("python", "PyQt Version", "6.x"))
        pi_layout.addWidget(InfoRow("developer", "Application Version", "USB DETECTOR v1.0"))
        scroll_layout.addWidget(self.card_pi)
        self.card_pi.hide()  # Avoid presenting hard-coded hardware values as live data.

        # Live consolidated reports, populated from the backend snapshot.
        self.card_reports = GlassCard()
        self.reports_layout = QVBoxLayout(self.card_reports)
        self.reports_layout.setContentsMargins(32, 32, 32, 32)
        self.reports_layout.setSpacing(12)
        lbl_reports_title = QLabel("CONSOLIDATED INCIDENT REPORTS")
        lbl_reports_title.setObjectName("lbl_reports_title")
        self.reports_layout.addWidget(lbl_reports_title)
        self.reports_empty = InfoRow("scan_complete", "Reports", "No reports generated")
        self.reports_layout.addWidget(self.reports_empty)
        self.report_rows = []
        self.latest_report_path = ""
        self.btn_open_reports = QPushButton("OPEN LATEST PDF REPORT")
        self.btn_open_reports.setFixedHeight(36)
        self.btn_open_reports.setEnabled(False)
        self.btn_open_reports.clicked.connect(self.open_latest_report)
        self.reports_layout.addWidget(self.btn_open_reports)
        scroll_layout.addWidget(self.card_reports)
        
        # 7. About Application Card
        self.card_about = GlassCard()
        about_layout = QVBoxLayout(self.card_about)
        about_layout.setContentsMargins(32, 32, 32, 32)
        about_layout.setSpacing(12)
        
        lbl_about_title = QLabel("ABOUT APPLICATION")
        lbl_about_title.setObjectName("lbl_about_title")
        about_layout.addWidget(lbl_about_title)
        
        self.lbl_about_desc = QLabel("Premium USB Security Scanner with Apple-inspired Liquid Glass interface for detecting, monitoring, and analyzing USB devices.")
        self.lbl_about_desc.setWordWrap(True)
        about_layout.addWidget(self.lbl_about_desc)
        
        about_layout.addWidget(InfoRow("developer", "Application Name", "USB DETECTOR"))
        about_layout.addWidget(InfoRow("developer", "Version", "1.0.0"))
        about_layout.addWidget(InfoRow("python", "Framework", "Python + PyQt6"))
        about_layout.addWidget(InfoRow("cpu", "Target Device", "Raspberry Pi 7-inch Touchscreen"))
        scroll_layout.addWidget(self.card_about)
        
        # 8. Check for Updates Card
        self.card_updates = GlassCard()
        updates_layout = QVBoxLayout(self.card_updates)
        updates_layout.setContentsMargins(32, 32, 32, 32)
        updates_layout.setSpacing(12)
        
        lbl_updates_title = QLabel("APPLICATION UPDATES")
        lbl_updates_title.setObjectName("lbl_updates_title")
        updates_layout.addWidget(lbl_updates_title)
        
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.updates_icon = VectorIcon("refresh", size=24, color_key="accent")
        status_text_layout = QVBoxLayout()
        self.lbl_updates_status = QLabel("Application is up to date")
        self.lbl_updates_versions = QLabel("Current: 1.0.0  •  Latest: 1.0.0")
        status_text_layout.addWidget(self.lbl_updates_status)
        status_text_layout.addWidget(self.lbl_updates_versions)
        status_row.addWidget(self.updates_icon)
        status_row.addLayout(status_text_layout, 1)
        updates_layout.addLayout(status_row)
        
        self.btn_check = QPushButton("Check for Updates")
        self.btn_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check.setFixedHeight(36)
        updates_layout.addWidget(self.btn_check)
        self.btn_check.hide()  # Backend status occupies this card; no fake update check.
        scroll_layout.addWidget(self.card_updates)

        self.card_hid_recovery = GlassCard()
        recovery_layout = QVBoxLayout(self.card_hid_recovery)
        recovery_layout.setContentsMargins(24, 20, 24, 20)
        recovery_title = QLabel("HID RECOVERY")
        recovery_title.setStyleSheet("font-size: 13px; font-weight: 800;")
        self.lbl_hid_recovery = QLabel("Only connected HID devices with matching signed fingerprints will be recovered.")
        self.btn_recover_hid = QPushButton("RECOVER TRUSTED HID")
        self.btn_recover_hid.clicked.connect(self.recover_hid_requested.emit)
        recovery_layout.addWidget(recovery_title)
        recovery_layout.addWidget(self.lbl_hid_recovery)
        recovery_layout.addWidget(self.btn_recover_hid)
        scroll_layout.addWidget(self.card_hid_recovery)
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)
        
        if theme_manager.current_theme == "dark":
            self.btn_dark.setChecked(True)
        else:
            self.btn_light.setChecked(True)
            
        self.btn_dark.clicked.connect(lambda: theme_manager.set_theme("dark"))
        self.btn_light.clicked.connect(lambda: theme_manager.set_theme("light"))
        
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(2500)
        self.update_timer.timeout.connect(self.on_update_check_finished)
        
        self.spin_timer = QTimer(self)
        self.spin_timer.setInterval(16)
        self.spin_timer.timeout.connect(self.on_spin_icon)
        self.spin_angle = 0
        
        self.btn_check.clicked.connect(self.start_update_check)
        
        self.update_styles()
        theme_manager.theme_changed.connect(self.update_styles)

    def start_update_check(self):
        self.btn_check.setEnabled(False)
        self.btn_check.setText("Checking...")
        self.lbl_updates_status.setText("Checking for updates...")
        self.spin_angle = 0
        self.spin_timer.start()
        self.update_timer.start()
        
    def on_spin_icon(self):
        self.spin_angle = (self.spin_angle + 6) % 360
        self.updates_icon.set_rotation(self.spin_angle)
        
    def on_update_check_finished(self):
        self.update_timer.stop()
        self.spin_timer.stop()
        self.updates_icon.set_rotation(0)
        self.lbl_updates_status.setText("Application is already up to date.")
        self.btn_check.setText("Check for Updates")
        self.btn_check.setEnabled(True)

    def update_styles(self):
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        
        accent = theme_manager.get_color("accent")
        glass_border = theme_manager.get_color("glass_border")
        text_pri = theme_manager.get_color("text_primary")
        text_sec = theme_manager.get_color("text_secondary")
        
        bg = "rgba(255, 255, 255, 6)" if theme_manager.current_theme == "dark" else "rgba(15, 23, 42, 6)"
        self.theme_row.setStyleSheet(f"background-color: {bg}; border: 0.5px solid {glass_border}; border-radius: 12px;")
        self.lbl_t_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self.lbl_t_desc.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 11px; background: transparent; border: none;")
        
        lbl_welcome = self.findChild(QLabel, "lbl_welcome")
        if lbl_welcome:
            lbl_welcome.setStyleSheet(f"color: {text_sec}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.5px;")
            
        for name in ["lbl_trusted_title", "lbl_quarantine_title", "lbl_notif_title", "lbl_net_title", "lbl_pi_title", "lbl_reports_title", "lbl_about_title", "lbl_updates_title"]:
            lbl = self.findChild(QLabel, name)
            if lbl:
                lbl.setStyleSheet(f"color: {text_sec}; font-size: 11px; font-weight: 800; font-family: 'Inter'; letter-spacing: 1.2px; background: transparent; border: none;")
                
        self.lbl_about_desc.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 12px; line-height: 1.4; background: transparent; border: none;")
        self.lbl_updates_status.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-weight: 700; font-size: 13px; background: transparent; border: none;")
        self.lbl_updates_versions.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 11px; background: transparent; border: none;")
        self.btn_check.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,255,255,10); color: {text_pri};
                border-radius: 12px; font-family: 'Inter'; font-weight: 800;
                font-size: 11px; border: 1px solid {glass_border}; }}
            QPushButton:hover {{ border: 1px solid {accent}; }}
            QPushButton:disabled {{ color: {text_sec}; border: 1px solid {glass_border}; }}
        """)
        self.btn_open_reports.setStyleSheet(f"""
            QPushButton {{ background: rgba(217,127,74,180); color: #ffffff;
                border-radius: 12px; font-family: 'Inter'; font-weight: 800;
                font-size: 11px; border: 1px solid {accent}; }}
            QPushButton:disabled {{ background: rgba(255,255,255,5); color: {text_sec};
                border: 1px solid {glass_border}; }}
        """)
        for btn, name in ((self.btn_dark, "dark"), (self.btn_light, "light")):
            selected = theme_manager.current_theme == name
            btn.setStyleSheet(f"""
                QPushButton {{ background: {'rgba(217,127,74,180)' if selected else 'rgba(255,255,255,10)'};
                    color: {'#ffffff' if selected else text_sec}; border-radius: 14px;
                    font-family: 'Inter'; font-weight: 800; font-size: 10px;
                    padding: 6px 14px; border: 1px solid {accent if selected else glass_border}; }}
            """)

    def apply_backend_status(self, system_status, resources):
        """Show real service capability/resource state in the existing cards."""
        status = system_status or {}
        resources = resources or {}
        ready = sum(1 for value in status.values()
                    if str(value).upper() in {"READY", "ONLINE", "ENABLED", "TRUE"})
        self.lbl_status.setText("Security engine online")
        self.lbl_about_desc.setText(
            "Live Raspberry Pi USB security service connected. "
            f"{ready}/{len(status)} reported capabilities ready; "
            f"{len(resources.get('quarantine', []))} quarantine records and "
            f"{len(resources.get('reports', []))} reports available."
        )
        email = status.get("email") or status.get("email_notifications") or "OPTIONAL / DISABLED"
        self.lbl_updates_status.setText(f"Backend connected — Email: {email}")
        self.lbl_updates_versions.setText("Configuration changes remain administrator-controlled through run.sh")
        if resources:
            self.apply_backend_resources(resources)

    @staticmethod
    def _remove_rows(layout, rows):
        for row in rows:
            layout.removeWidget(row)
            row.deleteLater()
        rows.clear()

    def apply_backend_resources(self, resources):
        resources = resources or {}
        self._remove_rows(self.reports_layout, self.report_rows)
        reports = resources.get("reports") or []
        self.reports_empty.setVisible(not reports)
        self.latest_report_path = ""
        for report in reports[:12]:
            verdict = str(report.get("verdict", "UNKNOWN"))
            incident = str(report.get("incident_id", "Unknown incident"))
            row = InfoRow("scan_complete", incident, verdict)
            row.setToolTip(
                f"PDF: {report.get('pdf_path', 'Unavailable')}\nJSON: {report.get('json_path', 'Unavailable')}"
            )
            self.reports_layout.insertWidget(self.reports_layout.count() - 1, row)
            self.report_rows.append(row)
            if not self.latest_report_path and report.get("pdf_path"):
                self.latest_report_path = str(report["pdf_path"])
        self.btn_open_reports.setEnabled(bool(self.latest_report_path))
        self._remove_rows(self.trusted_layout, self.trusted_dynamic)
        trusted = []
        for vid_pid, label in (resources.get("trusted_hid") or {}).items():
            trusted.append((str(label), f"HID · {vid_pid}"))
        for vid_pid, record in (resources.get("trusted_storage") or {}).items():
            label = record.get("label", "Trusted storage") if isinstance(record, dict) else str(record)
            trusted.append((label, f"STORAGE · {vid_pid}"))
        self.trusted_empty.setVisible(not trusted)
        for label, value in trusted[:12]:
            row = InfoRow("shield", label, value, is_trusted=True)
            self.trusted_layout.addWidget(row)
            self.trusted_dynamic.append(row)

        self._remove_rows(self.quarantine_layout, self.quarantine_dynamic)
        quarantine = resources.get("quarantine") or []
        self.lbl_quarantine_title.setText(f"QUARANTINE VAULT — {len(quarantine)} FILE(S)")
        self.quarantine_empty.setVisible(not quarantine)
        if not quarantine:
            self.quarantine_empty.lbl_val.setText("No records")
        for index, entry in enumerate(quarantine[::-1], 1):
            name = entry.get("original_name") or entry.get("original_path") or "Quarantined file"
            reason = entry.get("reason") or "Security engine detection"
            timestamp = str(entry.get("timestamp", "Unknown time")).replace("T", " ")[:19]
            device = entry.get("device_model") or entry.get("device_vid_pid") or "Unknown device"
            vault_path = entry.get("quarantine_path", "Unknown vault path")
            row = InfoRow("shield", f"{name} — {reason} — {device}",
                          f"{timestamp} · {vault_path}")
            row.setToolTip(
                f"Original: {entry.get('original_path', 'Unknown')}\n"
                f"Vault: {entry.get('quarantine_path', 'Unknown')}\n"
                f"SHA-256: {entry.get('sha256', 'Unknown')}"
            )
            row.add_action_button("RESTORE", lambda checked=False, i=index: self.quarantine_restore_requested.emit(i))
            row.add_action_button("DELETE", lambda checked=False, i=index: self.quarantine_delete_requested.emit(i))
            self.quarantine_layout.addWidget(row)
            self.quarantine_dynamic.append(row)

        email_status = resources.get("email_status") or {}
        enabled, ready = bool(email_status.get("enabled")), bool(email_status.get("ready"))
        email_text = "READY" if enabled and ready else "DISABLED" if not enabled else "CONFIGURATION REQUIRED"
        self.email_status_row.lbl_val.setText(email_text)
        self._remove_rows(self.notification_layout, self.email_delivery_rows)
        for delivery in (resources.get("email_deliveries") or [])[:10]:
            incident = delivery.get("incident_id", "Unknown incident")
            value = f"{delivery.get('status', 'UNKNOWN')} · attempts {delivery.get('attempts', 0)}"
            row = InfoRow("bell", str(incident), value)
            if delivery.get("error"):
                row.setToolTip(str(delivery["error"]))
            self.notification_layout.addWidget(row)
            self.email_delivery_rows.append(row)

    def apply_resource_event(self, event, data):
        """Immediately reflect an update while the full snapshot is refreshed."""
        if event == "email_delivery_updated":
            self.email_status_row.lbl_val.setText(str(data.get("status", "UPDATED")).upper())
        elif event == "quarantine_updated":
            self.quarantine_empty.setVisible(False)
            self.lbl_quarantine_title.setText(
                f"QUARANTINE VAULT — {len(self.quarantine_dynamic) + 1} FILE(S)"
            )
            name = data.get("original_name") or data.get("original_path") or "Quarantined file"
            row = InfoRow("shield", f"{name} — {data.get('reason', 'Quarantined')}",
                          str(data.get("quarantine_path", "Vault path pending")))
            self.quarantine_layout.addWidget(row)
            self.quarantine_dynamic.insert(0, row)

    def open_latest_report(self):
        if self.latest_report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.latest_report_path))
