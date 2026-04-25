"""Tests for pdfstudio.engine.signer.SignatureEngine.

Cryptographic cert-based signing is tested only when pyHanko is available.
Visual (drawn/typed) signing is tested unconditionally.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import fitz
import pytest

from pdfstudio.engine.signer import SignatureConfig, SignatureEngine

HAS_PYHANKO = importlib.util.find_spec("pyhanko") is not None


class TestVisualSignature:
    def test_typed_signature_writes_file(self, sample_pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "typed.pdf"
        cfg = SignatureConfig(
            page_index=0,
            rect=(72, 700, 300, 750),
            signer_name="Johnny Vercher",
            sig_type="typed",
        )
        engine = SignatureEngine()
        assert engine.sign_visual(sample_pdf, out, cfg)
        assert out.exists()
        assert out.stat().st_size > 0

        # Reopen — should still be a valid PDF.
        doc = fitz.open(str(out))
        assert doc.page_count == 1
        doc.close()

    def test_drawn_signature_with_image_bytes(self, sample_pdf: Path, tmp_path: Path) -> None:
        # Build a real valid PNG with Pillow (the tiny hardcoded one was malformed).
        import io

        from PIL import Image

        img = Image.new("RGBA", (200, 60), (255, 255, 255, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        out = tmp_path / "drawn.pdf"
        cfg = SignatureConfig(
            page_index=0,
            rect=(72, 700, 300, 750),
            signer_name="Johnny",
            sig_type="drawn",
            image_bytes=png_bytes,
        )
        engine = SignatureEngine()
        assert engine.sign_visual(sample_pdf, out, cfg)
        assert out.exists()

    def test_visual_signature_with_missing_input_fails_gracefully(self, tmp_path: Path) -> None:
        cfg = SignatureConfig(
            page_index=0,
            rect=(72, 700, 300, 750),
            signer_name="Someone",
            sig_type="typed",
        )
        engine = SignatureEngine()
        bogus = tmp_path / "missing.pdf"
        result = engine.sign_visual(bogus, tmp_path / "out.pdf", cfg)
        assert result is False


@pytest.mark.signing
@pytest.mark.skipif(not HAS_PYHANKO, reason="pyHanko not installed")
class TestCertificateSignature:
    def test_missing_cert_returns_false(self, sample_pdf: Path, tmp_path: Path) -> None:
        cfg = SignatureConfig(
            page_index=0,
            rect=(72, 700, 300, 750),
            signer_name="Someone",
            sig_type="cert",
            cert_path=str(tmp_path / "nonexistent.p12"),
            cert_password="pwd",
        )
        engine = SignatureEngine()
        assert not engine.sign_cryptographic(sample_pdf, tmp_path / "signed.pdf", cfg)


@pytest.mark.signing
@pytest.mark.skipif(not HAS_PYHANKO, reason="pyHanko not installed")
class TestVerify:
    def test_verify_unsigned_returns_empty(self, sample_pdf: Path) -> None:
        assert SignatureEngine().verify(sample_pdf) == []
