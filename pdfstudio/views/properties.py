"""
Properties panel — shows context-sensitive controls for the selected
tool, field, or annotation.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdfstudio.engine.fields import FieldDef
from pdfstudio.utils.theme import BORDER, TEXT_L


class ColorButton(QPushButton):
    """Button that shows and picks a color."""

    color_changed = Signal(QColor)

    def __init__(self, color: QColor = QColor(255, 230, 0), parent=None):
        super().__init__(parent)
        self._color = color
        self._apply()
        self.setFixedSize(32, 24)
        self.clicked.connect(self._pick)

    def _apply(self) -> None:
        self.setStyleSheet(
            f"background:{self._color.name()}; border:1px solid #555; border-radius:3px;"
        )

    def _pick(self) -> None:
        c = QColorDialog.getColor(self._color, self, "Choose Color")
        if c.isValid():
            self._color = c
            self._apply()
            self.color_changed.emit(c)

    @property
    def color(self) -> QColor:
        return self._color


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet(f"color: {BORDER};")


class PropertiesPanel(QWidget):
    """Right-side properties panel."""

    # Emitted when a property changes — caller decides what to do
    field_property_changed = Signal(str, object)  # property_name, value
    annot_color_changed = Signal(QColor)
    annot_opacity_changed = Signal(float)
    annot_line_width_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("properties_panel")
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignTop)

        self._title = QLabel("Properties")
        self._title.setObjectName("panel_title")
        self._layout.addWidget(self._title)
        self._layout.addWidget(Divider())

        self._annotation_section()
        self._layout.addStretch()

    # ------------------------------------------------------------------ #
    # Sections
    # ------------------------------------------------------------------ #

    def _annotation_section(self) -> None:
        lbl = QLabel("Annotation")
        lbl.setObjectName("section_title")
        self._layout.addWidget(lbl)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)

        self._annot_color = ColorButton(QColor(255, 230, 0))
        self._annot_color.color_changed.connect(self.annot_color_changed)
        form.addRow("Color:", self._annot_color)

        self._opacity_spin = QDoubleSpinBox()
        self._opacity_spin.setRange(0.1, 1.0)
        self._opacity_spin.setSingleStep(0.1)
        self._opacity_spin.setValue(0.5)
        self._opacity_spin.valueChanged.connect(self.annot_opacity_changed)
        form.addRow("Opacity:", self._opacity_spin)

        self._line_width = QDoubleSpinBox()
        self._line_width.setRange(0.5, 10.0)
        self._line_width.setSingleStep(0.5)
        self._line_width.setValue(1.5)
        self._line_width.valueChanged.connect(self.annot_line_width_changed)
        form.addRow("Line width:", self._line_width)

        self._layout.addLayout(form)
        self._layout.addWidget(Divider())

    def show_field_properties(self, fd: FieldDef) -> None:
        """Populate panel with field-specific properties."""
        self._title.setText(f"Field: {fd.name}")
        # In a full implementation we'd rebuild form rows for the field type.
        # For now, show a summary label.
        self._clear_field_section()
        info = QLabel(
            f"Type: {fd.field_type.value}\n"
            f"Page: {fd.page_index + 1}\n"
            f"Required: {'Yes' if fd.required else 'No'}"
        )
        info.setStyleSheet(f"color: {TEXT_L}; font-size: 12px;")
        info.setWordWrap(True)
        self._field_info = info
        self._layout.insertWidget(3, info)

    def _clear_field_section(self) -> None:
        if hasattr(self, "_field_info") and self._field_info:
            self._field_info.setParent(None)
            self._field_info = None
