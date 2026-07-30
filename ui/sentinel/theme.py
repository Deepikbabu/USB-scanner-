"""Shared Sentinel design tokens and application-wide Qt styling."""

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase


COLORS_DARK = {
    "bg": "#0B0908",
    "surface": "#161210",
    "surface_raised": "#1F1916",
    "surface_hover": "#2A211C",
    "glass_bg": "#161210",
    "glass_border": "#33271F",
    "border": "#33271F",
    "accent": "#E2611C",
    "accent_hover": "#F0873C",
    "accent_soft": "rgba(226, 97, 28, 0.16)",
    "text_primary": "#F5EEE7",
    "text_secondary": "#AC9C8D",
    "text_muted": "#6E6053",
    "success": "#6FA85E",
    "warning": "#E0A430",
    "danger": "#D6503C",
    "info": "#F0873C",
    "btn_bg": "#1F1916",
    "btn_hover": "#2A211C",
    "table_alt": "#1B1613",
}

COLORS_LIGHT = {
    "bg": "#FAF6F2",
    "surface": "#FFFFFF",
    "surface_raised": "#F3EBE3",
    "surface_hover": "#ECE0D4",
    "glass_bg": "#FFFFFF",
    "glass_border": "#E7D9C9",
    "border": "#E7D9C9",
    "accent": "#C24E14",
    "accent_hover": "#A5410F",
    "accent_soft": "rgba(194, 78, 20, 0.13)",
    "text_primary": "#221A14",
    "text_secondary": "#7A6C5C",
    "text_muted": "#A5947F",
    "success": "#3E7A34",
    "warning": "#9C6C10",
    "danger": "#B03A28",
    "info": "#C24E14",
    "btn_bg": "#F3EBE3",
    "btn_hover": "#ECE0D4",
    "table_alt": "#FCF8F4",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
RADIUS = {"sm": 9, "md": 12, "lg": 16}


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)
    motion_changed = pyqtSignal(bool)
    accessibility_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        settings = QSettings("BBBS", "USB Security Scanner")
        self.current_theme = str(settings.value("appearance/theme", "dark"))
        self.reduced_motion = str(settings.value("accessibility/reduced_motion", "false")).lower() == "true"
        self.high_contrast = str(settings.value("accessibility/high_contrast", "false")).lower() == "true"
        self.touch_mode = str(settings.value("accessibility/touch_mode", "false")).lower() == "true"
        self.text_scale = float(settings.value("accessibility/text_scale", 1.0))
        self._settings = settings

    @property
    def colors(self):
        return COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT

    def get_color(self, name):
        return self.colors.get(name, "#ffffff")

    def get_qcolor(self, name):
        value = self.get_color(name).strip()
        if value.startswith("rgba(") and value.endswith(")"):
            parts = [part.strip() for part in value[5:-1].split(",")]
            try:
                alpha = float(parts[3])
                return QColor(int(parts[0]), int(parts[1]), int(parts[2]),
                              int(alpha * 255) if alpha <= 1 else int(alpha))
            except (ValueError, IndexError):
                return QColor(0, 0, 0, 0)
        color = QColor(value)
        return color if color.isValid() else QColor(0, 0, 0, 0)

    def set_theme(self, theme_name):
        if theme_name in {"dark", "light"} and self.current_theme != theme_name:
            self.current_theme = theme_name
            self._settings.setValue("appearance/theme", theme_name)
            self.theme_changed.emit(theme_name)

    def set_reduced_motion(self, enabled):
        enabled = bool(enabled)
        if self.reduced_motion != enabled:
            self.reduced_motion = enabled
            self._settings.setValue("accessibility/reduced_motion", enabled)
            self.motion_changed.emit(enabled)

    def set_high_contrast(self, enabled):
        self.high_contrast = bool(enabled)
        self._settings.setValue("accessibility/high_contrast", self.high_contrast)
        self.accessibility_changed.emit()

    def set_touch_mode(self, enabled):
        self.touch_mode = bool(enabled)
        self._settings.setValue("accessibility/touch_mode", self.touch_mode)
        self.accessibility_changed.emit()

    def set_text_scale(self, scale):
        self.text_scale = max(0.9, min(1.3, float(scale)))
        self._settings.setValue("accessibility/text_scale", self.text_scale)
        self.accessibility_changed.emit()

    def stylesheet(self):
        c = self.colors
        available = set(QFontDatabase.families())
        font_family = next(
            (name for name in ("Manrope", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "Sans Serif")
             if name in available),
            "Sans Serif",
        )
        focus_width = 3 if self.high_contrast else 2
        button_height = 46 if self.touch_mode else 34
        row_height = 46 if self.touch_mode else 36
        base_size = int(10 * self.text_scale)
        contrast_border = c['text_secondary'] if self.high_contrast else c['border']
        return f"""
        * {{
            font-family: "{font_family}";
            font-size: {base_size}px;
            outline: none;
        }}
        QMainWindow, QWidget#appRoot {{
            background-color: {c['bg']};
            color: {c['text_primary']};
        }}
        QStackedWidget {{ background: transparent; }}
        QLabel {{ color: {c['text_primary']}; background: transparent; }}
        QLabel[muted="true"] {{ color: {c['text_secondary']}; }}
        QFrame#appCard, QFrame#glassCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['lg']}px;
        }}
        QPushButton {{
            min-height: {button_height}px;
            padding: 0 14px;
            color: {c['text_primary']};
            background-color: {c['btn_bg']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['sm']}px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {c['btn_hover']}; border-color: {c['accent']}; }}
        QPushButton:focus {{ border: {focus_width}px solid {c['accent']}; }}
        QPushButton:pressed {{ background-color: {c['accent_soft']}; }}
        QPushButton:disabled {{ color: {c['text_muted']}; background-color: {c['surface']}; }}
        QPushButton[variant="primary"] {{
            color: #170C06; background-color: {c['accent']}; border-color: {c['accent']};
        }}
        QPushButton[variant="primary"]:hover {{ background-color: {c['accent_hover']}; }}
        QPushButton[variant="danger"] {{
            color: {c['danger']}; background-color: transparent; border-color: {c['danger']};
        }}
        QPushButton[variant="ghost"] {{ background-color: transparent; border-color: transparent; }}
        QLineEdit, QComboBox, QDateEdit {{
            min-height: 34px;
            padding: 0 10px;
            color: {c['text_primary']};
            background-color: {c['surface_raised']};
            border: 1px solid {contrast_border};
            border-radius: {RADIUS['sm']}px;
            selection-background-color: {c['accent']};
        }}
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border-color: {c['accent']}; }}
        QDateEdit::drop-down {{ border: 0; width: 22px; }}
        QTableView, QTableWidget {{
            color: {c['text_primary']};
            background-color: {c['surface']};
            alternate-background-color: {c['table_alt']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['md']}px;
            gridline-color: {c['border']};
            selection-background-color: {c['accent_soft']};
            selection-color: {c['text_primary']};
        }}
        QTableView::item, QTableWidget::item {{ min-height: {row_height}px; padding: 7px 9px; border: 0; }}
        QTableView:focus, QTableWidget:focus {{ border: {focus_width}px solid {c['accent']}; }}
        QHeaderView::section {{
            min-height: 34px;
            padding: 6px 9px;
            color: {c['text_secondary']};
            background-color: {c['surface_raised']};
            border: 0;
            border-bottom: 1px solid {c['border']};
            font-weight: 700;
        }}
        QScrollBar:vertical {{ width: 8px; background: transparent; }}
        QScrollBar::handle:vertical {{ min-height: 28px; background: {c['border']}; border-radius: 4px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QProgressBar {{
            min-height: 20px; color: {c['text_primary']};
            background: {c['surface_raised']}; border: 1px solid {c['border']};
            border-radius: 6px; text-align: center;
        }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 5px; }}
        QToolTip {{
            color: {c['text_primary']}; background: {c['surface_raised']};
            border: 1px solid {c['border']}; padding: 6px;
        }}
        """

    def apply(self, application):
        application.setStyleSheet(self.stylesheet())


theme_manager = ThemeManager()
