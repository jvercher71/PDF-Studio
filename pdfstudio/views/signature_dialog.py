"""
Signature dialog — lets the user choose how to sign:
  1. Draw their signature with the mouse
  2. Type their name (rendered in a script font)
  3. Upload an image
  4. Use a certificate (.p12 / .pfx)

Returns a SignatureConfig ready to hand to SignatureEngine.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pdfstudio.engine.signer import SignatureConfig

log = logging.getLogger(__name__)

# Cross-platform cursive font list: first available font wins; fall back to Arial.
_CURSIVE_FONTS = [
    "Dancing Script",
    "Pacifico",
    "Caveat",
    "Satisfy",
    "Great Vibes",
    "Comic Sans MS",
    "URW Chancery L",
    "Brush Script MT",
    "Segoe Script",
    "cursive",
]
_available_families = set(QFontDatabase.families())
_SCRIPT_FONTS = [f for f in _CURSIVE_FONTS if f in _available_families] or ["Arial"]


# ──────────────────────────────────────────────────────────────────────
# Draw pad
# ──────────────────────────────────────────────────────────────────────


class DrawPad(QWidget):
    """Canvas the user draws their signature on."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 180)
        self.setStyleSheet("background: #FFFFFF; border: 1px solid #555; border-radius: 4px;")
        self.setCursor(Qt.CrossCursor)
        self._paths: list[list[QPoint]] = []
        self._current: list[QPoint] = []
        self._pen = QPen(QColor("#1A1A2E"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self._current = [e.position().toPoint()]

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._current:
            self._current.append(e.position().toPoint())
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self._current:
            self._paths.append(self._current)
            self._current = []

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))

        # Baseline
        painter.setPen(QPen(QColor("#CCCCCC"), 1, Qt.DashLine))
        y = int(self.height() * 0.72)
        painter.drawLine(20, y, self.width() - 20, y)

        painter.setPen(self._pen)
        for path in self._paths + ([self._current] if self._current else []):
            if len(path) < 2:
                continue
            for i in range(1, len(path)):
                painter.drawLine(path[i - 1], path[i])

    def clear(self) -> None:
        self._paths.clear()
        self._current.clear()
        self.update()

    def is_empty(self) -> bool:
        return not self._paths

    def to_png_bytes(self) -> bytes:
        """Export the drawing as PNG bytes."""
        pix = QPixmap(self.size())
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self._pen)
        for path in self._paths:
            if len(path) < 2:
                continue
            for i in range(1, len(path)):
                painter.drawLine(path[i - 1], path[i])
        painter.end()

        from PySide6.QtCore import QBuffer, QIODevice

        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        pix.save(buf, "PNG")
        return bytes(buf.data())


# ──────────────────────────────────────────────────────────────────────
# Tab: Draw
# ──────────────────────────────────────────────────────────────────────


class DrawTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Draw your signature:"))
        self._pad = DrawPad()
        layout.addWidget(self._pad, alignment=Qt.AlignHCenter)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._pad.clear)
        layout.addWidget(clear_btn, alignment=Qt.AlignRight)
        layout.addStretch()

    def image_bytes(self) -> bytes | None:
        if self._pad.is_empty():
            return None
        return self._pad.to_png_bytes()

    def is_ready(self) -> bool:
        return not self._pad.is_empty()


# ──────────────────────────────────────────────────────────────────────
# Tab: Type
# ──────────────────────────────────────────────────────────────────────


class TypeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Type your name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Your Full Name")
        self._name_edit.textChanged.connect(self._preview)
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("Style:"))
        self._font_combo = QComboBox()
        self._font_combo.addItems(["Script", "Elegant", "Bold", "Modern"])
        self._font_combo.currentIndexChanged.connect(self._preview)
        layout.addWidget(self._font_combo)

        # Preview
        self._preview_label = QLabel()
        self._preview_label.setFixedHeight(80)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "background: white; border: 1px solid #555; border-radius: 4px;"
        )
        layout.addWidget(self._preview_label)
        layout.addStretch()

        self._preview()

    def _preview(self) -> None:
        name = self._name_edit.text() or "Your Name"
        style_idx = self._font_combo.currentIndex()
        fonts = _SCRIPT_FONTS
        font_name = fonts[min(style_idx, len(fonts) - 1)]

        pix = QPixmap(500, 80)
        pix.fill(Qt.white)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        font = QFont(font_name, 32, QFont.Normal, True)
        painter.setFont(font)
        painter.setPen(QColor("#1A1A2E"))
        painter.drawText(pix.rect(), Qt.AlignCenter, name)
        painter.end()
        self._preview_label.setPixmap(pix)

    def name(self) -> str:
        return self._name_edit.text().strip()

    def image_bytes(self) -> bytes | None:
        name = self.name()
        if not name:
            return None
        pix = QPixmap(500, 120)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        style_idx = self._font_combo.currentIndex()
        font_name = _SCRIPT_FONTS[min(style_idx, len(_SCRIPT_FONTS) - 1)]
        font = QFont(font_name, 36, QFont.Normal, True)
        painter.setFont(font)
        painter.setPen(QColor("#1A1A2E"))
        painter.drawText(pix.rect(), Qt.AlignCenter, name)
        painter.end()

        from PySide6.QtCore import QBuffer, QIODevice

        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        pix.save(buf, "PNG")
        return bytes(buf.data())

    def is_ready(self) -> bool:
        return bool(self.name())


