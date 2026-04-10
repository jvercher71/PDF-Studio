"""
Main application window — wires together toolbar, canvas, sidebar,
properties panel, menus, status bar, and the document model.
"""
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QAction, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QSplitter,
    QStatusBar, QWidget, QHBoxLayout, QLabel,
)

from pdfstudio.models.document_model import DocumentModel
from pdfstudio.commands.base import UndoStack
from pdfstudio.views.canvas import PDFView, ToolMode
from pdfstudio.views.toolbar import MainToolbar
from pdfstudio.views.sidebar import Sidebar
from pdfstudio.views.properties import PropertiesPanel
from pdfstudio.views.signature_dialog import SignatureDialog
from pdfstudio.views.print_dialog import print_document
from pdfstudio.views.tab_order_dialog import TabOrderDialog
from pdfstudio.engine.signer import SignatureEngine, SignatureConfig
from pdfstudio.utils.theme import get_stylesheet

log = logging.getLogger(__name__)

PDF_FILTER = "PDF Files (*.pdf);;All Files (*)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._model = DocumentModel()
        self._undo = UndoStack(parent=self)

        self.setWindowTitle("Zeus PDF")
        self.resize(1280, 860)
        self.setStyleSheet(get_stylesheet())

        self._build_ui()
        self._build_menus()
        self._connect_signals()
        self._update_ui_state()

    # ------------------------------------------------------------------ #
    # UI Construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # Toolbar
        self._toolbar = MainToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self._toolbar)

        # Central area: sidebar | canvas | properties
        self._sidebar = Sidebar(self._model, self)
        self._canvas = PDFView(self._model, self._undo, self)
        self._properties = PropertiesPanel(self)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._properties)
        splitter.setSizes([160, 900, 220])
        splitter.setChildrenCollapsible(False)

        self.setCentralWidget(splitter)

        # Status bar
        self._status = QStatusBar(self)
        self.setStatusBar(self._status)
        self._status_label = QLabel("Ready")
        self._status.addWidget(self._status_label, 1)
        self._zoom_label = QLabel("Zoom: 100%")
        self._status.addPermanentWidget(self._zoom_label)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # ── File ─────────────────────────────────────────────────────────
        file_menu = mb.addMenu("&File")
        self._act_new    = self._action("&New",           "Ctrl+N",       file_menu)
        self._act_open   = self._action("&Open…",         "Ctrl+O",       file_menu)
        file_menu.addSeparator()
        self._act_save   = self._action("&Save",          "Ctrl+S",       file_menu)
        self._act_saveas = self._action("Save &As…",      "Ctrl+Shift+S", file_menu)
        self._act_flat   = self._action("Flatten & Save As…", "",         file_menu)
        file_menu.addSeparator()
        self._act_encrypt = self._action("Password Protect…", "",         file_menu)
        file_menu.addSeparator()
        self._act_print  = self._action("&Print…",        "Ctrl+P",       file_menu)
        file_menu.addSeparator()
        self._act_quit   = self._action("&Quit",          "Ctrl+Q",       file_menu)

        # ── Edit ─────────────────────────────────────────────────────────
        edit_menu = mb.addMenu("&Edit")
        self._act_undo = self._action("&Undo",  "Ctrl+Z",       edit_menu)
        self._act_redo = self._action("&Redo",  "Ctrl+Shift+Z", edit_menu)
        edit_menu.addSeparator()
        self._act_cut   = self._action("Cu&t",   "Ctrl+X", edit_menu)
        self._act_copy  = self._action("&Copy Text",  "Ctrl+C", edit_menu)
        self._act_paste = self._action("&Paste", "Ctrl+V", edit_menu)
        edit_menu.addSeparator()
        self._act_selall = self._action("Select &All Text", "Ctrl+A", edit_menu)
        self._act_text_select_tool = self._action("&Text Select Tool", "Ctrl+T", edit_menu)
        edit_menu.addSeparator()
        self._act_convert = self._action("Convert / Export As…", "Ctrl+E", edit_menu)

        # ── View ─────────────────────────────────────────────────────────
        view_menu = mb.addMenu("&View")
        self._act_zoom_in    = self._action("Zoom In",     "Ctrl++", view_menu)
        self._act_zoom_out   = self._action("Zoom Out",    "Ctrl+-", view_menu)
        self._act_fit_page   = self._action("Fit Page",    "Ctrl+0", view_menu)
        self._act_fit_width  = self._action("Fit Width",   "Ctrl+2", view_menu)

        # ── Pages ─────────────────────────────────────────────────────────
        pages_menu = mb.addMenu("&Pages")
        self._act_insert_page = self._action("Insert Page",     "", pages_menu)
        self._act_delete_page = self._action("Delete Page",     "", pages_menu)
        pages_menu.addSeparator()
        self._act_rot_cw   = self._action("Rotate Clockwise",     "", pages_menu)
        self._act_rot_ccw  = self._action("Rotate Counter-CW",    "", pages_menu)

        # ── Forms ─────────────────────────────────────────────────────────
        forms_menu = mb.addMenu("F&orms")
        self._act_tab_order = self._action("Edit Tab Order…", "", forms_menu)
        self._act_flatten   = self._action("Flatten Form Fields…", "", forms_menu)

        # ── Sign ──────────────────────────────────────────────────────────
        sign_menu = mb.addMenu("&Sign")
        self._act_sign_visual = self._action("Apply Visual Signature…", "", sign_menu)
        self._act_sign_cert   = self._action("Apply Certificate Signature…", "", sign_menu)
        self._act_verify_sig  = self._action("Verify Signatures…", "", sign_menu)

        # ── Help ──────────────────────────────────────────────────────────
        help_menu = mb.addMenu("&Help")
        self._action("About Zeus PDF", "", help_menu).triggered.connect(self._about)

    # ------------------------------------------------------------------ #
    # Signal Connections
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        # Toolbar file actions
        tb_new  = self._toolbar.action("New")
        tb_open = self._toolbar.action("Open")
        tb_save = self._toolbar.action("Save")
        tb_undo = self._toolbar.action("Undo")
        tb_redo = self._toolbar.action("Redo")
        if tb_new:  tb_new.triggered.connect(self._on_new)
        if tb_open: tb_open.triggered.connect(self._on_open)
        if tb_save: tb_save.triggered.connect(self._on_save)
        if tb_undo: tb_undo.triggered.connect(self._on_undo)
        if tb_redo: tb_redo.triggered.connect(self._on_redo)

        # Menu file
        self._act_new.triggered.connect(self._on_new)
        self._act_open.triggered.connect(self._on_open)
        self._act_save.triggered.connect(self._on_save)
        self._act_saveas.triggered.connect(self._on_save_as)
        self._act_flat.triggered.connect(self._on_flatten)
        self._act_encrypt.triggered.connect(self._on_encrypt)
        self._act_print.triggered.connect(self._on_print)
        self._act_quit.triggered.connect(self.close)

        # Edit
        self._act_undo.triggered.connect(self._on_undo)
        self._act_redo.triggered.connect(self._on_redo)
        self._act_copy.triggered.connect(self._canvas.copy_selected_text)
        self._act_selall.triggered.connect(self._canvas.select_all_text)
        self._act_text_select_tool.triggered.connect(
            lambda: self._canvas.set_tool(ToolMode.TEXT_SELECT))
        self._act_convert.triggered.connect(self._on_convert)

        # View
        self._act_zoom_in.triggered.connect(self._canvas.zoom_in)
        self._act_zoom_out.triggered.connect(self._canvas.zoom_out)
        self._act_fit_page.triggered.connect(self._canvas.zoom_fit_page)
        self._act_fit_width.triggered.connect(self._canvas.zoom_fit_width)

        # Pages
        self._act_insert_page.triggered.connect(self._on_insert_page)
        self._act_delete_page.triggered.connect(self._on_delete_page)
        self._act_rot_cw.triggered.connect(lambda: self._on_rotate(90))
        self._act_rot_ccw.triggered.connect(lambda: self._on_rotate(-90))

        # Forms
        self._act_tab_order.triggered.connect(self._on_tab_order)
        self._act_flatten.triggered.connect(self._on_flatten)

        # Sign
        self._act_sign_visual.triggered.connect(self._on_sign_visual)
        self._act_sign_cert.triggered.connect(self._on_sign_cert)
        self._act_verify_sig.triggered.connect(self._on_verify)

        # Toolbar tools
        self._toolbar.tool_selected.connect(self._canvas.set_tool)
        self._toolbar.zoom_changed.connect(self._on_zoom_combo)
        self._toolbar.page_jump.connect(self._canvas.scroll_to_page)

        # Canvas
        self._canvas.status_message.connect(self._set_status)
        self._canvas.page_changed.connect(self._on_page_changed)
        self._canvas.tool_changed.connect(self._on_tool_changed)

        # Sidebar
        self._sidebar.page_selected.connect(self._canvas.scroll_to_page)
        self._sidebar.field_selected.connect(self._properties.show_field_properties)

        # Properties → canvas
        self._properties.annot_color_changed.connect(
            lambda c: setattr(self._canvas, "annot_color", c))
        self._properties.annot_opacity_changed.connect(
            lambda v: setattr(self._canvas, "annot_opacity", v))
        self._properties.annot_line_width_changed.connect(
            lambda v: setattr(self._canvas, "annot_line_width", v))

        # Model
        self._model.document_changed.connect(self._on_document_changed)
        self._model.modified_changed.connect(self._update_title)
        self._undo.changed.connect(self._update_undo_state)

    # ------------------------------------------------------------------ #
    # Slots — File
    # ------------------------------------------------------------------ #

    def open_file(self, path: str | Path) -> None:
        try:
            self._model.open(path)
        except ValueError:
            pwd, ok = self._ask_password()
            if ok:
                try:
                    self._model.open(path, pwd)
                except ValueError:
                    QMessageBox.critical(self, "Error", "Incorrect password.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def _on_new(self) -> None:
        if self._confirm_discard():
            self._model.new()
            self._undo.clear()

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", PDF_FILTER)
        if path and self._confirm_discard():
            self.open_file(path)
            self._undo.clear()

    def _on_save(self) -> None:
        if not self._model.is_open:
            return
        if self._model.path is None:
            self._on_save_as()
            return
        try:
            self._model.save()
            self._undo.mark_clean()
            self._set_status("Saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _on_save_as(self) -> None:
        if not self._model.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", "", PDF_FILTER)
        if path:
            try:
                self._model.save(path)
                self._undo.mark_clean()
                self._set_status(f"Saved as {Path(path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def _on_flatten(self) -> None:
        if not self._model.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Flatten & Save As", "", PDF_FILTER)
        if path:
            try:
                self._model.save(path, flatten=True)
                self._set_status(f"Flattened: {Path(path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Flatten Error", str(e))

    def _on_encrypt(self) -> None:
        QMessageBox.information(self, "Password Protect",
                                "Enter a password to encrypt the saved PDF.")
        # Full implementation: custom dialog for user/owner passwords + permissions

    def _on_print(self) -> None:
        if not self._model.is_open:
            return
        self._set_status("Printing…")
        ok = print_document(self._model._pdf.raw(), parent=self, preview=False)
        self._set_status("Print job sent." if ok else "Print cancelled.")

    # ------------------------------------------------------------------ #
    # Slots — Edit
    # ------------------------------------------------------------------ #

    def _on_undo(self) -> None:
        desc = self._undo.undo()
        if desc:
            self._set_status(f"Undo: {desc}")

    def _on_redo(self) -> None:
        desc = self._undo.redo()
        if desc:
            self._set_status(f"Redo: {desc}")

    # ------------------------------------------------------------------ #
    # Slots — Pages
    # ------------------------------------------------------------------ #

    def _on_insert_page(self) -> None:
        if self._model.is_open:
            self._model.insert_page()

    def _on_delete_page(self) -> None:
        if not self._model.is_open or self._model.page_count <= 1:
            return
        idx = self._current_page_index()
        reply = QMessageBox.question(self, "Delete Page",
                                     f"Delete page {idx + 1}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._model.delete_page(idx)

    def _on_rotate(self, degrees: int) -> None:
        if self._model.is_open:
            self._model.rotate_page(self._current_page_index(), degrees)

    def _on_convert(self) -> None:
        if not self._model.is_open:
            return
        from pdfstudio.views.convert_dialog import ConvertDialog
        dlg = ConvertDialog(self._model, parent=self)
        dlg.exec()

    def _on_tab_order(self) -> None:
        if not self._model.is_open:
            return
        dlg = TabOrderDialog(self._model, self._current_page_index(), parent=self)
        dlg.exec()

    # ------------------------------------------------------------------ #
    # Slots — Signature
    # ------------------------------------------------------------------ #

    def _on_sign_visual(self) -> None:
        """Show the signature dialog immediately; user draws/types/uploads."""
        if not self._model.is_open:
            return
        # Use a centered rect on the current page as the default placement
        page_idx = self._current_page_index()
        pw, ph = self._model.page_size(page_idx)
        rect = (pw * 0.5 - 120, ph * 0.75, pw * 0.5 + 120, ph * 0.75 + 60)
        self._show_signature_dialog(page_idx, rect, sig_type="visual")

    def _on_sign_cert(self) -> None:
        """Show the signature dialog opened to the Certificate tab."""
        if not self._model.is_open:
            return
        page_idx = self._current_page_index()
        pw, ph = self._model.page_size(page_idx)
        rect = (pw * 0.5 - 120, ph * 0.75, pw * 0.5 + 120, ph * 0.75 + 60)
        self._show_signature_dialog(page_idx, rect, sig_type="cert")

    def _show_signature_dialog(self, page_idx: int, rect: tuple,
                                sig_type: str = "visual") -> None:
        dlg = SignatureDialog(page_idx, rect, parent=self)
        if sig_type == "cert":
            dlg._tabs.setCurrentIndex(3)
        if dlg.exec() != SignatureDialog.Accepted or dlg.result_config is None:
            return

        cfg = dlg.result_config
        if not self._model.path:
            # Need to save first so signer has a file to work on
            self._on_save_as()
            if not self._model.path:
                return

        output = self._model.path.with_stem(self._model.path.stem + "_signed")
        engine = SignatureEngine()

        if cfg.sig_type == "cert" and cfg.cert_path:
            ok = engine.sign_cryptographic(self._model.path, output, cfg)
        else:
            ok = engine.sign_visual(self._model.path, output, cfg)

        if ok:
            QMessageBox.information(
                self, "Signature Applied",
                f"Signed document saved as:\n{output.name}\n\n"
                "Opening signed copy…"
            )
            self.open_file(output)
        else:
            QMessageBox.critical(self, "Signing Failed",
                                 "Could not apply signature. Check the log for details.")

    def _on_verify(self) -> None:
        if not self._model.path:
            QMessageBox.information(self, "Verify", "Save the document first.")
            return
        results = SignatureEngine().verify(self._model.path)
        if not results:
            QMessageBox.information(self, "Signatures", "No signatures found in this document.")
            return
        lines = []
        for r in results:
            icon = "✅" if r.get("valid") else "❌"
            lines.append(f"{icon}  {r['field_name']}")
            if r.get("signer"):
                lines.append(f"     Signed: {r['signer']}")
            if r.get("reason"):
                lines.append(f"     Reason: {r['reason']}")
            if r.get("error"):
                lines.append(f"     Error: {r['error']}")
        QMessageBox.information(self, "Signature Verification", "\n".join(lines))

    # ------------------------------------------------------------------ #
    # Slots — Model / UI state
    # ------------------------------------------------------------------ #

    def _on_document_changed(self) -> None:
        self._update_ui_state()
        self._update_title()

    def _update_ui_state(self) -> None:
        has_doc = self._model.is_open
        for act in (self._act_save, self._act_saveas, self._act_flat,
                    self._act_encrypt, self._act_print, self._act_convert,
                    self._act_copy, self._act_selall, self._act_text_select_tool,
                    self._act_insert_page, self._act_delete_page,
                    self._act_rot_cw, self._act_rot_ccw,
                    self._act_tab_order, self._act_flatten,
                    self._act_sign_visual, self._act_sign_cert, self._act_verify_sig):
            act.setEnabled(has_doc)

        self._toolbar.set_page_count(self._model.page_count if has_doc else 0)
        self._update_undo_state()

    def _update_undo_state(self) -> None:
        self._act_undo.setEnabled(self._undo.can_undo)
        self._act_redo.setEnabled(self._undo.can_redo)
        self._act_undo.setText(
            f"&Undo {self._undo.undo_description}" if self._undo.can_undo else "&Undo"
        )
        self._act_redo.setText(
            f"&Redo {self._undo.redo_description}" if self._undo.can_redo else "&Redo"
        )

    def _update_title(self, *_) -> None:
        self.setWindowTitle(self._model.title)

    def _on_page_changed(self, index: int) -> None:
        self._toolbar.set_current_page(index)
        self._sidebar.highlight_page(index)

    def _on_tool_changed(self, mode: ToolMode) -> None:
        self._set_status(_TOOL_STATUS.get(mode, ""))

    def _on_zoom_combo(self, _) -> None:
        text = self._toolbar.zoom_text()
        if text == "Fit Page":
            self._canvas.zoom_fit_page()
        elif text == "Fit Width":
            self._canvas.zoom_fit_width()
        elif text.endswith("%"):
            try:
                pct = int(text[:-1])
                # Convert percentage to zoom factor; baseline 100% = 1.0
                self._canvas._set_zoom(pct / 100.0)
            except ValueError:
                pass

    def _set_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _current_page_index(self) -> int:
        return self._canvas._current_page

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _action(self, text: str, shortcut: str, menu) -> QAction:
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        menu.addAction(act)
        return act

    def _confirm_discard(self) -> bool:
        if not self._model.is_open or not self._model.is_modified:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.Discard | QMessageBox.Cancel,
        )
        return reply == QMessageBox.Discard

    def _ask_password(self) -> tuple[str, bool]:
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, "Password", "Enter PDF password:",
                                    echo=QInputDialog.Password)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _about(self) -> None:
        from PySide6.QtGui import QPixmap
        from pathlib import Path
        import sys
        box = QMessageBox(self)
        box.setWindowTitle("About Zeus PDF")
        # Works both from source and PyInstaller frozen bundle
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent.parent.parent
        logo_path = base / "assets" / "zeuspdf_128.png"
        if logo_path.exists():
            box.setIconPixmap(QPixmap(str(logo_path)).scaled(96, 96))
        box.setText(
            "<b style='font-size:16px;'>⚡ Zeus PDF v1.0</b><br><br>"
            "Built by <b>Vercher Technologies</b><br><br>"
            "Full-featured PDF editor — form fields, annotations,<br>"
            "digital signing, text extraction, and format conversion.<br><br>"
            "<span style='color:#888;font-size:11px;'>"
            "Powered by PyMuPDF · PySide6 · pyHanko"
            "</span>"
        )
        box.exec()


_TOOL_STATUS: dict[ToolMode, str] = {
    ToolMode.SELECT:          "Select mode — click to select, drag to move",
    ToolMode.TEXT_FIELD:      "Text Field — drag to place",
    ToolMode.CHECKBOX:        "Checkbox — drag to place",
    ToolMode.RADIO:           "Radio Button — drag to place",
    ToolMode.DROPDOWN:        "Dropdown — drag to place",
    ToolMode.LISTBOX:         "Listbox — drag to place",
    ToolMode.SIGNATURE_FIELD: "Signature Field — drag to place",
    ToolMode.BUTTON:          "Button — drag to place",
    ToolMode.HIGHLIGHT:       "Highlight — drag over text",
    ToolMode.UNDERLINE:       "Underline — drag over text",
    ToolMode.STRIKEOUT:       "Strikethrough — drag over text",
    ToolMode.NOTE:            "Sticky Note — click to place",
    ToolMode.TEXT_BOX:        "Text Box — drag to place",
    ToolMode.INK:             "Freehand Draw — drag to draw",
    ToolMode.RECTANGLE:       "Rectangle — drag to draw",
    ToolMode.ELLIPSE:         "Ellipse — drag to draw",
    ToolMode.LINE:            "Line — drag to draw",
    ToolMode.ARROW:           "Arrow — drag to draw",
    ToolMode.STAMP:           "Stamp — drag to place",
}
