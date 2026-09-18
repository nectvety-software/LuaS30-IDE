"""
theme.py — QSS của toàn bộ LuaS30 Studio.

Màu KHÔNG viết trực tiếp ở đây. Mỗi chỗ dùng một token `@TEN_TOKEN`, lấy từ
`app/ui/palette.py` — bảng màu duy nhất của Studio (VS Code Dark Modern:
nền neutral `#181818`/`#1e1e1e`, viền `#2b2b2b`/`#3c3c3c`, accent xanh `#0078d4`).

Đổi màu ở `palette.py` là đổi cả app. `_substitute()` ném lỗi ngay lúc import
nếu gặp token không tồn tại — nếu để nguyên, Qt sẽ **âm thầm bỏ qua** cả rule
đó và widget rơi về style mặc định, rất khó truy.
"""

from __future__ import annotations

import re

from app.ui import palette

_TOKEN_RE = re.compile(r"@([A-Z][A-Z0-9_]*)")


def _substitute(qss: str) -> str:
    """Thay mọi `@TOKEN` bằng giá trị trong palette.py. Lỗi nếu token lạ."""
    unknown: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        value = getattr(palette, name, None)
        if not isinstance(value, str) or not value.startswith("#"):
            unknown.add(name)
            return match.group(0)
        return value

    resolved = _TOKEN_RE.sub(repl, qss)
    if unknown:
        raise ValueError(
            "theme.py dùng token không có trong palette.py: "
            + ", ".join(sorted(unknown))
        )
    return resolved


