"""
Text selection overlay for Zeus PDF.

Adds a TEXT_SELECT tool mode to the canvas. When active:
  - User drags to define a selection rectangle on a page
  - All words whose bounding boxes intersect the rectangle are highlighted
  - Ctrl+C / Edit→Copy copies the selected text to the clipboard
  - The selection is cleared on next click or tool change

Uses PyMuPDF page.get_text("words") for word-level extraction.
page.get_text("blocks") for paragraph-aware extraction when Ctrl+A (select all).
"""

import logging

import fitz
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPen,
)
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsRectItem

log = logging.getLogger(__name__)

# Highlight color for selected text
SEL_HIGHLIGHT = QColor(0, 120, 212, 55)
SEL_BORDER = QColor(0, 90, 180, 120)


class WordHighlight(QGraphicsRectItem):
    """Thin semi-transparent rect drawn over a selected word."""

    def __init__(self, rect: QRectF, parent=None):
        super().__init__(rect, parent)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(SEL_HIGHLIGHT))
        self.setZValue(10)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)


class TextSelector(QObject):
    """
    Manages text selection state for one page at a time.
    Attach to the PDFView; it calls our methods on mouse events.
    """

    text_selected = Signal(str)  # emitted when selection changes

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self._scene = scene
        self._highlights: list[WordHighlight] = []
        self._selected_text: str = ""

        # Drag state
        self._drag_start: QPointF | None = None
        self._drag_page: int = -1
        self._rubber: QGraphicsRectItem | None = None

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #

    def begin_drag(self, scene_pos: QPointF, page_idx: int) -> None:
        self.clear()
        self._drag_start = scene_pos
        self._drag_page = page_idx
        self._rubber = QGraphicsRectItem()
        self._rubber.setPen(QPen(SEL_BORDER, 1, Qt.DashLine))
        self._rubber.setBrush(QBrush(QColor(0, 120, 212, 20)))
        self._rubber.setZValue(20)
        self._scene.addItem(self._rubber)

    def update_drag(self, scene_pos: QPointF) -> None:
        if self._rubber and self._drag_start:
            rect = QRectF(self._drag_start, scene_pos).normalized()
            self._rubber.setRect(rect)

    def end_drag(self, scene_pos: QPointF, fitz_page: fitz.Page, page_scene_rect: QRectF) -> str:
        """
        Finish drag, extract words in selection, highlight them.
        Returns the selected text string.
        """
        if self._rubber:
            self._scene.removeItem(self._rubber)
            self._rubber = None

        if not self._drag_start or not page_scene_rect:
            return ""

        drag_rect = QRectF(self._drag_start, scene_pos).normalized()
        self._drag_start = None

        # Convert scene rect → page point rect
        pw = fitz_page.rect.width
        ph = fitz_page.rect.height
        sw = page_scene_rect.width()
        sh = page_scene_rect.height()
        if sw == 0 or sh == 0:
            return ""

        sx = pw / sw
        sy = ph / sh

        # Local drag rect (relative to page top-left in scene)
        local = drag_rect.translated(-page_scene_rect.topLeft())
        pt_rect = fitz.Rect(
            local.left() * sx,
            local.top() * sy,
            local.right() * sx,
            local.bottom() * sy,
        )

        # Extract words intersecting the selection
        words = fitz_page.get_text("words")  # (x0,y0,x1,y1, word, block, line, word_idx)
        selected_words = []
        for w in words:
            wr = fitz.Rect(w[0], w[1], w[2], w[3])
            if wr.intersects(pt_rect):
                selected_words.append((wr, w[4]))  # rect, text

        if not selected_words:
            self._selected_text = ""
            return ""

        # Draw highlights
        for wr, _text in selected_words:
            # Convert page pt → scene coords
            scene_x0 = page_scene_rect.left() + wr.x0 / sx
            scene_y0 = page_scene_rect.top() + wr.y0 / sy
            scene_x1 = page_scene_rect.left() + wr.x1 / sx
            scene_y1 = page_scene_rect.top() + wr.y1 / sy
            h = WordHighlight(QRectF(scene_x0, scene_y0, scene_x1 - scene_x0, scene_y1 - scene_y0))
            self._scene.addItem(h)
            self._highlights.append(h)

        # Build text (respect reading order — words are already in order)
        self._selected_text = " ".join(w[1] for w in selected_words)
        self.text_selected.emit(self._selected_text)
        log.debug("Selected %d words: %r…", len(selected_words), self._selected_text[:60])
        return self._selected_text

    def select_all_text(self, fitz_page: fitz.Page, page_scene_rect: QRectF) -> str:
        """Select all text on the page."""
        self.clear()
        blocks = fitz_page.get_text("blocks")
        lines = [b[4].strip() for b in blocks if b[4].strip()]
        self._selected_text = "\n\n".join(lines)
        self.text_selected.emit(self._selected_text)
        return self._selected_text

    def copy_to_clipboard(self) -> bool:
        if not self._selected_text:
            return False
        QApplication.clipboard().setText(self._selected_text)
        log.info("Copied %d chars to clipboard", len(self._selected_text))
        return True

    def clear(self) -> None:
        for h in self._highlights:
            self._scene.removeItem(h)
        self._highlights.clear()
        self._selected_text = ""
        if self._rubber:
            self._scene.removeItem(self._rubber)
            self._rubber = None

    @property
    def selected_text(self) -> str:
        return self._selected_text

    @property
    def has_selection(self) -> bool:
        return bool(self._selected_text)
