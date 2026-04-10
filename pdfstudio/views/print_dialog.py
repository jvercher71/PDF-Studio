"""
Print pipeline — renders each PDF page via PyMuPDF at printer DPI
and paints it onto the QPrinter using QPainter.
"""
import logging
from typing import Optional

import fitz
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap, QImage
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PySide6.QtWidgets import QWidget, QMessageBox

log = logging.getLogger(__name__)


def print_document(doc: fitz.Document, parent: Optional[QWidget] = None,
                   preview: bool = False) -> bool:
    """
    Print a fitz.Document.

    Args:
        doc:     The open fitz document.
        parent:  Parent widget for dialogs.
        preview: If True, show print preview instead of going straight to printer.

    Returns True if user confirmed and print job was sent.
    """
    if doc is None or doc.page_count == 0:
        QMessageBox.warning(parent, "Print", "No document to print.")
        return False

    printer = QPrinter(QPrinter.HighResolution)
    printer.setPageMargins(0, 0, 0, 0)   # let page content fill the paper

    if preview:
        dlg = QPrintPreviewDialog(printer, parent)
        dlg.setWindowTitle("Print Preview — PDF Studio")
        dlg.paintRequested.connect(lambda p: _render_to_printer(doc, p))
        dlg.exec()
        return True
    else:
        dlg = QPrintDialog(printer, parent)
        dlg.setWindowTitle("Print")
        if dlg.exec() != QPrintDialog.Accepted:
            return False
        _render_to_printer(doc, printer)
        return True


def _render_to_printer(doc: fitz.Document, printer: QPrinter) -> None:
    """Render every page of doc onto printer."""
    dpi = printer.resolution()       # e.g. 600
    zoom = dpi / 72.0

    painter = QPainter(printer)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    page_range = _page_range(printer, doc.page_count)

    for i, page_idx in enumerate(page_range):
        if i > 0:
            printer.newPage()

        page = doc[page_idx]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        )
        qpix = QPixmap.fromImage(img.copy())

        # Scale pixmap to fit the printer page rect (preserving aspect)
        page_rect = painter.viewport()
        scaled = qpix.scaled(
            page_rect.width(), page_rect.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )

        # Center on page
        x = (page_rect.width() - scaled.width()) // 2
        y = (page_rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        log.debug("Printed page %d at %d dpi", page_idx, dpi)

    painter.end()
    log.info("Print job complete (%d pages)", len(page_range))


def _page_range(printer: QPrinter, total: int) -> list[int]:
    """Translate QPrinter page range to a list of 0-based page indices."""
    if printer.printRange() == QPrinter.AllPages:
        return list(range(total))
    elif printer.printRange() == QPrinter.PageRange:
        first = printer.fromPage() - 1   # QPrinter uses 1-based
        last = printer.toPage() - 1
        return list(range(max(0, first), min(total, last + 1)))
    elif printer.printRange() == QPrinter.CurrentPage:
        p = printer.fromPage() - 1
        return [p] if 0 <= p < total else [0]
    return list(range(total))