APP_STYLE = _substitute(r"""
QMainWindow, QWidget#AppRoot {
    background: @BG_SURFACE;
    color: @TEXT_2;
}
QWidget {
    color: @TEXT_2;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}
/* QMenuBar được nhúng trong CustomTitleBar (31px) do dark_theme.qss
   (#MainMenuBar) đảm nhận hoàn toàn; rule chung ở đây từng bump min-height
   xuống ::item khiến mọi menu tràn vào nút ">>". */
QMenu {
    background: @BG_RAISED;
    color: @TEXT_2;
    border: 1px solid @BORDER;
    padding: 4px;
}
QMenu::item { padding: 6px 28px 6px 24px; }
QMenu::item:selected { background: @BG_SELECT; color: @TEXT; }
QMenu::separator { height: 1px; background: @BORDER; margin: 4px 8px; }
QFrame#WorkbenchBar {
    background: @BG_INK;
    border-bottom: 1px solid @BORDER;
}
QLabel#WindowBrand { font-weight: 600; color: @TEXT_2; padding-left: 8px; }
QLabel#Muted, QLabel#PathLabel { color: @TEXT_4; }
QFrame#ActivityBar {
    background: @BG_INK;
    border-right: 1px solid @BORDER;
}
QToolButton#ActivityButton {
    border: none;
    background: transparent;
    color: @TEXT_5;
    font-size: 12px;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
}
QToolButton#ActivityButton:hover { color: @TEXT; background: transparent; }
QToolButton#ActivityButton:checked {
    color: @TEXT;
    background: transparent;
    border-left: 2px solid @ACCENT;
}
QFrame#ExplorerPanel, QTabWidget#SideTabs::pane {
    background: @BG_INK;
    border: 0;
    border-right: 1px solid @BORDER;
}
QLabel#SidePanelTitle {
    background: @BG_INK;
    color: @TEXT_3;
    font-size: 11px;
    font-weight: 600;
    padding-left: 20px;
    letter-spacing: 0.4px;
    border-bottom: 1px solid transparent;
}
QFrame#EditorPanel { background: @BG_SURFACE; border: 0; }
QFrame#FindBar {
    background: @BG_RAISED;
    border: 0;
    border-bottom: 1px solid @BORDER;
    border-radius: 0;
}
QLineEdit, QComboBox, QSpinBox {
    background: @BG_RAISED;
    color: @TEXT;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    min-height: 25px;
    padding: 0 7px;
    selection-background-color: @BG_SELECT_SOFT;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid @ACCENT; }
QLineEdit#CommandSearch {
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
    min-height: 25px;
    max-height: 27px;
    padding: 0 10px;
}
QLineEdit#CommandSearch:focus { border-color: @ACCENT; background: @BG_RAISED; }
QPushButton {
    min-height: 25px;
    padding: 0 10px;
    border-radius: 6px;
    border: 1px solid @BORDER_STRONG;
    background: @BG_PRESSED;
    color: @TEXT_2;
}
QPushButton:hover { background: @BORDER_STRONG; color: @TEXT; }
QPushButton#PrimaryButton { background: @ACCENT; border-color: @ACCENT; color: @ON_ACCENT; }
QPushButton#PrimaryButton:hover { background: @ACCENT_HOVER; }
QPushButton#SuccessButton { background: @GREEN; border-color: @GREEN; color: @ON_ACCENT; }
QPushButton#SuccessButton:hover { background: @GREEN_LIGHT; }
QTreeView, QTreeWidget, QListWidget {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    outline: 0;
    selection-background-color: @BG_SELECT;
    selection-color: @TEXT;
    alternate-background-color: @BG_ALT;
}
QTreeView::item, QTreeWidget::item { min-height: 22px; padding: 1px 3px; }
QTreeView::item:hover, QTreeWidget::item:hover { background: @BG_HOVER; }
/* Nền của CHÍNH QHeaderView, không chỉ ::section.
   Qt chỉ vẽ `::section` cho các section có thật; vùng nằm SAU section cuối
   (khi các cột không phủ hết bề rộng bảng) do widget header tự vẽ và rơi về
   palette mặc định — vốn là màu SÁNG, vì theme này chỉ dùng QSS chứ không đặt
   dark palette. Thiếu rule này thì Project Hub hiện một dải trắng bên phải
   hàng tiêu đề. */
QHeaderView {
    background: @BG_INK;
    border: 0;
}
QHeaderView::section {
    background: @BG_INK;
    color: @TEXT_4;
    border: none;
    border-bottom: 1px solid @BORDER;
    padding: 4px 6px;
}
QTabWidget::pane { border: 0; background: @BG_SURFACE; }
QTabBar { background: @BG_INK; }
QTabBar::tab {
    background: @BG_INK;
    border: none;
    border-right: 1px solid @BORDER;
    border-top: 1px solid transparent;
    padding: 7px 12px;
    min-width: 78px;
    color: @TEXT_4;
}
QTabBar::tab:selected {
    color: @TEXT;
    background: @BG_SURFACE;
    border-top: 1px solid @ACCENT;
}
QTabBar::tab:hover { background: @BG_HOVER; color: @TEXT_2; }
/* nút đóng tab: do StudioTabBar tự tạo, thay pixmap đỏ mặc định của Qt */
QToolButton#TabCloseButton {
    background: transparent;
    border: 0;
    border-radius: 6px;
    padding: 0;
}
QToolButton#TabCloseButton:hover { background: @BG_PRESSED; }
QPlainTextEdit#CodeEditor {
    background: @BG_SURFACE;
    color: @TEXT_2;
    border: none;
    selection-background-color: @BG_SELECT_SOFT;
    selection-color: @TEXT;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 13px;
}
QTabWidget#BottomPanel::pane {
    border: 0;
    border-top: 1px solid @BORDER;
    background: @BG_INK;
}
QTabWidget#BottomPanel QTabBar::tab {
    background: @BG_INK;
    color: @TEXT_4;
    border: 0;
    border-bottom: 1px solid transparent;
    padding: 4px 10px;
    min-width: 52px;
    font-size: 11px;
    text-transform: uppercase;
}
QTabWidget#BottomPanel QTabBar::tab:selected {
    color: @TEXT;
    border-top: 0;
    border-bottom: 1px solid @ACCENT;
}
QPlainTextEdit#LogView {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
QStatusBar {
    background: @STATUS_BG;
    color: @STATUS_FG;
    border: 0;
    min-height: 22px;
    max-height: 22px;
}
QStatusBar QLabel { color: @STATUS_FG; padding: 0 8px; font-size: 11px; }
QStatusBar::item { border: 0; }
QSplitter::handle { background: @BORDER; }
QSplitter::handle:hover { background: @BORDER_HOVER; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 3px; }
QScrollBar:vertical { background: @BG_INK; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: @SCROLL; min-height: 20px; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: @SCROLL_HOVER; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: @BG_INK; height: 7px; }
QScrollBar::handle:horizontal { background: @SCROLL; min-width: 20px; border-radius: 6px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QCompleter QAbstractItemView {
    background: @BG_RAISED;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    selection-background-color: @BG_SELECT;
    selection-color: @TEXT;
    outline: 0;
}
QDialog { background: @BG_SURFACE; }
QLabel#AboutMark {
    background: @ACCENT;
    color: @ON_ACCENT;
    border-radius: 8px;
    font-size: 18px;
    font-weight: 700;
}
QLabel#AboutTitle { color: @TEXT; font-size: 22px; font-weight: 650; }
QTabWidget#AboutTabs::pane { border: 1px solid @BORDER; background: @BG_SURFACE; }
QTextBrowser, QTextEdit, QPlainTextEdit {
    background: @BG_SURFACE;
    color: @TEXT_2;
    border: 1px solid @BORDER;
}
QTableWidget {
    background: @BG_SURFACE;
    color: @TEXT_2;
    border: 1px solid @BORDER;
    gridline-color: @BORDER;
    selection-background-color: @BG_SELECT;
}
QGraphicsView { background: @BG_INK; border: 1px solid @BORDER; }
QCheckBox { color: @TEXT_2; spacing: 5px; }
QMessageBox, QFileDialog { background: @BG_SURFACE; }
""")

