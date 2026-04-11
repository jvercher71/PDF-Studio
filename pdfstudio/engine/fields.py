"""
AcroForm field engine — read, write, create, delete PDF form fields.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

import fitz

log = logging.getLogger(__name__)


class FieldType(Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    LISTBOX = "listbox"
    SIGNATURE = "signature"
    BUTTON = "button"


# fitz widget types → our enum
_FITZ_TYPE_MAP = {
    fitz.PDF_WIDGET_TYPE_TEXT: FieldType.TEXT,
    fitz.PDF_WIDGET_TYPE_CHECKBOX: FieldType.CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: FieldType.RADIO,
    fitz.PDF_WIDGET_TYPE_COMBOBOX: FieldType.DROPDOWN,
    fitz.PDF_WIDGET_TYPE_LISTBOX: FieldType.LISTBOX,
    fitz.PDF_WIDGET_TYPE_SIGNATURE: FieldType.SIGNATURE,
    fitz.PDF_WIDGET_TYPE_BUTTON: FieldType.BUTTON,
}


@dataclass
class FieldDef:
    """Portable representation of a form field — not tied to fitz objects."""
    name: str
    field_type: FieldType
    page_index: int
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 in page points
    value: Any = ""
    default_value: Any = ""
    options: list[str] = field(default_factory=list)  # for dropdown/listbox/radio
    tooltip: str = ""
    required: bool = False
    read_only: bool = False
    multiline: bool = False
    font_size: float = 12.0
    font_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bg_color: Optional[tuple[float, float, float]] = None
    border_color: Optional[tuple[float, float, float]] = None
    tab_order: int = 0

    @property
    def fitz_rect(self) -> fitz.Rect:
        return fitz.Rect(*self.rect)


class FieldEngine:
    """Read and write AcroForm fields on a fitz.Document."""

    def __init__(self, doc: fitz.Document):
        self._doc = doc

    def load_all(self) -> list[FieldDef]:
        """Load every form field from the document."""
        fields: list[FieldDef] = []
        for page_index in range(len(self._doc)):
            page = self._doc[page_index]
            for widget in page.widgets():
                fd = self._widget_to_def(widget, page_index)
                if fd:
                    fields.append(fd)
        return fields

    def load_page(self, page_index: int) -> list[FieldDef]:
        """Load fields on a single page."""
        page = self._doc[page_index]
        return [
            fd for w in page.widgets()
            if (fd := self._widget_to_def(w, page_index)) is not None
        ]

    def set_value(self, page_index: int, field_name: str, value: Any) -> bool:
        """Set a field's value. Returns True if found and updated."""
        page = self._doc[page_index]
        for widget in page.widgets():
            if widget.field_name == field_name:
                widget.field_value = value
                widget.update()
                log.debug("Set field '%s' = %r on page %d", field_name, value, page_index)
                return True
        return False

    def add_field(self, fd: FieldDef) -> bool:
        """Add a new AcroForm field to the document."""
        page = self._doc[fd.page_index]

        # Validate and clamp field rect to the page boundaries.
        page_rect = page.rect
        field_rect = fitz.Rect(fd.rect).intersect(page_rect)
        if field_rect.is_empty:
            raise ValueError(
                f"Field rect {fd.rect} is outside or has zero area on "
                f"page {fd.page_index} (page rect: {page_rect})"
            )

        widget = fitz.Widget()
        widget.field_name = fd.name
        widget.field_type = self._type_to_fitz(fd.field_type)
        widget.rect = field_rect  # use clamped rect
        widget.field_value = fd.value
        widget.tooltip = fd.tooltip

        if fd.field_type == FieldType.TEXT:
            widget.text_fontsize = fd.font_size
            widget.text_color = fd.font_color
            if fd.multiline:
                widget.field_flags = fitz.PDF_FIELD_IS_MULTILINE

        if fd.options and fd.field_type in (FieldType.DROPDOWN, FieldType.LISTBOX, FieldType.RADIO):
            widget.choice_values = fd.options

        if fd.required:
            widget.field_flags = getattr(widget, "field_flags", 0) | fitz.PDF_FIELD_IS_REQUIRED

        if fd.read_only:
            widget.field_flags = getattr(widget, "field_flags", 0) | fitz.PDF_FIELD_IS_READ_ONLY

        if fd.bg_color:
            widget.fill_color = fd.bg_color
        if fd.border_color:
            widget.border_color = fd.border_color

        try:
            page.add_widget(widget)
            log.info("Added field '%s' (%s) on page %d", fd.name, fd.field_type.value, fd.page_index)
            return True
        except Exception as e:
            log.error("Failed to add field '%s': %s", fd.name, e)
            return False

    def delete_field(self, page_index: int, field_name: str) -> bool:
        """Delete a field by name. Returns True if found and deleted."""
        page = self._doc[page_index]
        for widget in page.widgets():
            if widget.field_name == field_name:
                page.delete_widget(widget)
                log.info("Deleted field '%s' on page %d", field_name, page_index)
                return True
        return False

    def flatten_page(self, page_index: int) -> None:
        """Bake all fields on a page into static content."""
        page = self._doc[page_index]
        page.clean_contents()

    def flatten_all(self) -> None:
        for i in range(len(self._doc)):
            self.flatten_page(i)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _widget_to_def(self, widget: fitz.Widget, page_index: int) -> Optional[FieldDef]:
        ft = _FITZ_TYPE_MAP.get(widget.field_type)
        if ft is None:
            return None
        r = widget.rect
        return FieldDef(
            name=widget.field_name or "",
            field_type=ft,
            page_index=page_index,
            rect=(r.x0, r.y0, r.x1, r.y1),
            value=widget.field_value or "",
            options=list(widget.choice_values or []),
            tooltip=widget.tooltip or "",
            read_only=bool(widget.field_flags & fitz.PDF_FIELD_IS_READ_ONLY),
            required=bool(widget.field_flags & fitz.PDF_FIELD_IS_REQUIRED),
            multiline=bool(widget.field_flags & fitz.PDF_FIELD_IS_MULTILINE),
            font_size=widget.text_fontsize or 12.0,
        )

    @staticmethod
    def _type_to_fitz(ft: FieldType) -> int:
        reverse = {v: k for k, v in _FITZ_TYPE_MAP.items()}
        return reverse.get(ft, fitz.PDF_WIDGET_TYPE_TEXT)
