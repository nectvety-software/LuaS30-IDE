from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

# Allow running this file directly without installing a Python package.
STUDIO_DIR = Path(__file__).resolve().parent
if str(STUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(STUDIO_DIR))

from app.core.utf8 import configure_utf8_stdio

configure_utf8_stdio()

from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLE


def main() -> int:
    QCoreApplication.setOrganizationName("LuaS30")
    QCoreApplication.setApplicationName("LuaS30 Studio")

    app = QApplication(sys.argv)
    app.setApplicationDisplayName("LuaS30 IDE")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow(engine_root=STUDIO_DIR.parent)
    window.show()
    return app.exec()


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())