APP_STYLE += _substitute(r"""
QFrame#Panel {
    background: @BG_SURFACE;
    border: 1px solid @BORDER;
    border-radius: 0;
}
QLabel#ViewTitle {
    color: @TEXT_3;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 0;
}
QLabel#HeroTitle { color: @TEXT; font-size: 24px; font-weight: 600; }
QLabel#SectionTitle { color: @TEXT_2; font-size: 12px; font-weight: 600; }
""")

APP_STYLE += _substitute(r"""
QFrame#ExplorerHeader {
    background: @BG_INK;
    border-bottom: 1px solid @BG_HOVER;
}
QPushButton#ExplorerToolButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    color: @TEXT_3;
    font-size: 11px;
}
QPushButton#ExplorerToolButton:hover {
    background: @BG_HOVER;
    color: @TEXT;
}
QTreeView {
    show-decoration-selected: 1;
}
QTreeView::item {
    min-height: 22px;
    border: none;
}
QTreeView::item:hover {
    background: @BG_HOVER;
}
QTreeView::item:selected {
    background: @BG_SELECT_SOFT;
}
""")

APP_STYLE += _substitute(r"""
QLabel#ProjectName {
    color: @TEXT_4;
    padding-left: 6px;
}
QLabel#WorkbenchState {
    color: @TEXT_4;
    padding-right: 6px;
}
QPushButton#CommandCenter {
    min-height: 24px;
    max-height: 24px;
    min-width: 320px;
    max-width: 520px;
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    color: @TEXT_4;
    text-align: center;
    padding: 0 12px;
}
QPushButton#CommandCenter:hover {
    background: @BG_RAISED;
    border-color: @BORDER_HOVER;
    color: @TEXT_2;
}
QLabel#WelcomeTitle {
    color: @TEXT;
    font-size: 25px;
    font-weight: 600;
}
QDialog#CommandPalette {
    background: @BG_RAISED;
    border: 1px solid @BORDER_STRONG;
}
QDialog#CommandPalette QListWidget {
    background: @BG_RAISED;
}
""")


APP_STYLE += _substitute(r"""
QTableView {
    background: @BG_SURFACE;
    color: @TEXT_2;
    border: 1px solid @BORDER;
    gridline-color: @BG_ALT;
    selection-background-color: @BG_SELECT;
    selection-color: @TEXT;
    alternate-background-color: @BG_HOVER;
}
QTableView::item { padding: 3px 5px; }
QTableView::item:hover { background: @BG_HOVER; }
""")


APP_STYLE += _substitute(r"""
QScrollArea#StartPageScroll,
QWidget#StartPage {
    background: @BG_INK;
    border: 0;
}
QWidget#StartPageContent {
    background: transparent;
}
QLabel#StartHeroTitle {
    color: @TEXT;
    font-size: 27px;
    font-weight: 600;
}
QLabel#StartHeroSubtitle {
    color: @TEXT_4;
    font-size: 18px;
}
QLabel#StartSectionTitle {
    color: @TEXT;
    font-size: 16px;
    font-weight: 600;
    padding: 2px 0 3px 0;
}
QLabel#StartCardTitle {
    color: @TEXT;
    font-size: 13px;
    font-weight: 600;
}
QLabel#StartPath {
    color: @TEXT_4;
    font-size: 11px;
}
QLabel#StartMetric {
    color: @TEXT_3;
    background: @BG_RAISED;
    border-radius: 6px;
    padding: 4px 7px;
}
QPushButton#StartLinkButton {
    min-height: 27px;
    max-height: 30px;
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: @ACCENT;
    text-align: left;
    padding: 0 5px;
}
QPushButton#StartLinkButton:hover {
    background: @BG_RAISED;
    color: @ACCENT_HOVER;
}
QFrame#StartCard {
    background: @BG_RAISED;
    border: 1px solid @BORDER;
    border-radius: 8px;
}
QFrame#StartCard:hover {
    border-color: @BORDER_HOVER;
    background: @BG_PRESSED;
}
QPushButton#StartCardButton {
    min-height: 25px;
    background: @BG_PRESSED;
    border: 1px solid @BORDER_STRONG;
}
QPushButton#StartCardButton:hover {
    background: @BORDER_STRONG;
    border-color: @BORDER_HOVER;
}
QListWidget#RecentProjects {
    background: transparent;
    border: 0;
    color: @TEXT_3;
    outline: 0;
}
QListWidget#RecentProjects::item {
    min-height: 42px;
    padding: 5px 6px;
    border-radius: 6px;
}
QListWidget#RecentProjects::item:hover {
    background: @BG_RAISED;
}
QListWidget#RecentProjects::item:selected {
    background: @BG_SELECT;
    color: @TEXT;
}
QLabel#RecentProjectName {
    color: @TEXT;
    font-size: 12px;
    font-weight: 600;
}
QLabel#RecentProjectPath {
    color: @TEXT_5;
    font-size: 10px;
}
QToolButton#RecentProjectMenu {
    color: @TEXT_3;
    background: transparent;
    border: 0;
    border-radius: 6px;
    padding: 3px;
}
QToolButton#RecentProjectMenu:hover {
    background: @BG_SELECT;
    color: @TEXT;
}
""")


