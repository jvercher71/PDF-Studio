"""Unit tests for pdfstudio.engine.renderer.PageRenderer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Qt pixmaps need a QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from pdfstudio.engine.document import PDFDocument
from pdfstudio.engine.renderer import PageRenderer


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    """A single QApplication for all renderer tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestRender:
    def test_render_returns_pixmap(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        renderer = PageRenderer(doc.raw())
        pixmap = renderer.render(0, dpi=96)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() > 0
        assert pixmap.height() > 0
        doc.close()

    def test_render_dpi_affects_size(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        renderer = PageRenderer(doc.raw())
        low = renderer.render(0, dpi=72)
        high = renderer.render(0, dpi=300)
        assert high.width() > low.width()
        assert high.height() > low.height()
        doc.close()

    def test_render_is_cached(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        renderer = PageRenderer(doc.raw())
        first = renderer.render(0, dpi=96)
        second = renderer.render(0, dpi=96)
        # Same instance = cache hit.
        assert first is second
        doc.close()


class TestThumbnail:
    def test_thumbnail_respects_max_width(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        renderer = PageRenderer(doc.raw())
        thumb = renderer.render_thumbnail(0, max_width=120)
        assert isinstance(thumb, QPixmap)
        assert thumb.width() <= 150, "Thumb exceeds reasonable bound"
        assert thumb.width() > 0
        doc.close()


class TestInvalidate:
    def test_invalidate_drops_cache_for_page(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        renderer = PageRenderer(doc.raw())
        first = renderer.render(0, dpi=96)
        renderer.invalidate(0)
        second = renderer.render(0, dpi=96)
        assert first is not second
        doc.close()

    def test_invalidate_all_drops_everything(self, multipage_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(multipage_pdf)
        renderer = PageRenderer(doc.raw())
        renderer.render(0, dpi=96)
        renderer.render(1, dpi=96)
        renderer.invalidate_all()
        # Internal state check: cache map empty.
        assert renderer._cache == {}  # type: ignore[attr-defined]
        doc.close()


class TestCacheEviction:
    def test_cache_respects_max(self, multipage_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(multipage_pdf)
        renderer = PageRenderer(doc.raw())
        from pdfstudio.engine import renderer as rmod

        original_max = rmod._CACHE_MAX
        try:
            rmod._CACHE_MAX = 3
            for i in range(5):
                renderer.render(i % 5, dpi=96)
            assert len(renderer._cache) <= 3  # type: ignore[attr-defined]
        finally:
            rmod._CACHE_MAX = original_max
        doc.close()
