"""Tests for pdfstudio.models.document_model.DocumentModel."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pdfstudio.engine.annotations import AnnotationDef, AnnotationType
from pdfstudio.engine.fields import FieldDef, FieldType
from pdfstudio.models.document_model import DocumentModel


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestLifecycle:
    def test_open_emits_document_changed(self, qtbot, sample_pdf: Path) -> None:
        model = DocumentModel()
        with qtbot.waitSignal(model.document_changed, timeout=1000):
            model.open(sample_pdf)
        assert model.is_open
        assert model.page_count == 1
        model.close()

    def test_new_emits_document_changed(self, qtbot) -> None:
        model = DocumentModel()
        with qtbot.waitSignal(model.document_changed, timeout=1000):
            model.new()
        assert model.is_open
        assert model.is_modified
        model.close()

    def test_close_resets(self, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        model.close()
        assert not model.is_open
        assert model.page_count == 0

    def test_title_shows_modified_marker(self, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        assert "•" not in model.title
        model.insert_page()
        assert "•" in model.title
        model.close()


class TestPageSignals:
    def test_insert_page_emits_document_changed(self, qtbot, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        with qtbot.waitSignal(model.document_changed, timeout=1000):
            model.insert_page()
        assert model.page_count == 2
        model.close()

    def test_rotate_page_emits_page_modified(self, qtbot, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        with qtbot.waitSignal(model.page_modified, timeout=1000) as blocker:
            model.rotate_page(0, 90)
        assert blocker.args == [0]
        model.close()

    def test_delete_page_emits_document_changed(self, qtbot, multipage_pdf: Path) -> None:
        model = DocumentModel()
        model.open(multipage_pdf)
        with qtbot.waitSignal(model.document_changed, timeout=1000):
            model.delete_page(1)
        assert model.page_count == 4
        model.close()


class TestFieldSignals:
    def test_add_field_emits_fields_changed(self, qtbot, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        fd = FieldDef(
            name="t",
            field_type=FieldType.TEXT,
            page_index=0,
            rect=(72, 100, 300, 130),
        )
        with qtbot.waitSignal(model.fields_changed, timeout=1000) as blocker:
            model.add_field(fd)
        assert blocker.args == [0]
        model.close()


class TestAnnotationSignals:
    def test_add_annotation_emits_annotations_changed(self, qtbot, sample_pdf: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        ad = AnnotationDef(
            annot_type=AnnotationType.RECTANGLE,
            page_index=0,
            rect=(50, 50, 150, 150),
        )
        with qtbot.waitSignal(model.annotations_changed, timeout=1000) as blocker:
            model.add_annotation(ad)
        assert blocker.args == [0]
        model.close()


class TestSave:
    def test_save_clears_modified_signal(self, qtbot, sample_pdf: Path, tmp_path: Path) -> None:
        model = DocumentModel()
        model.open(sample_pdf)
        model.insert_page()  # mark dirty
        out = tmp_path / "saved.pdf"
        with qtbot.waitSignal(model.modified_changed, timeout=1000) as blocker:
            model.save(out)
        assert blocker.args == [False]
        model.close()