APP_STYLE += _substitute(r"""
QFrame#TerminalToolbar {
    background: @BG_INK;
    border-bottom: 1px solid @BORDER;
}
QLabel#TerminalTitle {
    color: @TEXT_2;
    font-size: 11px;
    font-weight: 600;
}
QLabel#TerminalState {
    color: @TEXT_5;
    font-size: 10px;
    padding-left: 5px;
}
QPushButton#PanelToolButton {
    min-height: 20px;
    max-height: 20px;
    padding: 0 6px;
    background: transparent;
    border: 0;
}
QPushButton#PanelToolButton:hover {
    background: @BG_HOVER;
}
QPlainTextEdit#TerminalSurface {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    padding: 4px 7px 5px 7px;
    font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
    font-size: 11px;
    selection-background-color: @BG_SELECT_SOFT;
}
""")


APP_STYLE += _substitute(r"""
QToolButton#WorkbenchLayoutButton {
    min-width: 27px; max-width: 27px; min-height: 25px; max-height: 25px;
    border: 1px solid transparent; border-radius: 6px; background: transparent; padding: 0;
}
QToolButton#WorkbenchLayoutButton:hover { background: @BG_HOVER; border-color: @BORDER_STRONG; }
QToolButton#WorkbenchLayoutButton:checked { background: @BG_RAISED; border-color: @BORDER_HOVER; }
""")


APP_STYLE += _substitute(r"""
QComboBox {
    min-height: 25px;
    padding: 2px 7px;
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
}
QComboBox:hover {
    border-color: @BORDER_HOVER;
}
QComboBox QAbstractItemView {
    background: @BG_RAISED;
    border: 1px solid @BORDER_STRONG;
    selection-background-color: @BG_SELECT;
}
""")


APP_STYLE += _substitute(r"""
QToolButton#BottomPanelClose {
    min-width: 24px;
    max-width: 24px;
    min-height: 22px;
    max-height: 22px;
    margin: 1px 4px 0 0;
    padding: 0;
    background: transparent;
    border: 0;
    border-radius: 6px;
}
QToolButton#BottomPanelClose:hover {
    background: @BG_HOVER;
}
""")


APP_STYLE += _substitute(r"""
QPlainTextEdit#LogView {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
    font-size: 11px;
    selection-background-color: @BG_SELECT_SOFT;
}
QFrame#HexToolbar {
    background: @BG_ALT;
    border-bottom: 1px solid @BORDER;
}
QLabel#HexFile {
    color: @INFO;
    font-weight: 600;
}
QLabel#HexRange {
    color: @TEXT_4;
    font-family: Consolas, "Cascadia Mono", monospace;
}
QPlainTextEdit#HexView {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    padding: 4px 7px;
    font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
    font-size: 11px;
    selection-background-color: @BG_SELECT_SOFT;
}
""")


APP_STYLE += _substitute(r"""
QFrame#CenterWorkbench { background: @BG_INK; }
QWidget#AIChatView { background: @BG_INK; border-left: 1px solid @BORDER; }
QFrame#AIChatHeader { background: @BG_INK; border-bottom: 1px solid @BORDER; }
QLabel#AIChatTitle { color: @TEXT; font-weight: 600; font-size: 12px; }
QLabel#AIContextBadge {
    color: @INFO; background: @BG_RAISED; border: 1px solid @BORDER;
    border-radius: 6px; padding: 2px 5px; font-size: 10px;
}
QToolButton#AIChatToolButton {
    min-width: 24px; max-width: 24px; min-height: 23px; max-height: 23px;
    background: transparent; border: 0; border-radius: 6px;
}
QToolButton#AIChatToolButton:hover { background: @BG_HOVER; }
QFrame#AIConfigPanel { background: @BG_ALT; border-bottom: 1px solid @BORDER; }
QTextBrowser#AIChatTranscript {
    background: @BG_INK; color: @TEXT_2; border: 0; padding: 8px; font-size: 11px;
}
QFrame#AIChatComposer { background: @BG_INK; border-top: 1px solid @BORDER; }
QPlainTextEdit#AIChatPrompt {
    background: @BG_INK; color: @TEXT_2; border: 1px solid @BORDER_STRONG;
    border-radius: 8px; padding: 5px 7px; font-size: 11px;
}
QPlainTextEdit#AIChatPrompt:focus { border-color: @ACCENT; }
QLabel#AIChatStatus { color: @TEXT_4; font-size: 10px; }
QPushButton#AIChatSend {
    min-width: 66px; min-height: 25px; background: @ACCENT;
    border: 1px solid @ACCENT_HOVER; border-radius: 6px; color: @ON_ACCENT;
}
QPushButton#AIChatSend:hover { background: @ACCENT_HOVER; }
""")

