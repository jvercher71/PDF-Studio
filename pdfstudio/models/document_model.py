"""
Document model — the single source of truth for the open document.
Owns the PDFDocument, FieldEngine, AnnotationEngine, and PageRenderer.
Emits Qt signals so the UI can react to changes without polling.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from pdfstudio.engine.annotations import AnnotationDef, AnnotationEngine
from pdfstudio.engine.document import PDFDocument
from pdfstudio.engine.fields import FieldDef, FieldEngine
from pdfstudio.engine.renderer import PageRenderer

log = logging.getLogger(__name__)


class DocumentModel(QObject):
    # Emitted when a new document is loaded or closed
    document_changed = Signal()
    # Emitted when a specific page is modified (index)
    page_modified = Signal(int)
    # Emitted when the modified-state changes (True/False)
    modified_changed = Signal(bool)
    # Emitted after any field change
    fields_changed = Signal(int)  # page index
    # Emitted after any annotation change
    annotations_changed = Signal(int)  # page index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf = PDFDocument()
        self._renderer: PageRenderer | None = None
        self._fields: FieldEngine | None = None
        self._annots: AnnotationEngine | None = None

    # ------------------------------------------------------------------ #
    # Document lifecycle
    # ------------------------------------------------------------------ #

    def open(self, path: str | Path, password: str = "") -> None:
        self._pdf.open(path, password)
        self._init_engines()
        self.document_changed.emit()
        log.info("Document model: opened %s", path)

    def new(self) -> None:
        self._pdf.new()
        self._init_engines()
        self.document_changed.emit()

    def close(self) -> None:
        self._pdf.close()
        self._renderer = None
        self._fields = None
        self._annots = None
        self.document_changed.emit()

    def save(
        self, path: str | Path | None = None, flatten: bool = False, password: str = ""
    ) -> Path | None:
        if not self._pdf.is_open:
            return None
        saved_path = self._pdf.save(path, flatten=flatten, password=password)
        self.modified_changed.emit(False)
        return saved_path

    # ------------------------------------------------------------------ #
    # State queries
    # ------------------------------------------------------------------ #

    @property
    def is_open(self) -> bool:
        return self._pdf.is_open

    @property
    def is_modified(self) -> bool:
        return self._pdf.is_modified

    @property
    def page_count(self) -> int:
        return self._pdf.page_count

    @property
    def path(self) -> Path | None:
        return self._pdf.path

    @property
    def title(self) -> str:
        if not self._pdf.is_open:
            return "Zeus PDF"
        name = self._pdf.path.name if self._pdf.path else "Untitled"
        mark = " •" if self._pdf.is_modified else ""
        return f"{name}{mark} — Zeus PDF"

    def page_size(self, index: int) -> tuple[float, float]:
        return self._pdf.get_page_size(index)

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def render_page(self, index: int, dpi: int = 150):
        if self._renderer is None:
            return None
        return self._renderer.render(index, dpi)

    def render_thumbnail(self, index: int, max_width: int = 150):
        if self._renderer is None:
            return None
        return self._renderer.render_thumbnail(index, max_width)

    def invalidate_render(self, page_index: int) -> None:
        if self._renderer:
            self._renderer.invalidate(page_index)

    # ------------------------------------------------------------------ #
    # Page operations (delegated to PDFDocument)
    # ------------------------------------------------------------------ #

    def insert_page(self, index: int = -1) -> int:
        idx = self._pdf.insert_page(index)
        self._mark_modified()
        self.document_changed.emit()
        return idx

    def delete_page(self, index: int) -> None:
        self._pdf.delete_page(index)
        if self._renderer:
            self._renderer.invalidate(index)
        self._mark_modified()
        self.document_changed.emit()

    def move_page(self, from_index: int, to_index: int) -> None:
        self._pdf.move_page(from_index, to_index)
        self._mark_modified()
        self.document_changed.emit()

    def rotate_page(self, index: int, degrees: int) -> None:
        self._pdf.rotate_page(index, degrees)
        if self._renderer:
            self._renderer.invalidate(index)
        self._mark_modified()
        self.page_modified.emit(index)

    # ------------------------------------------------------------------ #
    # Fields
    # ------------------------------------------------------------------ #

    def load_fields(self, page_index: int) -> list[FieldDef]:
        if self._fields is None:
            return []
        return self._fields.load_page(page_index)

    def load_all_fields(self) -> list[FieldDef]:
        if self._fields is None:
            return []
        return self._fields.load_all()

    def add_field(self, fd: FieldDef) -> bool:
        if self._fields is None:
            return False
        ok = self._fields.add_field(fd)
        if ok:
            self._mark_modified()
            self.invalidate_render(fd.page_index)
            self.fields_changed.emit(fd.page_index)
        return ok

    def set_field_value(self, page_index: int, name: str, value) -> bool:
        if self._fields is None:
            return False
        ok = self._fields.set_value(page_index, name, value)
        if ok:
            self._mark_modified()
            self.invalidate_render(page_index)
            self.fields_changed.emit(page_index)
        return ok

    def delete_field(self, page_index: int, name: str) -> bool:
        if self._fields is None:
            return False
        ok = self._fields.delete_field(page_index, name)
        if ok:
            self._mark_modified()
            self.invalidate_render(page_index)
            self.fields_changed.emit(page_index)
        return ok

    # ------------------------------------------------------------------ #
    # Annotations
    # ------------------------------------------------------------------ #

    def load_annotations(self, page_index: int) -> list[AnnotationDef]:
        if self._annots is None:
            return []
        return self._annots.load_page(page_index)

    def load_annotations_with_xrefs(self, page_index: int) -> list[tuple[AnnotationDef, int]]:
        if self._annots is None:
            return []
        return self._annots.load_page_with_xrefs(page_index)

    def add_annotation(self, ad: AnnotationDef) -> str | None:
        if self._annots is None:
            return None
        xref = self._annots.add(ad)
        if xref:
            self._mark_modified()
            self.invalidate_render(ad.page_index)
            self.annotations_changed.emit(ad.page_index)
        return xref

    def delete_annotation(self, page_index: int, xref: int) -> bool:
        if self._annots is None:
            return False
        ok = self._annots.delete_by_xref(page_index, xref)
        if ok:
            self._mark_modified()
            self.invalidate_render(page_index)
            self.annotations_changed.emit(page_index)
        return ok

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _init_engines(self) -> None:
        raw = self._pdf.raw()
        self._renderer = PageRenderer(raw)
        self._fields = FieldEngine(raw)
        self._annots = AnnotationEngine(raw)

    def _mark_modified(self) -> None:
        was_modified = self._pdf.is_modified
        # PDFDocument tracks modification state internally
        if not was_modified:
            self.modified_changed.emit(True)
