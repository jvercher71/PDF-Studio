"""
Sidebar — thumbnail strip on the left + fields tree on the second tab.
"""
import logging
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QListWidget,
    QListWidgetItem, QLabel, QSizePolicy,
)

from pdfstudio.models.document_model import DocumentModel

log = logging.getLogger(__name__)


class ThumbnailList(QListWidget):
    page_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(120, 160))
        self.setSpacing(6)
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setUniformItemSizes(False)
        self.setWordWrap(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.currentRowChanged.connect(self.page_selected)

    def load(self, model: DocumentModel) -> None:
        self.clear()
        for i in range(model.page_count):
            thumb = model.render_thumbnail(i, max_width=120)
            item = QListWidgetItem(f"  {i + 1}")
            if thumb:
                item.setIcon(thumb)
            item.setSizeHint(QSize(130, 175))
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            self.addItem(item)

    def highlight(self, index: int) -> None:
        self.setCurrentRow(index)


class FieldsTree(QListWidget):
    """Flat list of all form fields in the document."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)
        self.setSpacing(2)

    def load(self, model: DocumentModel) -> None:
        self.clear()
        if not model.is_open:
            return
        fields = model.load_all_fields()
        for fd in fields:
            label = f"{fd.name}  [{fd.field_type.value}]  p.{fd.page_index + 1}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, fd)
            self.addItem(item)
        if not fields:
            item = QListWidgetItem("No form fields")
            item.setFlags(Qt.NoItemFlags)
            self.addItem(item)


class Sidebar(QWidget):
    page_selected = Signal(int)
    field_selected = Signal(object)  # FieldDef

    def __init__(self, model: DocumentModel, parent=None):
        super().__init__(parent)
        self._model = model
        self.setObjectName("sidebar")
        self.setFixedWidth(160)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._thumbnails = ThumbnailList()
        self._fields_tree = FieldsTree()

        self._tabs.addTab(self._thumbnails, "Pages")
        self._tabs.addTab(self._fields_tree, "Fields")
        layout.addWidget(self._tabs)

        self._thumbnails.page_selected.connect(self.page_selected)
        self._fields_tree.currentItemChanged.connect(self._on_field_selected)
        self._model.document_changed.connect(self._reload)
        self._model.fields_changed.connect(lambda _: self._reload_fields())

    def _reload(self) -> None:
        self._thumbnails.load(self._model)
        self._reload_fields()

    def _reload_fields(self) -> None:
        self._fields_tree.load(self._model)

    def highlight_page(self, index: int) -> None:
        self._thumbnails.highlight(index)

    def _on_field_selected(self, current, _previous) -> None:
        if current:
            fd = current.data(Qt.UserRole)
            if fd:
                self.field_selected.emit(fd)