APP_STYLE += _substitute(r"""
QDialog#MediaTekMREConfigDialog {
    background: transparent;
}
QFrame#MREDialogCard {
    background: @BG_SURFACE;
    border: 1px solid @BORDER_STRONG;
    border-radius: 12px;
}
QFrame#MREDialogTitleBar {
    background: @BG_INK;
    border: 0;
    border-bottom: 1px solid @BORDER;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}
QLabel#MREDialogIcon {
    background: @BG_RAISED;
    border-radius: 8px;
}
QLabel#MREDialogTitle {
    color: @TEXT;
    font-size: 14px;
    font-weight: 700;
}
QLabel#MREDialogSubtitle {
    color: @TEXT_4;
    font-size: 10px;
}
QToolButton#MREDialogClose {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    background: transparent;
    border: 0;
    border-radius: 8px;
}
QToolButton#MREDialogClose:hover {
    background: @BG_HOVER;
}
QWidget#MREDialogBody {
    background: @BG_SURFACE;
}
QLabel#MREFieldLabel {
    color: @TEXT_3;
    font-size: 11px;
    font-weight: 600;
}
QLineEdit#MREField, QComboBox#MRECombo {
    background: @BG_INK;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
    min-height: 34px;
    padding: 0 11px;
    font-family: Consolas, "Cascadia Mono", "Segoe UI", sans-serif;
}
QLineEdit#MREField:focus, QComboBox#MRECombo:focus {
    border: 1px solid @ACCENT;
}
QComboBox#MRECombo::drop-down {
    width: 28px;
    border: 0;
}
QComboBox#MRECombo QAbstractItemView {
    background: @BG_INK;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    selection-background-color: @BG_SELECT;
    selection-color: @TEXT;
    outline: 0;
}
QLabel#MREDialogHint {
    color: @INFO;
    background: @INFO_BG;
    border: 1px solid @INFO_BORDER;
    border-radius: 6px;
    padding: 7px 9px;
    font-size: 10px;
}
QLabel#MREPathPreview {
    color: @TEXT_5;
    font-size: 10px;
    padding-top: 2px;
}
QFrame#MREDialogFooter {
    background: @BG_SURFACE;
    border: 0;
    border-top: 1px solid @BORDER;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}
QPushButton#MRECancelButton {
    min-height: 34px;
    min-width: 82px;
    background: @BG_PRESSED;
    color: @TEXT_3;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
    padding: 0 14px;
}
QPushButton#MRECancelButton:hover {
    background: @BORDER_STRONG;
    color: @TEXT;
}
QPushButton#MRESaveButton {
    min-height: 34px;
    min-width: 118px;
    background: @ACCENT;
    color: @ON_ACCENT;
    border: 1px solid @ACCENT_HOVER;
    border-radius: 8px;
    padding: 0 15px;
    font-weight: 700;
}
QPushButton#MRESaveButton:hover {
    background: @ACCENT_HOVER;
}
""")


APP_STYLE += _substitute(r"""
QFrame#AIActivityFrame {
    background: @BG_INK;
    border-top: 1px solid @BORDER;
    border-bottom: 1px solid @BORDER;
}
QLabel#AIActivityTitle {
    color: @TEXT_3;
    font-size: 10px;
    font-weight: 700;
}
QLabel#AIActivityNote {
    color: @SCROLL_HOVER;
    font-size: 9px;
}
QPlainTextEdit#AIActivityView {
    background: @BG_INK;
    color: @TEXT_3;
    border: 1px solid @BORDER;
    border-radius: 8px;
    padding: 4px 5px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 10px;
}
QFrame#AIShellCard {
    background: @BG_ALT;
    border-top: 1px solid @BORDER_STRONG;
    border-bottom: 1px solid @BORDER_STRONG;
}
QLabel#AIShellTitle {
    color: @ACCENT;
    font-size: 10px;
    font-weight: 700;
}
QLabel#AIShellReason {
    color: @TEXT_3;
    font-size: 10px;
}
QLabel#AIShellRisk {
    color: @INFO;
    background: @BG_RAISED;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    padding: 2px 5px;
    font-size: 9px;
    font-weight: 700;
}
QLabel#AIShellRisk[risk="dangerous"] { color: @RED; border-color: @RED_BORDER; }
QLabel#AIShellRisk[risk="sensitive"] { color: @AMBER; border-color: @AMBER_BORDER; }
QLabel#AIShellRisk[risk="safe"] { color: @GREEN_LIGHT; border-color: @GREEN_BORDER; }
QPlainTextEdit#AIShellCommand {
    background: @BG_INK;
    color: @SYN_FUNC;
    border: 1px solid @BORDER;
    border-radius: 8px;
    padding: 5px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 10px;
}
QPushButton#AIShellRun {
    min-height: 25px;
    background: @ACCENT;
    color: @ON_ACCENT;
    border: 1px solid @ACCENT_HOVER;
    border-radius: 6px;
    padding: 0 9px;
}
QPushButton#AIShellRun:hover { background: @ACCENT_HOVER; }
QPushButton#AIShellReject {
    min-height: 25px;
    background: @BG_RAISED;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    padding: 0 9px;
}
QPushButton#AIShellReject:hover { background: @BG_PRESSED; }
""")

