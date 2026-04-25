"""
PDF Canvas — QGraphicsScene + QGraphicsView that renders pages and hosts
interactive overlay items (form fields, annotations, signature fields).

Tool modes: SELECT, TEXT_FIELD, CHECKBOX, RADIO, DROPDOWN, SIGNATURE,
            HIGHLIGHT, NOTE, RECTANGLE, ELLIPSE, LINE, ARROW, INK, STAMP
"""

import logging
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from pdfstudio.commands.annotation_commands import AddAnnotationCommand, DeleteAnnotationCommand
from pdfstudio.commands.base import UndoStack
from pdfstudio.commands.field_commands import AddFieldCommand, DeleteFieldCommand
from pdfstudio.engine.annotations import AnnotationDef, AnnotationType
from pdfstudio.engine.fields import FieldDef, FieldType
from pdfstudio.models.document_model import DocumentModel
from pdfstudio.views.overlay_items import OverlayManager
from pdfstudio.views.text_select import TextSelector

log = logging.getLogger(__name__)

PAGE_GAP = 20  # vertical gap between pages in pixels
PAGE_SHADOW = 6  # drop-shadow size
MIN_FIELD_SIZE = 20  # minimum drag size to create a field


class ToolMode(Enum):
    SELECT = auto()
    TEXT_SELECT = auto()  # text extraction / copy-paste
    # Form fields
    TEXT_FIELD = auto()
    CHECKBOX = auto()
    RADIO = auto()
    DROPDOWN = auto()
    LISTBOX = auto()
    SIGNATURE_FIELD = auto()
    BUTTON = auto()
    # Annotations
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKEOUT = auto()
    NOTE = auto()
    TEXT_BOX = auto()
    INK = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    LINE = auto()
    ARROW = auto()
    STAMP = auto()


# Map tool modes to their annotation types
_TOOL_TO_ANNOT = {
    ToolMode.HIGHLIGHT: AnnotationType.HIGHLIGHT,
    ToolMode.UNDERLINE: AnnotationType.UNDERLINE,
    ToolMode.STRIKEOUT: AnnotationType.STRIKEOUT,
    ToolMode.NOTE: AnnotationType.NOTE,
    ToolMode.TEXT_BOX: AnnotationType.TEXT_BOX,
    ToolMode.INK: AnnotationType.INK,
    ToolMode.RECTANGLE: AnnotationType.RECTANGLE,
    ToolMode.ELLIPSE: AnnotationType.ELLIPSE,
    ToolMode.LINE: AnnotationType.LINE,
    ToolMode.ARROW: AnnotationType.ARROW,
    ToolMode.STAMP: AnnotationType.STAMP,
}

# Map tool modes to field types
_TOOL_TO_FIELD = {
    ToolMode.TEXT_FIELD: FieldType.TEXT,
    ToolMode.CHECKBOX: FieldType.CHECKBOX,
    ToolMode.RADIO: FieldType.RADIO,
    ToolMode.DROPDOWN: FieldType.DROPDOWN,
    ToolMode.LISTBOX: FieldType.LISTBOX,
    ToolMode.SIGNATURE_FIELD: FieldType.SIGNATURE,
    ToolMode.BUTTON: FieldType.BUTTON,
}


class PDFScene(QGraphicsScene):
    """Holds page pixmap items and overlay graphics items."""

    page_clicked = Signal(int, QPointF)  # page_index, point in page coords

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_items: list[QGraphicsPixmapItem] = []
        self._page_rects: list[QRectF] = []  # scene coords of each page

    def clear_pages(self):
        self.clear()
        self._page_items.clear()
        self._page_rects.clear()

    def add_page(self, pixmap: QPixmap, y_offset: float) -> QGraphicsPixmapItem:
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(0, y_offset)
        item.setZValue(0)
        self.addItem(item)
        self._page_items.append(item)
        self._page_rects.append(QRectF(0, y_offset, pixmap.width(), pixmap.height()))
        return item

    def update_page(self, index: int, pixmap: QPixmap) -> None:
        if 0 <= index < len(self._page_items):
            self._page_items[index].setPixmap(pixmap)

    def page_rect(self, index: int) -> QRectF | None:
        if 0 <= index < len(self._page_rects):
            return self._page_rects[index]
        return None

    def page_at_pos(self, scene_pos: QPointF) -> tuple[int, QPointF]:
        """Returns (page_index, point_in_page_coords) or (-1, QPointF())."""
        for i, rect in enumerate(self._page_rects):
            if rect.contains(scene_pos):
                local = scene_pos - rect.topLeft()
                return i, local
        return -1, QPointF()

    def page_count(self) -> int:
        return len(self._page_items)


