import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from pdfstudio.views.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Zeus PDF")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Vercher Technologies")
    # AA_UseHighDpiPixmaps is the default in Qt6 — no need to set it

    window = MainWindow()
    window.show()

    # macOS: handle PDFs opened from Finder / "Open With" / dock-drop (Apple Events → QFileOpenEvent)
    app.fileOpenRequest.connect(window.open_file)

    # Open file passed as CLI arg (Windows file association, command line)
    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
