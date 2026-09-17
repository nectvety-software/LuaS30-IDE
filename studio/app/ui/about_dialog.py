from __future__ import annotations

import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, qVersion
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from app.core.paths import app_data_root, projects_root, tool_python
from app.ui import palette

# Nhà phát hành / bản quyền. MỘT nguồn duy nhất cho cả hộp thoại About lẫn tab
# About, để không có hai chuỗi bản quyền lệch nhau trong cùng một màn hình.
VENDOR = "Qeafivels"
COPYRIGHT = f"© {VENDOR} All rights reserved."
WEBSITE = "https://qeafivels.com/"
WEBSITE_LABEL = "https://qeafivels.com/"

# Màu link phải đặt NGAY TRONG thẻ <a>: QLabel/QTextBrowser tô <a> bằng
# `QPalette::Link`, không theo `color` của QSS, nên một rule QSS ở đây sẽ không
# có tác dụng. Dùng token palette (không chép hex) để link vẫn theo bộ màu.
_ANCHOR = f'style="color:{palette.ACCENT_HOVER};text-decoration:none;"'


def _link(url: str = WEBSITE, label: str = WEBSITE_LABEL) -> str:
    return f'<a href="{url}" {_ANCHOR}>{label}</a>'


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "Not installed"


def _tool_version(exe: Path) -> str:
    if not exe.is_file():
        return "Not found"
    if os.name != "nt" and exe.suffix.lower() == ".exe":
        return "Bundled Windows tool"
    try:
        out = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=4,
            check=False,
        )
        first = (out.stdout or out.stderr).splitlines()
        return first[0].strip() if first else "Available"
    except Exception:
        return "Available"


