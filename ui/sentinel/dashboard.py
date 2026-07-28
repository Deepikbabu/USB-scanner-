import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedLayout, QScrollArea, QFrame, QGraphicsOpacityEffect, QComboBox, QGridLayout, QProgressBar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QVariantAnimation, QEasingCurve, QTime, QPointF, QDateTime, QPropertyAnimation
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath
from theme import theme_manager
from widgets import GlassCard, AnimatedUSBWidget, CircularRiskRing, StatusBadge, draw_category_vector_icon, GlassProgressBar

class VectorIconWidget(QWidget):
    def __init__(self, icon_type, size=18, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.size = size
        self.setFixedSize(size, size)
        self.color = QColor("#D97F4A")
        
    def set_color(self, color):
        if isinstance(color, str):
            self.color = QColor(color)
        elif isinstance(color, QColor):
            self.color = color
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(self.color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = min(cx, cy) - 2.0
        
        if self.icon_type == "bell":
            path = QPainterPath()
            path.moveTo(cx - 5, cy + 3)
            path.lineTo(cx + 5, cy + 3)
            path.lineTo(cx + 4, cy - 2)
            path.cubicTo(cx + 4, cy - 6, cx - 4, cy - 6, cx - 4, cy - 2)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawArc(QRectF(cx - 1.5, cy + 3.5, 3.0, 3.0), 180 * 16, 180 * 16)
            painter.drawEllipse(QRectF(cx - 1.2, cy - 8.0, 2.4, 2.4))
        elif self.icon_type == "wifi":
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(QRectF(cx - 1.0, cy + 5.0, 2.0, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx - 3.5, cy + 1.0, 7.0, 7.0), 45 * 16, 90 * 16)
            painter.drawArc(QRectF(cx - 6.5, cy - 2.0, 13.0, 13.0), 45 * 16, 90 * 16)
            painter.drawArc(QRectF(cx - 9.5, cy - 5.0, 19.0, 19.0), 45 * 16, 90 * 16)
        elif self.icon_type == "bluetooth":
            path = QPainterPath()
            # Standard single-stroke elegant Bluetooth rune
            path.moveTo(cx - r * 0.4, cy - r * 0.4)
            path.lineTo(cx + r * 0.4, cy + r * 0.4)
            path.lineTo(cx, cy + r)
            path.lineTo(cx, cy - r)
            path.lineTo(cx + r * 0.4, cy - r * 0.4)
            path.lineTo(cx - r * 0.4, cy + r * 0.4)
            painter.drawPath(path)
        elif self.icon_type == "battery":
            # Neatly proportioned clean battery
            bw = self.width() * 0.65
            bh = self.height() * 0.42
            bx = (self.width() - bw - 2.0) / 2.0
            by = (self.height() - bh) / 2.0
            
            # Outer frame
            painter.drawRoundedRect(QRectF(bx, by, bw, bh), 1.5, 1.5)
            
            # Positive terminal (tip)
            tx = bx + bw
            tw = 1.5
            th = bh * 0.4
            ty = by + (bh - th) / 2.0
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(tx, ty, tw, th), 0.5, 0.5)
            
            # Inner charge level fill (82% charged)
            gap = 1.5
            inner_w = bw - 2.0 * gap
            inner_h = bh - 2.0 * gap
            inner_x = bx + gap
            inner_y = by + gap
            painter.drawRoundedRect(QRectF(inner_x, inner_y, inner_w * 0.82, inner_h), 0.5, 0.5)
        elif self.icon_type in ["clock", "time"]:
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - r + 3.0))
            painter.drawLine(QPointF(cx, cy), QPointF(cx + r - 4.0, cy))
        elif self.icon_type in ["calendar", "date"]:
            painter.drawRoundedRect(QRectF(cx - r, cy - r + 2, 2 * r, 2 * r - 2), 2, 2)
            painter.drawLine(QPointF(cx - r, cy - r + 6), QPointF(cx + r, cy - r + 6))
            painter.drawLine(QPointF(cx - r + 3, cy - r), QPointF(cx - r + 3, cy - r + 3))
            painter.drawLine(QPointF(cx + r - 3, cy - r), QPointF(cx + r - 3, cy - r + 3))
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(QRectF(cx - 3, cy + 1, 1.5, 1.5))
            painter.drawEllipse(QRectF(cx + 1, cy + 1, 1.5, 1.5))
            painter.drawEllipse(QRectF(cx - 3, cy + 4, 1.5, 1.5))
            painter.drawEllipse(QRectF(cx + 1, cy + 4, 1.5, 1.5))
        elif self.icon_type in ["status", "system"]:
            path = QPainterPath()
            path.moveTo(cx, cy - r)
            path.lineTo(cx + r, cy - r * 0.5)
            path.lineTo(cx + r, cy + r * 0.5)
            path.lineTo(cx, cy + r)
            path.lineTo(cx - r, cy + r * 0.5)
            path.lineTo(cx - r, cy - r * 0.5)
            path.closeSubpath()
            painter.drawPath(path)
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(QRectF(cx - 1.5, cy - 1.5, 3.0, 3.0))

SIMULATED_DEVICES = []  # Real devices arrive exclusively from the backend.
'''LEGACY_SAMPLE_DEVICES = [
    {
        "name": "SanDisk Ultra USB 3.0",
        "manufacturer": "SanDisk",
        "vid": "0x0781",
        "pid": "0x5583",
        "serial": "SDX2026A12345",
        "usb_version": "USB 3.0",
        "capacity": "64 GB",
        "used_space": "18 GB",
        "free_space": "46 GB",
        "file_system": "FAT32",
        "category": "USB Flash Drive",
        "classification": "USB Flash Drive",
        "is_bad": False
    },
    {
        "name": "Kingston DataTraveler",
        "manufacturer": "Kingston",
        "vid": "0x0930",
        "pid": "0x6543",
        "serial": "LGK2026A7712",
        "usb_version": "USB 3.1",
        "capacity": "128 GB",
        "used_space": "32 GB",
        "free_space": "96 GB",
        "file_system": "exFAT",
        "category": "Pen Drive",
        "classification": "Pen Drive",
        "is_bad": False
    },
    {
        "name": "Samsung T7 Portable SSD",
        "manufacturer": "Samsung",
        "vid": "0x04E8",
        "pid": "0x61F5",
        "serial": "SAMS2026T7990",
        "usb_version": "USB 3.2",
        "capacity": "1 TB",
        "used_space": "280 GB",
        "free_space": "744 GB",
        "file_system": "exFAT",
        "category": "External SSD",
        "classification": "External SSD",
        "is_bad": False
    },
    {
        "name": "Logitech MX Master Mouse",
        "manufacturer": "Logitech",
        "vid": "0x046D",
        "pid": "0xC52B",
        "serial": "LOGI9182C771",
        "usb_version": "USB 2.0",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "USB Mouse",
        "classification": "USB Mouse",
        "is_bad": False
    },
    {
        "name": "Dell Premium USB Mouse",
        "manufacturer": "Dell",
        "vid": "0x413C",
        "pid": "0x301A",
        "serial": "DELL65421MOU",
        "usb_version": "USB 2.0",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "USB Mouse",
        "classification": "USB Mouse",
        "is_bad": False
    },
    {
        "name": "Anker USB-C Hub Controller",
        "manufacturer": "Anker",
        "vid": "0x2109",
        "pid": "0x0817",
        "serial": "ANKR2026HUB",
        "usb_version": "USB-C",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "USB-C Device",
        "classification": "USB-C Device",
        "is_bad": False
    },
    {
        "name": "HDMI Capture Adapter",
        "manufacturer": "Anker",
        "vid": "0x1B1C",
        "pid": "0x1C2D",
        "serial": "HDMI99281ACC",
        "usb_version": "USB 3.0",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "HDMI Device",
        "classification": "HDMI Device",
        "is_bad": False
    },
    {
        "name": "3.5 mm Audio Adapter",
        "manufacturer": "Anker",
        "vid": "0x0B05",
        "pid": "0x1902",
        "serial": "AUD99281SND",
        "usb_version": "USB 2.0",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "3.5 mm Audio Device",
        "classification": "3.5 mm Audio Device",
        "is_bad": True
    },
    {
        "name": "Sony Professional SD Card",
        "manufacturer": "Sony",
        "vid": "0x054C",
        "pid": "0x09C2",
        "serial": "SDSK56482AX",
        "usb_version": "USB 3.0",
        "capacity": "32 GB",
        "used_space": "8 GB",
        "free_space": "24 GB",
        "file_system": "FAT32",
        "category": "SD Card",
        "classification": "SD Card",
        "is_bad": False
    },
    {
        "name": "Stealth Rubber Ducky V2",
        "manufacturer": "Corsair",
        "vid": "0x04D9",
        "pid": "0x1702",
        "serial": "SNX2A45B9137",
        "usb_version": "USB 2.0",
        "capacity": "N/A",
        "used_space": "0 GB",
        "free_space": "0 GB",
        "file_system": "N/A",
        "category": "USB Keyboard",
        "classification": "USB Keyboard",
        "is_bad": True
    },
]'''

class GlassOverlayPopup(QWidget):
    authorized = pyqtSignal(bool, dict)

    def __init__(self, device_data, parent=None):
        super().__init__(parent)
        self.device_data = device_data
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = GlassCard(self)
        self.card.setFixedSize(380, 240)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        
        # Threat Alert vs Normal Authorization Header
        title_text = "SECURITY AUTHORIZATION" if not device_data['is_bad'] else "CRITICAL ATTACK SHIELDED"
        color_theme = theme_manager.get_color("accent") if not device_data['is_bad'] else "#B5522B"
        
        self.lbl_title = QLabel(title_text)
        self.lbl_title.setStyleSheet(f"color: {color_theme}; font-family: 'Inter'; font-weight: 800; font-size: 15px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_device = QLabel(f"{device_data['name']}\nType: {device_data['category']} ({device_data['vid']}:{device_data['pid']})")
        self.lbl_device.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 500; font-size: 13px; line-height: 18px;")
        self.lbl_device.setWordWrap(True)
        self.lbl_device.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_warning = QLabel(
            "WARNING: This device behaves like a Human Interface Device (Keyboard) but is disguised as simple storage." 
            if device_data['is_bad'] else 
            "The connected peripheral is awaiting classification validation."
        )
        self.lbl_warning.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        
        if device_data['is_bad']:
            self.btn_action = QPushButton("ISOLATE && SHIELD")
            self.btn_action.setStyleSheet("""
                QPushButton {
                    background-color: #B5522B; color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px;
                }
                QPushButton:hover { background-color: #964423; }
            """)
            self.btn_action.clicked.connect(lambda: self.authorized.emit(False, self.device_data))
            btn_layout.addWidget(self.btn_action)
        else:
            self.btn_allow = QPushButton("ALLOW DEVICE")
            self.btn_allow.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.get_color('accent')}; color: black; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            self.btn_allow.clicked.connect(lambda: self.authorized.emit(True, self.device_data))
            
            self.btn_deny = QPushButton("BLOCK")
            self.btn_deny.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255,255,255,10); color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px; border: 0.5px solid rgba(255,255,255,20);
                }
                QPushButton:hover { background-color: rgba(255,255,255,18); }
            """)
            self.btn_deny.clicked.connect(lambda: self.authorized.emit(False, self.device_data))
            
            btn_layout.addWidget(self.btn_deny)
            btn_layout.addWidget(self.btn_allow)
            
        card_layout.addWidget(self.lbl_title)
        card_layout.addWidget(self.lbl_device)
        card_layout.addWidget(self.lbl_warning)
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(self.card)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

class NewDeviceFoundPopup(QWidget):
    action_clicked = pyqtSignal(bool, dict) # True for Inject, False for Eject

    def __init__(self, device_data, parent=None):
        super().__init__(parent)
        self.device_data = device_data
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = GlassCard(self)
        self.card.setFixedSize(380, 240)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        
        self.lbl_title = QLabel("NEW DEVICE FOUND")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-weight: 800; font-size: 15px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_device = QLabel(f"{device_data['name']}")
        self.lbl_device.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 700; font-size: 14px; line-height: 18px;")
        self.lbl_device.setWordWrap(True)
        self.lbl_device.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_warning = QLabel("A new USB device has been detected.\nWould you like to connect this device?")
        self.lbl_warning.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 12px;")
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        
        self.btn_eject = QPushButton("EJECT")
        self.btn_eject.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,10); color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px; border: 0.5px solid rgba(255,255,255,20);
            }
            QPushButton:hover { background-color: rgba(255,255,255,18); }
        """)
        self.btn_eject.clicked.connect(lambda: self.action_clicked.emit(False, self.device_data))
        
        self.btn_inject = QPushButton("INJECT")
        self.btn_inject.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('accent')}; color: black; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        self.btn_inject.clicked.connect(lambda: self.action_clicked.emit(True, self.device_data))
        
        btn_layout.addWidget(self.btn_eject)
        btn_layout.addWidget(self.btn_inject)
        
        card_layout.addWidget(self.lbl_title)
        card_layout.addWidget(self.lbl_device)
        card_layout.addWidget(self.lbl_warning)
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(self.card)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

TRUSTED_DEVICES = []  # Trust is supplied by backend fingerprint state.

def check_device_type_match(selected, actual):
    selected_clean = selected.lower().replace("adapter", "device").strip()
    actual_clean = actual.lower().replace("adapter", "device").strip()
    return (selected_clean == actual_clean) or (selected_clean in actual_clean) or (actual_clean in selected_clean)