APP_STYLE += _substitute(r"""
/* AI Workbench v1 */
QPushButton#AIAccessModeButton {
    min-height: 27px;
    max-height: 27px;
    min-width: 136px;
    background: @BG_RAISED;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
    padding: 0 9px 0 7px;
    text-align: left;
}
QPushButton#AIAccessModeButton:hover {
    background: @BG_PRESSED;
    border-color: @BORDER_HOVER;
}
QPushButton#AIAccessModeButton[accessMode="full"] {
    color: @ACCENT_HOVER;
    border-color: @AMBER_BORDER;
}
QMenu#AIAccessMenu {
    background: @BG_RAISED;
    color: @TEXT;
    border: 1px solid @BORDER_STRONG;
    border-radius: 12px;
    padding: 5px;
}
QMenu#AIAccessMenu::item {
    background: transparent;
    padding: 0;
    margin: 0;
}
QWidget#AIAccessOption {
    background: transparent;
    border: 0;
    border-radius: 8px;
}
QWidget#AIAccessOption:hover {
    background: @BG_PRESSED;
}
QWidget#AIAccessOption[checked="true"] {
    background: @BG_PRESSED;
}
QLabel#AIAccessOptionIcon {
    background: transparent;
    border: 0;
}
QPushButton#AIAccessOptionIconGlyph {
    background: transparent;
    border: 0;
    padding: 0;
}
QLabel#AIAccessOptionTitle {
    background: transparent;
    color: @TEXT;
    font-size: 12px;
    font-weight: 500;
}
QLabel#AIAccessOptionDescription {
    background: transparent;
    color: @TEXT_4;
    font-size: 10px;
}
QLabel#AIAccessOptionCheck {
    background: transparent;
    color: @TEXT;
    font-size: 15px;
    font-weight: 700;
}
QLabel#AIProviderCompact {
    color: @TEXT_4;
    font-size: 10px;
}
QPushButton#AIChatSendIcon {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border-radius: 6px;
    background: @BG_PRESSED;
    border: 1px solid @BORDER_STRONG;
}
QPushButton#AIChatSendIcon:hover {
    background: @ACCENT;
    border-color: @ACCENT_HOVER;
}
QPushButton#AIChatSendIcon[running="true"] {
    background: @RED_DEEP;
    border-color: @RED_DEEP;
}
QPushButton#AIChatSendIcon[running="true"]:hover {
    background: @RED_DEEP;
    border-color: @RED;
}
QFrame#AIChangesCard,
QFrame#AIShellCard {
    background: @BG_ALT;
    border-top: 1px solid @BORDER;
    border-bottom: 1px solid @BORDER;
}
QLabel#AIChangesTitle,
QLabel#AIShellTitle {
    color: @TEXT;
    font-weight: 600;
    font-size: 10px;
}
QLabel#AIChangesSummary {
    color: @GREEN;
    font-size: 10px;
}
QLabel#AIChangesFiles,
QLabel#AIShellReason {
    color: @TEXT_3;
    font-size: 10px;
}
QPushButton#AIReviewChanges,
QPushButton#AIRejectChanges,
QPushButton#AIApplyChanges,
QPushButton#AIShellReject,
QPushButton#AIShellRun {
    min-height: 24px;
    padding: 0 8px;
    border-radius: 6px;
    background: @BG_HOVER;
    border: 1px solid @BORDER_STRONG;
}
QPushButton#AIApplyChanges,
QPushButton#AIShellRun {
    background: @ACCENT;
    border-color: @ACCENT_HOVER;
    color: @ON_ACCENT;
}
QPushButton#AIApplyChanges:hover,
QPushButton#AIShellRun:hover {
    background: @ACCENT_HOVER;
}

/* AI provider dialog */
QDialog#AIProviderDialog { background: transparent; }
QFrame#AIProviderCard {
    background: @BG_SURFACE;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
}
QFrame#AIProviderTitleBar {
    background: @BG_RAISED;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 1px solid @BORDER;
}
QLabel#AIProviderTitle {
    color: @TEXT;
    font-size: 13px;
    font-weight: 600;
}
QToolButton#AIProviderClose {
    min-width: 25px;
    max-width: 25px;
    min-height: 23px;
    max-height: 23px;
    border: 0;
    border-radius: 6px;
    background: transparent;
}
QToolButton#AIProviderClose:hover { background: @RED_DEEP; }
QFrame#AIProviderFooter {
    background: @BG_HOVER;
    border-top: 1px solid @BORDER;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
}
QLabel#AIProviderHint { color: @TEXT_4; font-size: 10px; }
QLabel#AIProviderTestStatus[state="ok"] { color: @GREEN_LIGHT; }
QLabel#AIProviderTestStatus[state="error"] { color: @RED; }
QLabel#AIProviderTestStatus[state="busy"] { color: @INFO; }
QLabel#AIProviderTestStatus[state="idle"] { color: @TEXT_4; }
QPushButton#AIProviderTest,
QPushButton#AIProviderApply,
QPushButton#AIProviderCancel,
QPushButton#AIProviderSave {
    min-height: 27px;
    padding: 0 10px;
    border-radius: 8px;
    background: @BG_HOVER;
    border: 1px solid @BORDER_STRONG;
}
QPushButton#AIProviderSave {
    background: @ACCENT;
    border-color: @ACCENT_HOVER;
    color: @ON_ACCENT;
}
QPushButton#AIProviderSave:hover { background: @ACCENT_HOVER; }

/* VS Code-like AI diff tab */
QWidget#AIDiffView { background: @BG_INK; }
QFrame#AIDiffToolbar {
    background: @BG_ALT;
    border-bottom: 1px solid @BORDER;
}
QLabel#AIDiffTitle {
    color: @TEXT;
    font-weight: 600;
    font-size: 11px;
}
QLabel#AIDiffSummary { color: @INFO; font-size: 10px; }
QListWidget#AIDiffFiles {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    border-right: 1px solid @BORDER;
}
QListWidget#AIDiffFiles::item { padding: 6px 7px; }
QListWidget#AIDiffFiles::item:selected { background: @BG_SELECT; }
QLabel#AIDiffPaneTitle {
    min-height: 24px;
    padding-left: 8px;
    color: @TEXT_3;
    background: @BG_ALT;
    border-bottom: 1px solid @BORDER;
}
QPlainTextEdit#AIDiffBefore,
QPlainTextEdit#AIDiffAfter {
    background: @BG_INK;
    color: @TEXT_2;
    border: 0;
    padding: 5px 7px;
    font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
    font-size: 11px;
    selection-background-color: @BG_SELECT_SOFT;
}
QLabel#AIDiffStatus {
    min-height: 28px;
    padding: 4px 8px;
    color: @TEXT_4;
    background: @BG_ALT;
    border-top: 1px solid @BORDER;
}
QPushButton#AIDiffApply,
QPushButton#AIDiffReject {
    min-height: 25px;
    padding: 0 9px;
    border-radius: 6px;
    background: @BG_HOVER;
    border: 1px solid @BORDER_STRONG;
}
QPushButton#AIDiffApply {
    background: @ACCENT;
    border-color: @ACCENT_HOVER;
    color: @ON_ACCENT;
}
QPushButton#AIDiffApply:hover { background: @ACCENT_HOVER; }
""")