def collect_environment(engine_root: Path) -> list[tuple[str, str]]:
    gcc = engine_root / "toolchain" / "arm-gcc" / "bin" / "arm-none-eabi-gcc.exe"
    if not gcc.exists():
        gcc = engine_root / "toolchain" / "arm-gcc" / "bin" / "arm-none-eabi-gcc"
    emulator = engine_root / "emulator" / "VXPEmu.exe"
    lua_copy = engine_root / "vendor" / "lua-5.1.5" / "COPYRIGHT"
    return [
        ("LuaS30 IDE", _read_engine_version(engine_root)),
        ("Python", platform.python_version()),
        ("PySide6", _package_version("PySide6")),
        ("Qt runtime", qVersion()),
        ("Lua runtime", "5.1.5 (bundled source)" if lua_copy.exists() else "5.1.x"),
        ("LuaS30 Native SDK", "1.0 · own headers/API · runtime symbol ABI"),
        ("ARM GCC", _tool_version(gcc)),
        ("VXPEmu", "Bundled" if emulator.is_file() else "Not found"),
        ("OS", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ("Python executable", tool_python(engine_root)),
        ("AppData", str(app_data_root())),
        ("Projects", str(projects_root())),
    ]


def _read_engine_version(engine_root: Path) -> str:
    p = engine_root / "VERSION"
    try:
        return p.read_text(encoding="utf-8").strip() or "1.0.1"
    except OSError:
        return "1.0.1"


class AboutDialog(QDialog):
    def __init__(self, engine_root: Path, parent=None, start_tab: str = "about") -> None:
        super().__init__(parent)
        self.engine_root = engine_root.resolve()
        self.setWindowTitle("About LuaS30 IDE")
        self.resize(720, 560)
        self.setMinimumSize(620, 480)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        mark = QLabel("L30")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(54, 54)
        mark.setObjectName("AboutMark")
        titles = QVBoxLayout()
        name = QLabel("LuaS30 IDE")
        name.setObjectName("AboutTitle")
        version = QLabel(f"Version {_read_engine_version(self.engine_root)}")
        version.setObjectName("Muted")
        subtitle = QLabel("Compact Lua IDE, LuaS30 Native SDK, VXP build pipeline and verified emulator workflow")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        titles.addWidget(name)
        titles.addWidget(version)
        titles.addWidget(subtitle)
        head.addWidget(mark)
        head.addLayout(titles, 1)
        root.addLayout(head)
        root.addLayout(self._legal_row())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("AboutTabs")
        self.tabs.addTab(self._about_tab(), "About")
        self.tabs.addTab(self._environment_tab(), "Environment")
        self.tabs.addTab(self._credits_tab(), "Credits")
        self.tabs.addTab(self._paths_tab(), "Paths")
        root.addWidget(self.tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

        mapping = {"about": 0, "environment": 1, "credits": 2, "paths": 3}
        self.tabs.setCurrentIndex(mapping.get(start_tab, 0))

    @staticmethod
    def _open_website(url) -> None:
        """Mở website nhà phát hành bằng trình duyệt hệ thống.

        Nhận cả `str` (từ `QLabel.linkActivated`) lẫn `QUrl` (từ
        `QTextBrowser.anchorClicked`) nên hai chỗ nối chung một hàm.
        """
        QDesktopServices.openUrl(url if isinstance(url, QUrl) else QUrl(str(url)))

    def _wire_links(self, browser: QTextBrowser) -> QTextBrowser:
        """Cho MỌI link trong tài liệu mở ra trình duyệt hệ thống.

        `setOpenLinks(False)` chặn `QTextBrowser` điều hướng nội bộ — không có
        nó, bấm link sẽ thay luôn nội dung tài liệu (và với URL ngoài thì hiện
        trang trắng). `anchorClicked` sau đó đưa URL cho `_open_website`.

        Dùng chung cho cả 3 tab để không còn tab nào là ngoại lệ: tab nào thêm
        link sau này cũng tự mở ra ngoài, không im lặng hỏng.
        """
        browser.setOpenExternalLinks(False)
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(self._open_website)
        return browser

    def _link_label(self, html: str, name: str) -> QLabel:
        """QLabel rich-text có link mở ra ngoài qua `_open_website`.

        Không dùng `setOpenExternalLinks(True)`: như thế Qt tự mở và không có
        chỗ nào để chặn, nên test không kiểm được URL thật sự được mở.
        """
        label = QLabel(html)
        label.setObjectName(name)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setOpenExternalLinks(False)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.linkActivated.connect(self._open_website)
        return label

    def _legal_row(self) -> QHBoxLayout:
        """Bản quyền + website, hiện ở đầu hộp thoại nên thấy được ở MỌI tab."""
        row = QHBoxLayout()
        row.setSpacing(8)

        self.copyright_label = QLabel(COPYRIGHT)
        self.copyright_label.setObjectName("Muted")

        self.website_label = self._link_label(_link(), "AboutLink")

        row.addWidget(self.copyright_label)
        row.addStretch(1)
        row.addWidget(self.website_label)
        return row

    def _legal_footer(self) -> QLabel:
        """Dòng bản quyền đặt NGOÀI vùng cuộn của tab Credits.

        Đặt trong tài liệu HTML thì nó nằm dưới đáy khung: `toPlainText()` vẫn
        chứa nó nên test nào chỉ kiểm nội dung sẽ báo xanh, nhưng người dùng
        phải cuộn mới thấy — đã bị đúng như vậy ở lần render đầu.
        """
        self.credits_legal_label = self._link_label(f"{COPYRIGHT} · {_link()}", "Muted")
        return self.credits_legal_label

    def _about_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        text = self._wire_links(QTextBrowser())
        text.setHtml(
            f"""
            <h2>LuaS30 IDE</h2>
            <p>A focused desktop IDE for Lua applications targeting Nokia S30+/MRE-style VXP workflows.</p>
            <p>The Studio intentionally follows a compact VS Code-like workspace: activity bar, explorer,
            editor tabs, integrated build logs, status bar, assets, UI designer and emulator tools.</p>
            <p><b>Core components:</b> Code Editor · Lua 5.1 · Native SDK/API · ARM build · VXP packaging · Emulator</p>
            <p>Project files are stored under <code>Documents/LuaS30 Projects</code>. User configuration,
            caches and launcher logs are stored under <code>AppData/LuaS30IDE</code>.</p>
            <hr>
            <p>{COPYRIGHT}<br>
            Website: {_link()}</p>
            """
        )
        layout.addWidget(text)
        return page

    def _environment_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Component", "Detected version / location"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        values = collect_environment(self.engine_root)
        table.setRowCount(len(values))
        for row, (name, value) in enumerate(values):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(value))
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 150)
        layout.addWidget(table)
        return page

    def _credits_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        text = self._wire_links(QTextBrowser())
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        text.setHtml(
            """
            <h2>Environment & library credits</h2>
            <p>LuaS30 IDE thanks the projects and runtimes used by the desktop development environment.</p>
            <ul>
              <li><b>Python</b> — Python Software Foundation. Used by the Studio, launcher and build tools.</li>
              <li><b>PySide6 / Qt for Python</b> — Qt Project / The Qt Company. Used for the desktop UI.</li>
              <li><b>Qt 6</b> — UI/runtime framework used by the Studio and bundled emulator components.</li>
              <li><b>Segoe Fluent Icons / Segoe MDL2 Assets</b> — Windows system icon fonts used by the Studio icon layer. LuaS30 does not bundle or redistribute these font files.</li>
              <li><b>Lua 5.1.5</b> — Lua.org, PUC-Rio. Embedded language runtime; distributed under the Lua MIT license.</li>
              <li><b>GNU ARM toolchain</b> — ARM/GNU compiler tools used to produce ARM ELF binaries.</li>
              <li><b>Unicorn Engine</b> — CPU emulation component used by the bundled VXP emulator workflow.</li>
              <li><b>VXPEmu</b> — bundled emulator executable used for local VXP testing.</li>
              <li><b>LuaS30 Native SDK/API</b> — project-owned headers, capability layer and runtime ABI resolver. No vendor MRE static SDK libraries are linked.</li>
            </ul>
            <p>License and attribution files shipped with a component remain authoritative. Lua's license is
            included at <code>vendor/lua-5.1.5/COPYRIGHT</code>. Additional project notices are kept in
            <code>doc/legal/THIRD_PARTY_NOTICES.md</code>.</p>
            <p>No third-party runtime is hidden from this screen: detected environment versions are listed in
            the <b>Environment</b> tab.</p>
            """
        )
        layout.addWidget(text, 1)
        layout.addWidget(self._legal_footer())
        return page

    def _paths_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        text = self._wire_links(QTextBrowser())
        rows = [
            ("Engine", self.engine_root),
            ("AppData", app_data_root()),
            ("Projects", projects_root()),
            ("License (project)", self.engine_root / "LICENSE"),
            ("Third-party notices", self.engine_root / "doc" / "legal" / "THIRD_PARTY_NOTICES.md"),
            ("Lua license", self.engine_root / "vendor" / "lua-5.1.5" / "COPYRIGHT"),
        ]
        html = ["<h2>Important paths</h2><table cellspacing='8'>"]
        for key, value in rows:
            html.append(f"<tr><td><b>{key}</b></td><td><code>{value}</code></td></tr>")
        html.append("</table>")
        text.setHtml("".join(html))
        layout.addWidget(text)
        return page