class UnknownDevicePopup(QWidget):
    action_clicked = pyqtSignal(str, str, dict) # action ('scan' or 'block'), selected_type, device_data

    def __init__(self, device_data, parent=None):
        super().__init__(parent)
        self.device_data = device_data
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = GlassCard(self)
        self.card.setFixedSize(400, 360)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        
        self.lbl_title = QLabel("New Device Found")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-weight: 800; font-size: 15px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        details_layout = QGridLayout()
        details_layout.setSpacing(8)
        
        lbl_name_tag = QLabel("Device Name:")
        lbl_name_tag.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-weight: 600; font-size: 12px;")
        self.lbl_name_val = QLabel(device_data['name'])
        self.lbl_name_val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: bold; font-size: 12px;")
        self.lbl_name_val.setWordWrap(True)
        
        lbl_type_tag = QLabel("Detected Device Type:")
        lbl_type_tag.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-weight: 600; font-size: 12px;")
        self.lbl_type_val = QLabel(device_data['category'])
        self.lbl_type_val.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-weight: bold; font-size: 12px;")
        
        details_layout.addWidget(lbl_name_tag, 0, 0)
        details_layout.addWidget(self.lbl_name_val, 0, 1)
        details_layout.addWidget(lbl_type_tag, 1, 0)
        details_layout.addWidget(self.lbl_type_val, 1, 1)
        
        self.lbl_msg = QLabel("A USB device has been detected.\nPlease select the type of device you want to scan.")
        self.lbl_msg.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_question = QLabel("What type of device would you like to scan?")
        self.lbl_question.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: 600;")
        self.lbl_question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.combo_types = QComboBox()
        self.combo_types.addItems([
            "USB Flash Drive",
            "Pen Drive",
            "External HDD",
            "External SSD",
            "USB Keyboard",
            "USB Mouse",
            "USB-C Device",
            "HDMI Adapter",
            "3.5 mm Audio Device",
            "SD Card",
            "Mobile Device",
            "Unknown Device"
        ])
        
        bg_color = "#1e2c3a" if theme_manager.current_theme == 'dark' else "#ffffff"
        text_color = "#ffffff" if theme_manager.current_theme == 'dark' else "#000000"
        self.combo_types.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(255, 255, 255, 12);
                color: {theme_manager.get_color('text_primary')};
                border: 0.5px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
                padding: 6px 12px;
                font-family: 'Inter';
                font-size: 12px;
                min-width: 220px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_color};
                color: {text_color};
                border: 0.5px solid rgba(255, 255, 255, 20);
                selection-background-color: {theme_manager.get_color('accent')};
                selection-color: black;
            }}
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        
        self.btn_block = QPushButton("Block")
        self.btn_block.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,10); color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px; border: 0.5px solid rgba(255,255,255,20);
            }
            QPushButton:hover { background-color: rgba(255,255,255,18); }
        """)
        self.btn_block.clicked.connect(self.on_block_clicked)
        
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('accent')}; color: black; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        self.btn_scan.clicked.connect(self.on_scan_clicked)
        
        btn_layout.addWidget(self.btn_block)
        btn_layout.addWidget(self.btn_scan)
        
        card_layout.addWidget(self.lbl_title)
        card_layout.addLayout(details_layout)
        card_layout.addWidget(self.lbl_msg)
        card_layout.addWidget(self.lbl_question)
        card_layout.addWidget(self.combo_types, 0, Qt.AlignmentFlag.AlignCenter)
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(self.card)

    def on_block_clicked(self):
        self.action_clicked.emit("block", self.combo_types.currentText(), self.device_data)

    def on_scan_clicked(self):
        self.action_clicked.emit("scan", self.combo_types.currentText(), self.device_data)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

class VerificationSuccessPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = GlassCard(self)
        self.card.setFixedSize(380, 180)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        
        self.lbl_title = QLabel("Device Verified")
        self.lbl_title.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-weight: 800; font-size: 15px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_msg = QLabel("Device type verified successfully.\nStarting security scan...")
        self.lbl_msg.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 13px; font-weight: bold;")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card_layout.addWidget(self.lbl_title)
        card_layout.addWidget(self.lbl_msg)
        layout.addWidget(self.card)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

class DeviceMismatchPopup(QWidget):
    action_clicked = pyqtSignal(str, dict) # 'retry' or 'block', device_data

    def __init__(self, detected_type, selected_type, device_data, parent=None):
        super().__init__(parent)
        self.device_data = device_data
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.card = GlassCard(self)
        self.card.setFixedSize(400, 300)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)
        
        self.lbl_title = QLabel("Device Type Mismatch")
        self.lbl_title.setStyleSheet("color: #B5522B; font-family: 'Inter'; font-weight: 800; font-size: 15px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_msg = QLabel("The selected device type does not match the connected device.")
        self.lbl_msg.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        lbl_det_tag = QLabel("Detected Device:")
        lbl_det_tag.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-weight: 600; font-size: 12px;")
        lbl_det_val = QLabel(detected_type)
        lbl_det_val.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-weight: bold; font-size: 12px;")
        
        lbl_sel_tag = QLabel("Selected Device:")
        lbl_sel_tag.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-weight: 600; font-size: 12px;")
        lbl_sel_val = QLabel(selected_type)
        lbl_sel_val.setStyleSheet("color: #B5522B; font-family: 'Inter'; font-weight: bold; font-size: 12px;")
        
        grid.addWidget(lbl_det_tag, 0, 0)
        grid.addWidget(lbl_det_val, 0, 1)
        grid.addWidget(lbl_sel_tag, 1, 0)
        grid.addWidget(lbl_sel_val, 1, 1)
        
        self.lbl_submsg = QLabel("Please verify the connected device before scanning.")
        self.lbl_submsg.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_submsg.setWordWrap(True)
        self.lbl_submsg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        
        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('accent')}; color: black; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        self.btn_retry.clicked.connect(lambda: self.action_clicked.emit("retry", self.device_data))
        
        self.btn_block = QPushButton("Block Device")
        self.btn_block.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10); color: white; border-radius: 10px; padding: 10px; font-weight: bold; font-family: 'Inter'; font-size: 12px; border: 0.5px solid rgba(255, 255, 255, 20);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 18); }
        """)
        self.btn_block.clicked.connect(lambda: self.action_clicked.emit("block", self.device_data))
        
        btn_layout.addWidget(self.btn_retry)
        btn_layout.addWidget(self.btn_block)
        
        card_layout.addWidget(self.lbl_title)
        card_layout.addWidget(self.lbl_msg)
        card_layout.addLayout(grid)
        card_layout.addWidget(self.lbl_submsg)
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(self.card)

class ClassificationIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.category = "Unknown Device"
        self.setFixedSize(40, 40)
        
    def set_category(self, category):
        self.category = category
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        draw_category_vector_icon(painter, self.category, 0, 0, 40)

class DeviceClassificationCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        self.lbl_title = QLabel("DEVICE CLASSIFICATION")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        content = QHBoxLayout()
        content.setSpacing(12)
        
        self.icon_widget = ClassificationIconWidget()
        content.addWidget(self.icon_widget)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        self.lbl_type = QLabel("No Device Detected")
        self.lbl_type.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 13px; font-weight: bold;")
        
        self.lbl_desc = QLabel("Waiting for USB Device peripheral insertion...")
        self.lbl_desc.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(self.lbl_type)
        text_layout.addWidget(self.lbl_desc)
        content.addLayout(text_layout, 1)
        
        layout.addLayout(content)
        theme_manager.theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()
        
    def reset(self):
        self.icon_widget.set_category("Unknown Device")
        self.lbl_type.setText("No Device Detected")
        self.lbl_desc.setText("Waiting for USB Device peripheral insertion...")
        
    def update_classification(self, category):
        self.icon_widget.set_category(category)
        self.lbl_type.setText(category)
        
        descriptions = {
            "USB Flash Drive": "Removable flash storage device for quick file transfers.",
            "Pen Drive": "Ultra-portable NAND flash memory storage peripheral.",
            "External HDD": "High-capacity mechanical external storage disk drive.",
            "External SSD": "Solid-state rapid external storage partition.",
            "USB Keyboard": "Standard alphanumeric input device, potential keystroke vector.",
            "USB Mouse": "Precision optical pointer cursor control device.",
            "USB-C Device": "Universal bus high-speed multi-role controller.",
            "HDMI Device": "Direct digital video stream capture and display output controller.",
            "3.5 mm Audio Device": "External acoustic transceiver and sound processing card.",
            "SD Card": "Miniature flash memory expansion standard.",
            "Mobile Device": "Interactive handheld terminal with internal communication chips.",
            "Unknown Device": "Unidentified or generic universal serial bus controller."
        }
        self.lbl_desc.setText(descriptions.get(category, "Unclassified external hardware controller connected."))

    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_type.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 13px; font-weight: bold;")
        self.lbl_desc.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")

class LargeDeviceIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.category = "Unknown Device"
        self.setFixedSize(40, 40)
        
    def set_category(self, category):
        self.category = category
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_category_vector_icon(painter, self.category, 0, 0, 40)

class TrustProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0  # 0 to 100
        self.color_hex = "#00e676"
        self.setMinimumHeight(6)
        self.setMaximumHeight(6)
        self.setFixedWidth(130)
        
        # Continuous glow animation timer for the moving shine/pulse effect
        self.glow_timer = QTimer(self)
        self.glow_timer.timeout.connect(self.update_glow)
        self.glow_timer.start(25) # ~40 FPS for super smooth movement
        self.glow_offset = 0.0
        
    def set_progress(self, progress, color_hex):
        self.progress = progress
        self.color_hex = color_hex
        self.update()
        
    def update_glow(self):
        # Move the glow offset continuously
        self.glow_offset += 0.02
        if self.glow_offset > 1.2:
            self.glow_offset = -0.2
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track Background (glassmorphic look)
        rect = QRectF(0, 1, self.width(), 4)
        bg_color = QColor(255, 255, 255, 18) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 2, 2)
        
        # Filled Progress segment
        fill_width = self.width() * (self.progress / 100.0)
        if fill_width > 0:
            fill_rect = QRectF(0, 1, fill_width, 4)
            gradient = QLinearGradient(0, 0, fill_width, 0)
            
            # Premium Cyber Gradients - Recolored to Monochrome Rust
            if self.color_hex == "#00e676":  # Trusted -> Accent to Muted Rust
                gradient.setColorAt(0, QColor("#D97F4A"))
                gradient.setColorAt(1, QColor("#8A6455"))
            elif self.color_hex == "#ff1744":  # Blocked -> Dark Rust Red to Dark Charcoal Rust
                gradient.setColorAt(0, QColor("#B5522B"))
                gradient.setColorAt(1, QColor("#702315"))
            elif self.color_hex == "#ffb300":  # Unknown -> Muted Tan to Muted Brown
                gradient.setColorAt(0, QColor("#C98A5E"))
                gradient.setColorAt(1, QColor("#8A7568"))
            else:
                c = QColor(self.color_hex)
                gradient.setColorAt(0, c)
                gradient.setColorAt(1, c.lighter(125))
                
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill_rect, 2, 2)
            
            # Highlight/Glow/Shine animation overlay
            glow_width = 35.0
            glow_start = fill_width * self.glow_offset - (glow_width / 2.0)
            highlight_gradient = QLinearGradient(glow_start, 0, glow_start + glow_width, 0)
            highlight_gradient.setColorAt(0, QColor(255, 255, 255, 0))
            highlight_gradient.setColorAt(0.5, QColor(255, 255, 255, 180)) # Crisp white core
            highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(highlight_gradient))
            painter.setClipRect(fill_rect)
            painter.drawRoundedRect(QRectF(glow_start, 1, glow_width, 4), 2, 2)

class LiquidGlassBadge(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("liquidGlassBadge")
        self.status = "None"
        self.target_score = 0
        self.current_score = 0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_score_row = QLabel()
        self.lbl_score_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # New sleek progress bar widget
        self.progress_bar_widget = TrustProgressBar()
        
        self.lbl_status_row = QLabel()
        self.lbl_status_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Backward compatibility attributes
        self.lbl_bar_row = QLabel()
        self.lbl_bar_row.hide()
        
        self.lbl_text = QLabel()
        self.lbl_text.hide()
        
        layout.addWidget(self.lbl_score_row)
        layout.addWidget(self.progress_bar_widget, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_status_row)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.on_anim_tick)
        
        self.set_status("None")
        
    def set_status(self, status):
        self.status = status
        if status == "Trusted":
            self.target_score = 96
        elif status == "Blocked":
            self.target_score = 15
        elif status == "Unknown":
            self.target_score = 65
        else:
            self.target_score = 0
            
        self.current_score = 0
        self.anim_timer.start(25)
        self.update_ui()
        
    def on_anim_tick(self):
        if self.current_score < self.target_score:
            self.current_score += 2
            if self.current_score >= self.target_score:
                self.current_score = self.target_score
                self.anim_timer.stop()
            self.update_ui()
        elif self.current_score > self.target_score:
            self.current_score -= 2
            if self.current_score <= self.target_score:
                self.current_score = self.target_score
                self.anim_timer.stop()
            self.update_ui()
        else:
            self.anim_timer.stop()
            
    def update_ui(self):
        score_val = f"{self.current_score}%"
        
        total_blocks = 10
        filled_blocks = int(round(self.current_score * total_blocks / 100))
        bar_str = "█" * filled_blocks + "░" * (total_blocks - filled_blocks)
        
        if self.status == "Trusted":
            color = "#D97F4A"
            status_lbl = "✓ Trusted"
        elif self.status == "Blocked":
            color = "#B5522B"
            status_lbl = "✗ Suspicious"
        elif self.status == "Unknown":
            color = "#C98A5E"
            status_lbl = "⚠ Unknown"
        else:
            color = "#8A7568"
            status_lbl = "░ Offline"
            
        self.lbl_score_row.setText(f"<span style='color: {theme_manager.get_color('text_secondary')}; font-family: Inter; font-size: 8px; font-weight: 800; letter-spacing: 0.5px;'>TRUST SCORE:</span> <span style='color: {color}; font-family: Inter; font-size: 11px; font-weight: 800;'>{score_val}</span>")
        self.lbl_bar_row.setText(f"<span style='color: {color}; font-family: \"JetBrains Mono\", monospace; font-size: 11px; font-weight: bold;'>{bar_str}</span>")
        self.lbl_status_row.setText(f"<span style='color: {color}; font-family: Inter; font-size: 9px; font-weight: 800;'>{status_lbl.upper()}</span>")
        
        # Update custom progress bar
        self.progress_bar_widget.set_progress(self.current_score, color)
        
        self.lbl_text.setText(status_lbl)
        self.update_style()
        
    def update_style(self):
        self.setStyleSheet("""
            #liquidGlassBadge {
                background-color: transparent;
                border: none;
            }
        """)

class DummyFingerprintPanel:
    def __init__(self, target_label):
        self.lbl = target_label
    def set_fingerprint(self, text):
        self.lbl.setText(text)

class DummyPortBlockWidget:
    def __init__(self, port_label, speed_label):
        self.lbl_value = port_label
        self.lbl_sub = speed_label

class DeviceInfoCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("deviceInfoCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)
        
        self.lbl_title = QLabel("DEVICE INFORMATION")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        # ----------------------------------------------------
        # SECTION 1: HEADER ROW
        # ----------------------------------------------------
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 4, 0, 4)
        header_layout.setSpacing(14)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Left Side Group (Cohesive group for Icon, Name, and Type)
        left_group_layout = QHBoxLayout()
        left_group_layout.setContentsMargins(0, 0, 0, 0)
        left_group_layout.setSpacing(14)
        left_group_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.icon_widget = LargeDeviceIconWidget()
        left_group_layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_device_name = QLabel("No Device Connected")
        self.lbl_device_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 13px; font-weight: 800;")
        self.lbl_device_name.setWordWrap(True)
        
        self.lbl_device_type = QLabel("Waiting for connection...")
        self.lbl_device_type.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 500;")
        
        text_layout.addWidget(self.lbl_device_name)
        text_layout.addWidget(self.lbl_device_type)
        left_group_layout.addLayout(text_layout)
        
        header_layout.addLayout(left_group_layout, 1)
        
        # Right Side (Redesigned Trust Score Indicator)
        self.badge = LiquidGlassBadge()
        header_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.badge_widget = self.badge
        self.badge_lbl = self.badge.lbl_text
        
        layout.addWidget(self.header_widget)
        
        # Main content container (visible only when device is connected)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # ----------------------------------------------------
        # SECTION 2: SPECIFICATIONS GRID (Left & Right columns side-by-side)
        # ----------------------------------------------------
        self.spec_columns_widget = QWidget()
        grid_layout_sec2 = QGridLayout(self.spec_columns_widget)
        grid_layout_sec2.setContentsMargins(0, 2, 0, 2)
        grid_layout_sec2.setHorizontalSpacing(24)
        grid_layout_sec2.setVerticalSpacing(4)
        
        self.fields = {
            "name": self.lbl_device_name
        }
        self.field_labels = []
        
        # Set column stretch for the 4-column grid (Col A: Label, Value, Col B: Label, Value)
        grid_layout_sec2.setColumnStretch(0, 3)
        grid_layout_sec2.setColumnStretch(1, 5)
        grid_layout_sec2.setColumnStretch(2, 3)
        grid_layout_sec2.setColumnStretch(3, 5)
        
        left_specs = [
            ("Manufacturer", "manufacturer"),
            ("Vendor ID", "vid"),
            ("Product ID", "pid"),
            ("Serial Number", "serial"),
            ("USB Type", "usb_type"),
            ("Capacity", "capacity"),
            ("Used Space", "used_space"),
            ("Free Space", "free_space"),
        ]
        
        right_specs = [
            ("File System", "file_system"),
            ("Encryption", "encryption"),
            ("Power", "power"),
            ("USB Version", "usb_version"),
            ("USB Port", "port"),
            ("Connected Time", "conn_time"),
            ("Active Time", "timer"),
            ("Fingerprint", "fingerprint"),
        ]
        
        for idx, (label, key) in enumerate(left_specs):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 600;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            val = QLabel("N/A")
            val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
            val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            grid_layout_sec2.addWidget(lbl, idx, 0)
            grid_layout_sec2.addWidget(val, idx, 1)
            
            self.fields[key] = val
            self.field_labels.append((lbl, val))
            
        for idx, (label, key) in enumerate(right_specs):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 600;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            val = QLabel("N/A")
            val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
            val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            grid_layout_sec2.addWidget(lbl, idx, 2)
            grid_layout_sec2.addWidget(val, idx, 3)
            
            self.fields[key] = val
            self.field_labels.append((lbl, val))
            
        # Hidden/dummy compatibility fields & panels
        self.fields["speed"] = QLabel()
        self.port_block_widget = DummyPortBlockWidget(self.fields["port"], self.fields["speed"])
        self.fp_panel = DummyFingerprintPanel(self.fields["fingerprint"])
        
        content_layout.addWidget(self.spec_columns_widget)
        layout.addWidget(self.content_widget)
        
        # Standard placeholder widget
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setContentsMargins(0, 8, 0, 8)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_placeholder_main = QLabel("No Device Connected")
        self.lbl_placeholder_main.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_placeholder_sub = QLabel("Waiting for USB Device...")
        self.lbl_placeholder_sub.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px;")
        
        placeholder_layout.addWidget(self.lbl_placeholder_main, 0, Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.lbl_placeholder_sub, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder_widget)
        
        # Compatibility/legacy alias variables
        self.grid_widget = self.content_widget
        self.grid_layout = grid_layout_sec2
        
        self.reset()
        theme_manager.theme_changed.connect(self.update_theme_styles)
        
    def reset(self):
        self.content_widget.hide()
        self.header_widget.hide()
        self.placeholder_widget.show()
        self.badge.set_status("None")
        self.badge.hide()
        for key, val in self.fields.items():
            if key == "name":
                val.setText("No Device Connected")
            else:
                val.setText("N/A")
        self.lbl_device_type.setText("Waiting for connection...")
        self.icon_widget.set_category("Unknown Device")
        self.fp_panel.set_fingerprint("N/A")
        
    def update_device(self, dev, conn_time, authorized=True):
        self.placeholder_widget.hide()
        self.header_widget.show()
        self.content_widget.show()
        
        if not authorized:
            self.badge.set_status("Blocked")
            self.badge.show()
        else:
            if dev.get("name") in TRUSTED_DEVICES:
                self.badge.set_status("Trusted")
            else:
                self.badge.set_status("Unknown")
            self.badge.show()
            
        self.fields["name"].setText(dev.get("name", "Unknown"))
        self.lbl_device_type.setText(dev.get("category", "USB Peripheral"))
        self.icon_widget.set_category(dev.get("category", "Unknown Device"))
        
        self.fields["manufacturer"].setText(dev.get("manufacturer", "Unknown"))
        self.fields["vid"].setText(dev.get("vid", "N/A"))
        self.fields["pid"].setText(dev.get("pid", "N/A"))
        self.fields["serial"].setText(dev.get("serial", "N/A"))
        
        self.fields["usb_type"].setText(dev.get("classification", dev.get("category", "Mass Storage")))
        
        is_bad = dev.get("is_bad", False)
        self.fields["encryption"].setText(str(dev.get("encryption", "UNKNOWN")))
        
        usb_ver = dev.get("usb_version", "UNKNOWN")
        self.fields["power"].setText(str(dev.get("power", "UNKNOWN")))
        
        self.fields["usb_version"].setText(usb_ver)
        
        self.fields["port"].setText(str(dev.get("port", "UNKNOWN")))
        self.fields["speed"].setText(str(dev.get("speed", "UNKNOWN")))
        self.fields["capacity"].setText(dev.get("capacity", "N/A"))
        self.fields["used_space"].setText(dev.get("used_space", "N/A"))
        self.fields["free_space"].setText(dev.get("free_space", "N/A"))
        self.fields["file_system"].setText(dev.get("file_system", "N/A"))
        self.fields["conn_time"].setText(conn_time)
        self.fields["timer"].setText("00:00:00")
        
        self.fp_panel.set_fingerprint(str(dev.get("fingerprint", "UNKNOWN")))
        
    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_placeholder_main.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_placeholder_sub.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px;")
        self.lbl_device_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 13px; font-weight: 800;")
        self.lbl_device_type.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 500;")
        
        self.setStyleSheet(f"""
            QFrame#deviceInfoCard {{
                background-color: transparent;
                border: none;
            }}
        """)
        for lbl, val in self.field_labels:
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 600;")
            val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold;")

class StorageInformationCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        self.lbl_title = QLabel("STORAGE INFORMATION")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        # Placeholder Widget
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setContentsMargins(0, 10, 0, 10)
        self.lbl_placeholder = QLabel("No Storage Device Connected")
        self.lbl_placeholder.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 12px; font-style: italic;")
        placeholder_layout.addWidget(self.lbl_placeholder, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder_widget)
        
        # Stats Widget
        self.stats_widget = QWidget()
        stats_layout_inner = QVBoxLayout(self.stats_widget)
        stats_layout_inner.setContentsMargins(0, 0, 0, 0)
        stats_layout_inner.setSpacing(10)
        
        self.stats_layout = QHBoxLayout()
        self.lbl_capacity = QLabel("Capacity: N/A")
        self.lbl_used = QLabel("Used: N/A")
        self.lbl_free = QLabel("Free: N/A")
        
        for lbl in [self.lbl_capacity, self.lbl_used, self.lbl_free]:
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            self.stats_layout.addWidget(lbl)
            
        stats_layout_inner.addLayout(self.stats_layout)
        
        bar_label_layout = QHBoxLayout()
        self.lbl_usage_title = QLabel("Storage Used")
        self.lbl_usage_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
        
        self.lbl_percentage = QLabel("0%")
        self.lbl_percentage.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
        
        bar_label_layout.addWidget(self.lbl_usage_title)
        bar_label_layout.addStretch()
        bar_label_layout.addWidget(self.lbl_percentage)
        stats_layout_inner.addLayout(bar_label_layout)
        
        self.progress_bar = GlassProgressBar()
        stats_layout_inner.addWidget(self.progress_bar)
        
        layout.addWidget(self.stats_widget)
        
        self.reset()
        theme_manager.theme_changed.connect(self.update_theme_styles)
        
    def enterEvent(self, event):
        # Override to remove hover animation
        pass

    def leaveEvent(self, event):
        # Override to remove hover animation
        pass
        
    def reset(self):
        self.placeholder_widget.show()
        self.stats_widget.hide()
        self.lbl_capacity.setText("Capacity: N/A")
        self.lbl_used.setText("Used: N/A")
        self.lbl_free.setText("Free: N/A")
        self.lbl_percentage.setText("0%")
        self.progress_bar.setValue(0)
        
    def update_storage(self, dev):
        cap_str = dev.get("capacity", "N/A")
        if cap_str == "N/A" or not cap_str:
            self.reset()
            return
            
        self.placeholder_widget.hide()
        self.stats_widget.show()
        
        used_str = dev.get("used_space", "0 GB")
        free_str = dev.get("free_space", "N/A")
        
        self.lbl_capacity.setText(f"Capacity: {cap_str}")
        self.lbl_used.setText(f"Used: {used_str}")
        self.lbl_free.setText(f"Free: {free_str}")
        
        try:
            if cap_str == "N/A" or ("GB" not in cap_str and "TB" not in cap_str):
                percent = 0
            else:
                cap_val = float(cap_str.split()[0])
                if "TB" in cap_str:
                    cap_val *= 1024
                used_val = float(used_str.split()[0])
                if "TB" in used_str:
                    used_val *= 1024
                percent = int((used_val / cap_val) * 100) if cap_val > 0 else 0
        except Exception:
            percent = 0
            
        self.progress_anim = QVariantAnimation(self)
        self.progress_anim.setDuration(800)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(percent)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.progress_anim.valueChanged.connect(self._on_anim_val)
        self.progress_anim.start()
        
    def _on_anim_val(self, val):
        self.progress_bar.setValue(val)
        self.lbl_percentage.setText(f"{int(val)}%")

    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_placeholder.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 12px; font-style: italic;")
        for lbl in [self.lbl_capacity, self.lbl_used, self.lbl_free]:
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
        self.lbl_usage_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold;")
        self.lbl_percentage.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")

class ShieldServiceIcon(QWidget):
    def __init__(self, service_type, size=14, parent=None):
        super().__init__(parent)
        self.service_type = service_type
        self.size = size
        self.setFixedSize(size, size)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(theme_manager.get_color("text_secondary"))
        pen = QPen(color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = min(cx, cy) - 1.0
        
        if self.service_type == "USB Monitoring":
            # Draw a premium device/USB-like connection node icon
            painter.drawEllipse(QRectF(cx - 1.2, cy - 4.0, 2.4, 2.4)) # center circle
            painter.drawLine(QPointF(cx, cy - 1.5), QPointF(cx, cy + 4.0)) # main trunk
            painter.drawLine(QPointF(cx, cy + 1.0), QPointF(cx - 3.0, cy - 1.5)) # left branch
            painter.drawLine(QPointF(cx, cy + 2.0), QPointF(cx + 3.0, cy + 0.0)) # right branch
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(cx - 4.0, cy - 2.5, 2.0, 2.0)) # left node square
            painter.drawEllipse(QRectF(cx + 2.0, cy - 1.0, 2.0, 2.0)) # right node circle
        elif self.service_type == "Malware Engine":
            # Draw a cyber bug/scanning insect
            # Body line
            painter.drawLine(QPointF(cx, cy - 4.0), QPointF(cx, cy + 4.0))
            # Head
            painter.drawEllipse(QRectF(cx - 1.5, cy - 4.0, 3.0, 2.4))
            # Back/Shell
            painter.drawArc(QRectF(cx - 3.5, cy - 1.5, 7.0, 5.0), 0, 180 * 16)
            # Legs
            painter.drawLine(QPointF(cx - 2.5, cy - 0.5), QPointF(cx - 5.0, cy - 1.8))
            painter.drawLine(QPointF(cx + 2.5, cy - 0.5), QPointF(cx + 5.0, cy - 1.8))
            painter.drawLine(QPointF(cx - 3.0, cy + 1.2), QPointF(cx - 5.5, cy + 1.2))
            painter.drawLine(QPointF(cx + 3.0, cy + 1.2), QPointF(cx + 5.5, cy + 1.2))
            painter.drawLine(QPointF(cx - 2.5, cy + 2.8), QPointF(cx - 5.0, cy + 4.0))
            painter.drawLine(QPointF(cx + 2.5, cy + 2.8), QPointF(cx + 5.0, cy + 4.0))
        elif self.service_type == "ClamAV":
            # Draw an elegant double helix / scan node
            path = QPainterPath()
            path.moveTo(cx - 3.0, cy - 4.0)
            path.cubicTo(cx - 1.0, cy - 4.0, cx + 1.0, cy + 4.0, cx + 3.0, cy + 4.0)
            path.moveTo(cx + 3.0, cy - 4.0)
            path.cubicTo(cx + 1.0, cy - 4.0, cx - 1.0, cy + 4.0, cx - 3.0, cy + 4.0)
            painter.drawPath(path)
            # Connection rungs
            painter.drawLine(QPointF(cx - 2.0, cy - 2.0), QPointF(cx + 2.0, cy - 2.0))
            painter.drawLine(QPointF(cx - 0.8, cy), QPointF(cx + 0.8, cy))
            painter.drawLine(QPointF(cx - 2.0, cy + 2.0), QPointF(cx + 2.0, cy + 2.0))
        elif self.service_type == "YARA":
            # Draw a sleek magnifying glass / search icon
            painter.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, 2 * r - 3, 2 * r - 3))
            painter.drawLine(QPointF(cx + 1.2, cy + 1.2), QPointF(cx + r - 0.5, cy + r - 0.5))
        elif self.service_type == "Database":
            # Draw database cylinder stack
            painter.drawEllipse(QRectF(cx - 4.0, cy - 4.0, 8.0, 2.6)) # top ellipse
            painter.drawArc(QRectF(cx - 4.0, cy - 1.0, 8.0, 2.6), 180 * 16, 180 * 16) # middle arc
            painter.drawArc(QRectF(cx - 4.0, cy + 2.0, 8.0, 2.6), 180 * 16, 180 * 16) # bottom arc
            painter.drawLine(QPointF(cx - 4.0, cy - 2.7), QPointF(cx - 4.0, cy + 3.3)) # left border
            painter.drawLine(QPointF(cx + 4.0, cy - 2.7), QPointF(cx + 4.0, cy + 3.3)) # right border
        elif self.service_type == "Internet":
            # Draw internet / globe node
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawEllipse(QRectF(cx - 2.0, cy - r, 4.0, 2 * r)) # vertical longitudinal ellipse
            painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy)) # equator

class ShieldPulseIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.pulse = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40) # Subtle premium speed
        
    def tick(self):
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        
        # Dynamic theme accent color
        accent_color = QColor(theme_manager.get_color("accent"))
        
        # Subtle glow ring
        glow = QColor(accent_color)
        glow_alpha = max(0, min(255, int(40 + 50 * math.sin(self.pulse))))
        glow.setAlpha(glow_alpha)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        r_glow = 4.0 + 1.2 * math.sin(self.pulse)
        painter.drawEllipse(QPointF(cx, cy), r_glow, r_glow)
        
        # Solid center dot
        painter.setBrush(QBrush(accent_color))
        painter.drawEllipse(QPointF(cx, cy), 2.0, 2.0)

class ShieldRowWidget(QWidget):
    def __init__(self, service_type, val_text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22) # Extremely compact and clean height
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Left side: Name (Icon removed as requested)
        self.lbl_name = QLabel(service_type)
        self.lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_name.setFixedWidth(140) # Keep name column consistent width to align status
        
        layout.addWidget(self.lbl_name)
        
        # Right side: Pulsing dot and status text
        self.pulse_indicator = ShieldPulseIndicator()
        self.lbl_val = QLabel(val_text)
        self.lbl_val.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.pulse_indicator)
        layout.addWidget(self.lbl_val)
        layout.addStretch()
        
        self.hover_active = False
        
    def enterEvent(self, event):
        self.hover_active = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.hover_active = False
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.hover_active:
            bg_color = QColor(255, 255, 255, 6) if theme_manager.current_theme == "dark" else QColor(0, 0, 0, 6)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(self.rect()), 4, 4)

class SystemHealthCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        
        self.lbl_title = QLabel("SYSTEM SHIELD INTEGRITY")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        items = [
            ("USB Monitoring", "Active"),
            ("Malware Engine", "Running"),
            ("ClamAV", "Running"),
            ("YARA", "Loaded"),
            ("Database", "Updated Today"),
            ("Internet", "Connected"),
        ]
        
        self.rows = []
        
        for idx, (label, val) in enumerate(items):
            row_widget = ShieldRowWidget(label, val)
            layout.addWidget(row_widget)
            self.rows.append((row_widget.lbl_name, row_widget.lbl_val))
            
        theme_manager.theme_changed.connect(self.update_health_theme)
        self.update_health_theme()
        
    def update_health_theme(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        for lbl_name, lbl_val in self.rows:
            lbl_name.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
            lbl_val.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")

class PulsingDotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.pulse = 0
        self.connected = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)
        
    def tick(self):
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)
        self.update()
        
    def set_connected(self, connected):
        self.connected = connected
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2, self.height() / 2
        
        accent = QColor(theme_manager.get_color("accent"))
        glow_alpha = max(0, min(255, int(80 + 70 * math.sin(self.pulse))))
        accent.setAlpha(glow_alpha)
        
        painter.setBrush(QBrush(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 6 + 2 * math.sin(self.pulse), 6 + 2 * math.sin(self.pulse))
        
        solid_color = QColor(theme_manager.get_color("accent"))
        painter.setBrush(QBrush(solid_color))
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

class LiveMonitoringPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        self.pulse_dot = PulsingDotWidget()
        layout.addWidget(self.pulse_dot)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.lbl_title = QLabel("USB MONITORING ACTIVE")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent; border: none;")
        
        self.lbl_status = QLabel("Waiting for USB Device...")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_status)
        layout.addLayout(text_layout, 1)
        
        self.setStyleSheet("background: transparent; border: none;")
        theme_manager.theme_changed.connect(self.update_theme_styles)
        
    def set_connected(self, connected, device_name="", authorized=True):
        self.pulse_dot.set_connected(connected)
        if connected:
            if device_name == "Evaluating peripheral...":
                self.lbl_title.setText("EVALUATING PORT INTRUSION...")
                self.lbl_status.setText("Checking descriptors...")
            elif not authorized:
                self.lbl_title.setText("THREAT MITIGATED: BLOCKED")
                self.lbl_status.setText("Device Isolated")
            else:
                self.lbl_title.setText("MONITORING CONNECTED DEVICE")
                self.lbl_status.setText(f"Active: {device_name}")
        else:
            self.lbl_title.setText("USB MONITORING ACTIVE")
            self.lbl_status.setText("Waiting for USB Device...")

    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px; background: transparent; border: none;")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold; background: transparent; border: none;")

class NotificationCenter(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notificationCenter")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)
        
        # Compatibility console layout (not added to main layout)
        self.console = QVBoxLayout()
        
        # --- SECTION: DEVICE ACTIVITY ---
        self.activity_frame = QFrame()
        self.activity_frame.setObjectName("activityFrame")
        act_layout = QHBoxLayout(self.activity_frame)
        act_layout.setContentsMargins(8, 6, 8, 6)
        act_layout.setSpacing(8)
        
        self.lbl_act_indicator = QLabel("●")
        self.lbl_act_indicator.setStyleSheet("color: #8898a6; font-size: 11px; background: transparent; border: none;")
        
        self.lbl_act_title = QLabel("Device Activity Status:")
        self.lbl_act_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; background: transparent; border: none;")
        
        self.lbl_act_status = QLabel("Idle")
        self.lbl_act_status.setStyleSheet("color: #8898a6; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        act_layout.addWidget(self.lbl_act_indicator)
        act_layout.addWidget(self.lbl_act_title)
        act_layout.addWidget(self.lbl_act_status, 1)
        layout.addWidget(self.activity_frame)
        
        # --- SECTION: MINI ACTIVITY TIMELINE ---
        self.timeline_frame = QFrame()
        self.timeline_frame.setObjectName("timelineFrame")
        time_layout = QVBoxLayout(self.timeline_frame)
        time_layout.setContentsMargins(8, 6, 8, 6)
        time_layout.setSpacing(4)
        
        self.lbl_time_title = QLabel("MINI ACTIVITY TIMELINE")
        self.lbl_time_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 9px; font-weight: 800; letter-spacing: 0.5px; background: transparent; border: none;")
        time_layout.addWidget(self.lbl_time_title)
        
        self.timeline_rows_layout = QVBoxLayout()
        self.timeline_rows_layout.setSpacing(4)
        time_layout.addLayout(self.timeline_rows_layout)
        
        layout.addWidget(self.timeline_frame)
        
        # Glow timer for active status
        self.act_glow_timer = QTimer(self)
        self.act_glow_timer.timeout.connect(self.animate_act_status)
        self.act_glow_timer.start(50)
        self.glow_phase = 0.0
        
        self.logs = []
        self.timeline_events = [] # List of dicts: {"time": "hh:mm", "text": "Connected"}
        
        self.add_timeline_event(QTime.currentTime().toString("hh:mm"), "Ready")
        
        theme_manager.theme_changed.connect(self.update_log_styles)
        self.update_log_styles()
        
    def set_activity_status(self, status):
        display_status = status
        if status == "Completed...":
            display_status = "Completed"
            
        self.lbl_act_status.setText(display_status)
        
        if display_status == "Idle":
            color = "#8A7568"
        elif display_status == "Reading Files...":
            color = "#C98A5E"
        elif display_status == "Scanning...":
            color = "#D97F4A"
        elif display_status == "Analyzing...":
            color = "#D97F4A"
        elif display_status in ["Completed", "Completed..."]:
            color = "#D97F4A"
        else:
            color = theme_manager.get_color("accent")
            
        self.lbl_act_status.setStyleSheet(f"color: {color}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        self.lbl_act_indicator.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent; border: none;")
        
        # Smooth opacity transition
        effect = QGraphicsOpacityEffect(self.lbl_act_status)
        self.lbl_act_status.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.lbl_act_status._fade_anim = anim
        anim.start()
        
    def animate_act_status(self):
        status = self.lbl_act_status.text()
        if status in ["Reading Files...", "Scanning...", "Analyzing..."]:
            self.glow_phase = (self.glow_phase + 0.1) % (2 * math.pi)
            opacity = 0.5 + 0.5 * math.sin(self.glow_phase)
            
            if status == "Reading Files...":
                color_rgba = f"rgba(201, 138, 94, {opacity:.2f})"
            elif status == "Scanning...":
                color_rgba = f"rgba(217, 127, 74, {opacity:.2f})"
            else:
                color_rgba = f"rgba(217, 127, 74, {opacity:.2f})"
                
            self.lbl_act_status.setStyleSheet(f"color: {color_rgba}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
            self.lbl_act_indicator.setStyleSheet(f"color: {color_rgba}; font-size: 11px; background: transparent; border: none;")
            
    def add_timeline_event(self, time_str, event_text):
        self.timeline_events.append({"time": time_str, "text": event_text})
        if len(self.timeline_events) > 3:
            self.timeline_events.pop(0)
        self.update_timeline_ui()
        
    def update_timeline_ui(self):
        while self.timeline_rows_layout.count() > 0:
            item = self.timeline_rows_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
                
        for ev in self.timeline_events:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)
            
            lbl_time = QLabel(ev["time"])
            lbl_time.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
            
            lbl_dot = QLabel("•")
            color_accent = theme_manager.get_color("accent")
            if ev["text"] == "Connected":
                dot_color = "#C98A5E"
            elif ev["text"] == "Authorized":
                dot_color = "#D97F4A"
            elif ev["text"] == "Ready":
                dot_color = color_accent
            elif ev["text"] == "Blocked":
                dot_color = "#B5522B"
            else:
                dot_color = theme_manager.get_color("text_secondary")
                
            lbl_dot.setStyleSheet(f"color: {dot_color}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            
            lbl_text = QLabel(ev["text"])
            lbl_text.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
            
            row_layout.addWidget(lbl_time)
            row_layout.addWidget(lbl_dot)
            row_layout.addWidget(lbl_text, 1)
            
            self.timeline_rows_layout.addWidget(row)
            
            effect = QGraphicsOpacityEffect(row)
            row.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            row._fade_anim = anim
            anim.start()
            
    def add_log(self, msg):
        time_str = QTime.currentTime().toString("hh:mm:ss")
        log_text = f"[{time_str}] {msg}"
        
        lbl = QLabel(log_text)
        lbl.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'JetBrains Mono'; font-size: 9px; background: transparent; border: none;")
        lbl.setWordWrap(True)
        
        self.console.addWidget(lbl)
        self.logs.append(lbl)
        
        if len(self.logs) > 5:
            oldest = self.logs.pop(0)
            self.console.removeWidget(oldest)
            oldest.deleteLater()
            
        time_hm = QTime.currentTime().toString("hh:mm")
        event_name = None
        
        if "insertion detected" in msg:
            event_name = "Connected"
            self.set_activity_status("Reading Files...")
            QTimer.singleShot(600, lambda: self.set_activity_status("Scanning..."))
            QTimer.singleShot(1200, lambda: self.set_activity_status("Analyzing..."))
        elif "Access granted" in msg:
            event_name = "Authorized"
        elif "Scan complete" in msg or "Scan completed" in msg:
            event_name = "Ready"
            self.set_activity_status("Completed...")
        elif "ejected" in msg:
            event_name = "Ejected"
            self.set_activity_status("Idle")
        elif "Blocked" in msg:
            event_name = "Blocked"
            self.set_activity_status("Idle")
            
        if event_name:
            self.add_timeline_event(time_hm, event_name)
            
    def update_log_styles(self):
        for lbl in self.logs:
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'JetBrains Mono'; font-size: 9px; background: transparent; border: none;")
            
        self.activity_frame.setStyleSheet("""
            QFrame#activityFrame {
                background: transparent;
                border: none;
            }
        """)
        
        self.timeline_frame.setStyleSheet("""
            QFrame#timelineFrame {
                background: transparent;
                border: none;
            }
        """)
        self.lbl_act_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; background: transparent; border: none;")
        self.lbl_time_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 9px; font-weight: 800; letter-spacing: 0.5px; background: transparent; border: none;")

class SecurityRecommendationCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        self.lbl_title = QLabel("SECURITY RECOMMENDATION")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        self.lbl_rec = QLabel("Waiting for a USB Device. Insert a USB storage device to begin monitoring.")
        self.lbl_rec.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_rec.setWordWrap(True)
        layout.addWidget(self.lbl_rec)
        
        self.lbl_details = QLabel("All ports are actively audited and sandboxed.")
        self.lbl_details.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_details.setWordWrap(True)
        layout.addWidget(self.lbl_details)
        
        theme_manager.theme_changed.connect(self.update_theme_styles)
        
    def reset(self):
        self.lbl_rec.setText("Waiting for a USB Device. Insert a USB storage device to begin monitoring.")
        self.lbl_details.setText("All ports are actively audited and sandboxed.")
        self.update_theme_styles()
        
    def update_recommendation(self, dev, authorized):
        if not authorized:
            self.lbl_rec.setText("CRITICAL: Potentially suspicious device blocked.")
            self.lbl_details.setText("Threat signature matched. Ensure peripheral is inspected before authorization.")
        else:
            self.lbl_rec.setText("Device appears safe. Recommended: Run Quick Scan.")
            self.lbl_details.setText("No immediate active malware footprints detected during port evaluation.")
        self.update_theme_styles()
            
    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_rec.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_details.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")

class LastScanSummaryCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        self.lbl_title = QLabel("LAST SCAN SUMMARY")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(6)
        
        # Balance columns without stretching to the two ends
        self.grid_layout.setColumnMinimumWidth(0, 100)
        self.grid_layout.setColumnMinimumWidth(2, 100)
        self.grid_layout.setColumnStretch(0, 0)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 0)
        self.grid_layout.setColumnStretch(3, 1)
        
        self.fields = {}
        self.field_labels = []
        
        fields_config = [
            ("Date:", "date", "15-Jul-2026", 0, 0),
            ("Time:", "time", "10:45 AM", 0, 2),
            ("Device:", "device", "SanDisk Ultra USB 3.0", 1, 0),
            ("Duration:", "duration", "14 Seconds", 1, 2),
            ("Files Scanned:", "files", "1,248", 2, 0),
            ("Threats Found:", "threats", "0", 2, 2),
            ("Risk Score:", "risk_score", "0%", 3, 0),
            ("Status:", "status", "Completed Successfully", 3, 2),
        ]
        
        for (label_text, key, default_val, r_idx, c_idx) in fields_config:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-weight: 600;")
            
            val = QLabel(default_val)
            val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            val.setWordWrap(True)
            val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            self.grid_layout.addWidget(lbl, r_idx, c_idx)
            self.grid_layout.addWidget(val, r_idx, c_idx + 1)
            
            self.fields[key] = val
            self.field_labels.append((lbl, val))
            
        layout.addWidget(self.grid_widget)
        
        theme_manager.theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()
        
    def reset(self):
        self.fields["date"].setText("15-Jul-2026")
        self.fields["time"].setText("10:45 AM")
        self.fields["device"].setText("SanDisk Ultra USB 3.0")
        self.fields["files"].setText("1,248")
        self.fields["threats"].setText("0")
        self.fields["risk_score"].setText("0%")
        self.fields["duration"].setText("14 Seconds")
        self.fields["status"].setText("Completed Successfully")
        self.update_theme_styles()
        
    def update_scan(self, scan_data):
        date_val = scan_data.get("date", "Today")
        if date_val == "Today":
            date_val = QDateTime.currentDateTime().toString("dd-MMM-yyyy")
        self.fields["date"].setText(date_val)
        
        time_val = scan_data.get("time")
        if not time_val:
            time_val = QTime.currentTime().toString("hh:mm AP")
        self.fields["time"].setText(time_val)
        
        device_name = scan_data.get("device")
        if not device_name:
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, 'connected_device'):
                    if parent.connected_device:
                        device_name = parent.connected_device.get('name', 'N/A')
                    break
                parent = parent.parent()
            if not device_name:
                device_name = "SanDisk Ultra USB 3.0"
        self.fields["device"].setText(device_name)
        
        files = scan_data.get("files", 1248)
        if isinstance(files, int):
            files_str = f"{files:,}"
        else:
            files_str = str(files)
        self.fields["files"].setText(files_str)
        
        threats = int(scan_data.get("threats", 0) or 0)
        self.fields["threats"].setText(str(threats))

        risk_score = max(0, min(100, int(scan_data.get("risk_score", 0) or 0)))
        self.fields["risk_score"].setText(f"{risk_score}/100")
        status = scan_data.get("status")
        if not status:
            status = "Threat Detected" if threats > 0 else "Completed Successfully"
        self.fields["status"].setText(str(status))
            
        dur = scan_data.get("duration", "14 Seconds")
        self.fields["duration"].setText(dur)
        
        self.update_theme_styles()
        
    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        for lbl, val in self.field_labels:
            lbl.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-weight: 600;")
            val.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            
        threats_text = self.fields["threats"].text()
        try:
            threats_count = int(threats_text.replace(",", ""))
        except ValueError:
            threats_count = 0
            
        if threats_count > 0:
            self.fields["threats"].setStyleSheet("color: #B5522B; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            self.fields["status"].setStyleSheet("color: #B5522B; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            self.fields["risk_score"].setStyleSheet("color: #B5522B; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
        else:
            self.fields["threats"].setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            self.fields["status"].setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            self.fields["risk_score"].setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")

class TrustedDevicesCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)
        
        self.lbl_title = QLabel("TRUSTED DEVICES")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        self.device_labels = []
        for dev_name in ["SanDisk Ultra USB 3.0", "Kingston DataTraveler", "Samsung T7 SSD"]:
            lbl = QLabel(f"✓  {dev_name}")
            lbl.setStyleSheet(f"color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")
            layout.addWidget(lbl)
            self.device_labels.append(lbl)
            
        self.lbl_more = QLabel("+2 More Trusted Devices")
        self.lbl_more.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-style: italic;")
        layout.addWidget(self.lbl_more)
        
        theme_manager.theme_changed.connect(self.update_theme_styles)
        
    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_more.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px; font-style: italic;")
        for lbl in self.device_labels:
            lbl.setStyleSheet(f"color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold;")

class SparklineGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = [18, 35, 24, 67, 42, 30, 15]
        self.anim_progress = 0.0  # 0.0 to 1.0
        self.setMinimumHeight(45)
        self.setMaximumHeight(45)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(25)  # ~40 FPS for super smooth draw
        
    def on_timer(self):
        if self.anim_progress < 1.0:
            self.anim_progress += 0.03
            if self.anim_progress > 1.0:
                self.anim_progress = 1.0
                self.timer.stop()
            self.update()
            
    def reset_animation(self):
        self.anim_progress = 0.0
        self.timer.start(25)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.data:
            return
            
        width = self.width()
        height = self.height()
        
        # Calculate coordinates
        points = []
        x_step = width / (len(self.data) - 1) if len(self.data) > 1 else width
        
        max_val = 100
        min_val = 0
        val_range = max_val - min_val if max_val != min_val else 1
        
        for i, val in enumerate(self.data):
            x = i * x_step
            # leave margins for points
            y = height - 6 - ((val - min_val) / val_range) * (height - 12)
            points.append(QPointF(x, y))
            
        path = QPainterPath()
        if points:
            path.moveTo(points[0])
            for i in range(1, len(points)):
                p0 = points[i-1]
                p1 = points[i]
                dx = p1.x() - p0.x()
                c1 = QPointF(p0.x() + dx/2, p0.y())
                c2 = QPointF(p0.x() + dx/2, p1.y())
                path.cubicTo(c1, c2, p1)
                
        painter.save()
        clip_rect = QRectF(0, 0, width * self.anim_progress, height)
        painter.setClipRect(clip_rect)
        
        # Draw soft gradient under the curve
        gradient_path = QPainterPath(path)
        gradient_path.lineTo(points[-1].x(), height)
        gradient_path.lineTo(points[0].x(), height)
        gradient_path.closeSubpath()
        
        grad = QLinearGradient(0, 0, 0, height)
        accent_color = QColor(theme_manager.get_color('accent'))
        grad.setColorAt(0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 35))
        grad.setColorAt(1, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(gradient_path)
        
        # Draw subtle glowing pen backing
        pen_glow = QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 75), 3.0)
        painter.setPen(pen_glow)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Draw solid crisp core line
        pen_core = QPen(accent_color, 1.5)
        painter.setPen(pen_core)
        painter.drawPath(path)
        
        # Draw glowing points
        for pt in points:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 90)))
            painter.drawEllipse(pt, 3.5, 3.5)
            
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(pt, 1.5, 1.5)
            
        painter.restore()

