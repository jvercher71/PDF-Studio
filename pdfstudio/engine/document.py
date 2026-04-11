"""
PDF document engine — open, save, page operations.
All file I/O lives here. Nothing above this layer touches fitz directly.
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

log = logging.getLogger(__name__)


class PDFDocument:
    """Wraps a fitz.Document and exposes clean operations."""

    def __init__(self):
        self._doc: Optional[fitz.Document] = None
        self._path: Optional[Path] = None
        self._modified: bool = False

    # ------------------------------------------------------------------ #
    # Open / close
    # ------------------------------------------------------------------ #

    def open(self, path: str | Path, password: str = "") -> None:
        """Open a PDF from disk. Raises ValueError on bad password, RuntimeError on corrupt file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        doc = fitz.open(str(path))
        if doc.needs_pass:
            if not doc.authenticate(password):
                doc.close()
                raise ValueError("Incorrect password.")

        if self._doc is not None:
            self._doc.close()

        self._doc = doc
        self._path = path
        self._modified = False
        log.info("Opened: %s (%d pages)", path, len(doc))

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
            self._path = None
            self._modified = False

    def new(self) -> None:
        """Create a blank single-page document."""
        if self._doc:
            self._doc.close()
        self._doc = fitz.open()
        self._doc.new_page(width=612, height=792)  # US Letter
        self._path = None
        self._modified = True

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save(self, path: str | Path | None = None, flatten: bool = False,
             password: str = "") -> Path:
        """
        Save to path (or original path if None).
        flatten=True embeds all form fields and annotations as static content.
        password, when non-empty, encrypts the output with AES-256.
        """
        self._require_open()
        target = Path(path) if path else self._path
        if target is None:
            raise ValueError("No path specified and document was never saved.")

        # Backup original before overwriting
        if target.exists() and target == self._path:
            backup = target.with_suffix(".bak")
            shutil.copy2(target, backup)

        save_opts: dict = {
            "garbage": 4,
            "deflate": True,
            "clean": True,
        }

        if password:
            save_opts["encryption"] = fitz.PDF_ENCRYPT_AES_256
            save_opts["owner_pw"] = password
            save_opts["user_pw"] = password

        if flatten:
            # Flatten AcroForms — bake fields into page content
            for page in self._doc:
                page.clean_contents()
            save_opts["expand"] = True

        self._doc.save(str(target), **save_opts)
        self._path = target
        self._modified = False
        log.info("Saved: %s (flatten=%s)", target, flatten)
        return target

    def save_copy(self, path: str | Path) -> Path:
        """Save a copy without changing the tracked path."""
        self._require_open()
        target = Path(path)
        self._doc.save(str(target), garbage=4, deflate=True)
        log.info("Copy saved: %s", target)
        return target

    def encrypt(self, path: str | Path, user_password: str, owner_password: str = "",
                permissions: int = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY) -> Path:
        """Save an encrypted copy."""
        self._require_open()
        target = Path(path)
        self._doc.save(
            str(target),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=user_password,
            owner_pw=owner_password or user_password,
            permissions=permissions,
            garbage=4,
            deflate=True,
        )
        log.info("Encrypted copy saved: %s", target)
        return target

    # ------------------------------------------------------------------ #
    # Page operations
    # ------------------------------------------------------------------ #

    @property
    def page_count(self) -> int:
        return len(self._doc) if self._doc else 0

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    def get_page(self, index: int) -> fitz.Page:
        self._require_open()
        if not (0 <= index < self.page_count):
            raise IndexError(f"Page index {index} out of range (0–{self.page_count - 1})")
        return self._doc[index]

    def get_page_size(self, index: int) -> tuple[float, float]:
        """Returns (width, height) in points."""
        page = self.get_page(index)
        rect = page.rect
        return rect.width, rect.height

    def insert_page(self, index: int = -1, width: float = 612, height: float = 792) -> int:
        """Insert a blank page. Returns actual inserted index."""
        self._require_open()
        idx = self._doc.new_page(pno=index, width=width, height=height).number
        self._modified = True
        log.info("Inserted page at %d", idx)
        return idx

    def delete_page(self, index: int) -> None:
        self._require_open()
        self._doc.delete_page(index)
        self._modified = True
        log.info("Deleted page %d", index)

    def move_page(self, from_index: int, to_index: int) -> None:
        self._require_open()
        self._doc.move_page(from_index, to_index)
        self._modified = True

    def rotate_page(self, index: int, degrees: int) -> None:
        """Rotate by 90, 180, or 270 degrees (cumulative)."""
        self._require_open()
        page = self.get_page(index)
        page.set_rotation((page.rotation + degrees) % 360)
        self._modified = True

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def get_metadata(self) -> dict:
        self._require_open()
        return self._doc.metadata

    def set_metadata(self, **kwargs) -> None:
        self._require_open()
        self._doc.set_metadata(kwargs)
        self._modified = True

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _require_open(self) -> None:
        if self._doc is None:
            raise RuntimeError("No document is open.")

    def raw(self) -> fitz.Document:
        """Direct fitz.Document access — use sparingly."""
        self._require_open()
        return self._doc
