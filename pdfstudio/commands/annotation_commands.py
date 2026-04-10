"""
Commands for annotation operations.
"""
from pdfstudio.commands.base import Command
from pdfstudio.engine.annotations import AnnotationDef
from pdfstudio.models.document_model import DocumentModel


class AddAnnotationCommand(Command):
    def __init__(self, model: DocumentModel, ad: AnnotationDef):
        super().__init__(f"Add {ad.annot_type.value}")
        self._model = model
        self._ad = ad
        self._xref: str | None = None

    def execute(self) -> None:
        self._xref = self._model.add_annotation(self._ad)

    def undo(self) -> None:
        if self._xref is not None:
            self._model.delete_annotation(self._ad.page_index, int(self._xref))


class DeleteAnnotationCommand(Command):
    def __init__(self, model: DocumentModel, ad: AnnotationDef, xref: int):
        super().__init__(f"Delete {ad.annot_type.value}")
        self._model = model
        self._ad = ad
        self._xref = xref

    def execute(self) -> None:
        self._model.delete_annotation(self._ad.page_index, self._xref)

    def undo(self) -> None:
        self._model.add_annotation(self._ad)


class PageRotateCommand(Command):
    def __init__(self, model: DocumentModel, page_index: int, degrees: int):
        super().__init__(f"Rotate page {page_index + 1} by {degrees}°")
        self._model = model
        self._page = page_index
        self._degrees = degrees

    def execute(self) -> None:
        self._model.rotate_page(self._page, self._degrees)

    def undo(self) -> None:
        self._model.rotate_page(self._page, -self._degrees)


class DeletePageCommand(Command):
    def __init__(self, model: DocumentModel, page_index: int):
        super().__init__(f"Delete page {page_index + 1}")
        self._model = model
        self._page = page_index

    def execute(self) -> None:
        self._model.delete_page(self._page)

    def undo(self) -> None:
        # Re-insert a blank page — best we can do without serializing full page content
        self._model.insert_page(self._page)