class CompactStatRow(QWidget):
    def __init__(self, icon, label, value, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.lbl_icon_label = QLabel(f"{icon}  {label}")
        self.lbl_icon_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(self.lbl_icon_label)
        layout.addStretch()
        layout.addWidget(self.lbl_value)
        
    def update_theme_styles(self):
        self.lbl_icon_label.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        self.lbl_value.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")

class CompactStatusChip(QFrame):
    def __init__(self, text="● Recent Scan Clean", color="#D97F4A", parent=None):
        super().__init__(parent)
        self.setObjectName("compactStatusChip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_text = QLabel(text)
        self.lbl_text.setStyleSheet(f"color: {color}; font-family: 'Inter'; font-size: 9px; font-weight: 800; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_text)
        
        self.color = color
        self.update_style()
        theme_manager.theme_changed.connect(self.update_style)
        
    def update_style(self):
        color_str = self.color.lstrip('#')
        if len(color_str) == 6:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
        else:
            r, g, b = 217, 127, 74
            
        bg = f"rgba({r}, {g}, {b}, 0.08)" if theme_manager.current_theme == "dark" else f"rgba({r}, {g}, {b}, 0.05)"
        border = f"rgba({r}, {g}, {b}, 0.2)" if theme_manager.current_theme == "dark" else f"rgba({r}, {g}, {b}, 0.15)"
        
        self.setStyleSheet(f"""
            #compactStatusChip {{
                background-color: {bg};
                border: 0.5px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

class ScanHistoryOverviewCard(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scanHistoryOverviewCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)
        
        self.lbl_title = QLabel("SCAN HISTORY OVERVIEW")
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)
        
        self.sparkline = SparklineGraph(self)
        layout.addWidget(self.sparkline)
        
        self.stat_rows = []
        
        self.row_last_scan = CompactStatRow("⏱", "Last Scan", "UNAVAILABLE", self)
        layout.addWidget(self.row_last_scan)
        self.stat_rows.append(self.row_last_scan)
        
        self.row_recent_risk = CompactStatRow("☣", "Recent Risk", "UNAVAILABLE", self)
        layout.addWidget(self.row_recent_risk)
        self.stat_rows.append(self.row_recent_risk)
        
        self.row_weekly_scans = CompactStatRow("📊", "Weekly Scans", "18", self)
        layout.addWidget(self.row_weekly_scans)
        self.stat_rows.append(self.row_weekly_scans)
        
        self.status_container = QHBoxLayout()
        self.status_container.setContentsMargins(0, 2, 0, 0)
        self.status_chip = CompactStatusChip("● NO RECENT SCAN", "#808080", self)
        self.status_container.addWidget(self.status_chip)
        self.status_container.addStretch()
        layout.addLayout(self.status_container)
        
        theme_manager.theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()
        
    def update_theme_styles(self):
        self.lbl_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        
        for row in self.stat_rows:
            row.update_theme_styles()
            
        self.setStyleSheet(f"""
            QFrame#scanHistoryOverviewCard {{
                background-color: transparent;
                border: none;
            }}
        """)
        
    def enterEvent(self, event):
        self.sparkline.reset_animation()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        super().leaveEvent(event)

class PremiumDateTimeWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("premiumDateTimeWidget")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_day = QLabel()
        self.lbl_day.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_date = QLabel()
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_time = QLabel()
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.lbl_day)
        layout.addWidget(self.lbl_date)
        layout.addWidget(self.lbl_time)
        
        self.update_style()
        theme_manager.theme_changed.connect(self.update_style)
        
    def setText(self, text_ignored):
        current_dt = QDateTime.currentDateTime()
        self.lbl_day.setText(current_dt.toString("dddd").upper())
        self.lbl_date.setText(current_dt.toString("d MMMM yyyy"))
        self.lbl_time.setText(current_dt.toString("hh:mm:ss AP"))
        
    def update_style(self):
        accent = theme_manager.get_color('accent')
        text_primary = theme_manager.get_color('text_primary')
        text_secondary = theme_manager.get_color('text_secondary')
        
        self.lbl_day.setStyleSheet(f"""
            QLabel {{
                color: {text_secondary};
                font-family: 'Inter';
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 1.2px;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
        """)
        
        self.lbl_date.setStyleSheet(f"""
            QLabel {{
                color: {text_primary};
                font-family: 'Inter';
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
        """)
        
        self.lbl_time.setStyleSheet(f"""
            QLabel {{
                color: {accent};
                font-family: 'JetBrains Mono';
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
        """)
        
        bg = "rgba(255, 255, 255, 0.04)" if theme_manager.current_theme == "dark" else "rgba(0, 0, 0, 0.03)"
        border = "rgba(255, 255, 255, 0.08)" if theme_manager.current_theme == "dark" else "rgba(0, 0, 0, 0.06)"
        
        self.setStyleSheet(f"""
            #premiumDateTimeWidget {{
                background-color: {bg};
                border: 0.5px solid {border};
                border-radius: 8px;
            }}
        """)

class SystemTrayDropdown(GlassCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemTrayDropdown")
        self.setFixedSize(300, 440)
        self.hide()
        
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.opacity_changed = None  # placeholder for property
        self.opacity_effect.setOpacity(0.0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)
        header_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_icon = VectorIconWidget("status", size=14)
        self.lbl_header = QLabel("SYSTEM STATUS")
        self.lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_row.addWidget(self.status_icon)
        header_row.addWidget(self.lbl_header)
        layout.addLayout(header_row)
        
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)
        
        # Wi-Fi Section
        wifi_layout = QHBoxLayout()
        self.wifi_icon = VectorIconWidget("wifi", size=14)
        self.lbl_wifi_title = QLabel("Wi-Fi")
        self.lbl_wifi_val = QLabel("Connected")
        wifi_layout.addWidget(self.wifi_icon)
        wifi_layout.addWidget(self.lbl_wifi_title)
        wifi_layout.addStretch()
        wifi_layout.addWidget(self.lbl_wifi_val)
        layout.addLayout(wifi_layout)
        
        wifi_detail = QHBoxLayout()
        wifi_detail.setContentsMargins(18, 0, 0, 0)
        self.lbl_ssid_lbl = QLabel("SSID")
        self.lbl_ssid_val = QLabel("USB Detector Lab")
        wifi_detail.addWidget(self.lbl_ssid_lbl)
        wifi_detail.addStretch()
        wifi_detail.addWidget(self.lbl_ssid_val)
        layout.addLayout(wifi_detail)
        
        wifi_sig = QHBoxLayout()
        wifi_sig.setContentsMargins(18, 0, 0, 0)
        self.lbl_sig_lbl = QLabel("Signal Strength")
        self.lbl_sig_val = QLabel("Excellent")
        wifi_sig.addWidget(self.lbl_sig_lbl)
        wifi_sig.addStretch()
        wifi_sig.addWidget(self.lbl_sig_val)
        layout.addLayout(wifi_sig)
        
        self.sep2 = QFrame()
        self.sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep2)
        
        # Bluetooth Section
        bt_layout = QHBoxLayout()
        self.bt_icon = VectorIconWidget("bluetooth", size=14)
        self.lbl_bt_title = QLabel("Bluetooth")
        self.lbl_bt_val = QLabel("Enabled")
        bt_layout.addWidget(self.bt_icon)
        bt_layout.addWidget(self.lbl_bt_title)
        bt_layout.addStretch()
        bt_layout.addWidget(self.lbl_bt_val)
        layout.addLayout(bt_layout)
        
        bt_detail = QHBoxLayout()
        bt_detail.setContentsMargins(18, 0, 0, 0)
        self.lbl_bt_dev = QLabel("Connected Devices")
        self.lbl_bt_dev_val = QLabel("1")
        bt_detail.addWidget(self.lbl_bt_dev)
        bt_detail.addStretch()
        bt_detail.addWidget(self.lbl_bt_dev_val)
        layout.addLayout(bt_detail)
        
        self.sep3 = QFrame()
        self.sep3.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep3)
        
        # Battery Section
        bat_layout = QHBoxLayout()
        self.bat_icon = VectorIconWidget("battery", size=14)
        self.lbl_bat_title = QLabel("Battery")
        self.lbl_bat_val = QLabel("82%")
        bat_layout.addWidget(self.bat_icon)
        bat_layout.addWidget(self.lbl_bat_title)
        bat_layout.addStretch()
        bat_layout.addWidget(self.lbl_bat_val)
        layout.addLayout(bat_layout)
        
        bat_chg = QHBoxLayout()
        bat_chg.setContentsMargins(18, 0, 0, 0)
        self.lbl_chg = QLabel("Charging")
        self.lbl_chg_val = QLabel("No")
        bat_chg.addWidget(self.lbl_chg)
        bat_chg.addStretch()
        bat_chg.addWidget(self.lbl_chg_val)
        layout.addLayout(bat_chg)
        
        bat_rem = QHBoxLayout()
        bat_rem.setContentsMargins(18, 0, 0, 0)
        self.lbl_rem = QLabel("Estimated Remaining")
        self.lbl_rem_val = QLabel("5 Hours")
        bat_rem.addWidget(self.lbl_rem)
        bat_rem.addStretch()
        bat_rem.addWidget(self.lbl_rem_val)
        layout.addLayout(bat_rem)
        
        self.sep4 = QFrame()
        self.sep4.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep4)
        
        # System Time Section
        time_layout = QHBoxLayout()
        self.time_icon = VectorIconWidget("time", size=14)
        self.lbl_time_title = QLabel("System Time")
        time_layout.addWidget(self.time_icon)
        time_layout.addWidget(self.lbl_time_title)
        layout.addLayout(time_layout)
        
        self.lbl_tray_time = QLabel("12:00:00 PM")
        self.lbl_tray_date = QLabel("Thursday, July 9, 2026")
        layout.addWidget(self.lbl_tray_time)
        layout.addWidget(self.lbl_tray_date)
        
        self.sep5 = QFrame()
        self.sep5.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep5)
        
        # Recent Notifications
        notif_layout_title = QHBoxLayout()
        self.notif_icon = VectorIconWidget("bell", size=14)
        self.lbl_notif_title = QLabel("Recent Notifications")
        notif_layout_title.addWidget(self.notif_icon)
        notif_layout_title.addWidget(self.lbl_notif_title)
        layout.addLayout(notif_layout_title)
        
        self.lbl_notifs = []
        notifs = [
            "USB Monitoring Active",
            "Database Updated Today",
            "No Critical Threats"
        ]
        for n in notifs:
            lbl_n = QLabel(f"• {n}")
            layout.addWidget(lbl_n)
            self.lbl_notifs.append(lbl_n)
            
        self.apply_theme_colors()
        theme_manager.theme_changed.connect(self.apply_theme_colors)
        
    def apply_theme_colors(self):
        accent = theme_manager.get_color('accent')
        text_pri = theme_manager.get_color('text_primary')
        text_sec = theme_manager.get_color('text_secondary')
        
        self.status_icon.set_color(accent)
        self.wifi_icon.set_color(accent)
        self.bt_icon.set_color(accent)
        self.bat_icon.set_color(accent)
        self.time_icon.set_color(accent)
        self.notif_icon.set_color(accent)
        
        self.lbl_header.setStyleSheet(f"color: {accent}; font-family: 'Inter'; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; background: transparent; border: none;")
        self.sep.setStyleSheet("color: rgba(217, 127, 74, 0.10); max-height: 1px; border: none; background: rgba(217, 127, 74, 0.10);")
        self.lbl_wifi_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        self.lbl_wifi_val.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.lbl_ssid_lbl.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; background: transparent; border: none;")
        self.lbl_ssid_val.setStyleSheet(f"color: {text_pri}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        self.lbl_sig_lbl.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; background: transparent; border: none;")
        self.lbl_sig_val.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self.lbl_bt_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        self.lbl_bt_val.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.lbl_bt_dev.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; background: transparent; border: none;")
        self.lbl_bt_dev_val.setStyleSheet(f"color: {text_pri}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self.lbl_bat_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        self.lbl_bat_val.setStyleSheet("color: #D97F4A; font-family: 'Inter'; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.lbl_chg.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; background: transparent; border: none;")
        self.lbl_chg_val.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        self.lbl_rem.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; background: transparent; border: none;")
        self.lbl_rem_val.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self.lbl_time_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        self.lbl_tray_time.setStyleSheet(f"color: {text_pri}; font-family: 'JetBrains Mono'; font-size: 10px; font-weight: bold; margin-left: 18px; background: transparent; border: none;")
        self.lbl_tray_date.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; margin-left: 18px; background: transparent; border: none;")
        
        self.lbl_notif_title.setStyleSheet(f"color: {text_pri}; font-family: 'Inter'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        for lbl_n in self.lbl_notifs:
            lbl_n.setStyleSheet(f"color: {text_sec}; font-family: 'Inter'; font-size: 10px; margin-left: 18px; background: transparent; border: none;")
            
        is_dark = (theme_manager.current_theme == "dark")
        sep_color = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.06)"
        for sep in [self.sep2, self.sep3, self.sep4, self.sep5]:
            sep.setStyleSheet(f"color: {sep_color}; max-height: 1px; border: none; background: {sep_color};")

    def update_time_and_date(self):
        curr = QDateTime.currentDateTime()
        self.lbl_tray_time.setText(curr.toString("hh:mm:ss AP"))
        self.lbl_tray_date.setText(curr.toString("dddd, MMMM d, yyyy"))

    def animate_show(self, target_pos):
        self.raise_()
        self.show()
        
        if hasattr(self, "_anim_group") and self._anim_group.state() == QPropertyAnimation.State.Running:
            self._anim_group.stop()
            
        # Slide down
        from PyQt6.QtCore import QPoint
        self.pos_anim = QPropertyAnimation(self, b"pos", self)
        self.pos_anim.setDuration(250)
        self.pos_anim.setStartValue(QPoint(target_pos.x(), target_pos.y() - 15))
        self.pos_anim.setEndValue(target_pos)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade in
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setDuration(250)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        from PyQt6.QtCore import QParallelAnimationGroup
        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self.pos_anim)
        self._anim_group.addAnimation(self.fade_anim)
        self._anim_group.start()
        
    def animate_hide(self, target_pos, callback=None):
        if hasattr(self, "_anim_group") and self._anim_group.state() == QPropertyAnimation.State.Running:
            self._anim_group.stop()
            
        from PyQt6.QtCore import QPoint
        self.pos_anim = QPropertyAnimation(self, b"pos", self)
        self.pos_anim.setDuration(200)
        self.pos_anim.setStartValue(self.pos())
        self.pos_anim.setEndValue(QPoint(target_pos.x(), target_pos.y() - 15))
        self.pos_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        from PyQt6.QtCore import QParallelAnimationGroup
        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self.pos_anim)
        self._anim_group.addAnimation(self.fade_anim)
        
        if callback:
            self._anim_group.finished.connect(callback)
        self._anim_group.finished.connect(self.hide)
        self._anim_group.start()

class DashboardSparkline(QWidget):
    def __init__(self, title, color='#25B7F3', parent=None):
        super().__init__(parent); self.title=title; self.color=QColor(color); self.values=[0]*7; self.setMinimumHeight(110)
    def set_values(self, values): self.values=list(values[-7:]) or [0]; self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(QPen(QColor('#1F3A50'),1)); r=self.rect().adjusted(8,22,-8,-8); p.drawLine(r.left(),r.bottom(),r.right(),r.bottom()); hi=max(self.values) or 1; step=r.width()/max(1,len(self.values)-1); pts=[QPointF(r.left()+i*step,r.bottom()-v/hi*r.height()) for i,v in enumerate(self.values)]; p.setPen(QPen(self.color,2));
        for a,b in zip(pts,pts[1:]): p.drawLine(a,b)
        p.setPen(QColor('#B7C0D1')); p.drawText(8,15,self.title)

class DashboardPage(QWidget):
    retry_requested = pyqtSignal()
    device_authorized = pyqtSignal(dict)
    device_blocked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.live_totals = {"devices": 0, "files": 0, "threats": 0, "quarantined": 0}

    def apply_backend_incidents(self, incidents):
        """Aggregate persisted incidents so dashboard totals never use sample data."""
        incidents = incidents or []
        devices = len({str(i.get('device_fingerprint') or i.get('fingerprint') or i.get('device_name') or i.get('incident_id')) for i in incidents})
        files = sum(int(i.get('files_scanned') or i.get('scan_summary', {}).get('files_scanned') or 0) for i in incidents)
        threats = sum(int(i.get('threats') or i.get('findings_count') or i.get('scan_summary', {}).get('threats') or 0) for i in incidents)
        quarantined = sum(int(i.get('quarantine_count') or i.get('quarantined') or 0) for i in incidents)
        self.live_totals = {"devices": devices, "files": files, "threats": threats, "quarantined": quarantined}
        if hasattr(self, 'kpi_values'):
            for key, value in self.live_totals.items(): self.kpi_values[key].setText(f'{value:,}')
            recent = incidents[-7:]; previous = incidents[-14:-7]
            def total(items, key): return sum(int(i.get(key) or i.get('scan_summary', {}).get(key) or 0) for i in items)
            for key in self.live_totals:
                rk = {'devices':'device_name','files':'files_scanned','threats':'threats','quarantined':'quarantine_count'}[key]
                rv = len({str(i.get('device_fingerprint') or i.get('device_name') or i.get('incident_id')) for i in recent}) if key=='devices' else total(recent,rk)
                pv = len({str(i.get('device_fingerprint') or i.get('device_name') or i.get('incident_id')) for i in previous}) if key=='devices' else total(previous,rk)
                delta = 0 if not pv else round((rv-pv)*100/pv)
                if key in self.kpi_trends: self.kpi_trends[key].setText(('↑' if delta>=0 else '↓') + f' {abs(delta)}% vs previous period')
        if hasattr(self, 'risk_chart'):
            self.risk_chart.set_values([int(i.get('risk') or i.get('risk_score') or 0) for i in incidents])
            self.scan_chart.set_values([int(i.get('files_scanned') or 0) for i in incidents])
            self.threat_chart.set_values([int(i.get('threats') or i.get('findings_count') or 0) for i in incidents])
        if hasattr(self, 'activity_label'):
            lines=[]
            for item in incidents[-6:][::-1]:
                stamp=str(item.get('timestamp') or item.get('completed_at') or 'Recent')[:19]
                device=item.get('device_name') or item.get('fingerprint') or 'USB device'
                verdict=item.get('verdict') or ('Threat found' if int(item.get('threats') or 0)>0 else 'Clean')
                lines.append(f'{stamp}   {device}   —   {verdict}')
            self.activity_label.setText('\n'.join(lines) if lines else 'No scan activity recorded yet.')
        if hasattr(self, 'threat_distribution'):
            counts={'Malware':0,'Suspicious':0,'PUP':0,'Other':0}
            for item in incidents:
                for finding in (item.get('findings') or item.get('threats_detail') or []):
                    kind=str(finding.get('category') or finding.get('threat_type') or finding.get('type') or 'Other').upper()
                    key='Malware' if 'MALWARE' in kind or 'TROJAN' in kind or 'VIRUS' in kind else 'Suspicious' if 'SUSP' in kind else 'PUP' if 'PUP' in kind else 'Other'; counts[key]+=1
            self.threat_distribution.setText('   '.join(f'{k}: {v}' for k,v in counts.items()))
            for key, bar in self.threat_bars.items(): bar.setValue(counts[key])
        self._incident_totals_updated = True
        self.connected_device = None
        self.device_idx = 0
        
        self.connection_time_elapsed = 0
        self.is_timer_running = False
        
        # The first call lazily builds the legacy dashboard widgets. Snapshot
        # refreshes must only update data, never rebuild the layout.
        if hasattr(self, 'root_layout'):
            return
        self.root_layout = QStackedLayout(self)
        self.root_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        scroll.setWidget(self.content_widget)
        
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header block
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 10)
        
        left_header = QVBoxLayout()
        left_header.setSpacing(4)
        
        lbl_welcome = QLabel("USB DETECTOR")
        lbl_welcome.setStyleSheet(f"color: {theme_manager.get_color('accent')}; font-size: 20px; font-weight: 900; font-family: 'Inter'; letter-spacing: 1px;")
        
        self.lbl_subtitle = QLabel("Advanced USB Security Scanner")
        self.lbl_subtitle.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter'; font-weight: 600; letter-spacing: 0.5px;")
        
        self.lbl_status = QLabel("Secure Terminal: Idle")
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        
        left_header.addWidget(lbl_welcome)
        left_header.addWidget(self.lbl_subtitle)
        left_header.addWidget(self.lbl_status)
        self.btn_retry = QPushButton('Retry connection'); self.btn_retry.hide(); self.btn_retry.clicked.connect(self.retry_requested.emit); left_header.addWidget(self.btn_retry)
        header_layout.addLayout(left_header)
        
        header_layout.addStretch()
        
        # Right Header (Day Date Time & Notification small tab)
        right_header = QHBoxLayout()
        right_header.setSpacing(12)
        right_header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_datetime = PremiumDateTimeWidget(self)
        
        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self.update_datetime_label)
        self.datetime_timer.start(1000)
        self.update_datetime_label()
        
        self.notif_tab = QFrame()
        self.notif_tab.setObjectName("notifTab")
        self.notif_tab.setStyleSheet(f"""
            QFrame#notifTab {{
                background-color: rgba(255,255,255,8);
                border: 0.5px solid rgba(255,255,255,15);
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background-color: transparent;
            }}
        """)
        notif_layout = QHBoxLayout(self.notif_tab)
        notif_layout.setContentsMargins(8, 4, 8, 4)
        notif_layout.setSpacing(4)
        
        self.lbl_bell_icon = VectorIconWidget("bell", size=14)
        
        self.lbl_notif_count = QLabel("1")
        self.lbl_notif_count.setStyleSheet("color: #B5522B; font-size: 10px; font-weight: 900; background: transparent; border: none;")
        
        notif_layout.addWidget(self.lbl_bell_icon)
        notif_layout.addWidget(self.lbl_notif_count)
        
        self.notif_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notif_tab.mousePressEvent = self.toggle_dropdown_tray
        
        right_header.addWidget(self.lbl_datetime)
        right_header.addWidget(self.notif_tab)
        header_layout.addLayout(right_header)
        
        layout.addLayout(header_layout)

        # Live overview totals (authoritative values are supplied by backend snapshots).
        kpi_row = QHBoxLayout(); self.kpi_values = {}
        self.kpi_trends = {}
        for key, title, color in [('devices','Devices scanned','#25B7F3'),('files','Files scanned','#25B7F3'),('threats','Threats found','#FF5C5C'),('quarantined','Files quarantined','#FFB020')]:
            card=QFrame(); card.setStyleSheet('QFrame{background:#0D1B2A;border:1px solid #1F3A50;border-radius:8px}')
            cl=QVBoxLayout(card); t=QLabel(title.upper()); t.setStyleSheet('color:#8FA4B8;font-size:10px;font-weight:700'); v=QLabel('0'); v.setStyleSheet(f'color:{color};font-size:22px;font-weight:800'); trend=QLabel('— no comparison data'); trend.setStyleSheet('color:#8FA4B8;font-size:9px'); cl.addWidget(t); cl.addWidget(v); cl.addWidget(trend); self.kpi_values[key]=v; self.kpi_trends[key]=trend; kpi_row.addWidget(card)
        layout.addLayout(kpi_row)
        chart_row=QHBoxLayout(); self.risk_chart=DashboardSparkline('Risk trend','#FF5C5C'); self.scan_chart=DashboardSparkline('Files scanned','#25B7F3'); self.threat_chart=DashboardSparkline('Threats found','#FFB020'); chart_row.addWidget(self.risk_chart); chart_row.addWidget(self.scan_chart); chart_row.addWidget(self.threat_chart); layout.addLayout(chart_row)
        activity_card=QFrame(); activity_card.setStyleSheet('QFrame{background:#0D1B2A;border:1px solid #1F3A50;border-radius:8px}'); al=QVBoxLayout(activity_card); ah=QLabel('RECENT ACTIVITY'); ah.setStyleSheet('color:#8FD8FF;font-size:11px;font-weight:700'); self.activity_label=QLabel('No scan activity recorded yet.'); self.activity_label.setStyleSheet('color:#B7C0D1;font-size:11px'); self.activity_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); al.addWidget(ah); al.addWidget(self.activity_label); layout.addWidget(activity_card)
        dist_card=QFrame(); dist_card.setStyleSheet('QFrame{background:#0D1B2A;border:1px solid #1F3A50;border-radius:8px}'); dl=QVBoxLayout(dist_card); dh=QLabel('THREAT DISTRIBUTION'); dh.setStyleSheet('color:#8FD8FF;font-size:11px;font-weight:700'); self.threat_distribution=QLabel('Malware: 0   Suspicious: 0   PUP: 0   Other: 0'); self.threat_distribution.setStyleSheet('color:#B7C0D1;font-size:12px'); dl.addWidget(dh); dl.addWidget(self.threat_distribution); self.threat_bars={}
        for key,color in [('Malware','#FF5C5C'),('Suspicious','#FFB020'),('PUP','#25B7F3'),('Other','#8FA4B8')]:
            bar=QProgressBar(); bar.setRange(0,100); bar.setValue(0); bar.setFormat(key+'  %p%'); bar.setStyleSheet(f'QProgressBar{{color:#B7C0D1;background:#12283A;border:0;border-radius:4px;text-align:left;padding:2px}} QProgressBar::chunk{{background:{color};border-radius:3px}}'); dl.addWidget(bar); self.threat_bars[key]=bar
        layout.addWidget(dist_card)
        
        # Absolute-positioned overlay system tray dropdown
        self.dropdown_tray = SystemTrayDropdown(self.content_widget)
        
        # Interactive Emulation Terminal Card
        self.left_card = GlassCard()
        left_layout = QVBoxLayout(self.left_card)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(12)
        
        lbl_usb_title = QLabel("DEVICE EMULATION TERMINAL")
        lbl_usb_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        left_layout.addWidget(lbl_usb_title)
        
        self.usb_visualizer = AnimatedUSBWidget()
        left_layout.addWidget(self.usb_visualizer, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.live_monitor = LiveMonitoringPanel()
        left_layout.addWidget(self.live_monitor)
        
        self.btn_trigger = QPushButton("SIMULATE PHYSICAL INJECTION")
        self.btn_trigger.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('accent')};
                color: #000000;
                border-radius: 12px;
                padding: 12px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.95;
            }}
        """)
        # Deliberately no click handler: physical udev events are authoritative.
        self.btn_trigger.hide()
        
        # 2. Device Status Card
        self.meta_subcard = GlassCard()
        self.meta_subcard.setObjectName("metaSubcard")
        meta_layout = QVBoxLayout(self.meta_subcard)
        meta_layout.setContentsMargins(20, 20, 20, 20)
        meta_layout.setSpacing(8)
        
        self.lbl_meta_title = QLabel("DEVICE STATUS")
        self.lbl_meta_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        meta_layout.addWidget(self.lbl_meta_title)
        
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        
        self.status_dot = QWidget()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("background-color: #8A7568; border-radius: 4px;")
        status_row.addWidget(self.status_dot)
        
        self.lbl_meta_name = QLabel("No Device Connected")
        self.lbl_meta_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        status_row.addWidget(self.lbl_meta_name, 1)
        meta_layout.addLayout(status_row)
        
        self.lbl_meta_category = QLabel("Waiting for USB Device...")
        self.lbl_meta_category.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        
        self.lbl_meta_vid_pid = QLabel("Hardware ID: N/A")
        self.lbl_meta_vid_pid.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        
        meta_layout.addWidget(self.lbl_meta_category)
        meta_layout.addWidget(self.lbl_meta_vid_pid)
        
        # Risk Ring View Card (Trust Score / Threat Rating)
        self.risk_card = GlassCard()
        risk_card_layout = QVBoxLayout(self.risk_card)
        risk_card_layout.setContentsMargins(20, 20, 20, 20)
        risk_card_layout.setSpacing(12)
        
        risk_h_layout = QHBoxLayout()
        self.risk_ring = CircularRiskRing()
        risk_info_layout = QVBoxLayout()
        self.lbl_threat_level = QLabel("THREAT SCORE: CLEAR")
        self.lbl_threat_level.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 700; font-size: 14px;")
        self.lbl_risk_sub = QLabel("No anomalies identified on active ports.")
        self.lbl_risk_sub.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_risk_sub.setWordWrap(True)
        risk_info_layout.addWidget(self.lbl_threat_level)
        risk_info_layout.addWidget(self.lbl_risk_sub)
        
        risk_h_layout.addWidget(self.risk_ring)
        risk_h_layout.addLayout(risk_info_layout, 1)
        risk_card_layout.addLayout(risk_h_layout)

        # 3. Last Scan Summary
        self.last_scan_card = LastScanSummaryCard()
        
        # 4. Scan History Mini Analytics (small graph only)
        self.scan_history_overview_card = ScanHistoryOverviewCard()
        self.scan_history_overview_card.row_last_scan.hide()
        self.scan_history_overview_card.row_recent_risk.hide()
        self.scan_history_overview_card.row_weekly_scans.hide()
        self.scan_history_overview_card.status_chip.hide()
        
        # 5. Device Information (Compact redesign)
        self.device_info_card = DeviceInfoCard()
        
        # 6. Device Classification
        self.device_class_card = DeviceClassificationCard()
        
        # 7. Storage Information
        self.storage_card = StorageInformationCard()
        
        # 12. Device Activity / 13. Mini Activity Timeline (NotificationCenter)
        self.notification_center = NotificationCenter()
        
        # Preserved sub-cards and other metrics
        self.trusted_devices_card = TrustedDevicesCard()
        self.system_health_card = SystemHealthCard()
        self.recommendation_card = SecurityRecommendationCard()
        
        # Single-column layout vertical sequence
        layout.addWidget(self.left_card)
        layout.addWidget(self.meta_subcard)
        layout.addWidget(self.risk_card)
        layout.addWidget(self.last_scan_card)
        layout.addWidget(self.scan_history_overview_card)
        layout.addWidget(self.device_info_card)
        layout.addWidget(self.device_class_card)
        layout.addWidget(self.storage_card)
        layout.addWidget(self.trusted_devices_card)
        layout.addWidget(self.system_health_card)
        layout.addWidget(self.notification_center)
        layout.addWidget(self.recommendation_card)
        
        self.root_layout.addWidget(scroll)
        
        # Hide standard cards initially
        self.device_info_card.hide()
        self.device_class_card.hide()
        self.storage_card.hide()
        self.recommendation_card.hide()
        
        # Real devices are supplied exclusively by the privileged backend.
        
        theme_manager.theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        self.lbl_status.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-size: 24px; font-weight: 800; font-family: 'Inter';")
        self.btn_trigger.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.get_color('accent')};
                color: #000000;
                border-radius: 12px;
                padding: 12px;
                font-family: 'Inter';
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.95;
            }}
        """)
        self.lbl_threat_level.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-weight: 700; font-size: 14px;")
        self.lbl_meta_name.setStyleSheet(f"color: {theme_manager.get_color('text_primary')}; font-family: 'Inter'; font-size: 12px; font-weight: bold;")
        self.lbl_subtitle.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 11px; font-family: 'Inter'; font-weight: 600; letter-spacing: 0.5px;")
        self.lbl_meta_title.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-size: 10px; font-weight: 800; font-family: 'Inter'; letter-spacing: 0.8px;")
        self.lbl_meta_category.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        self.lbl_meta_vid_pid.setStyleSheet(f"color: {theme_manager.get_color('text_secondary')}; font-family: 'Inter'; font-size: 11px;")
        
        self.lbl_bell_icon.set_color(theme_manager.get_color('accent'))
        
        self.meta_subcard.setStyleSheet("""
            #metaSubcard {
                background: transparent;
                border: none;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

    def update_datetime_label(self):
        current_dt = QDateTime.currentDateTime()
        self.lbl_datetime.setText(current_dt.toString("dddd, MMM d, yyyy - hh:mm:ss AP"))
        if hasattr(self, 'dropdown_tray') and self.dropdown_tray.isVisible():
            self.dropdown_tray.update_time_and_date()
        
        if self.is_timer_running:
            self.connection_time_elapsed += 1
            hours = self.connection_time_elapsed // 3600
            minutes = (self.connection_time_elapsed % 3600) // 60
            seconds = self.connection_time_elapsed % 60
            timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.device_info_card.fields["timer"].setText(timer_str)

    def toggle_dropdown_tray(self, event=None):
        if self.dropdown_tray.isVisible() and self.dropdown_tray.opacity_effect.opacity() > 0.1:
            from PyQt6.QtCore import QPointF
            pos_in_parent = self.notif_tab.mapTo(self.content_widget, QPointF(0, 0).toPoint())
            target_pos = QPointF(pos_in_parent.x() + self.notif_tab.width() - self.dropdown_tray.width(), pos_in_parent.y() + self.notif_tab.height() + 8).toPoint()
            self.dropdown_tray.animate_hide(target_pos)
        else:
            from PyQt6.QtCore import QPointF
            pos_in_parent = self.notif_tab.mapTo(self.content_widget, QPointF(0, 0).toPoint())
            target_pos = QPointF(pos_in_parent.x() + self.notif_tab.width() - self.dropdown_tray.width(), pos_in_parent.y() + self.notif_tab.height() + 8).toPoint()
            self.dropdown_tray.update_time_and_date()
            self.dropdown_tray.animate_show(target_pos)

    def start_simulated_detection_timer(self, delay_ms):
        # Retained only for source compatibility with the supplied design.
        # Simulation can never be activated in the integrated application.
        return
        if hasattr(self, 'detection_timer') and self.detection_timer is not None:
            self.detection_timer.stop()
            self.detection_timer.deleteLater()
        self.detection_timer = QTimer(self)
        self.detection_timer.setSingleShot(True)
        self.detection_timer.timeout.connect(self.trigger_automatic_device_found)
        self.detection_timer.start(delay_ms)

    def trigger_automatic_device_found(self):
        return
        if self.connected_device is not None:
            return
            
        device = SIMULATED_DEVICES[self.device_idx]
        self.device_idx = (self.device_idx + 1) % len(SIMULATED_DEVICES)
        self.detect_new_device(device)

    def detect_new_device(self, device):
        self.show_unknown_device_popup(device)

    def handle_trusted_device_found(self, device):
        self.notification_center.add_log("Trusted Device Detected")
        self.notification_center.add_log("Automatically Authorized")
        self.start_scanning_workflow(device)

    def show_unknown_device_popup(self, device):
        self.clear_popups()
        
        self.unknown_popup = UnknownDevicePopup(device, self)
        self.unknown_popup.action_clicked.connect(self.handle_unknown_popup_action)
        self.unknown_popup.resize(self.size())
        
        self.fade_in_widget(self.unknown_popup, 400)
        self.root_layout.addWidget(self.unknown_popup)
        self.root_layout.setCurrentWidget(self.unknown_popup)

    def handle_unknown_popup_action(self, action, selected_type, device):
        if action == "block":
            self.clear_popups()
            self.handle_popup_action(False, device)
        elif action == "scan":
            match = check_device_type_match(selected_type, device['category'])
            if match:
                self.show_verification_success_popup(device)
            else:
                self.show_device_mismatch_popup(device['category'], selected_type, device)

    def show_verification_success_popup(self, device):
        self.clear_popups()
        
        self.success_popup = VerificationSuccessPopup(self)
        self.success_popup.resize(self.size())
        self.fade_in_widget(self.success_popup, 400)
        self.root_layout.addWidget(self.success_popup)
        self.root_layout.setCurrentWidget(self.success_popup)
        
        QTimer.singleShot(2000, lambda: self.finish_verification_success(device))

    def finish_verification_success(self, device):
        self.clear_popups()
        self.start_scanning_workflow(device)

    def show_device_mismatch_popup(self, detected_type, selected_type, device):
        self.clear_popups()
        
        self.mismatch_popup = DeviceMismatchPopup(detected_type, selected_type, device, self)
        self.mismatch_popup.action_clicked.connect(self.handle_mismatch_action)
        self.mismatch_popup.resize(self.size())
        self.fade_in_widget(self.mismatch_popup, 400)
        self.root_layout.addWidget(self.mismatch_popup)
        self.root_layout.setCurrentWidget(self.mismatch_popup)

    def handle_mismatch_action(self, action, device):
        self.clear_popups()
        if action == "retry":
            self.show_unknown_device_popup(device)
        elif action == "block":
            self.handle_popup_action(False, device)

    def clear_popups(self):
        for attr in ['new_device_popup', 'popup', 'success_popup', 'mismatch_popup', 'unknown_popup']:
            if hasattr(self, attr):
                widget = getattr(self, attr)
                if widget is not None:
                    try:
                        self.root_layout.removeWidget(widget)
                        widget.deleteLater()
                    except Exception:
                        pass
                    setattr(self, attr, None)
                    
        scroll_area = self.root_layout.widget(0)
        self.root_layout.setCurrentWidget(scroll_area)

    def start_scanning_workflow(self, device):
        return
        self.connected_device = device
        self.usb_visualizer.set_connected(True, device['category'])
        self.lbl_status.setText("Peripherals Evaluation...")
        
        self.live_monitor.set_connected(True, "Evaluating peripheral...")
        
        self.lbl_meta_name.setText("Evaluating Device...")
        self.lbl_meta_category.setText("Analyzing port credentials...")
        self.lbl_meta_vid_pid.setText("Hardware ID: Evaluating...")
        self.status_dot.setStyleSheet("background-color: #C98A5E; border-radius: 4px;")
        
        self.is_timer_running = False
        self.connection_time_elapsed = 0
        
        self.notification_center.add_log(f"USB insertion detected: {device['name']}")
        
        # Switch to Scan page and start scan if MainWindow is available
        from PyQt6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'pages_stack') and hasattr(widget, 'nav_bar'):
                widget.nav_bar.set_active_tab(1)  # Tab 1 is Scan Page
                if hasattr(widget, 'page_scan'):
                    widget.page_scan.start_scan()
                break
                
        QTimer.singleShot(2000, lambda: self.complete_authorization_workflow(device))

    def complete_authorization_workflow(self, device):
        self.lbl_status.setText("Access Authorized")
        self.lbl_threat_level.setText("THREAT SCORE: CLEAR")
        self.lbl_risk_sub.setText("Device is successfully registered and cleared.")
        self.device_authorized.emit(device)
        
        self.live_monitor.set_connected(True, device['name'], authorized=True)
        self.notification_center.add_log(f"Access granted to: {device['name']}")
        self.notification_center.add_log("Classification: " + device['category'])
        self.notification_center.add_log("Scan completed: 0 threats identified.")
        
        self.is_timer_running = True
        self.connection_time_elapsed = 0
        
        self.lbl_meta_name.setText("USB Connected")
        self.lbl_meta_category.setText("Device Authorized")
        self.lbl_meta_vid_pid.setText(f"Hardware ID: {device['vid']}:{device['pid']}")
        self.status_dot.setStyleSheet("background-color: #D97F4A; border-radius: 4px;")
        
        self.recommendation_card.update_recommendation(device, authorized=True)
        
        conn_time = QTime.currentTime().toString("hh:mm:ss AP")
        self.device_info_card.update_device(device, conn_time, authorized=True)
        self.device_class_card.update_classification(device['category'])
        self.storage_card.update_storage(device)
        
        self.fade_in_widget(self.device_info_card, 400)
        self.fade_in_widget(self.device_class_card, 400)
        self.fade_in_widget(self.recommendation_card, 400)
        
        if device.get("capacity", "N/A") != "N/A":
            self.fade_in_widget(self.storage_card, 400)
        else:
            self.storage_card.hide()
            
        if hasattr(self, 'btn_trigger') and self.btn_trigger is not None:
            self.btn_trigger.setText("EJECT EMULATOR CONNECTION")

    def start_authorization_workflow(self, device):
        self.detect_new_device(device)

    def trigger_physical_injection(self):
        return
        if self.connected_device is not None:
            self.reset_to_idle(logged_eject_device=self.connected_device)
        else:
            device = SIMULATED_DEVICES[self.device_idx]
            self.device_idx = (self.device_idx + 1) % len(SIMULATED_DEVICES)
            self.detect_new_device(device)

    def reset_to_idle(self, logged_eject_device=None):
        self.clear_popups()
        self.lbl_status.setText("Secure Terminal: Idle")
        self.usb_visualizer.set_connected(False)
        self.risk_ring.set_threat(False)
        self.lbl_threat_level.setText("THREAT SCORE: CLEAR")
        self.lbl_risk_sub.setText("No anomalies identified on active ports.")
        
        self.lbl_meta_name.setText("No Device Connected")
        self.lbl_meta_category.setText("Waiting for USB Device...")
        self.lbl_meta_vid_pid.setText("Hardware ID: N/A")
        self.status_dot.setStyleSheet("background-color: #8A7568; border-radius: 4px;")
        
        self.device_info_card.reset()
        self.device_class_card.reset()
        self.storage_card.reset()
        self.recommendation_card.reset()
        
        self.device_info_card.hide()
        self.device_class_card.hide()
        self.storage_card.hide()
        self.recommendation_card.hide()
        
        self.live_monitor.set_connected(False)
        if logged_eject_device:
            self.notification_center.add_log(f"Device ejected safely: {logged_eject_device['name']}")
            
        self.is_timer_running = False
        self.connection_time_elapsed = 0
        self.connected_device = None
        
        # Remain idle until the backend publishes another physical insertion.

    def apply_backend_device(self, device):
        """Render a real device without starting any simulated workflow."""
        defaults = {
            "name": "Unknown USB device", "manufacturer": "Unknown",
            "vid": "----", "pid": "----", "serial": "Unavailable",
            "usb_version": "Unknown", "category": "USB device",
            "classification": "Unknown", "capacity": "N/A",
            "used_space": "N/A", "free_space": "N/A", "file_system": "N/A",
        }
        defaults.update(device or {})
        self.connected_device = defaults
        self._backend_scan_summary = {
            "device": defaults["name"], "files": 0, "threats": 0,
            "risk_score": 0, "duration": "In progress", "status": "Scanning",
        }
        self.last_scan_card.update_scan(self._backend_scan_summary)
        self.connection_time_elapsed = 0
        self.is_timer_running = True
        self.usb_visualizer.set_connected(True, defaults["category"])
        self.live_monitor.set_connected(True, defaults["name"], authorized=False)
        self.lbl_status.setText("Device isolated — analysis in progress")
        self.lbl_meta_name.setText(defaults["name"])
        self.lbl_meta_category.setText("Backend verification active")
        self.lbl_meta_vid_pid.setText(f"Hardware ID: {defaults['vid']}:{defaults['pid']}")
        self.status_dot.setStyleSheet("background-color: #C98A5E; border-radius: 4px;")
        self.device_info_card.update_device(defaults, QTime.currentTime().toString("hh:mm:ss AP"), authorized=False)
        self.device_class_card.update_classification(defaults["category"])
        self.device_info_card.show()
        self.device_class_card.show()
        self.notification_center.add_log(f"Physical USB detected: {defaults['name']}")

    def apply_backend_state(self, state, detail=""):
        state = str(state or "UNKNOWN").upper()
        if state == "CLASSIFIED" and self.connected_device:
            category_map = {"keyboard": "USB Keyboard", "mouse": "USB Mouse",
                            "storage": "USB Flash Drive", "phone": "Mobile Device",
                            "other": "Unknown Device"}
            category = category_map.get(str(detail).lower(), str(detail).replace("_", " ").title())
            self.connected_device["category"] = category
            self.connected_device["classification"] = category
            self.usb_visualizer.set_connected(True, category)
            self.device_class_card.update_classification(category)
            self.device_info_card.update_device(
                self.connected_device, QTime.currentTime().toString("hh:mm:ss AP"), authorized=False
            )
        self.lbl_status.setText(state.replace("_", " ").title())
        self.lbl_meta_category.setText(detail or state.replace("_", " ").title())
        authorized = state in {"CLEAN", "TRUSTED", "AUTHORIZED", "ALLOWED", "COMPLETED"}
        dangerous = state in {"BLOCKED", "DANGEROUS", "SUSPICIOUS", "QUARANTINED"}
        self.status_dot.setStyleSheet(
            f"background-color: {'#D97F4A' if authorized else '#D14D41' if dangerous else '#C98A5E'}; border-radius: 4px;"
        )
        if self.connected_device:
            self.live_monitor.set_connected(True, self.connected_device["name"], authorized=authorized)
        self.notification_center.add_log(f"{state}: {detail}".rstrip(": "))

    def apply_backend_risk(self, data):
        values = data or {}
        breakdown = values.get("original") or values.get("breakdown") or values
        score = int(breakdown.get("total", values.get("total", values.get("total_risk", values.get("score", 0)))) or 0)
        remediated = bool((data or {}).get("remediated"))
        level = (
            "DANGEROUS" if score >= 60 else
            "SUSPICIOUS" if remediated or score >= 25 else "CLEAR"
        )
        self.risk_ring.set_threat(score >= 25 or remediated)
        self.lbl_threat_level.setText(f"THREAT SCORE: {score}/100 — {level}")
        categories = ("hardware", "trust", "interface", "behavior", "storage", "nvd", "malware")
        details = ", ".join(
            f"{key.title()}: {breakdown.get(key, 0)}" for key in categories
        )
        if (data or {}).get("remediated"):
            details += f". Quarantine verified; post-remediation score: {(data or {}).get('final_total', 0)}"
        self.lbl_risk_sub.setText(
            details or "Risk score calculated by the backend security engine."
        )
        summary = getattr(self, "_backend_scan_summary", {})
        summary.update({"risk_score": score, "status": level})
        self._backend_scan_summary = summary
        self.last_scan_card.update_scan(summary)

    def apply_backend_finding(self, data):
        severity = str((data or {}).get("severity", "INFO")).upper()
        if severity not in {"MEDIUM", "HIGH", "CRITICAL", "DANGEROUS"}:
            return
        summary = getattr(self, "_backend_scan_summary", {})
        summary["threats"] = int(summary.get("threats", 0) or 0) + 1
        summary["status"] = "Threat Detected"
        self._backend_scan_summary = summary
        self.last_scan_card.update_scan(summary)

    def apply_backend_scan_complete(self, data):
        """Apply authoritative engine totals to the Overview scan summary."""
        summary = getattr(self, "_backend_scan_summary", {})
        summary.update({
            "files": int((data or {}).get("files", 0) or 0),
            "threats": int((data or {}).get("threats", 0) or 0),
            "duration": (data or {}).get("duration") or "Completed",
        })
        summary["status"] = (
            "Threat Detected" if summary["threats"] > 0 else "Scan Clean"
        )
        original = (data or {}).get("original_risk") or {}
        if original:
            summary["risk_score"] = int(original.get("total", 0) or 0)
        self._backend_scan_summary = summary
        self.last_scan_card.update_scan(summary)

    def apply_backend_report(self, data):
        values = data or {}
        verdict = str(values.get("verdict", "INCOMPLETE")).upper()
        risk = values.get("risk_breakdown") or {}
        score = int(risk.get("total", values.get("total_risk", 0)) or 0)
        if values.get("device"):
            device = dict(self.connected_device or {})
            device.update(values["device"])
            self.connected_device = device
            self.device_info_card.update_device(device, QTime.currentTime().toString("hh:mm:ss AP"),
                                                 authorized=verdict in {"CLEAN", "TRUSTED"})
        self.lbl_threat_level.setText(f"THREAT SCORE: {score}/100 — {verdict}")
        self.risk_ring.set_threat(verdict in {"DANGEROUS", "SUSPICIOUS", "INCOMPLETE"})
        summary = getattr(self, "_backend_scan_summary", {})
        summary.update({"risk_score": score, "status": verdict,
                        "threats": len(values.get("findings", []))})
        self._backend_scan_summary = summary
        self.lbl_status.setText(f"Analysis complete — {verdict}")
        self.lbl_meta_category.setText(f"Report generated: {verdict}")
        self.notification_center.add_log(f"Consolidated report ready: {verdict}")
        summary = getattr(self, "_backend_scan_summary", {})
        summary["status"] = verdict
        self._backend_scan_summary = summary
        self.last_scan_card.update_scan(summary)

    def apply_backend_disconnect(self):
        self.reset_to_idle(logged_eject_device=self.connected_device)

    def fade_in_widget(self, widget, duration=400):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        widget.show()
        
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        widget._fade_anim = anim
        anim.start()

    def show_auth_popup(self, device):
        self.popup = GlassOverlayPopup(device, self)
        self.popup.authorized.connect(self.handle_popup_action)
        self.popup.resize(self.size())
        
        self.fade_in_widget(self.popup, 400)
        self.root_layout.addWidget(self.popup)
        self.root_layout.setCurrentWidget(self.popup)

    def handle_popup_action(self, authorized, device):
        if hasattr(self, 'popup') and self.popup is not None:
            popup = self.popup
            self.root_layout.removeWidget(popup)
            popup.deleteLater()
            self.popup = None
        
        scroll_area = self.root_layout.widget(0)
        self.root_layout.setCurrentWidget(scroll_area)
        
        conn_time = QTime.currentTime().toString("hh:mm:ss AP")
        
        if authorized:
            self.lbl_status.setText("Access Authorized")
            self.lbl_threat_level.setText("THREAT SCORE: CLEAR")
            self.lbl_risk_sub.setText("Device is successfully registered and cleared.")
            self.device_authorized.emit(device)
            
            self.live_monitor.set_connected(True, device['name'], authorized=True)
            self.notification_center.add_log(f"Access granted to: {device['name']}")
            self.notification_center.add_log("Classification: " + device['category'])
            self.notification_center.add_log("Scan completed: 0 threats identified.")
            
            self.is_timer_running = True
            self.connection_time_elapsed = 0
            
            self.lbl_meta_name.setText("USB Connected")
            self.lbl_meta_category.setText("Device Authorized")
            self.lbl_meta_vid_pid.setText(f"Hardware ID: {device['vid']}:{device['pid']}")
            self.status_dot.setStyleSheet("background-color: #D97F4A; border-radius: 4px;")
            
            self.recommendation_card.update_recommendation(device, authorized=True)
            
            # Populate and show standard details cards only on successful authorization
            self.device_info_card.update_device(device, conn_time, authorized=authorized)
            self.device_class_card.update_classification(device['category'])
            self.storage_card.update_storage(device)
            
            self.fade_in_widget(self.device_info_card, 400)
            self.fade_in_widget(self.device_class_card, 400)
            self.fade_in_widget(self.recommendation_card, 400)
            
            if device.get("capacity", "N/A") != "N/A":
                self.fade_in_widget(self.storage_card, 400)
            else:
                self.storage_card.hide()
        else:
            self.reset_to_idle()
            self.notification_center.add_log("Device Blocked Successfully")
            self.device_blocked.emit(device)
            
        if hasattr(self, 'btn_trigger') and self.btn_trigger is not None:
            self.btn_trigger.setText("EJECT EMULATOR CONNECTION")

    def on_scan_completed(self, scan_data):
        self.last_scan_card.update_scan(scan_data)
        self.notification_center.add_log(f"Scan complete: {scan_data['files']} audited, {scan_data['threats']} threats.")
