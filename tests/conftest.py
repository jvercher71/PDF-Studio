"""
Shared pytest fixtures for the Zeus PDF test suite.

Fixture design:
- All PDFs are generated programmatically so the suite has no binary blobs
  and is reproducible on every platform.
- `tmp_path` is used for any file I/O so tests can't stomp on each other.
- A QApplication fixture is provided for the few GUI smoke tests; all
  non-GUI tests are kept engine-level and can run headless without Qt.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

# Force Qt into offscreen mode before anything imports QApplication.
# This lets the GUI smoke tests run on headless CI runners.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# fitz / PyMuPDF segfaults on macOS arm64 if imported during pytest's
# assertion-rewriting phase (the SWIG _mupdf C extension's create_module
# trips a dyld issue). Importing it lazily inside fixtures sidesteps that.


# ──────────────────────────────────────────────────────────────────────
# Sample PDF builders — deterministic, in-memory
# ──────────────────────────────────────────────────────────────────────


def _make_pdf(pages: int = 1, with_text: bool = True) -> bytes:
    """Build a simple multi-page PDF in memory."""
    import fitz

    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=612, height=792)  # US Letter
        if with_text:
            page.insert_text(
                fitz.Point(72, 100),
                f"Page {i + 1} of {pages} — sample text for testing.",
                fontsize=14,
            )
            page.insert_text(
                fitz.Point(72, 130),
                "The quick brown fox jumps over the lazy dog.",
                fontsize=11,
            )
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """Single-page blank PDF."""
    p = tmp_path / "blank.pdf"
    p.write_bytes(_make_pdf(pages=1, with_text=False))
    return p


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Single-page PDF with text content."""
    p = tmp_path / "sample.pdf"
    p.write_bytes(_make_pdf(pages=1, with_text=True))
    return p


@pytest.fixture
def multipage_pdf(tmp_path: Path) -> Path:
    """Five-page PDF — for page-ops testing (insert/delete/rotate)."""
    p = tmp_path / "multipage.pdf"
    p.write_bytes(_make_pdf(pages=5, with_text=True))
    return p


@pytest.fixture
def encrypted_pdf(tmp_path: Path) -> tuple[Path, str]:
    """Password-protected PDF. Returns (path, password)."""
    import fitz

    p = tmp_path / "encrypted.pdf"
    password = "secret123"
    doc = fitz.open("pdf", _make_pdf(pages=2))
    doc.save(
        str(p),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password,
    )
    doc.close()
    return p, password


@pytest.fixture
def pdf_factory(tmp_path: Path) -> Callable[..., Path]:
    """Factory fixture: build a PDF with caller-specified params."""
    counter = {"i": 0}

    def make(pages: int = 1, with_text: bool = True, name: str | None = None) -> Path:
        counter["i"] += 1
        filename = name or f"custom_{counter['i']}.pdf"
        p = tmp_path / filename
        p.write_bytes(_make_pdf(pages=pages, with_text=with_text))
        return p

    return make


# ──────────────────────────────────────────────────────────────────────
# GUI helpers — only loaded if pytest-qt is available and tests request them
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def qapp_cls():
    """Override for pytest-qt's default QApplication class."""
    from PySide6.QtWidgets import QApplication

    return QApplication


# ──────────────────────────────────────────────────────────────────────
# Make `pdfstudio` importable without `pip install -e .` during local dev.
# ──────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
