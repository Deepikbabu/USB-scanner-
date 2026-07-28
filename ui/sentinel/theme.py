"""Shared Sentinel design tokens and application-wide Qt styling."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase


COLORS_DARK = {
    "bg": "#07131F",
    "surface": "#0B1B2A",
    "surface_raised": "#102438",
    "surface_hover": "#142C42",
    "glass_bg": "#0B1B2A",
    "glass_border": "#1D3850",
    "border": "#1D3850",
    "accent": "#159EEA",
    "accent_hover": "#28B4FF",
    "accent_soft": "rgba(21, 158, 234, 0.14)",
    "text_primary": "#F3F7FB",
    "text_secondary": "#9DB0C2",
    "text_muted": "#6F8498",
    "success": "#46D37B",
    "warning": "#FFB82E",
    "danger": "#FF5D63",
    "info": "#35BDF2",
    "btn_bg": "#102B43",
    "btn_hover": "#163B59",
    "table_alt": "#0E2031",
}

COLORS_LIGHT = {
    "bg": "#F3F7FA",
    "surface": "#FFFFFF",
    "surface_raised": "#F8FBFD",
    "surface_hover": "#EDF5FA",
    "glass_bg": "#FFFFFF",
    "glass_border": "#CCDCE7",
    "border": "#CCDCE7",
    "accent": "#087DC1",
    "accent_hover": "#056BA6",
    "accent_soft": "rgba(8, 125, 193, 0.12)",
    "text_primary": "#102334",
    "text_secondary": "#52687A",
    "text_muted": "#718596",
    "success": "#168B4E",
    "warning": "#B66B00",
    "danger": "#D63742",
    "info": "#087DC1",
    "btn_bg": "#E7F1F7",
    "btn_hover": "#D8EAF4",
    "table_alt": "#F5F9FC",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
RADIUS = {"sm": 6, "md": 9, "lg": 12}


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_theme = "dark"

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
            self.theme_changed.emit(theme_name)

    def stylesheet(self):
        c = self.colors
        available = set(QFontDatabase.families())
        font_family = next(
            (name for name in ("Inter", "Segoe UI", "DejaVu Sans", "Arial", "Sans Serif")
             if name in available),
            "Sans Serif",
        )
        return f"""
        * {{
            font-family: "{font_family}";
            outline: none;
        }}
        QMainWindow, QWidget#appRoot {{
            background-color: {c['bg']};
            color: {c['text_primary']};
        }}
        QLabel {{ color: {c['text_primary']}; background: transparent; }}
        QLabel[muted="true"] {{ color: {c['text_secondary']}; }}
        QFrame#appCard, QFrame#glassCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['lg']}px;
        }}
        QPushButton {{
            min-height: 34px;
            padding: 0 14px;
            color: {c['text_primary']};
            background-color: {c['btn_bg']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['sm']}px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {c['btn_hover']}; border-color: {c['accent']}; }}
        QPushButton:pressed {{ background-color: {c['accent_soft']}; }}
        QPushButton:disabled {{ color: {c['text_muted']}; background-color: {c['surface']}; }}
        QPushButton[variant="primary"] {{
            color: white; background-color: {c['accent']}; border-color: {c['accent']};
        }}
        QPushButton[variant="primary"]:hover {{ background-color: {c['accent_hover']}; }}
        QPushButton[variant="danger"] {{
            color: {c['danger']}; background-color: transparent; border-color: {c['danger']};
        }}
        QPushButton[variant="ghost"] {{ background-color: transparent; border-color: transparent; }}
        QLineEdit, QComboBox {{
            min-height: 34px;
            padding: 0 10px;
            color: {c['text_primary']};
            background-color: {c['surface_raised']};
            border: 1px solid {c['border']};
            border-radius: {RADIUS['sm']}px;
            selection-background-color: {c['accent']};
        }}
        QLineEdit:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
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
        QTableView::item, QTableWidget::item {{ min-height: 36px; padding: 7px 9px; border: 0; }}
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
