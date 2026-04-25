# Changelog

All notable changes to Zeus PDF will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-25

First production release. This is the same feature set as the prior 1.0
preview, plus a hardening pass with bug fixes, a real test suite, and CI.

### Added

- **Test suite** — 90 unit tests across the engine, model, command, and
  rendering layers, plus opt-in GUI smoke tests
  (`ZEUS_GUI_TESTS=1 pytest`).
- **Continuous integration** — GitHub Actions matrix on Ubuntu, Windows,
  and macOS, against Python 3.10–3.12. Lints with ruff, formats with
  black, type-checks with mypy, runs pytest with coverage.
- **Pre-commit hooks** — ruff, black, mypy, trailing-whitespace, large-file
  guard.
- **Single-source versioning** — `pdfstudio/__version__.py` is now the
  authoritative version. The PyInstaller spec, Inno Setup script, macOS
  bundle Info.plist, build scripts, and About dialog all read from it.
- **Atomic saves** — overwriting the currently-open PDF now writes to a
  sibling `.tmp` file and atomically renames into place, so a crash
  mid-save can never corrupt the original. A timestamped `.bak` is still
  created first.
- **Cross-platform logging** — rotating log files in
  `~/Library/Logs/ZeusPDF` (macOS), `%LOCALAPPDATA%\ZeusPDF\logs`
  (Windows), or `$XDG_STATE_HOME/zeuspdf` (Linux).

### Fixed

- `FieldEngine._widget_to_def` crashed on PyMuPDF ≥ 1.24 because
  `fitz.Widget.tooltip` was removed. Now reads from
  `field_label` / `tool_tip` / `tooltip` whichever the runtime exposes.
- `FieldEngine.add_field` overwrote `field_flags` instead of OR-ing them,
  so a field that was both `multiline` and `required` would silently
  lose one flag. Now combines flags into a single bitfield.
- `FieldEngine` referenced `fitz.PDF_FIELD_IS_MULTILINE`, which was
  renamed to `PDF_TX_FIELD_IS_MULTILINE`. A compatibility shim now
  picks the right symbol on either version.
- `AnnotationEngine._create_annot` had a dead expression on the
  HIGHLIGHT branch (assigned to a discarded local before falling
  through). Cleaned up.
- `AnnotationEngine._create_annot` rejected TEXT_BOX annotations on
  PyMuPDF ≥ 1.24 because `add_freetext_annot` no longer accepts
  `border_color=`. Now uses a best-effort `set_colors` call after
  creation.
- `AnnotationEngine._create_annot` rejected STAMP annotations because
  `add_stamp_annot` requires an integer `STAMP_*` enum, not a string
  name. The string is now mapped via `getattr(fitz, ...)` with a
  sensible fallback.
- `AnnotationEngine.update_content` passed the full `annot.info` dict
  back to `set_info`, which rejects non-content keys. Now passes
  `content=` only.
- `AnnotationEngine._annot_to_def` propagated PyMuPDF's "unset opacity"
  sentinel (`-1`) into the `AnnotationDef` dataclass. Now normalised to
  the `[0.0, 1.0]` range.
- `UndoStack.push` could leave `_index` stale after the stack overflowed
  past `max_history`. Defensive fix even though the path was hard to
  trigger in practice.
- `UndoStack.mark_clean` didn't emit the `changed` signal, so the title
  bar's modified marker and the Edit menu's undo description stayed
  stale after Save. Now emits.
- `PDFDocument.save` failed when overwriting the currently-open file on
  PyMuPDF ≥ 1.24, which now requires `incremental=True` for in-place
  saves. The atomic save-to-temp-then-rename strategy sidesteps the
  restriction and is safer.
- `MainWindow` reached into `canvas._set_zoom` (private). Now uses the
  new public `Canvas.set_zoom`.

### Changed

- `setup.py` and `requirements-signing.txt` removed. `pyproject.toml` is
  now the single source of project metadata, dependencies, and tool
  configuration (ruff, black, mypy, pytest, coverage).
- `requirements.txt` retained as a thin convenience file mirroring the
  runtime dependencies in `pyproject.toml` for quick installs.
- The About dialog reads version, app name, and publisher from
  `pdfstudio/__version__.py` instead of hard-coded strings.