class PDFView(QGraphicsView):
    """
    Main viewing widget. Handles:
    - Pan (middle-mouse or Space+drag)
    - Zoom (Ctrl+scroll, Ctrl+=/-)
    - Tool mode interactions (rubber-band drag to place fields/annotations)
    - Ink drawing
    """

    tool_changed = Signal(ToolMode)
    status_message = Signal(str)
    page_changed = Signal(int)  # current visible page changed

    def __init__(self, model: DocumentModel, undo_stack: UndoStack, parent=None):
        super().__init__(parent)
        self._model = model
        self._undo = undo_stack
        self._tool = ToolMode.SELECT
        self._dpi = 150
        self._zoom = 1.0
        self._current_page = 0

        self._scene = PDFScene(self)
        self.setScene(self._scene)

        # Overlay manager for interactive field/annotation handles
        self._overlay = OverlayManager(self._scene)

        # Text selector
        self._text_selector = TextSelector(self._scene, self)
        self._text_selector.text_selected.connect(
            lambda t: self.status_message.emit(f"Selected: {len(t)} chars — Ctrl+C to copy")
        )

        # Ink drawing state
        self._ink_drawing = False
        self._ink_points: list[tuple[float, float]] = []
        self._ink_item: QGraphicsRectItem | None = None

        # Drag-to-place state
        self._drag_start: QPointF | None = None
        self._drag_rect_item: QGraphicsRectItem | None = None
        self._drag_page: int = -1

        # Annotation color / properties (set from properties panel)
        self.annot_color = QColor(255, 230, 0)
        self.annot_opacity = 0.5
        self.annot_line_width = 1.5
        self.stamp_name = "Draft"
        self.field_counter: dict[str, int] = {}  # for auto-naming new fields

        self._setup_view()
        self._connect_model()

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def _setup_view(self):
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setBackgroundBrush(QBrush(QColor("#3C3C3C")))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _connect_model(self):
        self._model.document_changed.connect(self._reload_all)
        self._model.page_modified.connect(self._reload_page)
        self._model.fields_changed.connect(self._reload_page)
        self._model.annotations_changed.connect(self._reload_page)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_tool(self, mode: ToolMode) -> None:
        self._tool = mode
        if mode == ToolMode.SELECT:
            cursor = Qt.ArrowCursor
        elif mode == ToolMode.TEXT_SELECT:
            cursor = Qt.IBeamCursor
        else:
            cursor = Qt.CrossCursor
        self.setCursor(QCursor(cursor))
        if mode != ToolMode.TEXT_SELECT:
            self._text_selector.clear()
        self.tool_changed.emit(mode)

    def copy_selected_text(self) -> bool:
        """Copy currently selected text to clipboard. Returns True if anything copied."""
        return self._text_selector.copy_to_clipboard()

    def select_all_text(self) -> None:
        """Select all text on the current page."""
        page_rect = self._scene.page_rect(self._current_page)
        if not page_rect:
            return
        fitz_page = self._model._pdf.raw()[self._current_page]
        self._text_selector.select_all_text(fitz_page, page_rect)

    def set_dpi(self, dpi: int) -> None:
        self._dpi = dpi
        self._reload_all()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom * 1.2)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom / 1.2)

    def zoom_fit_page(self) -> None:
        if not self._model.is_open:
            return
        w, h = self._model.page_size(self._current_page)
        vw = self.viewport().width() - 40
        vh = self.viewport().height() - 40
        scale = min(vw / w, vh / h)
        self._set_zoom(scale * 72 / self._dpi)

    def zoom_fit_width(self) -> None:
        if not self._model.is_open:
            return
        w, _ = self._model.page_size(self._current_page)
        vw = self.viewport().width() - 40
        self._set_zoom((vw / w) * 72 / self._dpi)

    def scroll_to_page(self, index: int) -> None:
        rect = self._scene.page_rect(index)
        if rect:
            self.ensureVisible(rect, 20, 20)
            self._current_page = index
            self.page_changed.emit(index)

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _reload_all(self) -> None:
        self._overlay.clear_all()
        self._scene.clear_pages()
        if not self._model.is_open:
            return

        y = PAGE_GAP
        for i in range(self._model.page_count):
            pixmap = self._model.render_page(i, self._dpi)
            if pixmap:
                self._scene.add_page(pixmap, y)
                y += pixmap.height() + PAGE_GAP

        # Set scene rect with padding
        total_h = y
        max_w = max(
            (
                self._scene.page_rect(i).width()
                for i in range(self._model.page_count)
                if self._scene.page_rect(i)
            ),
            default=0,
        )
        self._scene.setSceneRect(-PAGE_GAP, -PAGE_GAP, max_w + PAGE_GAP * 2, total_h)

        for i in range(self._model.page_count):
            self._load_page_overlays(i)

    def _reload_page(self, index: int) -> None:
        pixmap = self._model.render_page(index, self._dpi)
        if pixmap:
            self._scene.update_page(index, pixmap)
        for item in self._overlay.items_on_page(index):
            self._overlay.remove(item)
        self._load_page_overlays(index)

    def _load_page_overlays(self, page_idx: int) -> None:
        """Add interactive overlay items for all fields and annotations on a page."""
        page_rect = self._scene.page_rect(page_idx)
        if not page_rect or page_rect.width() == 0 or page_rect.height() == 0:
            return

        pw, ph = self._model.page_size(page_idx)
        scale_x = pw / page_rect.width()  # page pts per scene pixel
        scale_y = ph / page_rect.height()
        page_orig = page_rect.topLeft()

        def pt_to_scene(x0, y0, x1, y1) -> QRectF:
            return QRectF(
                page_orig.x() + x0 / scale_x,
                page_orig.y() + y0 / scale_y,
                (x1 - x0) / scale_x,
                (y1 - y0) / scale_y,
            )

        for fd in self._model.load_fields(page_idx):
            sr = pt_to_scene(*fd.rect)
            self._overlay.add_field(
                sr,
                fd.field_type.value,
                fd.name,
                scale_x=scale_x,
                scale_y=scale_y,
                page_origin=page_orig,
                page_index=page_idx,
                on_deleted=lambda it, f=fd: self._on_field_deleted(it, f),
            )

        for ad, xref in self._model.load_annotations_with_xrefs(page_idx):
            sr = pt_to_scene(*ad.rect)
            c = ad.color
            from PySide6.QtGui import QColor as _QColor

            color = _QColor(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 80)
            self._overlay.add_annotation(
                sr,
                ad.annot_type.value,
                color,
                scale_x=scale_x,
                scale_y=scale_y,
                page_origin=page_orig,
                page_index=page_idx,
                on_deleted=lambda it, a=ad, x=xref: self._on_annot_deleted(it, a, x),
            )

    def _on_field_deleted(self, item, fd: FieldDef) -> None:
        self._overlay.remove(item)
        self._undo.push(DeleteFieldCommand(self._model, fd))

    def _on_annot_deleted(self, item, ad: AnnotationDef, xref: int) -> None:
        self._overlay.remove(item)
        self._undo.push(DeleteAnnotationCommand(self._model, ad, xref))

    def set_zoom(self, zoom: float) -> None:
        """Public setter for zoom factor (1.0 = 100%)."""
        self._set_zoom(zoom)

    def _set_zoom(self, zoom: float) -> None:
        zoom = max(0.1, min(zoom, 8.0))
        factor = zoom / self._zoom
        self._zoom = zoom
        self.scale(factor, factor)
        self.status_message.emit(f"Zoom: {int(zoom * 100)}%")

    # ------------------------------------------------------------------ #
    # Mouse events
    # ------------------------------------------------------------------ #

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            self._set_zoom(self._zoom * (1.15 if delta > 0 else 1 / 1.15))
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake = QMouseEvent(
                event.type(), event.position(), Qt.LeftButton, Qt.LeftButton, event.modifiers()
            )
            super().mousePressEvent(fake)
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        page_idx, local_pos = self._scene.page_at_pos(scene_pos)

        if self._tool == ToolMode.SELECT:
            super().mousePressEvent(event)
            return

        if self._tool == ToolMode.TEXT_SELECT:
            if page_idx >= 0:
                self._text_selector.begin_drag(scene_pos, page_idx)
                self._drag_page = page_idx
            return

        if self._tool == ToolMode.INK:
            if page_idx >= 0:
                self._ink_drawing = True
                self._ink_points = [(local_pos.x(), local_pos.y())]
            return

        # Drag-to-place for all other tools
        if event.button() == Qt.LeftButton and page_idx >= 0:
            self._drag_start = scene_pos
            self._drag_page = page_idx
            # Ghost rect
            self._drag_rect_item = QGraphicsRectItem()
            pen = QPen(QColor("#0066CC"), 1.5, Qt.DashLine)
            self._drag_rect_item.setPen(pen)
            self._drag_rect_item.setBrush(QBrush(QColor(0, 102, 204, 30)))
            self._scene.addItem(self._drag_rect_item)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())

        if self._tool == ToolMode.TEXT_SELECT:
            self._text_selector.update_drag(scene_pos)
            return

        if self._tool == ToolMode.INK and self._ink_drawing:
            page_idx, local_pos = self._scene.page_at_pos(scene_pos)
            if page_idx >= 0:
                self._ink_points.append((local_pos.x(), local_pos.y()))
            return

        if self._drag_start and self._drag_rect_item:
            drag_rect = QRectF(self._drag_start, scene_pos).normalized()
            self._drag_rect_item.setRect(drag_rect)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        if self._tool == ToolMode.TEXT_SELECT:
            page_rect = self._scene.page_rect(self._drag_page) if self._drag_page >= 0 else None
            if page_rect and self._drag_page >= 0:
                fitz_page = self._model._pdf.raw()[self._drag_page]
                self._text_selector.end_drag(scene_pos, fitz_page, page_rect)
            self._drag_page = -1
            return

        if self._tool == ToolMode.INK and self._ink_drawing:
            self._ink_drawing = False
            if len(self._ink_points) > 2:
                page_idx, _ = self._scene.page_at_pos(scene_pos)
                if page_idx < 0:
                    page_idx = self._drag_page
                self._commit_ink(page_idx)
            self._ink_points.clear()
            return

        if self._drag_start and self._drag_rect_item and self._drag_page >= 0:
            drag_rect = QRectF(self._drag_start, scene_pos).normalized()
            self._scene.removeItem(self._drag_rect_item)
            self._drag_rect_item = None

            page_rect = self._scene.page_rect(self._drag_page)
            if (
                page_rect
                and drag_rect.width() > MIN_FIELD_SIZE
                and drag_rect.height() > MIN_FIELD_SIZE
            ):
                # Convert scene rect → page points
                scale_x = self._model.page_size(self._drag_page)[0] / page_rect.width()
                scale_y = self._model.page_size(self._drag_page)[1] / page_rect.height()
                local_rect = drag_rect.translated(-page_rect.topLeft())
                pt_rect = (
                    local_rect.x() * scale_x,
                    local_rect.y() * scale_y,
                    local_rect.right() * scale_x,
                    local_rect.bottom() * scale_y,
                )
                self._commit_tool(self._drag_page, pt_rect)

            self._drag_start = None
            self._drag_page = -1

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.ZoomIn):
            self.zoom_in()
        elif event.matches(QKeySequence.ZoomOut):
            self.zoom_out()
        elif event.matches(QKeySequence.Copy):
            self.copy_selected_text()
        elif event.matches(QKeySequence.SelectAll):
            self.select_all_text()
        elif event.key() == Qt.Key_Escape:
            self._text_selector.clear()
            self.set_tool(ToolMode.SELECT)
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------ #
    # Commit actions
    # ------------------------------------------------------------------ #

    def _commit_tool(self, page_idx: int, pt_rect: tuple) -> None:
        if self._tool in _TOOL_TO_FIELD:
            self._place_field(page_idx, pt_rect)
        elif self._tool in _TOOL_TO_ANNOT:
            self._place_annotation(page_idx, pt_rect)

    def _place_field(self, page_idx: int, pt_rect: tuple) -> None:
        field_type = _TOOL_TO_FIELD[self._tool]
        count = self.field_counter.get(field_type.value, 0) + 1
        self.field_counter[field_type.value] = count
        name = f"{field_type.value}_{count}"

        fd = FieldDef(
            name=name,
            field_type=field_type,
            page_index=page_idx,
            rect=pt_rect,
        )
        self._undo.push(AddFieldCommand(self._model, fd))
        log.info("Placed %s field '%s' on page %d", field_type.value, name, page_idx)

    def _place_annotation(self, page_idx: int, pt_rect: tuple) -> None:
        annot_type = _TOOL_TO_ANNOT[self._tool]
        c = (self.annot_color.redF(), self.annot_color.greenF(), self.annot_color.blueF())

        ad = AnnotationDef(
            annot_type=annot_type,
            page_index=page_idx,
            rect=pt_rect,
            color=c,
            opacity=self.annot_opacity,
            line_width=self.annot_line_width,
            stamp_name=self.stamp_name,
        )
        self._undo.push(AddAnnotationCommand(self._model, ad))

    def _commit_ink(self, page_idx: int) -> None:
        if not self._ink_points:
            return
        # Convert pixel coords → page points
        page_rect = self._scene.page_rect(page_idx)
        if not page_rect:
            return
        pw, ph = self._model.page_size(page_idx)
        sx = pw / page_rect.width()
        sy = ph / page_rect.height()
        pts = [(x * sx, y * sy) for x, y in self._ink_points]

        # Bounding rect for the ink stroke
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        pt_rect = (min(xs), min(ys), max(xs), max(ys))

        c = (self.annot_color.redF(), self.annot_color.greenF(), self.annot_color.blueF())
        ad = AnnotationDef(
            annot_type=AnnotationType.INK,
            page_index=page_idx,
            rect=pt_rect,
            ink_list=[pts],
            color=c,
            line_width=self.annot_line_width,
        )
        self._undo.push(AddAnnotationCommand(self._model, ad))