# ──────────────────────────────────────────────────────────────────────
# Tab: Image
# ──────────────────────────────────────────────────────────────────────


class ImageTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bytes: bytes | None = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Upload a signature image (PNG/JPG):"))
        btn = QPushButton("Browse…")
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

        self._preview = QLabel("No image selected")
        self._preview.setFixedHeight(100)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            "background: white; border: 1px solid #555; border-radius: 4px; color: #999;"
        )
        layout.addWidget(self._preview)
        layout.addStretch()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Signature Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
        )
        if path:
            self._bytes = Path(path).read_bytes()
            pix = QPixmap(path).scaled(
                self._preview.width(),
                self._preview.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._preview.setPixmap(pix)

    def image_bytes(self) -> bytes | None:
        return self._bytes

    def is_ready(self) -> bool:
        return self._bytes is not None


# ──────────────────────────────────────────────────────────────────────
# Tab: Certificate
# ──────────────────────────────────────────────────────────────────────


class CertTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cert_path: str | None = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Select your PKCS#12 certificate (.p12 / .pfx):"))
        cert_row = QHBoxLayout()
        self._cert_label = QLabel("No certificate selected")
        self._cert_label.setStyleSheet("color: #999;")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_cert)
        cert_row.addWidget(self._cert_label, 1)
        cert_row.addWidget(browse_btn)
        layout.addLayout(cert_row)

        layout.addWidget(QLabel("Certificate password:"))
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setPlaceholderText("Leave blank if none")
        layout.addWidget(self._password)

        layout.addWidget(QLabel("Reason:"))
        self._reason = QLineEdit()
        self._reason.setPlaceholderText("e.g. I approve this document")
        layout.addWidget(self._reason)

        layout.addWidget(QLabel("Location:"))
        self._location = QLineEdit()
        self._location.setPlaceholderText("e.g. New Orleans, LA")
        layout.addWidget(self._location)

        layout.addStretch()

    def _browse_cert(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Certificate", "", "PKCS#12 (*.p12 *.pfx);;All Files (*)"
        )
        if path:
            self._cert_path = path
            self._cert_label.setText(Path(path).name)
            self._cert_label.setStyleSheet("color: #D4D4D4;")

    def cert_path(self) -> str | None:
        return self._cert_path

    def password(self) -> str:
        return self._password.text()

    def reason(self) -> str:
        return self._reason.text()

    def location(self) -> str:
        return self._location.text()

    def is_ready(self) -> bool:
        return self._cert_path is not None


# ──────────────────────────────────────────────────────────────────────
# Main Dialog
# ──────────────────────────────────────────────────────────────────────


class SignatureDialog(QDialog):
    """
    Full signature dialog. Call exec() and then read .result_config
    if accepted.
    """

    def __init__(self, page_index: int, rect: tuple, signer_name: str = "", parent=None):
        super().__init__(parent)
        self._page_index = page_index
        self._rect = rect
        self.result_config: SignatureConfig | None = None

        self.setWindowTitle("Sign Document")
        self.setMinimumWidth(560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Signer name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Signer name:"))
        self._signer_name = QLineEdit(signer_name)
        self._signer_name.setPlaceholderText("Your Full Name")
        name_row.addWidget(self._signer_name)
        layout.addLayout(name_row)

        # Tab widget
        self._tabs = QTabWidget()
        self._draw_tab = DrawTab()
        self._type_tab = TypeTab()
        self._image_tab = ImageTab()
        self._cert_tab = CertTab()

        self._tabs.addTab(self._draw_tab, "✏ Draw")
        self._tabs.addTab(self._type_tab, "T  Type")
        self._tabs.addTab(self._image_tab, "🖼 Image")
        self._tabs.addTab(self._cert_tab, "🔐 Certificate")
        layout.addWidget(self._tabs)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Apply Signature")
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _apply(self) -> None:
        tab_idx = self._tabs.currentIndex()
        tabs = [self._draw_tab, self._type_tab, self._image_tab, self._cert_tab]
        active = tabs[tab_idx]

        if not active.is_ready():
            QMessageBox.warning(
                self, "Incomplete", "Please complete the signature before applying."
            )
            return

        signer_name = self._signer_name.text().strip()

        if tab_idx == 3:  # Certificate
            self.result_config = SignatureConfig(
                page_index=self._page_index,
                rect=self._rect,
                signer_name=signer_name,
                sig_type="cert",
                cert_path=self._cert_tab.cert_path(),
                cert_password=self._cert_tab.password(),
                reason=self._cert_tab.reason(),
                location=self._cert_tab.location(),
            )
        else:
            img_bytes = active.image_bytes()
            sig_type = "drawn" if tab_idx in (0, 2) else "typed"
            self.result_config = SignatureConfig(
                page_index=self._page_index,
                rect=self._rect,
                signer_name=signer_name,
                sig_type=sig_type,
                image_bytes=img_bytes,
            )

        self.accept()
