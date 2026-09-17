from __future__ import annotations

import sys
from pathlib import Path

# Ban frozen (PyInstaller one-dir): exe nam ngay trong thu muc cai dat,
# engine_root la thu muc chua exe. Ban source: engine_root la thu muc cha
# cua studio/.
if getattr(sys, "frozen", False):
    ENGINE_ROOT = Path(sys.executable).resolve().parent
    STUDIO_DIR = Path(getattr(sys, "_MEIPASS", str(ENGINE_ROOT)))
else:
    STUDIO_DIR = Path(__file__).resolve().parent
    ENGINE_ROOT = STUDIO_DIR.parent
    # Allow running this file directly without installing a Python package.
    if str(STUDIO_DIR) not in sys.path:
        sys.path.insert(0, str(STUDIO_DIR))


def _version_text() -> str:
    try:
        return (ENGINE_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args or "-V" in args:
        # Co nhe cho verify_release + kiem tra nhanh, khong can mo Qt.
        print(f"LuaS30 IDE {_version_text()}")
        return 0

    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    from app.core.utf8 import configure_utf8_stdio

    configure_utf8_stdio()

    from app.ui.main_window import MainWindow
    from app.ui.theme import APP_STYLE

    QCoreApplication.setOrganizationName("LuaS30")
    QCoreApplication.setApplicationName("LuaS30 Studio")

    app = QApplication(sys.argv)
    app.setApplicationDisplayName("LuaS30 IDE")
    app.setStyleSheet(APP_STYLE)
    icon = _app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    window = MainWindow(engine_root=ENGINE_ROOT)
    window.show()
    return app.exec()


def _app_icon() -> object:
    """Logo app cho taskbar + tat ca cua so/dialog (fallback: khong dat)."""
    from app.ui.icons import app_icon

    icon = app_icon(ENGINE_ROOT)
    return icon if not icon.isNull() else None


if __name__ == "__main__":
    raise SystemExit(main())
