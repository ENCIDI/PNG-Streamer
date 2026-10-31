from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app import paths

BG = "#0D0E12"
SIDEBAR = "#101217"
SURFACE = "#16181E"
SURFACE_2 = "#1E2129"
SURFACE_3 = "#252833"
FIELD = "#0F1115"
BORDER = "#252831"
BORDER_STRONG = "#2F3440"
BORDER_HOVER = "#3A3F4B"
TEXT = "#E8EAF0"
MUTED = "#8A90A0"
FAINT = "#5A6070"
ACCENT = "#C8F65A"
ACCENT_HOVER = "#D7FA80"
ACCENT_INK = "#0D0E12"
DANGER = "#FF6B6B"
WARNING = "#FFB547"
DIM_SEGMENT = "#23262E"

FONT_FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "Noto Sans", "Cantarell", "sans-serif"]
BASE_POINT_SIZE = 9.75


def color(value: str, alpha: float = 1.0) -> QColor:
    result = QColor(value)
    result.setAlphaF(alpha)
    return result


def rgba(value: str, alpha: float) -> str:
    c = QColor(value)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def font(point_size: float = BASE_POINT_SIZE, weight: QFont.Weight = QFont.Normal) -> QFont:
    result = QFont()
    result.setFamilies(FONT_FAMILIES)
    result.setPointSizeF(point_size)
    result.setWeight(weight)
    return result


def mono_font(point_size: float = BASE_POINT_SIZE) -> QFont:
    result = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    result.setFamilies(["Cascadia Mono", "JetBrains Mono", "Consolas", "DejaVu Sans Mono", result.family()])
    result.setPointSizeF(point_size)
    return result


def _load_fonts() -> None:
    fonts_dir = paths.RESOURCES_DIR / "assets" / "fonts"
    for font_file in sorted(fonts_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font_file))


QSS = f"""
QWidget {{ color: {TEXT}; }}
QToolTip {{
    background: {SURFACE_3}; color: {TEXT}; border: 1px solid {BORDER_STRONG};
    border-radius: 6px; padding: 5px 8px;
}}
#root {{ background: {BG}; }}
#sidebar {{ background: {SIDEBAR}; border-right: 1px solid #1A1C22; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#faint {{ color: {FAINT}; }}
QLabel#danger {{ color: {DANGER}; }}
QLabel#chip {{
    background: {SURFACE_2}; color: {MUTED}; border-radius: 7px; padding: 4px 9px;
}}

QPushButton#nav {{
    text-align: left; padding: 10px 12px; border: none; border-radius: 10px;
    color: {MUTED}; background: transparent;
}}
QPushButton#nav:hover {{ background: #171A20; color: {TEXT}; }}
QPushButton#nav:checked {{ background: {SURFACE_2}; color: {TEXT}; }}

#card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #181A21, stop:1 #14161B);
    border: 1px solid {BORDER}; border-radius: 16px;
}}
#subcard {{
    background: {rgba(SURFACE_2, 0.55)}; border: 1px solid {BORDER}; border-radius: 12px;
}}
#banner {{
    background: {rgba(ACCENT, 0.08)}; border: 1px solid {rgba(ACCENT, 0.28)}; border-radius: 12px;
}}

QPushButton {{
    background: {SURFACE_2}; border: 1px solid {BORDER_STRONG}; border-radius: 10px;
    padding: 8px 14px; color: {TEXT};
}}
QPushButton:hover {{ background: {SURFACE_3}; border-color: {BORDER_HOVER}; }}
QPushButton:pressed {{ background: {SURFACE_2}; }}
QPushButton:disabled {{ color: {FAINT}; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton#primary {{
    background: {ACCENT}; color: {ACCENT_INK}; border: none; font-weight: 600; padding: 9px 18px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {rgba(ACCENT, 0.25)}; color: {rgba(ACCENT_INK, 0.6)}; }}
QPushButton#danger {{ background: transparent; color: {DANGER}; border: 1px solid {rgba(DANGER, 0.35)}; }}
QPushButton#danger:hover {{ background: {rgba(DANGER, 0.12)}; }}
QPushButton#flat, QToolButton#flat {{
    background: transparent; border: none; border-radius: 8px; padding: 6px; color: {MUTED};
}}
QPushButton#flat:hover, QToolButton#flat:hover {{ background: {SURFACE_3}; color: {TEXT}; }}
QPushButton#link {{
    background: transparent; border: none; padding: 0; color: {ACCENT}; text-align: left;
}}
QPushButton#link:hover {{ text-decoration: underline; }}

#segmented {{ background: {FIELD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QPushButton#segment {{
    background: transparent; border: none; border-radius: 7px; padding: 6px 14px; color: {MUTED};
}}
QPushButton#segment:hover {{ color: {TEXT}; }}
QPushButton#segment:checked {{ background: {SURFACE_3}; color: {TEXT}; }}

QComboBox {{
    background: {SURFACE_2}; border: 1px solid {BORDER_STRONG}; border-radius: 10px;
    padding: 0 30px 0 12px; min-height: 36px;
}}
QComboBox:hover {{ border-color: {BORDER_HOVER}; }}
QComboBox:disabled {{ color: {FAINT}; background: {SURFACE}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; border: 1px solid {BORDER_STRONG}; outline: 0; padding: 4px;
    selection-background-color: {SURFACE_3}; selection-color: {TEXT};
}}

QLineEdit, QSpinBox {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 0 12px;
    min-height: 36px; selection-background-color: {rgba(ACCENT, 0.35)};
}}
QLineEdit:hover, QSpinBox:hover {{ border-color: {BORDER_HOVER}; }}
QLineEdit:focus, QSpinBox:focus {{ border-color: {rgba(ACCENT, 0.6)}; }}
QLineEdit#url {{ color: {ACCENT}; }}
QSpinBox QLineEdit {{ background: transparent; border: none; padding: 0; min-height: 0; }}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border; width: 0; height: 0; border: none; image: none;
}}

QSlider {{ min-height: 22px; }}
QSlider::groove:horizontal {{ height: 4px; background: {DIM_SEGMENT}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: #FFFFFF; }}
QSlider::sub-page:horizontal:disabled {{ background: {FAINT}; }}
QSlider::handle:horizontal:disabled {{ background: {FAINT}; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SURFACE_3}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HOVER}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    height: 0; background: none;
}}
QScrollBar:horizontal {{ height: 0; }}

QMenu {{
    background: {SURFACE_2}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {SURFACE_3}; }}
QMenu::item:disabled {{ color: {MUTED}; }}
QMenu::separator {{ height: 1px; background: {BORDER_STRONG}; margin: 5px 4px; }}

QDialog {{ background: {SURFACE}; }}
QProgressBar {{
    background: {DIM_SEGMENT}; border: none; border-radius: 3px; max-height: 6px; text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
"""


def apply(app: QApplication) -> None:
    _load_fonts()
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setFont(font())
    app.setStyleSheet(QSS)
