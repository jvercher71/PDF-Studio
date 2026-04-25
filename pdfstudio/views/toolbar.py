"""
Main toolbar — tools, zoom, page navigation.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QToolBar,
    QWidget,
)

from pdfstudio.views.canvas import ToolMode

# Unicode stand-ins (no icon files needed for MVP)
_ICONS: dict[ToolMode, str] = {
    ToolMode.SELECT: "↖",
    ToolMode.TEXT_SELECT: "𝐓",  # noqa: RUF001 — bold T glyph distinguishes from plain T below
    ToolMode.TEXT_FIELD: "T",
    ToolMode.CHECKBOX: "☑",
    ToolMode.RADIO: "⊙",
    ToolMode.DROPDOWN: "⌄",
    ToolMode.LISTBOX: "≡",
    ToolMode.SIGNATURE_FIELD: "✍",
    ToolMode.BUTTON: "⏎",
    ToolMode.HIGHLIGHT: "▓",
    ToolMode.UNDERLINE: "U̲",
    ToolMode.STRIKEOUT: "S̶",
    ToolMode.NOTE: "💬",
    ToolMode.TEXT_BOX: "A",
    ToolMode.INK: "✏",
    ToolMode.RECTANGLE: "▭",
    ToolMode.ELLIPSE: "○",
    ToolMode.LINE: "╱",  # noqa: RUF001 — diagonal box-drawing glyph used as line icon
    ToolMode.ARROW: "→",
    ToolMode.STAMP: "⬡",
}

_TOOLTIPS: dict[ToolMode, str] = {
    ToolMode.SELECT: "Select / Move (Esc)",
    ToolMode.TEXT_SELECT: "Select Text (Ctrl+T) — drag to select, Ctrl+C to copy",
    ToolMode.TEXT_FIELD: "Text Field",
    ToolMode.CHECKBOX: "Checkbox",
    ToolMode.RADIO: "Radio Button",
    ToolMode.DROPDOWN: "Dropdown",
    ToolMode.LISTBOX: "Listbox",
    ToolMode.SIGNATURE_FIELD: "Signature Field",
    ToolMode.BUTTON: "Button",
    ToolMode.HIGHLIGHT: "Highlight",
    ToolMode.UNDERLINE: "Underline",
    ToolMode.STRIKEOUT: "Strikethrough",
    ToolMode.NOTE: "Sticky Note",
    ToolMode.TEXT_BOX: "Text Box",
    ToolMode.INK: "Freehand Draw",
    ToolMode.RECTANGLE: "Rectangle",
    ToolMode.ELLIPSE: "Ellipse",
    ToolMode.LINE: "Line",
    ToolMode.ARROW: "Arrow",
    ToolMode.STAMP: "Stamp",
}


class MainToolbar(QToolBar):
    tool_selected = Signal(ToolMode)
    zoom_changed = Signal(int)  # dpi-equivalent; caller converts
    page_jump = Signal(int)  # 1-based

    def __init__(self, parent=None):
        super().__init__("Main Toolbar", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)

        self._build()

    def _build(self) -> None:
        # ── File group ──────────────────────────────────────────────────
        self._add_action("New", "Ctrl+N", "New document")
        self._add_action("Open", "Ctrl+O", "Open PDF")
        self._add_action("Save", "Ctrl+S", "Save")
        self.addSeparator()

        # ── Undo / Redo ─────────────────────────────────────────────────
        self._add_action("Undo", "Ctrl+Z", "Undo")
        self._add_action("Redo", "Ctrl+Shift+Z", "Redo")
        self.addSeparator()

        # ── Select / Text Select ─────────────────────────────────────────
        self._add_tool(ToolMode.SELECT, checkable=True, checked=True)
        self._add_tool(ToolMode.TEXT_SELECT, checkable=True)
        self.addSeparator()

        # ── Form fields ─────────────────────────────────────────────────
        for mode in (
            ToolMode.TEXT_FIELD,
            ToolMode.CHECKBOX,
            ToolMode.RADIO,
            ToolMode.DROPDOWN,
            ToolMode.LISTBOX,
            ToolMode.SIGNATURE_FIELD,
            ToolMode.BUTTON,
        ):
            self._add_tool(mode, checkable=True)
        self.addSeparator()

        # ── Annotations ─────────────────────────────────────────────────
        for mode in (
            ToolMode.HIGHLIGHT,
            ToolMode.UNDERLINE,
            ToolMode.STRIKEOUT,
            ToolMode.NOTE,
            ToolMode.TEXT_BOX,
            ToolMode.INK,
            ToolMode.RECTANGLE,
            ToolMode.ELLIPSE,
            ToolMode.LINE,
            ToolMode.ARROW,
            ToolMode.STAMP,
        ):
            self._add_tool(mode, checkable=True)
        self.addSeparator()

        # ── Zoom ─────────────────────────────────────────────────────────
        self._zoom_combo = QComboBox()
        self._zoom_combo.setFixedWidth(90)
        self._zoom_combo.addItems(
            ["50%", "75%", "100%", "125%", "150%", "200%", "300%", "Fit Page", "Fit Width"]
        )
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        self.addWidget(self._zoom_combo)
        self.addSeparator()

        # ── Page navigation ──────────────────────────────────────────────
        self.addWidget(QLabel("  Page:"))
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setFixedWidth(60)
        self._page_spin.valueChanged.connect(lambda v: self.page_jump.emit(v - 1))
        self.addWidget(self._page_spin)
        self._page_total = QLabel(" / 0")
        self.addWidget(self._page_total)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

    def _add_action(self, text: str, shortcut: str, tip: str) -> QAction:
        action = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.setToolTip(f"{tip}  ({shortcut})")
        self.addAction(action)
        return action

    def _add_tool(self, mode: ToolMode, checkable: bool = False, checked: bool = False) -> QAction:
        icon_text = _ICONS.get(mode, mode.name)
        action = QAction(icon_text, self)
        action.setToolTip(_TOOLTIPS.get(mode, mode.name))
        action.setCheckable(checkable)
        action.setChecked(checked)
        action.setData(mode)
        if checkable:
            self._action_group.addAction(action)
        action.triggered.connect(lambda checked, m=mode: self.tool_selected.emit(m))
        self.addAction(action)
        return action

    def _on_zoom_changed(self, text: str) -> None:
        self.zoom_changed.emit(0)  # MainWindow reads the combo directly

    def set_page_count(self, count: int) -> None:
        self._page_spin.setMaximum(max(1, count))
        self._page_total.setText(f" / {count}")

    def set_current_page(self, index: int) -> None:
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(index + 1)
        self._page_spin.blockSignals(False)

    def zoom_text(self) -> str:
        return self._zoom_combo.currentText()

    def action(self, text: str) -> QAction | None:
        for a in self.actions():
            if a.text() == text:
                return a
        return None
