"""
Zeus PDF theme — dark professional palette inspired by Adobe/Affinity.
Cross-platform: font stack covers Windows, macOS, and Linux.
"""

# ── Palette ────────────────────────────────────────────────────────────
BG_DARK     = "#1E1E1E"    # app background
BG_PANEL    = "#252526"    # sidebar / panel bg
BG_TOOLBAR  = "#2D2D2D"    # toolbar bg
BG_CARD     = "#2D2D30"    # card / widget bg
BORDER      = "#3C3C3C"    # subtle border
BORDER_L    = "#555555"    # lighter border

ACCENT      = "#0078D4"    # primary blue (MS Fluent-ish)
ACCENT_H    = "#106EBE"    # hover
ACCENT_P    = "#005A9E"    # pressed

SUCCESS     = "#16A34A"
WARNING     = "#D97706"
DANGER      = "#DC2626"

TEXT        = "#D4D4D4"    # primary text
TEXT_L      = "#9D9D9D"    # secondary text
TEXT_D      = "#F0F0F0"    # high-emphasis text
WHITE       = "#FFFFFF"

TOOL_ACTIVE = "#0078D4"    # active tool button bg
TOOL_HOVER  = "#3A3A3A"


def get_stylesheet() -> str:
    return f"""
/* ── App base ──────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT};
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", Arial, sans-serif;
    font-size: 13px;
}}

QSplitter::handle {{
    background: {BORDER};
    width: 1px;
    height: 1px;
}}

/* ── Menu bar ───────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_TOOLBAR};
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
    background-color: {BG_CARD};
    color: {TEXT};
    border: 1px solid {BORDER_L};
    border-radius: 6px;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: {WHITE};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── Toolbar ────────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {BG_TOOLBAR};
    border-bottom: 1px solid {BORDER};
    padding: 4px 6px;
    spacing: 2px;
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 4px 6px;
}}
QToolButton {{
    background: transparent;
    color: {TEXT};
    border: none;
    border-radius: 5px;
    padding: 5px 7px;
    font-size: 13px;
}}
QToolButton:hover {{
    background: {TOOL_HOVER};
    color: {TEXT_D};
}}
QToolButton:checked, QToolButton:pressed {{
    background: {TOOL_ACTIVE};
    color: {WHITE};
}}
QToolButton[popupMode="1"] {{
    padding-right: 18px;
}}

/* ── Status bar ─────────────────────────────────────────────────────── */
QStatusBar {{
    background: {BG_TOOLBAR};
    color: {TEXT_L};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
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
    background: {BG_PANEL};
}}
QTabBar::tab {{
    background: {BG_DARK};
    color: {TEXT_L};
    padding: 7px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {TEXT_D};
    border-bottom: 2px solid {ACCENT};
    background: {BG_PANEL};
}}
QTabBar::tab:hover:!selected {{
    background: {TOOL_HOVER};
    color: {TEXT};
}}

/* ── Scroll bars ────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_L};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: #777;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_L};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #777;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Buttons ────────────────────────────────────────────────────────── */
QPushButton {{
    background: {ACCENT};
    color: {WHITE};
    border: none;
    border-radius: 5px;
    padding: 6px 16px;
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
    background: transparent;
    color: {ACCENT};
    border: 1px solid {ACCENT};
}}
QPushButton#secondary:hover {{
    background: rgba(0, 120, 212, 0.12);
}}
QPushButton#danger {{
    background: {DANGER};
    color: {WHITE};
}}
QPushButton#danger:hover {{
    background: #B91C1C;
}}

/* ── Inputs ─────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_CARD};
    color: {TEXT_D};
    border: 1px solid {BORDER_L};
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
    selection-color: {WHITE};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
    outline: none;
}}
QLineEdit:disabled, QTextEdit:disabled {{
    color: {TEXT_L};
    background: {BG_DARK};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {TEXT_L};
    width: 0;
    height: 0;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    color: {TEXT};
    border: 1px solid {BORDER_L};
    selection-background-color: {ACCENT};
    selection-color: {WHITE};
    outline: none;
}}

/* ── Labels ─────────────────────────────────────────────────────────── */
QLabel#section_title {{
    color: {TEXT_D};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 12px 0 6px 0;
}}
QLabel#panel_title {{
    color: {TEXT_D};
    font-size: 14px;
    font-weight: 600;
    padding-bottom: 8px;
}}

/* ── List / tree widgets ────────────────────────────────────────────── */
QListWidget, QTreeWidget, QTableWidget {{
    background: {BG_PANEL};
    color: {TEXT};
    border: none;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 5px 8px;
    border-radius: 4px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: rgba(0, 120, 212, 0.25);
    color: {TEXT_D};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background: {TOOL_HOVER};
}}
QHeaderView::section {{
    background: {BG_DARK};
    color: {TEXT_L};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}

/* ── Slider ─────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER_L};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* ── Dialog / message boxes ─────────────────────────────────────────── */
QDialog {{
    background: {BG_PANEL};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}
QMessageBox {{
    background: {BG_PANEL};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}

/* ── Tooltip ────────────────────────────────────────────────────────── */
QToolTip {{
    background: {BG_CARD};
    color: {TEXT_D};
    border: 1px solid {BORDER_L};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
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
