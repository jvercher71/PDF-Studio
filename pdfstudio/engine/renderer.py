"""
Page renderer — converts fitz pages to QPixmap for display.
Caches rendered pages by (index, dpi) to avoid redundant work.
"""

import logging

import fitz
from PySide6.QtGui import QImage, QPixmap

log = logging.getLogger(__name__)

DEFAULT_DPI = 150
_CACHE_MAX = 20  # pages kept in memory


class PageRenderer:
    """
    Renders PDF pages to QPixmap.

    Usage:
        renderer = PageRenderer(doc)
        pixmap = renderer.render(page_index, dpi=150)
    """

    def __init__(self, doc: fitz.Document):
        self._doc = doc
        self._cache: dict[tuple[int, int], QPixmap] = {}
        self._cache_order: list[tuple[int, int]] = []

    def render(self, page_index: int, dpi: int = DEFAULT_DPI) -> QPixmap:
        """Render a page. Returns cached QPixmap if available."""
        key = (page_index, dpi)
        if key in self._cache:
            return self._cache[key]

        pixmap = self._render_page(page_index, dpi)
        self._store(key, pixmap)
        return pixmap

    def invalidate(self, page_index: int) -> None:
        """Drop all cached renders for a page (call after edits)."""
        to_remove = [k for k in self._cache if k[0] == page_index]
        for k in to_remove:
            del self._cache[k]
            if k in self._cache_order:
                self._cache_order.remove(k)

    def invalidate_all(self) -> None:
        self._cache.clear()
        self._cache_order.clear()

    def render_thumbnail(self, page_index: int, max_width: int = 150) -> QPixmap:
        """Render a low-res thumbnail scaled to at most max_width pixels."""
        page = self._doc[page_index]
        w = page.rect.width
        if w <= 0:
            return self._render_page(page_index, 36)
        # Compute exact DPI so the rendered pixmap width == max_width (capped).
        thumbnail_dpi = max(18, min(300, (max_width / w) * 72))
        pix = self._render_page(page_index, int(thumbnail_dpi))
        # Belt and braces — hard-scale if the integer DPI rounded up.
        if pix.width() > max_width:
            from PySide6.QtCore import Qt

            pix = pix.scaledToWidth(max_width, Qt.SmoothTransformation)
        return pix

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _render_page(self, page_index: int, dpi: int) -> QPixmap:
        page = self._doc[page_index]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # fitz pixmap → QImage → QPixmap
        img = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        )
        # QImage.fromData is safer for persistence (pix.samples is a memoryview)
        qpix = QPixmap.fromImage(img.copy())
        log.debug("Rendered page %d @ %d dpi (%dx%d)", page_index, dpi, pix.width, pix.height)
        return qpix

    def _store(self, key: tuple[int, int], pixmap: QPixmap) -> None:
        if len(self._cache) >= _CACHE_MAX:
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = pixmap
        self._cache_order.append(key)