APP_STYLE += _substitute(r"""
/* Chat session menu */
QMenu#AISessionsMenu {
    background: @BG_RAISED;
    color: @TEXT_2;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
    padding: 5px;
    min-width: 260px;
}
QMenu#AISessionsMenu::item {
    min-height: 25px;
    padding: 3px 10px;
    border-radius: 8px;
}
QMenu#AISessionsMenu::item:selected { background: @BG_SELECT; color: @TEXT; }
QMenu#AISessionsMenu::item:disabled { color: @SCROLL_HOVER; }
QMenu#AISessionsMenu::separator {
    height: 1px;
    background: @BORDER_STRONG;
    margin: 4px 6px;
}
""")

APP_STYLE += _substitute(r"""
/* ============================ UI DESIGNER ============================ */
QToolBar#DesignerToolbar {
    background: @BG_INK;
    border: 0;
    border-bottom: 1px solid @BORDER;
    padding: 2px 6px;
    spacing: 2px;
}
QToolBar#DesignerToolbar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 2px 5px;
    color: @TEXT_2;
}
QToolBar#DesignerToolbar QToolButton:hover {
    background: @BG_HOVER;
    border-color: @BORDER_STRONG;
}
QToolBar#DesignerToolbar QToolButton:checked {
    background: @BG_SELECT;
    border-color: @ACCENT_HOVER;
}
QToolBar#DesignerToolbar::separator {
    width: 1px;
    background: @BORDER_STRONG;
    margin: 3px 5px;
}

QLabel#DesignerBreadcrumb {
    background: @BG_SURFACE;
    color: @TEXT_4;
    font-size: 11px;
    padding: 3px 4px;
    border-bottom: 1px solid @BORDER;
}

QWidget#ScreenBar {
    background: @BG_RAISED;
    border-bottom: 1px solid @BORDER;
}
QLabel#ScreenBarLabel {
    color: @TEXT_4;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}
QComboBox#ScreenCombo {
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    min-height: 22px;
    padding: 0 6px;
}
QComboBox#ScreenCombo:hover { border-color: @SCROLL_HOVER; }
QToolButton#ScreenActionBtn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}
QToolButton#ScreenActionBtn:hover { background: @BG_HOVER; border-color: @BORDER_STRONG; }

QWidget#DesignerPalette {
    background: @BG_INK;
    border-right: 1px solid @BORDER;
}
QTreeWidget#PaletteTree {
    background: transparent;
    border: 0;
    outline: 0;
}
QTreeWidget#PaletteTree::item { min-height: 22px; padding: 0; }
QLineEdit#PaletteSearch {
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    min-height: 22px;
    margin: 6px;
}
QLabel#PaletteHint {
    color: @TEXT_4;
    font-size: 10px;
    padding: 4px 8px 8px 8px;
}

QWidget#LayersPanel {
    background: @BG_INK;
    border-left: 1px solid @BORDER;
}
QLabel#PanelHeaderTitle {
    color: @TEXT_3;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}
QWidget#LayerTools { background: transparent; }
QToolButton#LayerToolBtn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}
QToolButton#LayerToolBtn:hover { background: @BG_HOVER; border-color: @BORDER_STRONG; }
QListWidget#LayerList {
    background: @BG_SURFACE;
    border: 0;
    outline: 0;
}
QListWidget#LayerList::item { min-height: 20px; padding: 0 4px; }
QListWidget#LayerList::item:hover { background: @BG_HOVER; }
QListWidget#LayerList::item:selected {
    background: @BG_SELECT;
    color: @TEXT;
}

QWidget#InspectorForm {
    background: @BG_INK;
    border-left: 1px solid @BORDER;
}
QLabel#InspectorSelection {
    color: @TEXT_4;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}
QLabel#InspectorSelectionText {
    color: @TEXT_2;
    font-weight: 600;
}
QLabel#PropGroupLabel {
    color: @TEXT_4;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 6px 2px 2px 2px;
}
QFrame#PropRow { background: transparent; border: 0; }
QLabel#PropName { color: @TEXT_4; }
QLabel#InlineFieldLabel { color: @TEXT_4; font-size: 10px; }
QLineEdit#PropIdEdit {
    background: @BG_INK;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    min-height: 22px;
    font-family: Consolas, "Courier New", monospace;
}
QLineEdit#PropIdEdit[state="error"] { border-color: @RED; }
QLabel#PropertyHint {
    color: @TEXT_4;
    font-size: 10px;
    padding: 6px 2px;
}

QPushButton#ColorButton { min-height: 22px; }
QFrame#ColorPopup {
    background: @BG_RAISED;
    border: 1px solid @BORDER_STRONG;
    border-radius: 8px;
}

QWidget#ModalDialog { background: @BG_SURFACE; }
QWidget#DialogTitleBar {
    background: @BG_INK;
    border-bottom: 1px solid @BORDER;
}
QLabel#DialogTitleText { color: @TEXT_2; font-weight: 600; }
QPushButton#DialogCloseButton {
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: @TEXT_4;
}
QPushButton#DialogCloseButton:hover { background: @RED_DEEP; color: @TEXT; }
QFrame#ModalCard { background: @BG_SURFACE; border: 1px solid @BORDER; border-radius: 8px; }
QScrollArea#ModalBody { background: transparent; border: 0; }
QScrollArea#ModalBody > QWidget > QWidget { background: transparent; }
QWidget#ModalFooter { background: transparent; }
QFrame#DesignerCard {
    background: @BG_RAISED;
    border: 1px solid @BORDER;
    border-radius: 8px;
}
QLabel#DialogHint { color: @TEXT_4; font-size: 11px; }
QLabel#DialogHint[state="error"] { color: @RED; }
QLabel#DialogHint[state="ok"] { color: @GREEN; }
QPushButton#GhostButton {
    background: @BG_PRESSED;
    border: 1px solid @BORDER_STRONG;
    border-radius: 6px;
    color: @TEXT_2;
}
QPushButton#GhostButton:hover { background: @BORDER_STRONG; color: @TEXT; }
""")
