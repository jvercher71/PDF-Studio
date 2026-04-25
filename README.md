# Zeus PDF

> A full-featured, native desktop PDF editor for Windows and macOS.
> Built by **Vercher Technologies**.

Zeus PDF lets you edit, annotate, sign, and fill out PDFs without sending them
to a cloud service. Everything stays on your machine.

---

## Features

- **Form editing** — text, checkbox, radio, dropdown, listbox, and signature fields
- **Annotations** — highlights, underlines, strikeouts, sticky notes, text boxes,
  freehand ink, rectangles, ellipses, lines, arrows, stamps
- **Digital signatures** — typed, drawn, or cryptographically signed via PAdES
  (powered by pyHanko)
- **Page operations** — insert, delete, rotate, reorder, merge, split
- **Format conversion** — export to DOCX, XLSX, plain text, images
- **Tab order editor** — control the tab sequence through form fields
- **Text selection & extraction** — searchable, copyable PDF text
- **Undo / redo** — full history across all editing operations
- **Auto-save with backups** — never lose work to a crash

---

## Installation

### Windows

Download `ZeusPDF_Setup_v<version>_Windows.exe` from the
[releases page](https://github.com/jvercher71/PDF-Studio/releases) and run it.

The installer:
- Installs to your user profile (no admin rights required)
- Optionally associates `.pdf` files with Zeus PDF
- Adds Start Menu and optional Desktop shortcuts

### macOS

Download `ZeusPDF_v<version>_Mac.dmg` from releases, open it, and drag
**Zeus PDF** to your Applications folder.

First launch: right-click the app → **Open** to bypass Gatekeeper (until the
app is notarized).

### From source

```bash
git clone https://github.com/jvercher71/PDF-Studio.git
cd PDF-Studio
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[full]"
python main.py
```

---

## Development

### Setup

```bash
pip install -e ".[full,dev]"
pre-commit install
```

### Running tests

```bash
pytest                       # all tests except the opt-in GUI suite
pytest --cov=pdfstudio       # with coverage
ZEUS_GUI_TESTS=1 pytest      # include the GUI smoke tests
```

### Linting / formatting / types

```bash
ruff check pdfstudio tests
black pdfstudio tests main.py
mypy pdfstudio
```

These run automatically on every commit via pre-commit hooks.

---

## Building installers

The version shown in installers comes from `pdfstudio/__version__.py` — bump
it there, commit, and the build scripts pick it up everywhere.

### Windows

Requires [Inno Setup 6+](https://jrsoftware.org/isdl.php).

```cmd
build_windows.bat
```

Output:
- `dist\ZeusPDF\ZeusPDF.exe` — the portable app
- `Output\ZeusPDF_Setup_v<version>_Windows.exe` — the installer

### macOS

Requires [`create-dmg`](https://github.com/create-dmg/create-dmg) for the DMG step.

```bash
bash build.sh
```

Output:
- `dist/Zeus PDF.app` — the `.app` bundle
- `dist/ZeusPDF_v<version>_Mac.dmg` — the disk image

---

## Architecture

```
pdfstudio/
├── engine/       PDF operations — PyMuPDF-backed, no Qt dependencies
├── models/       Qt models exposing engine state via signals
├── views/        PySide6 UI
├── commands/     Command pattern for undo/redo
└── utils/        Theme, helpers
```

The engine layer is the one that should be covered by unit tests. The view
layer is covered by opt-in GUI smoke tests.

---

## License

Proprietary. © Vercher Technologies. See [LICENSE](LICENSE).

Built on top of these great open-source libraries:
[PySide6 (LGPL)](https://www.qt.io/qt-for-python),
[PyMuPDF (AGPL/commercial)](https://pymupdf.readthedocs.io/),
[pyHanko (MIT)](https://github.com/MatthiasValvekens/pyHanko),
[pypdf (BSD)](https://pypdf.readthedocs.io/),
[Pillow (HPND)](https://pillow.readthedocs.io/).
