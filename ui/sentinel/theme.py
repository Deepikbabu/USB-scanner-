from PyQt6.QtCore import QObject, pyqtSignal

COLORS_DARK = {
    'bg': '#0D0705',
    'glass_bg': 'rgba(23, 17, 13, 0.93)',
    'glass_border': 'rgba(58, 36, 24, 0.75)',
    'accent': '#D97F4A',
    'text_primary': '#F2EDE8',
    'text_secondary': '#B09080',
    'text_muted': '#8A7568',
    'btn_bg': 'rgba(217, 127, 74, 0.12)',
    'btn_hover': 'rgba(217, 127, 74, 0.25)',
}

COLORS_LIGHT = {
    'bg': '#FAF8F5',
    'glass_bg': 'rgba(244, 238, 236, 0.90)',
    'glass_border': 'rgba(210, 200, 194, 0.75)',
    'accent': '#D97F4A',
    'text_primary': '#2B2522',
    'text_secondary': '#827771',
    'text_muted': '#8A7568',
    'btn_bg': 'rgba(0, 0, 0, 8)',
    'btn_hover': 'rgba(217, 127, 74, 0.18)',
}

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_theme = "dark"

    def get_color(self, name):
        colors = COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT
        return colors.get(name, '#ffffff')

    def get_qcolor(self, name):
        from PyQt6.QtGui import QColor
        color_str = self.get_color(name).strip()
        if color_str.startswith("rgba(") and color_str.endswith(")"):
            parts = color_str[5:-1].split(",")
            if len(parts) == 4:
                try:
                    r = int(parts[0].strip())
                    g = int(parts[1].strip())
                    b = int(parts[2].strip())
                    a_str = parts[3].strip()
                    if "." in a_str:
                        a_val = float(a_str)
                        a = int(a_val * 255.0)
                    else:
                        a = int(a_str)
                    return QColor(r, g, b, max(0, min(255, a)))
                except ValueError:
                    pass
        elif color_str.startswith("rgb(") and color_str.endswith(")"):
            parts = color_str[4:-1].split(",")
            if len(parts) == 3:
                try:
                    r = int(parts[0].strip())
                    g = int(parts[1].strip())
                    b = int(parts[2].strip())
                    return QColor(r, g, b)
                except ValueError:
                    pass
        qc = QColor(color_str)
        if qc.isValid():
            return qc
        return QColor(0, 0, 0, 0)

    def set_theme(self, theme_name):
        if theme_name in ["dark", "light"] and self.current_theme != theme_name:
            self.current_theme = theme_name
            self.theme_changed.emit(theme_name)

    @property
    def colors(self):
        return COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT

theme_manager = ThemeManager()

