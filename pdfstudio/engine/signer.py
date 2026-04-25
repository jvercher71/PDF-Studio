"""
Signature engine — visual signature placement and cryptographic signing via pyHanko.
Supports: drawn signature image, typed name (rendered to image), certificate-based signing.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SignatureConfig:
    """Configuration for a signing operation."""

    page_index: int
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 in page points
    signer_name: str = ""
    reason: str = ""
    location: str = ""
    # One of: "drawn" (PNG bytes), "typed" (text rendered to image), "cert" (pkcs12 path)
    sig_type: str = "typed"
    image_bytes: bytes | None = None  # For drawn/image signatures
    cert_path: str | None = None  # Path to .p12 / .pfx
    cert_password: str | None = None


class SignatureEngine:
    """
    Applies signatures to a PDF.

    For simple visual-only signatures (drawn/typed), we embed an image annotation
    in the signature field. For cryptographic signing, we use pyHanko.
    """

    def sign_visual(
        self, pdf_path: str | Path, output_path: str | Path, config: SignatureConfig
    ) -> bool:
        """
        Embed a visual (non-cryptographic) signature image into the PDF.
        Use this for drawn/typed signatures without a certificate.
        """
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            page = doc[config.page_index]
            rect = fitz.Rect(*config.rect)

            if config.image_bytes:
                # Stamp the signature image onto the page
                page.insert_image(rect, stream=config.image_bytes, keep_proportion=True)
            else:
                # Typed name: render text into the rect
                page.draw_rect(rect, color=(0.8, 0.8, 0.9), fill=(0.95, 0.95, 1.0))
                page.insert_textbox(
                    rect,
                    config.signer_name,
                    fontsize=14,
                    color=(0.1, 0.1, 0.5),
                    align=fitz.TEXT_ALIGN_CENTER,
                )
                # Signature line
                y = rect.y1 - 4
                page.draw_line(
                    fitz.Point(rect.x0 + 4, y),
                    fitz.Point(rect.x1 - 4, y),
                    color=(0.2, 0.2, 0.6),
                    width=0.5,
                )
                if config.signer_name:
                    page.insert_text(
                        fitz.Point(rect.x0 + 4, rect.y1 + 10),
                        config.signer_name,
                        fontsize=7,
                        color=(0.4, 0.4, 0.4),
                    )

            doc.save(str(output_path), garbage=4, deflate=True)
            doc.close()
            log.info("Visual signature applied → %s", output_path)
            return True
        except Exception as e:
            log.error("Visual signature failed: %s", e)
            return False

    def sign_cryptographic(
        self, pdf_path: str | Path, output_path: str | Path, config: SignatureConfig
    ) -> bool:
        """
        Apply a cryptographic PAdES signature using pyHanko.
        Requires a PKCS#12 (.p12/.pfx) certificate.
        """
        try:
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
            from pyhanko.sign import fields as hanko_fields
            from pyhanko.sign import signers

            with open(str(pdf_path), "rb") as f:
                writer = IncrementalPdfFileWriter(f)

                # Add a signature field if none exists
                field_name = "Signature1"
                hanko_fields.append_signature_field(
                    writer,
                    hanko_fields.SigFieldSpec(
                        field_name,
                        on_page=config.page_index,
                        box=config.rect,
                    ),
                )

                signer = signers.SimpleSigner.load_pkcs12(
                    pfx_file=config.cert_path,
                    passphrase=config.cert_password.encode() if config.cert_password else None,
                )

                sig_meta = signers.PdfSignatureMetadata(
                    field_name=field_name,
                    reason=config.reason or "I approve this document",
                    location=config.location,
                    name=config.signer_name,
                )

                with open(str(output_path), "wb") as out:
                    signers.sign_pdf(writer, sig_meta, signer=signer, output=out)

            log.info("Cryptographic signature applied → %s", output_path)
            return True

        except ImportError:
            log.error("pyHanko not installed. Install with: pip install pyHanko")
            return False
        except Exception as e:
            log.error("Cryptographic signing failed: %s", e)
            return False

    def verify(self, pdf_path: str | Path) -> list[dict]:
        """
        Verify all signatures in a PDF.
        Returns a list of dicts with keys: field_name, valid, signer, reason.
        """
        try:
            from pyhanko.pdf_utils.reader import PdfFileReader
            from pyhanko.sign import validation

            results = []
            with open(str(pdf_path), "rb") as f:
                reader = PdfFileReader(f)
                for field_name, sig_obj, _ in reader.embedded_signatures:
                    try:
                        status = validation.validate_pdf_signature(sig_obj)
                        results.append(
                            {
                                "field_name": field_name,
                                "valid": status.valid,
                                "intact": status.intact,
                                "signer": status.signer_reported_dt,
                                "reason": status.sig_object.get("/Reason", ""),
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "field_name": field_name,
                                "valid": False,
                                "error": str(e),
                            }
                        )
            return results

        except ImportError:
            log.error("pyHanko not installed.")
            return []
        except Exception as e:
            log.error("Signature verification failed: %s", e)
            return []
