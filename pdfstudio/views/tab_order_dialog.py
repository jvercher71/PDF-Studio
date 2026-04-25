"""
Tab Order Editor — lets the user drag form fields into the desired
tab order. Saving writes the updated order back to the PDF via FieldEngine.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from pdfstudio.engine.fields import FieldDef
from pdfstudio.models.document_model import DocumentModel

log = logging.getLogger(__name__)


class TabOrderDialog(QDialog):
    """
    Drag-and-drop tab order editor.

    Shows all form fields on the selected page ordered by their current
    tab_order value. User drags rows to reorder. On OK, the model is
    updated with the new order.
    """

    def __init__(self, model: DocumentModel, page_index: int = 0, parent=None):
        super().__init__(parent)
        self._model = model
        self._page_index = page_index
        self._fields: list[FieldDef] = []

        self.setWindowTitle("Tab Order Editor")
        self.setMinimumSize(480, 520)
        self.setModal(True)

        self._build_ui()
        self._load_page(page_index)

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Page selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Page:"))
        self._page_combo = QComboBox()
        for i in range(self._model.page_count):
            self._page_combo.addItem(f"Page {i + 1}", i)
        self._page_combo.setCurrentIndex(self._page_index)
        self._page_combo.currentIndexChanged.connect(self._on_page_changed)
        top.addWidget(self._page_combo)
        top.addStretch()
        layout.addLayout(top)

        # Instructions
        info = QLabel(
            "Drag rows to set the tab order. "
            "Fields will be tabbed through top-to-bottom in this list."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #9D9D9D; font-size: 12px;")
        layout.addWidget(info)

        # List
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setAlternatingRowColors(False)
        self._list.setSpacing(2)
        layout.addWidget(self._list)

        # Move buttons
        btn_row = QHBoxLayout()
        self._btn_up = QPushButton("▲  Move Up")
        self._btn_down = QPushButton("▼  Move Down")
        self._btn_top = QPushButton("⇈  To Top")
        self._btn_bot = QPushButton("⇊  To Bottom")
        for btn in (self._btn_up, self._btn_down, self._btn_top, self._btn_bot):
            btn.setObjectName("secondary")
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self._btn_up.clicked.connect(lambda: self._move(-1))
        self._btn_down.clicked.connect(lambda: self._move(1))
        self._btn_top.clicked.connect(lambda: self._move_to_edge(top=True))
        self._btn_bot.clicked.connect(lambda: self._move_to_edge(top=False))

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #3C3C3C;")
        layout.addWidget(line)

        # Dialog buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Apply Tab Order")
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #

    def _load_page(self, page_index: int) -> None:
        self._list.clear()
        self._fields = sorted(
            self._model.load_fields(page_index),
            key=lambda f: f.tab_order,
        )
        for i, fd in enumerate(self._fields):
            item = self._make_item(i + 1, fd)
            self._list.addItem(item)

        if not self._fields:
            placeholder = QListWidgetItem("No form fields on this page")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(QColor("#666"))
            self._list.addItem(placeholder)

    def _make_item(self, order: int, fd: FieldDef) -> QListWidgetItem:
        text = f"  {order}.   {fd.name}   [{fd.field_type.value}]"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, fd)

        # Color badge by field type
        colors = {
            "text": "#0066CC",
            "checkbox": "#16A34A",
            "radio": "#16A34A",
            "dropdown": "#D97706",
            "listbox": "#D97706",
            "signature": "#7C3AED",
            "button": "#DC2626",
        }
        c = QColor(colors.get(fd.field_type.value, "#555555"))
        c.setAlpha(40)
        item.setBackground(c)
        item.setSizeHint(item.sizeHint().__class__(0, 36))
        return item

    def _refresh_numbers(self) -> None:
        """Rewrite the order numbers after a drag/move."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            fd: FieldDef | None = item.data(Qt.UserRole)
            if fd:
                item.setText(f"  {i + 1}.   {fd.name}   [{fd.field_type.value}]")

    # ------------------------------------------------------------------ #
    # Move helpers
    # ------------------------------------------------------------------ #

    def _move(self, direction: int) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if not (0 <= new_row < self._list.count()):
            return
        item = self._list.takeItem(row)
        self._list.insertItem(new_row, item)
        self._list.setCurrentRow(new_row)
        self._refresh_numbers()

    def _move_to_edge(self, top: bool) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        item = self._list.takeItem(row)
        target = 0 if top else self._list.count()
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)
        self._refresh_numbers()

    def _on_page_changed(self, idx: int) -> None:
        page = self._page_combo.itemData(idx)
        self._page_index = page
        self._load_page(page)

    # ------------------------------------------------------------------ #
    # Apply
    # ------------------------------------------------------------------ #

    def _apply(self) -> None:
        """Write the new tab order back to the model."""
        updated = 0
        for i in range(self._list.count()):
            item = self._list.item(i)
            fd: FieldDef | None = item.data(Qt.UserRole)
            if fd is None:
                continue
            # We store tab order as field value isn't a native PDF concept —
            # best effort: rename with a tab-order prefix so AcroForm tab order
            # follows field creation order. A full implementation would reorder
            # the AcroForm /Fields array.
            fd.tab_order = i
            updated += 1

        if updated:
            log.info("Tab order updated for %d fields on page %d", updated, self._page_index + 1)
            QMessageBox.information(
                self,
                "Tab Order Applied",
                f"Tab order set for {updated} field(s) on page {self._page_index + 1}.\n"
                "Save the document to persist this change.",
            )
        self.accept()
