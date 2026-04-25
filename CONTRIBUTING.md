# Contributing to Zeus PDF

Thanks for taking the time to improve Zeus PDF. These notes will get you
oriented quickly.

## Getting set up

```bash
git clone https://github.com/jvercher71/PDF-Studio.git
cd PDF-Studio
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[full,dev]"
pre-commit install
```

`pre-commit install` wires ruff, black, mypy, and a few sanity hooks into
your git hooks so they run automatically on every commit.

## Running tests

```bash
pytest                       # 90 unit tests, runs in ~3 seconds
pytest --cov=pdfstudio       # with coverage report
ZEUS_GUI_TESTS=1 pytest      # also run the GUI smoke tests
```

The GUI smoke tests are opt-in because they need a real Qt platform
plugin to drain background threads cleanly between tests. They pass on a
real desktop; they hang under CI's offscreen Qt unless the Sidebar's
thumbnail thread gets a proper `closeEvent` cleanup. That cleanup is on
the TODO list.

## Code style

- **Formatting**: black, line length 100.
- **Linting**: ruff (pyflakes, pycodestyle, isort, bugbear, pyupgrade,
  simplify).
- **Typing**: mypy. The baseline is "soft" today — `continue-on-error`
  in CI — but new code should be fully typed.

The pre-commit hook will block any commit that fails these checks.

## Architecture conventions

```
pdfstudio/
├── engine/      Pure PyMuPDF — no Qt imports allowed.
├── models/      QObject/QAbstractItemModel — wrap engine, emit signals.
├── views/       PySide6 widgets. Read from models, dispatch commands.
└── commands/    Command pattern for undo/redo. Mutations live here.
```

A few rules that keep the layering clean:

1. **Engine never imports Qt.** If you need to signal something from the
   engine, return a value or raise — let the model translate it into a
   Qt signal. Tests rely on this so they can run headless.
2. **Mutations go through commands.** If a user action changes the
   document state, it should be a `Command` on the undo stack. Direct
   model mutations from views are a bug.
3. **Views are stateless about the document.** They read from the model
   on every refresh. If you find yourself caching document state in a
   view, push it into the model.

## Writing tests

Engine and model changes need tests. Use the fixtures in
`tests/conftest.py` rather than checking PDFs into the repo:

- `blank_pdf` — single blank page
- `sample_pdf` — single page with text
- `multipage_pdf` — five pages with text
- `encrypted_pdf` — `(path, password)` for password-protected fixtures
- `pdf_factory(pages=, with_text=)` — build a custom one

If your change is in the view layer and only really tests with a real
window, gate it on `ZEUS_GUI_TESTS=1` like the other GUI tests so CI
doesn't hang.

## Bumping the version

Edit `pdfstudio/__version__.py`. That's the single source of truth — it's
read by the About dialog, `pyproject.toml`, the macOS bundle Info.plist,
the Windows installer's filename and "Programs and Features" entry, and
the build scripts' output filenames.

After bumping, add a section to `CHANGELOG.md` and tag the release:

```bash
git tag v1.1.0
git push --tags
```

## Pull requests

- One concern per PR. Big drive-by reformats are hard to review.
- Add tests for any bug fix. The bug should reproduce as a failing test
  before your change, and pass after.
- If the change touches the user experience (new menu item, dialog,
  keyboard shortcut), add a one-line note to `CHANGELOG.md` under
  `## [Unreleased]`.
