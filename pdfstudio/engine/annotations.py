"""
Annotation engine — highlight, sticky note, shapes, ink, stamps.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import fitz

log = logging.getLogger(__name__)


class AnnotationType(Enum):
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    NOTE = "note"
    TEXT_BOX = "textbox"
    INK = "ink"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    LINE = "line"
    ARROW = "arrow"
    STAMP = "stamp"
    IMAGE = "image"


@dataclass
class AnnotationDef:
    annot_type: AnnotationType
    page_index: int
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1
    content: str = ""
    color: tuple[float, float, float] = (1.0, 0.9, 0.0)   # RGB 0–1
    fill_color: Optional[tuple[float, float, float]] = None
    opacity: float = 0.5
    line_width: float = 1.5
    ink_list: Optional[list[list[tuple[float, float]]]] = None  # for ink
    stamp_name: str = "Draft"
    author: str = ""

    @property
    def fitz_rect(self) -> fitz.Rect:
        return fitz.Rect(*self.rect)


class AnnotationEngine:
    """Add, update, delete annotations on a fitz.Document."""

    def __init__(self, doc: fitz.Document):
        self._doc = doc

    def load_page(self, page_index: int) -> list[AnnotationDef]:
        """Load all annotations from a page."""
        page = self._doc[page_index]
        result = []
        for annot in page.annots():
            ad = self._annot_to_def(annot, page_index)
            if ad:
                result.append(ad)
        return result

    def add(self, ad: AnnotationDef) -> Optional[str]:
        """Add an annotation. Returns the annotation's xref as string ID, or None on failure."""
        page = self._doc[ad.page_index]
        try:
            annot = self._create_annot(page, ad)
            if annot is None:
                return None
            annot.set_opacity(ad.opacity)
            if ad.author:
                annot.set_info(content=ad.content, title=ad.author)
            elif ad.content:
                annot.set_info(content=ad.content)
            annot.update()
            xref = str(annot.xref)
            log.info("Added %s annotation on page %d (xref=%s)", ad.annot_type.value, ad.page_index, xref)
            return xref
        except Exception as e:
            log.error("Failed to add annotation: %s", e)
            return None

    def delete_by_xref(self, page_index: int, xref: int) -> bool:
        page = self._doc[page_index]
        for annot in page.annots():
            if annot.xref == xref:
                page.delete_annot(annot)
                log.info("Deleted annotation xref=%d on page %d", xref, page_index)
                return True
        return False

    def update_content(self, page_index: int, xref: int, content: str) -> bool:
        page = self._doc[page_index]
        for annot in page.annots():
            if annot.xref == xref:
                info = annot.info
                info["content"] = content
                annot.set_info(**info)
                annot.update()
                return True
        return False

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _create_annot(self, page: fitz.Page, ad: AnnotationDef) -> Optional[fitz.Annot]:
        r = ad.fitz_rect
        c = ad.color
        fc = ad.fill_color

        match ad.annot_type:
            case AnnotationType.HIGHLIGHT:
                quads = r.get_area() and page.search_for("", quads=True)
                return page.add_highlight_annot(r)

            case AnnotationType.UNDERLINE:
                return page.add_underline_annot(r)

            case AnnotationType.STRIKEOUT:
                return page.add_strikeout_annot(r)

            case AnnotationType.NOTE:
                return page.add_text_annot(r.tl, ad.content or "Note")

            case AnnotationType.TEXT_BOX:
                annot = page.add_freetext_annot(
                    r, ad.content or "",
                    fontsize=12, text_color=c,
                    fill_color=fc or (1, 1, 0.8),
                    border_color=c,
                )
                return annot

            case AnnotationType.INK:
                if not ad.ink_list:
                    return None
                annot = page.add_ink_annot(ad.ink_list)
                annot.set_border(width=ad.line_width)
                annot.set_colors(stroke=c)
                return annot

            case AnnotationType.RECTANGLE:
                annot = page.add_rect_annot(r)
                annot.set_border(width=ad.line_width)
                annot.set_colors(stroke=c, fill=fc)
                return annot

            case AnnotationType.ELLIPSE:
                annot = page.add_circle_annot(r)
                annot.set_border(width=ad.line_width)
                annot.set_colors(stroke=c, fill=fc)
                return annot

            case AnnotationType.LINE | AnnotationType.ARROW:
                p1 = fitz.Point(r.x0, r.y0)
                p2 = fitz.Point(r.x1, r.y1)
                annot = page.add_line_annot(p1, p2)
                annot.set_border(width=ad.line_width)
                annot.set_colors(stroke=c)
                if ad.annot_type == AnnotationType.ARROW:
                    annot.set_line_ends(fitz.PDF_ANNOT_LE_OPEN_ARROW, fitz.PDF_ANNOT_LE_NONE)
                return annot

            case AnnotationType.STAMP:
                return page.add_stamp_annot(r, stamp=ad.stamp_name)

            case _:
                log.warning("Unhandled annotation type: %s", ad.annot_type)
                return None

    def _annot_to_def(self, annot: fitz.Annot, page_index: int) -> Optional[AnnotationDef]:
        type_map = {
            fitz.PDF_ANNOT_HIGHLIGHT: AnnotationType.HIGHLIGHT,
            fitz.PDF_ANNOT_UNDERLINE: AnnotationType.UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT: AnnotationType.STRIKEOUT,
            fitz.PDF_ANNOT_TEXT: AnnotationType.NOTE,
            fitz.PDF_ANNOT_FREE_TEXT: AnnotationType.TEXT_BOX,
            fitz.PDF_ANNOT_INK: AnnotationType.INK,
            fitz.PDF_ANNOT_SQUARE: AnnotationType.RECTANGLE,
            fitz.PDF_ANNOT_CIRCLE: AnnotationType.ELLIPSE,
            fitz.PDF_ANNOT_LINE: AnnotationType.LINE,
            fitz.PDF_ANNOT_STAMP: AnnotationType.STAMP,
        }
        at = type_map.get(annot.type[0])
        if at is None:
            return None
        r = annot.rect
        info = annot.info
        colors = annot.colors
        stroke = colors.get("stroke") or (1.0, 0.9, 0.0)
        return AnnotationDef(
            annot_type=at,
            page_index=page_index,
            rect=(r.x0, r.y0, r.x1, r.y1),
            content=info.get("content", ""),
            author=info.get("title", ""),
            color=tuple(stroke[:3]) if stroke else (1.0, 0.9, 0.0),
            opacity=annot.opacity,
        )
