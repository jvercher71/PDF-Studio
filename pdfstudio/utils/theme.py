"""
Zeus PDF theme — Apple-inspired premium Light Mode aesthetic.
Cross-platform: uses system fonts on macOS, elegant fallbacks on Windows/Linux.
"""

# ── Palette ────────────────────────────────────────────────────────────
BG_APP = "#F5F5F7"  # standard macOS window background
BG_PANEL = "#F5F5F7"  # sidebar / properties panel bg
BG_TOOLBAR = "#FFFFFF"  # toolbar bg / main white elements
BG_CARD = "#FFFFFF"  # card / input bg
BORDER = "#E5E5EA"  # subtle border for dividers
BORDER_D = "#C7C7CC"  # slightly darker border for inputs

ACCENT = "#007AFF"  # Apple signature blue
ACCENT_H = "#0062CC"  # hover state
ACCENT_P = "#0051AB"  # pressed state

SUCCESS = "#34C759"  # Apple green
WARNING = "#FF9500"  # Apple orange
DANGER = "#FF3B30"  # Apple red

TEXT = "#1D1D1F"  # absolute primary solid text (almost black)
TEXT_L = "#86868B"  # secondary text (silvery gray)
TEXT_D = "#000000"  # maximum contrast text
WHITE = "#FFFFFF"

TOOL_ACTIVE = "#E8F0FE"  # extremely soft blue highlight for tools
TOOL_ACTIVE_TEXT = "#007AFF"  # active tool icon color
TOOL_HOVER = "#E5E5EA"  # soft gray hover


def get_stylesheet() -> str:
    return f"""
/* ── App base ──────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG_APP};
    color: {TEXT};
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF UI Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QSplitter::handle {{
    background: {BORDER};
    width: 1px;
    height: 1px;
}}

/* ── Menu bar ───────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_APP};
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{
    background: {ACCENT};
    color: {WHITE};
    border-radius: 4px;
}}
QMenu {{
    background-color: rgba(255, 255, 255, 0.95);
    color: {TEXT};
    border: 1px solid {BORDER_D};
    border-radius: 8px;
    padding: 6px 0;
}}
QMenu::item {{
    padding: 6px 32px 6px 16px;
    border-radius: 4px;
    margin: 0 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: {WHITE};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 6px 12px;
}}

/* ── Toolbar ────────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {BG_TOOLBAR};
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    spacing: 6px;
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 4px 10px;
}}
QToolButton {{
    background: transparent;
    color: {TEXT};
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 14px;
}}
QToolButton:hover {{
    background: {TOOL_HOVER};
    color: {TEXT};
}}
QToolButton:checked, QToolButton:pressed {{
    background: {TOOL_ACTIVE};
    color: {TOOL_ACTIVE_TEXT};
}}
QToolButton[popupMode="1"] {{
    padding-right: 20px;
}}

/* ── Status bar ─────────────────────────────────────────────────────── */
QStatusBar {{
    background: {BG_APP};
    color: {TEXT_L};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 4px 10px;
}}

/* ── Panels / sidebar ───────────────────────────────────────────────── */
QFrame#sidebar {{
    background: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}
QFrame#properties_panel {{
    background: {BG_PANEL};
    border-left: 1px solid {BORDER};
}}

/* ── Tab widget ─────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_APP};
    border-radius: 6px;
    margin-top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_L};
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT};
}}

/* ── Scroll bars ────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_D};
    border-radius: 6px;
    min-height: 40px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A1A1A6;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_D};
    border-radius: 6px;
    min-width: 40px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #A1A1A6;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Buttons ────────────────────────────────────────────────────────── */
QPushButton {{
    background: {ACCENT};
    color: {WHITE};
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {ACCENT_H};
}}
QPushButton:pressed {{
    background: {ACCENT_P};
}}
QPushButton:disabled {{
    background: {BORDER};
    color: {TEXT_L};
}}
QPushButton#secondary {{
    background: {WHITE};
    color: {ACCENT};
    border: 1px solid {BORDER_D};
}}
QPushButton#secondary:hover {{
    background: #F9F9FB;
    border-color: {BORDER_D};
}}
QPushButton#danger {{
    background: {DANGER};
    color: {WHITE};
}}
QPushButton#danger:hover {{
    background: #D32F2F;
}}

/* ── Inputs ─────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {WHITE};
    color: {TEXT};
    border: 1px solid {BORDER_D};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: rgba(0, 122, 255, 0.2);
    selection-color: {TEXT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
    outline: none;
}}
QLineEdit:disabled, QTextEdit:disabled {{
    color: {TEXT_L};
    background: {BG_APP};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {TEXT_L};
    width: 0;
    height: 0;
    margin-right: 12px;
}}
QComboBox QAbstractItemView {{
    background: rgba(255, 255, 255, 0.95);
    color: {TEXT};
    border: 1px solid {BORDER_D};
    border-radius: 6px;
    selection-background-color: {ACCENT};
    selection-color: {WHITE};
    outline: none;
    padding: 4px;
}}

/* ── Labels ─────────────────────────────────────────────────────────── */
QLabel#section_title {{
    color: {TEXT_L};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    padding: 16px 0 8px 0;
}}
QLabel#panel_title {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 600;
    padding-bottom: 12px;
}}

/* ── List / tree widgets ────────────────────────────────────────────── */
QListWidget, QTreeWidget, QTableWidget {{
    background: transparent;
    color: {TEXT};
    border: none;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 6px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {ACCENT};
    color: {WHITE};
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
    background: {TOOL_HOVER};
}}
QHeaderView::section {{
    background: {BG_APP};
    color: {TEXT_L};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 500;
}}

/* ── Slider ─────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {WHITE};
    border: 1px solid {BORDER_D};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* ── Dialog / message boxes ─────────────────────────────────────────── */
QDialog {{
    background: {BG_APP};
}}
QDialogButtonBox QPushButton {{
    min-width: 90px;
}}
QMessageBox {{
    background: {BG_APP};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}

/* ── Tooltip ────────────────────────────────────────────────────────── */
QToolTip {{
    background: rgba(0, 0, 0, 0.85);
    color: {WHITE};
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}

/* ── Splitter handle ────────────────────────────────────────────────── */
QSplitter::handle:horizontal {{
    background: {BORDER};
    width: 1px;
}}
QSplitter::handle:vertical {{
    background: {BORDER};
    height: 1px;
}}
"""
