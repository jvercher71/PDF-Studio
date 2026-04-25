"""
Overlay items — interactive QGraphicsItem subclasses that sit on top of
rendered page pixmaps. Each placed field or annotation gets one of these.

Features:
  - 8-handle resize (corners + edge midpoints)
  - Drag to move
  - Delete key removes the item
  - Double-click opens the properties/edit dialog
  - Emits signals so the controller can sync changes back to the PDF engine
"""

import logging
from collections.abc import Callable
from typing import ClassVar

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QKeyEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

log = logging.getLogger(__name__)

# ── Visual constants ───────────────────────────────────────────────────
HANDLE_SIZE = 8  # px — handle square size
HANDLE_COLOR = QColor("#0066CC")
HANDLE_BORDER = QColor("#FFFFFF")
SEL_BORDER = QColor("#0066CC")
SEL_FILL = QColor(0, 102, 204, 18)
FIELD_COLORS = {
    "text": QColor(0, 102, 204, 30),
    "checkbox": QColor(0, 160, 80, 30),
    "radio": QColor(0, 160, 80, 30),
    "dropdown": QColor(160, 80, 0, 30),
    "listbox": QColor(160, 80, 0, 30),
    "signature": QColor(100, 0, 160, 30),
    "button": QColor(180, 60, 0, 30),
}
FIELD_BORDER_COLORS = {
    k: QColor(v.red(), v.green(), v.blue(), 180) for k, v in FIELD_COLORS.items()
}


# ── Handle positions (8 handles) ───────────────────────────────────────
class Handle:
    TL = 0
    TC = 1
    TR = 2
    ML = 3
    MR = 4
    BL = 5
    BC = 6
    BR = 7

    CURSORS: ClassVar[dict[int, Qt.CursorShape]] = {
        TL: Qt.SizeFDiagCursor,
        TC: Qt.SizeVerCursor,
        TR: Qt.SizeBDiagCursor,
        ML: Qt.SizeHorCursor,
        MR: Qt.SizeHorCursor,
        BL: Qt.SizeBDiagCursor,
        BC: Qt.SizeVerCursor,
        BR: Qt.SizeFDiagCursor,
    }


def _handle_rects(rect: QRectF) -> dict[int, QRectF]:
    """Return the 8 handle QRectFs for a given bounding rect."""
    hs = HANDLE_SIZE
    hh = hs / 2
    cx = rect.center().x()
    cy = rect.center().y()
    x0, y0 = rect.left(), rect.top()
    x1, y1 = rect.right(), rect.bottom()

    def mk(x: float, y: float) -> QRectF:
        return QRectF(x - hh, y - hh, hs, hs)

    return {
        Handle.TL: mk(x0, y0),
        Handle.TC: mk(cx, y0),
        Handle.TR: mk(x1, y0),
        Handle.ML: mk(x0, cy),
        Handle.MR: mk(x1, cy),
        Handle.BL: mk(x0, y1),
        Handle.BC: mk(cx, y1),
        Handle.BR: mk(x1, y1),
    }


# ── Signals carrier (QGraphicsObject doesn't allow multiple inheritance easily) ─
class OverlaySignals(QObject):
    moved = Signal(object, QRectF)  # item, new_rect in page-point coords
    resized = Signal(object, QRectF)
    deleted = Signal(object)
    double_clicked = Signal(object)


