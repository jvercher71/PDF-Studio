"""
Zeus PDF — application entry point.

Launches the Qt application, installs logging, and wires up the main window.
Handles CLI file arguments (Windows/Linux file associations) and macOS
Apple-Event file-open requests.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pdfstudio import __app_name__, __publisher__, __version__


def _log_dir() -> Path:
    """Per-user log directory. Cross-platform."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ZeusPDF"
    if sys.platform.startswith("win"):
        return (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "ZeusPDF"
            / "logs"
        )
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "zeuspdf"


def _setup_logging() -> None:
    """Configure root logger with console + rotating-file handlers."""
    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "zeuspdf.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Wipe any pre-existing handlers (e.g. from interactive shells)
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(fmt))
    root.addHandler(console)

    try:
        file_h = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_h.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_h)
    except OSError as e:  # read-only FS, etc.
        root.warning("Could not open log file %s: %s", log_file, e)

    # Quiet down noisy third parties
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("fitz").setLevel(logging.WARNING)


def _resource_path(name: str) -> Path:
    """Return a path to a bundled resource, whether running frozen or from source."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / name


def main() -> int:
    _setup_logging()
    log = logging.getLogger("main")
    log.info("%s v%s starting (Python %s)", __app_name__, __version__, sys.version.split()[0])

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__publisher__)
    app.setOrganizationDomain("verchertechnologies.one")

    # App icon (optional — no fatal error if assets are missing)
    icon_path = _resource_path("assets/zeuspdf_256.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Import after QApplication exists — pulls in widgets that need the event loop.
    from pdfstudio.views.main_window import MainWindow

    window = MainWindow()
    window.show()

    # macOS: handle PDFs opened from Finder / Dock drop (Apple Events)
    app.fileOpenRequest.connect(window.open_file)

    # Windows/Linux: file association sends the path as argv[1]
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if Path(candidate).exists():
            window.open_file(candidate)

    try:
        return app.exec()
    except Exception:
        log.exception("Unhandled exception in event loop")
        return 1


if __name__ == "__main__":
    sys.exit(main())
