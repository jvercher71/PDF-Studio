"""Unit tests for pdfstudio.engine.annotations.AnnotationEngine."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdfstudio.engine.annotations import AnnotationDef, AnnotationEngine, AnnotationType
from pdfstudio.engine.document import PDFDocument


@pytest.fixture
def engine_with_doc(sample_pdf: Path) -> tuple[AnnotationEngine, PDFDocument]:
    doc = PDFDocument()
    doc.open(sample_pdf)
    return AnnotationEngine(doc.raw()), doc


class TestAddAnnotation:
    def test_add_highlight(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        ad = AnnotationDef(
            annot_type=AnnotationType.HIGHLIGHT,
            page_index=0,
            rect=(72, 95, 400, 115),
            color=(1.0, 1.0, 0.0),
        )
        xref = engine.add(ad)
        assert xref is not None
        assert xref.isdigit()
        doc.close()

    def test_add_rectangle(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        ad = AnnotationDef(
            annot_type=AnnotationType.RECTANGLE,
            page_index=0,
            rect=(100, 100, 200, 200),
            color=(1.0, 0.0, 0.0),
            line_width=2.0,
        )
        xref = engine.add(ad)
        assert xref is not None
        doc.close()

    def test_add_ink_requires_ink_list(
        self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        ad_bad = AnnotationDef(
            annot_type=AnnotationType.INK,
            page_index=0,
            rect=(0, 0, 100, 100),
        )
        assert engine.add(ad_bad) is None

        ad_good = AnnotationDef(
            annot_type=AnnotationType.INK,
            page_index=0,
            rect=(0, 0, 100, 100),
            ink_list=[[(10, 10), (20, 20), (30, 15), (40, 25)]],
            color=(0.0, 0.0, 1.0),
            line_width=1.5,
        )
        assert engine.add(ad_good) is not None
        doc.close()

    @pytest.mark.parametrize(
        "annot_type",
        [
            AnnotationType.UNDERLINE,
            AnnotationType.STRIKEOUT,
            AnnotationType.NOTE,
            AnnotationType.TEXT_BOX,
            AnnotationType.ELLIPSE,
            AnnotationType.LINE,
            AnnotationType.ARROW,
            AnnotationType.STAMP,
        ],
    )
    def test_add_all_annotation_types(
        self,
        engine_with_doc: tuple[AnnotationEngine, PDFDocument],
        annot_type: AnnotationType,
    ) -> None:
        engine, doc = engine_with_doc
        ad = AnnotationDef(
            annot_type=annot_type,
            page_index=0,
            rect=(100, 100, 200, 150),
            content="Test" if annot_type == AnnotationType.NOTE else "",
        )
        xref = engine.add(ad)
        assert xref is not None, f"Failed to add {annot_type.value}"
        doc.close()


class TestLoadAnnotations:
    def test_load_empty_page(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        assert engine.load_page(0) == []
        doc.close()

    def test_load_after_add(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, _doc = engine_with_doc
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.RECTANGLE,
                page_index=0,
                rect=(50, 50, 150, 150),
            )
        )
        annots = engine.load_page(0)
        assert len(annots) == 1
        assert annots[0].annot_type == AnnotationType.RECTANGLE

    def test_opacity_is_normalized(
        self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]
    ) -> None:
        """Regression: fitz returns -1 for unset opacity — don't pass that through."""
        engine, doc = engine_with_doc
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.RECTANGLE,
                page_index=0,
                rect=(50, 50, 150, 150),
            )
        )
        annots = engine.load_page(0)
        assert 0.0 <= annots[0].opacity <= 1.0, f"opacity not normalized: {annots[0].opacity}"
        doc.close()

    def test_load_with_xrefs(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.RECTANGLE,
                page_index=0,
                rect=(50, 50, 150, 150),
            )
        )
        pairs = engine.load_page_with_xrefs(0)
        assert len(pairs) == 1
        ad, xref = pairs[0]
        assert isinstance(xref, int)
        assert ad.annot_type == AnnotationType.RECTANGLE
        doc.close()


class TestDeleteAnnotation:
    def test_delete_by_xref(self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.RECTANGLE,
                page_index=0,
                rect=(50, 50, 150, 150),
            )
        )
        pairs = engine.load_page_with_xrefs(0)
        assert len(pairs) == 1
        _, xref = pairs[0]
        assert engine.delete_by_xref(0, xref)
        assert engine.load_page(0) == []
        doc.close()

    def test_delete_unknown_xref_returns_false(
        self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        assert not engine.delete_by_xref(0, 99999)
        doc.close()


class TestUpdateContent:
    def test_update_sticky_note_content(
        self, engine_with_doc: tuple[AnnotationEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.NOTE,
                page_index=0,
                rect=(100, 100, 120, 120),
                content="Original",
            )
        )
        pairs = engine.load_page_with_xrefs(0)
        _, xref = pairs[0]
        assert engine.update_content(0, xref, "Updated")
        annots = engine.load_page(0)
        assert annots[0].content == "Updated"
        doc.close()


class TestRoundtrip:
    def test_annotations_survive_save_reload(self, sample_pdf: Path, tmp_path: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        engine = AnnotationEngine(doc.raw())
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.RECTANGLE,
                page_index=0,
                rect=(100, 100, 200, 200),
                color=(1.0, 0.0, 0.0),
                line_width=2.0,
            )
        )
        engine.add(
            AnnotationDef(
                annot_type=AnnotationType.HIGHLIGHT,
                page_index=0,
                rect=(72, 95, 400, 115),
                color=(1.0, 1.0, 0.0),
            )
        )
        out = tmp_path / "annotated.pdf"
        doc.save(out)
        doc.close()

        d2 = PDFDocument()
        d2.open(out)
        engine2 = AnnotationEngine(d2.raw())
        annots = engine2.load_page(0)
        types = {a.annot_type for a in annots}
        assert AnnotationType.RECTANGLE in types
        assert AnnotationType.HIGHLIGHT in types
        d2.close()