# ── Base overlay item ──────────────────────────────────────────────────
class OverlayItem(QGraphicsItem):
    """
    Base class for all interactive overlay items (fields + annotations).

    rect is in SCENE coordinates (pixels). page_to_scene / scene_to_page
    conversion is handled externally by the canvas, which sets self.scale_x
    and self.scale_y so the item can report changes in page-point space.
    """

    def __init__(
        self,
        scene_rect: QRectF,
        label: str = "",
        fill_color: QColor = QColor(0, 102, 204, 30),
        border_color: QColor = QColor(0, 102, 204, 180),
        parent: QGraphicsItem = None,
    ):
        super().__init__(parent)
        self._rect = scene_rect
        self._label = label
        self._fill = fill_color
        self._border = border_color

        self.signals = OverlaySignals()
        self.scale_x: float = 1.0  # scene-px → page-pt conversion factors
        self.scale_y: float = 1.0
        self.page_origin: QPointF = QPointF(0, 0)  # scene position of page top-left

        # State
        self._active_handle: int | None = None
        self._drag_start: QPointF | None = None
        self._drag_orig_rect: QRectF | None = None

        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
            | QGraphicsItem.ItemIsFocusable,
        )
        self.setAcceptHoverEvents(True)
        self.setPos(scene_rect.topLeft())
        # Internal rect always has origin at (0,0)
        self._local_rect = QRectF(0, 0, scene_rect.width(), scene_rect.height())

    # ── QGraphicsItem protocol ───────────────────────────────────────

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE
        return self._local_rect.adjusted(-pad, -pad, pad, pad)

    def shape(self):
        from PySide6.QtGui import QPainterPath

        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None
    ) -> None:
        painter.setRenderHint(QPainter.Antialiasing)

        # Body
        painter.setBrush(QBrush(self._fill))
        pen = QPen(self._border, 1.5, Qt.DashLine if not self.isSelected() else Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRoundedRect(self._local_rect, 3, 3)

        # Label
        if self._label:
            painter.setPen(QPen(self._border.darker(130)))
            font = QFont("Arial", 9)
            painter.setFont(font)
            painter.drawText(
                self._local_rect.adjusted(4, 2, -4, -2),
                Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                self._label,
            )

        # Handles when selected
        if self.isSelected():
            self._paint_handles(painter)

    def _paint_handles(self, painter: QPainter) -> None:
        painter.setPen(QPen(HANDLE_BORDER, 1))
        painter.setBrush(QBrush(HANDLE_COLOR))
        for rect in _handle_rects(self._local_rect).values():
            painter.drawRect(rect)

    # ── Hover ────────────────────────────────────────────────────────

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if self.isSelected():
            for handle_id, rect in _handle_rects(self._local_rect).items():
                if rect.contains(event.pos()):
                    self.setCursor(QCursor(Handle.CURSORS[handle_id]))
                    return
        self.setCursor(QCursor(Qt.SizeAllCursor))

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.setCursor(QCursor(Qt.ArrowCursor))

    # ── Mouse ────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._active_handle = None
            if self.isSelected():
                for handle_id, rect in _handle_rects(self._local_rect).items():
                    if rect.contains(event.pos()):
                        self._active_handle = handle_id
                        self._drag_start = event.pos()
                        self._drag_orig_rect = QRectF(self._local_rect)
                        event.accept()
                        return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle is not None and self._drag_start is not None:
            delta = event.pos() - self._drag_start
            self._resize(self._active_handle, delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle is not None:
            self._active_handle = None
            self._drag_start = None
            self._drag_orig_rect = None
            self.signals.resized.emit(self, self._scene_rect_in_page_pts())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.signals.double_clicked.emit(self)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.signals.deleted.emit(self)
            return
        # Arrow-key nudge (1px per press, 10px with Shift)
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        pos = self.pos()
        if event.key() == Qt.Key_Left:
            self.setPos(pos.x() - step, pos.y())
        elif event.key() == Qt.Key_Right:
            self.setPos(pos.x() + step, pos.y())
        elif event.key() == Qt.Key_Up:
            self.setPos(pos.x(), pos.y() - step)
        elif event.key() == Qt.Key_Down:
            self.setPos(pos.x(), pos.y() + step)
        else:
            super().keyPressEvent(event)
            return
        self.signals.moved.emit(self, self._scene_rect_in_page_pts())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.signals.moved.emit(self, self._scene_rect_in_page_pts())
        return super().itemChange(change, value)

    # ── Resize logic ─────────────────────────────────────────────────

    def _resize(self, handle: int, delta: QPointF) -> None:
        orig = self._drag_orig_rect
        min_size = HANDLE_SIZE * 3

        x0, y0 = orig.left(), orig.top()
        x1, y1 = orig.right(), orig.bottom()
        dx, dy = delta.x(), delta.y()

        if handle in (Handle.TL, Handle.ML, Handle.BL):
            x0 = min(x0 + dx, x1 - min_size)
        if handle in (Handle.TR, Handle.MR, Handle.BR):
            x1 = max(x1 + dx, x0 + min_size)
        if handle in (Handle.TL, Handle.TC, Handle.TR):
            y0 = min(y0 + dy, y1 - min_size)
        if handle in (Handle.BL, Handle.BC, Handle.BR):
            y1 = max(y1 + dy, y0 + min_size)

        new_rect = QRectF(x0, y0, x1 - x0, y1 - y0)
        # Move item position if top-left shifted
        offset = new_rect.topLeft() - orig.topLeft()
        if offset.manhattanLength() > 0:
            self.setPos(self.pos() + offset)
            new_rect.translate(-offset)

        self.prepareGeometryChange()
        self._local_rect = new_rect
        self.update()

    # ── Coordinate conversion ────────────────────────────────────────

    def _scene_rect_in_page_pts(self) -> QRectF:
        """Return current rect as page-point coordinates for the PDF engine."""
        tl = self.pos() - self.page_origin
        return QRectF(
            tl.x() * self.scale_x,
            tl.y() * self.scale_y,
            self._local_rect.width() * self.scale_x,
            self._local_rect.height() * self.scale_y,
        )

    def update_rect(self, scene_rect: QRectF) -> None:
        """Externally update position/size (e.g. after undo)."""
        self.prepareGeometryChange()
        self.setPos(scene_rect.topLeft())
        self._local_rect = QRectF(0, 0, scene_rect.width(), scene_rect.height())
        self.update()


# ── Concrete field overlay ─────────────────────────────────────────────
class FieldOverlayItem(OverlayItem):
    """Overlay for AcroForm fields — color-coded by field type."""

    def __init__(self, scene_rect: QRectF, field_type: str, field_name: str, parent=None):
        fill = FIELD_COLORS.get(field_type, QColor(100, 100, 100, 30))
        border = FIELD_BORDER_COLORS.get(field_type, QColor(100, 100, 100, 180))
        super().__init__(
            scene_rect, label=field_name, fill_color=fill, border_color=border, parent=parent
        )
        self.field_type = field_type
        self.field_name = field_name

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        # Type badge in top-right corner
        badge_rect = QRectF(
            self._local_rect.right() - 40,
            self._local_rect.top(),
            40,
            14,
        )
        if badge_rect.isValid() and self._local_rect.width() > 50:
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QPen(self._border.darker(110)))
            painter.drawText(badge_rect, Qt.AlignRight | Qt.AlignTop, self.field_type)


# ── Concrete annotation overlay ────────────────────────────────────────
class AnnotationOverlayItem(OverlayItem):
    """Overlay for annotations (highlight, text box, shapes, etc.)."""

    def __init__(
        self,
        scene_rect: QRectF,
        annot_type: str,
        color: QColor = QColor(255, 230, 0, 80),
        parent=None,
    ):
        border = QColor(color.red(), color.green(), color.blue(), 200)
        super().__init__(
            scene_rect, label=annot_type, fill_color=color, border_color=border, parent=parent
        )
        self.annot_type = annot_type


# ── Overlay manager ────────────────────────────────────────────────────
class OverlayManager:
    """
    Tracks all overlay items on the scene.
    The canvas delegates item lifecycle here.
    """

    def __init__(self, scene):
        self._scene = scene
        self._items: list[OverlayItem] = []

    def add_field(
        self,
        scene_rect: QRectF,
        field_type: str,
        field_name: str,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        page_origin: QPointF = None,
        page_index: int = 0,
        on_moved: Callable | None = None,
        on_resized: Callable | None = None,
        on_deleted: Callable | None = None,
        on_double_clicked: Callable | None = None,
    ) -> FieldOverlayItem:
        item = FieldOverlayItem(scene_rect, field_type, field_name)
        item.scale_x = scale_x
        item.scale_y = scale_y
        item.page_origin = page_origin if page_origin is not None else QPointF(0, 0)
        item.setData(0, page_index)
        self._wire(item, on_moved, on_resized, on_deleted, on_double_clicked)
        self._scene.addItem(item)
        self._items.append(item)
        return item

    def add_annotation(
        self,
        scene_rect: QRectF,
        annot_type: str,
        color: QColor = QColor(255, 230, 0, 80),
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        page_origin: QPointF = None,
        page_index: int = 0,
        on_deleted: Callable | None = None,
    ) -> AnnotationOverlayItem:
        item = AnnotationOverlayItem(scene_rect, annot_type, color)
        item.scale_x = scale_x
        item.scale_y = scale_y
        item.page_origin = page_origin if page_origin is not None else QPointF(0, 0)
        item.setData(0, page_index)
        if on_deleted:
            item.signals.deleted.connect(on_deleted)
        self._scene.addItem(item)
        self._items.append(item)
        return item

    def remove(self, item: OverlayItem) -> None:
        if item in self._items:
            self._items.remove(item)
        self._scene.removeItem(item)

    def clear_page(self, page_items: list[OverlayItem]) -> None:
        for item in page_items:
            self.remove(item)

    def clear_all(self) -> None:
        for item in list(self._items):
            self._scene.removeItem(item)
        self._items.clear()

    def items_on_page(self, page_index: int) -> list[OverlayItem]:
        # Items store their page via setData(0, page_index)
        return [i for i in self._items if i.data(0) == page_index]

    def selected_items(self) -> list[OverlayItem]:
        return [i for i in self._items if i.isSelected()]

    def deselect_all(self) -> None:
        for item in self._items:
            item.setSelected(False)

    @staticmethod
    def _wire(item: OverlayItem, on_moved, on_resized, on_deleted, on_double_clicked) -> None:
        if on_moved:
            item.signals.moved.connect(on_moved)
        if on_resized:
            item.signals.resized.connect(on_resized)
        if on_deleted:
            item.signals.deleted.connect(on_deleted)
        if on_double_clicked:
            item.signals.double_clicked.connect(on_double_clicked)
