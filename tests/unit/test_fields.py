"""Unit tests for pdfstudio.engine.fields.FieldEngine."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdfstudio.engine.document import PDFDocument
from pdfstudio.engine.fields import FieldDef, FieldEngine, FieldType


@pytest.fixture
def engine_with_doc(sample_pdf: Path) -> tuple[FieldEngine, PDFDocument]:
    doc = PDFDocument()
    doc.open(sample_pdf)
    return FieldEngine(doc.raw()), doc


class TestLoadFields:
    def test_empty_document_returns_empty_list(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        assert engine.load_all() == []
        assert engine.load_page(0) == []
        doc.close()


class TestAddField:
    def test_add_text_field(self, engine_with_doc: tuple[FieldEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        fd = FieldDef(
            name="firstname",
            field_type=FieldType.TEXT,
            page_index=0,
            rect=(72, 200, 300, 230),
            value="",
        )
        assert engine.add_field(fd)

        fields = engine.load_all()
        assert len(fields) == 1
        assert fields[0].name == "firstname"
        assert fields[0].field_type == FieldType.TEXT
        doc.close()

    def test_add_checkbox(self, engine_with_doc: tuple[FieldEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        fd = FieldDef(
            name="agree",
            field_type=FieldType.CHECKBOX,
            page_index=0,
            rect=(72, 300, 90, 318),
        )
        assert engine.add_field(fd)
        fields = engine.load_all()
        assert len(fields) == 1
        assert fields[0].field_type == FieldType.CHECKBOX
        doc.close()

    def test_add_dropdown_with_options(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        fd = FieldDef(
            name="country",
            field_type=FieldType.DROPDOWN,
            page_index=0,
            rect=(72, 400, 250, 430),
            options=["US", "CA", "MX"],
        )
        assert engine.add_field(fd)
        fields = engine.load_all()
        assert len(fields) == 1
        assert fields[0].field_type == FieldType.DROPDOWN
        assert set(fields[0].options) == {"US", "CA", "MX"}
        doc.close()

    def test_add_field_combines_flags(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        """Regression: add_field used to overwrite field_flags, losing flags."""
        engine, doc = engine_with_doc
        fd = FieldDef(
            name="comments",
            field_type=FieldType.TEXT,
            page_index=0,
            rect=(72, 500, 400, 600),
            multiline=True,
            required=True,
        )
        assert engine.add_field(fd)

        fields = engine.load_all()
        assert fields[0].multiline is True
        assert fields[0].required is True
        doc.close()

    def test_add_field_out_of_bounds_raises(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        # Way off the page
        fd = FieldDef(
            name="oob",
            field_type=FieldType.TEXT,
            page_index=0,
            rect=(10000, 10000, 11000, 11000),
        )
        with pytest.raises(ValueError, match="outside or has zero area"):
            engine.add_field(fd)
        doc.close()

    def test_add_field_partial_out_of_bounds_clamps(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        """Fields that only partly hang off the page should be clamped, not rejected."""
        engine, doc = engine_with_doc
        fd = FieldDef(
            name="clamp_me",
            field_type=FieldType.TEXT,
            page_index=0,
            rect=(550, 750, 900, 900),  # extends past page edge
        )
        assert engine.add_field(fd), "Partially OOB fields should clamp and succeed"
        doc.close()


class TestSetValue:
    def test_set_value_returns_true_on_match(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        engine.add_field(
            FieldDef(
                name="note",
                field_type=FieldType.TEXT,
                page_index=0,
                rect=(72, 100, 400, 130),
            )
        )
        assert engine.set_value(0, "note", "hello world")
        fields = engine.load_all()
        assert fields[0].value == "hello world"
        doc.close()

    def test_set_value_unknown_field_returns_false(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        assert not engine.set_value(0, "nonexistent", "anything")
        doc.close()


class TestDeleteField:
    def test_delete_removes_field(self, engine_with_doc: tuple[FieldEngine, PDFDocument]) -> None:
        engine, doc = engine_with_doc
        engine.add_field(
            FieldDef(
                name="tmp",
                field_type=FieldType.TEXT,
                page_index=0,
                rect=(72, 100, 200, 130),
            )
        )
        assert len(engine.load_all()) == 1
        assert engine.delete_field(0, "tmp")
        assert engine.load_all() == []
        doc.close()

    def test_delete_unknown_returns_false(
        self, engine_with_doc: tuple[FieldEngine, PDFDocument]
    ) -> None:
        engine, doc = engine_with_doc
        assert not engine.delete_field(0, "nonexistent")
        doc.close()


class TestRoundtrip:
    def test_fields_survive_save_reload(self, sample_pdf: Path, tmp_path: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        engine = FieldEngine(doc.raw())
        engine.add_field(
            FieldDef(
                name="email",
                field_type=FieldType.TEXT,
                page_index=0,
                rect=(72, 100, 400, 130),
                value="",
                required=True,
            )
        )
        engine.set_value(0, "email", "johnny@example.com")

        out = tmp_path / "roundtrip.pdf"
        doc.save(out)
        doc.close()

        d2 = PDFDocument()
        d2.open(out)
        engine2 = FieldEngine(d2.raw())
        fields = engine2.load_all()
        assert len(fields) == 1
        assert fields[0].name == "email"
        assert fields[0].value == "johnny@example.com"
        assert fields[0].required is True
        d2.close()
