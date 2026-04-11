"""
Commands for annotation operations.
"""
import fitz

from pdfstudio.commands.base import Command
from pdfstudio.engine.annotations import AnnotationDef
from pdfstudio.models.document_model import DocumentModel


class AddAnnotationCommand(Command):
    def __init__(self, model: DocumentModel, ad: AnnotationDef):
        super().__init__(f"Add {ad.annot_type.value}")
        self._model = model
        self._ad = ad
        self._xref: str | None = None
        self._annot_nm: str = ""

    def execute(self) -> None:
        self._xref = self._model.add_annotation(self._ad)
        # Store the stable /NM name so undo can find the annotation even if
        # xrefs shift after a save/reload cycle.
        if self._xref is not None:
            page = self._model._pdf.raw()[self._ad.page_index]
            for annot in page.annots():
                if str(annot.xref) == self._xref:
                    self._annot_nm = annot.info.get("name", "")
                    break

    def undo(self) -> None:
        if self._xref is not None:
            xref = int(self._xref)
            page_idx = self._ad.page_index
            # Prefer lookup by /NM name; fall back to xref if name is empty.
            if self._annot_nm:
                page = self._model._pdf.raw()[page_idx]
                for annot in page.annots():
                    if annot.info.get("name", "") == self._annot_nm:
                        xref = annot.xref
                        break
            self._model.delete_annotation(page_idx, xref)


class DeleteAnnotationCommand(Command):
    def __init__(self, model: DocumentModel, ad: AnnotationDef, xref: int):
        super().__init__(f"Delete {ad.annot_type.value}")
        self._model = model
        self._ad = ad
        self._xref = xref
        self._annot_nm: str = ""
        # Capture /NM name at construction time while annotation still exists.
        page = model._pdf.raw()[ad.page_index]
        for annot in page.annots():
            if annot.xref == xref:
                self._annot_nm = annot.info.get("name", "")
                break

    def execute(self) -> None:
        xref = self._xref
        # Prefer lookup by /NM name; fall back to stored xref.
        if self._annot_nm:
            page = self._model._pdf.raw()[self._ad.page_index]
            for annot in page.annots():
                if annot.info.get("name", "") == self._annot_nm:
                    xref = annot.xref
                    break
        self._model.delete_annotation(self._ad.page_index, xref)

    def undo(self) -> None:
        xref_str = self._model.add_annotation(self._ad)
        # Refresh xref and /NM name so a subsequent redo finds the right annot.
        if xref_str is not None:
            self._xref = int(xref_str)
            page = self._model._pdf.raw()[self._ad.page_index]
            for annot in page.annots():
                if annot.xref == self._xref:
                    self._annot_nm = annot.info.get("name", "")
                    break


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
        self._page_idx = page_index
        self._page_bytes: bytes | None = None

    def execute(self) -> None:
        # Serialize the page to bytes *before* deleting so undo can restore it.
        doc = self._model._pdf.raw()
        tmp = fitz.open()
        tmp.insert_pdf(doc, from_page=self._page_idx, to_page=self._page_idx)
        self._page_bytes = tmp.tobytes()
        tmp.close()
        self._model.delete_page(self._page_idx)

    def undo(self) -> None:
        if self._page_bytes is not None:
            doc = self._model._pdf.raw()
            tmp = fitz.open("pdf", self._page_bytes)
            doc.insert_pdf(tmp, from_page=0, to_page=0, start_at=self._page_idx)
            tmp.close()
            # Mark model as modified and notify the UI.
            self._model._pdf._modified = True
            self._model.document_changed.emit()
