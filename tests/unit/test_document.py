"""Unit tests for pdfstudio.engine.document.PDFDocument."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pdfstudio.engine.document import PDFDocument


class TestOpenClose:
    def test_open_existing_file(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        assert doc.is_open
        assert doc.page_count == 1
        assert doc.path == sample_pdf
        assert not doc.is_modified
        doc.close()

    def test_open_missing_file_raises(self, tmp_path: Path) -> None:
        doc = PDFDocument()
        with pytest.raises(FileNotFoundError):
            doc.open(tmp_path / "does_not_exist.pdf")

    def test_open_encrypted_without_password_raises(self, encrypted_pdf: tuple[Path, str]) -> None:
        path, _ = encrypted_pdf
        doc = PDFDocument()
        with pytest.raises(ValueError, match="password"):
            doc.open(path)

    def test_open_encrypted_with_password(self, encrypted_pdf: tuple[Path, str]) -> None:
        path, password = encrypted_pdf
        doc = PDFDocument()
        doc.open(path, password=password)
        assert doc.is_open
        assert doc.page_count == 2
        doc.close()

    def test_open_encrypted_with_wrong_password_raises(
        self, encrypted_pdf: tuple[Path, str]
    ) -> None:
        path, _ = encrypted_pdf
        doc = PDFDocument()
        with pytest.raises(ValueError):
            doc.open(path, password="wrong")

    def test_close_resets_state(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        doc.close()
        assert not doc.is_open
        assert doc.path is None
        assert doc.page_count == 0

    def test_reopen_closes_previous(self, sample_pdf: Path, blank_pdf: Path) -> None:
        """Opening a second file must release the first."""
        doc = PDFDocument()
        doc.open(sample_pdf)
        doc.open(blank_pdf)
        assert doc.path == blank_pdf
        doc.close()


class TestNewDocument:
    def test_new_creates_single_page_letter(self) -> None:
        doc = PDFDocument()
        doc.new()
        assert doc.is_open
        assert doc.page_count == 1
        assert doc.is_modified
        width, height = doc.get_page_size(0)
        assert width == pytest.approx(612.0)
        assert height == pytest.approx(792.0)
        doc.close()

    def test_new_replaces_existing(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        doc.new()
        assert doc.path is None
        assert doc.page_count == 1
        doc.close()


class TestPageOperations:
    def test_insert_page_at_end(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        idx = doc.insert_page()
        assert doc.page_count == 2
        # fitz insert_page(-1) creates at the end
        assert idx >= 0
        assert doc.is_modified
        doc.close()

    def test_insert_page_at_index(self) -> None:
        doc = PDFDocument()
        doc.new()
        doc.insert_page(0)  # prepend
        doc.insert_page(1)  # insert between 0 and the original
        assert doc.page_count == 3
        doc.close()

    def test_delete_page(self, multipage_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(multipage_pdf)
        doc.delete_page(2)
        assert doc.page_count == 4
        assert doc.is_modified
        doc.close()

    def test_delete_invalid_page_raises(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        with pytest.raises(Exception):  # fitz raises its own RuntimeError  # noqa: B017
            doc.delete_page(99)
        doc.close()

    def test_move_page(self, multipage_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(multipage_pdf)
        doc.move_page(0, 4)
        assert doc.page_count == 5
        assert doc.is_modified
        doc.close()

    def test_rotate_page_cumulative(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        doc.rotate_page(0, 90)
        assert doc.get_page(0).rotation == 90
        doc.rotate_page(0, 90)
        assert doc.get_page(0).rotation == 180
        doc.rotate_page(0, 180)  # wraps back to 0
        assert doc.get_page(0).rotation == 0
        doc.close()

    def test_page_size(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        w, h = doc.get_page_size(0)
        assert (w, h) == pytest.approx((612.0, 792.0))
        doc.close()

    def test_get_page_out_of_range_raises(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        with pytest.raises(IndexError):
            doc.get_page(99)
        with pytest.raises(IndexError):
            doc.get_page(-1)
        doc.close()


class TestSave:
    def test_save_to_new_path(self, sample_pdf: Path, tmp_path: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        out = tmp_path / "saved.pdf"
        doc.save(out)
        assert out.exists()
        assert out.stat().st_size > 0
        # After Save-As, path should update and is_modified should reset.
        assert doc.path == out
        assert not doc.is_modified
        doc.close()

    def test_save_overwrite_creates_backup(self, sample_pdf: Path, tmp_path: Path) -> None:
        """Saving over the currently open file should produce a .bak."""
        target = tmp_path / "target.pdf"
        target.write_bytes(sample_pdf.read_bytes())
        doc = PDFDocument()
        doc.open(target)
        doc.insert_page()
        doc.save()
        backup = target.with_suffix(".bak")
        assert backup.exists(), "Backup file should be created on overwrite"
        doc.close()

    def test_save_without_path_raises(self) -> None:
        doc = PDFDocument()
        doc.new()
        with pytest.raises(ValueError):
            doc.save()
        doc.close()

    def test_save_with_password_encrypts_output(self, sample_pdf: Path, tmp_path: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        out = tmp_path / "encrypted_out.pdf"
        doc.save(out, password="hunter2")
        doc.close()

        # Reopen and verify encryption
        d2 = fitz.open(str(out))
        assert d2.needs_pass
        assert d2.authenticate("hunter2")
        d2.close()

    def test_save_copy_preserves_tracked_path(self, sample_pdf: Path, tmp_path: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        original_path = doc.path
        out = tmp_path / "copy.pdf"
        doc.save_copy(out)
        assert out.exists()
        assert doc.path == original_path  # unchanged
        doc.close()


class TestMetadata:
    def test_get_metadata(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        meta = doc.get_metadata()
        assert isinstance(meta, dict)
        # Newly generated PDFs have at least these keys
        assert "format" in meta
        doc.close()

    def test_set_metadata_marks_modified(self, sample_pdf: Path) -> None:
        doc = PDFDocument()
        doc.open(sample_pdf)
        doc.set_metadata(title="Test Document", author="Pytest")
        assert doc.is_modified
        meta = doc.get_metadata()
        assert meta["title"] == "Test Document"
        assert meta["author"] == "Pytest"
        doc.close()


class TestRequireOpen:
    def test_operations_raise_when_closed(self) -> None:
        doc = PDFDocument()
        with pytest.raises(RuntimeError, match="No document"):
            doc.save("anywhere.pdf")
        with pytest.raises(RuntimeError):
            doc.insert_page()
        with pytest.raises(RuntimeError):
            doc.get_page(0)
