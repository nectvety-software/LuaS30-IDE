from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from app.core.paths import tool_python
from app.ui.icons import apply_icon


STARTUP_MODES = (
    ("Welcome", "welcome"),
    ("Project Hub", "project_hub"),
    ("Empty Editor", "empty_editor"),
)

COMPILER_PROFILES = (
    ("Auto Detect", "auto"),
    ("ARM GCC (MRE)", "gcc"),
    ("RVDS / RVCT", "rvds"),
    ("ARM ADS 1.2", "ads12"),
)

S30PLUS_PROFILES = (
    ("Auto - prefer Native MRE SDK", "auto"),
    ("Standalone ABI Resolver", "standalone"),
    ("S30+ Native MRE SDK", "s30plus-native"),
    ("Nokia 225 Dual SIM RM-1011", "nokia225-rm1011"),
)


class SettingsView(QWidget):
    startup_mode_changed = Signal(str)
    compiler_profile_changed = Signal(str)
    toolchain_root_changed = Signal(str)
    compat_profile_changed = Signal(str)
    mre_sdk_root_changed = Signal(str)
    device_imsi_changed = Signal(str)

    def __init__(
        self,
        engine_root: Path,
        *,
        startup_mode: str = "welcome",
        compiler_profile: str = "auto",
        toolchain_root: Path | None = None,
        compat_profile: str = "auto",
        mre_sdk_root: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.engine_root = Path(engine_root)
        self._toolchain_root = Path(toolchain_root or (self.engine_root / "toolchain/arm-gcc"))
        self._mre_sdk_root = Path(mre_sdk_root).expanduser() if mre_sdk_root else Path()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        title = QLabel("SETTINGS")
        title.setObjectName("ViewTitle")
        root.addWidget(title)

        startup_frame = QFrame()
        startup_frame.setObjectName("Panel")
        startup_form = QFormLayout(startup_frame)
        startup_form.setContentsMargins(14, 12, 14, 12)
        startup_form.setSpacing(8)

        self.startup_mode = QComboBox()
        for label, value in STARTUP_MODES:
            self.startup_mode.addItem(label, value)
        self.startup_mode.setToolTip(
            "Choose which workspace screen is activated when LuaS30 Studio starts."
        )

        self.startup_description = QLabel()
        self.startup_description.setObjectName("Muted")
        self.startup_description.setWordWrap(True)

        startup_form.addRow("Startup screen", self.startup_mode)
        startup_form.addRow("", self.startup_description)
        root.addWidget(startup_frame)

        compiler_frame = QFrame()
        compiler_frame.setObjectName("Panel")
        compiler_form = QFormLayout(compiler_frame)
        compiler_form.setContentsMargins(14, 12, 14, 12)
        compiler_form.setSpacing(8)

        self.compiler_profile = QComboBox()
        for label, value in COMPILER_PROFILES:
            self.compiler_profile.addItem(label, value)
        self.compiler_profile.setToolTip(
            "Select ARM GCC, RVDS/RVCT, ADS1.2, or let LuaS30 auto-detect the toolchain."
        )

        root_row = QWidget()
        root_layout = QHBoxLayout(root_row)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(5)
        self.toolchain_root = QLineEdit()
        self.toolchain_root.setText(str(self._toolchain_root))
        browse = QPushButton("Browse")
        apply_icon(browse, "folder_open", 14)
        browse.clicked.connect(self._browse_toolchain)
        root_layout.addWidget(self.toolchain_root, 1)
        root_layout.addWidget(browse)

        self.compiler_description = QLabel()
        self.compiler_description.setObjectName("Muted")
        self.compiler_description.setWordWrap(True)

        compiler_form.addRow("Compiler profile", self.compiler_profile)
        compiler_form.addRow("Toolchain root", root_row)
        compiler_form.addRow("", self.compiler_description)
        root.addWidget(compiler_frame)

        compat_frame = QFrame()
        compat_frame.setObjectName("Panel")
        compat_form = QFormLayout(compat_frame)
        compat_form.setContentsMargins(14, 12, 14, 12)
        compat_form.setSpacing(8)

        self.compat_profile = QComboBox()
        for label, value in S30PLUS_PROFILES:
            self.compat_profile.addItem(label, value)

        sdk_row = QWidget()
        sdk_layout = QHBoxLayout(sdk_row)
        sdk_layout.setContentsMargins(0, 0, 0, 0)
        sdk_layout.setSpacing(5)
        self.mre_sdk_root = QLineEdit()
        self.mre_sdk_root.setPlaceholderText("MRE SDK root (or set MRE_SDK)")
        if self._mre_sdk_root:
            self.mre_sdk_root.setText(str(self._mre_sdk_root))
        sdk_browse = QPushButton("Browse")
        apply_icon(sdk_browse, "folder_open", 14)
        sdk_browse.clicked.connect(self._browse_mre_sdk)
        sdk_layout.addWidget(self.mre_sdk_root, 1)
        sdk_layout.addWidget(sdk_browse)

        self.device_imsi = QLineEdit()
        self.device_imsi.setEchoMode(QLineEdit.EchoMode.Password)
        self.device_imsi.setPlaceholderText("Optional; session only, never saved")
        self.device_imsi.setToolTip(
            "Nokia retail firmware commonly requires VXP binding to SIM 1 IMSI. "
            "LuaS30 passes this to the builder in the process environment and does not save it."
        )

        self.compat_description = QLabel()
        self.compat_description.setObjectName("Muted")
        self.compat_description.setWordWrap(True)

        compat_form.addRow("S30+ compatibility", self.compat_profile)
        compat_form.addRow("MRE SDK root", sdk_row)
        compat_form.addRow("Nokia IMSI", self.device_imsi)
        compat_form.addRow("", self.compat_description)
        root.addWidget(compat_frame)

        environment = QFrame()
        environment.setObjectName("Panel")
        form = QFormLayout(environment)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(8)

        self.python = QLineEdit()
        self.python.setReadOnly(True)
        self.gcc = QLineEdit()
        self.gcc.setReadOnly(True)
        self.emu = QLineEdit()
        self.emu.setReadOnly(True)
        self.core = QLineEdit()
        self.core.setReadOnly(True)

        form.addRow("Python", self.python)
        form.addRow("ARM GCC", self.gcc)
        form.addRow("VXPEmu", self.emu)
        form.addRow("LuaS30 Native SDK", self.core)

        refresh = QPushButton("Refresh Environment")
        apply_icon(refresh, "refresh", 14)
        refresh.clicked.connect(self.refresh)
        form.addRow("", refresh)

        root.addWidget(environment)
        root.addStretch(1)

        self.startup_mode.currentIndexChanged.connect(self._startup_changed)
        self.compiler_profile.currentIndexChanged.connect(self._compiler_changed)
        self.toolchain_root.editingFinished.connect(self._toolchain_changed)
        self.compat_profile.currentIndexChanged.connect(self._compat_changed)
        self.mre_sdk_root.editingFinished.connect(self._mre_sdk_changed)
        self.device_imsi.editingFinished.connect(
            lambda: self.device_imsi_changed.emit(self.device_imsi.text().strip())
        )
        self.set_startup_mode(startup_mode)
        self.set_compiler_profile(compiler_profile)
        self.set_compat_profile(compat_profile)
        self.refresh()

    def set_startup_mode(self, mode: str) -> None:
        mode = str(mode or "welcome")
        index = self.startup_mode.findData(mode)
        if index < 0:
            index = self.startup_mode.findData("welcome")
        blocked = self.startup_mode.blockSignals(True)
        self.startup_mode.setCurrentIndex(index)
        self.startup_mode.blockSignals(blocked)
        self._update_startup_description()

    def current_startup_mode(self) -> str:
        value = self.startup_mode.currentData()
        return str(value or "welcome")

    def _startup_changed(self, _index: int) -> None:
        self._update_startup_description()
        self.startup_mode_changed.emit(self.current_startup_mode())

    def _update_startup_description(self) -> None:
        mode = self.current_startup_mode()
        descriptions = {
            "welcome": (
                "Open the VS Code-style Welcome page with Start, Recent projects, "
                "Project Storage summary and quick actions."
            ),
            "project_hub": (
                "Open the full Project Hub / Project Storage manager first, with "
                "project search, create, import, duplicate, rename and delete actions."
            ),
            "empty_editor": (
                "Open a clean editor workspace with no source file and no tool page "
                "selected. The current project and layout can still be restored."
            ),
        }
        self.startup_description.setText(descriptions.get(mode, descriptions["welcome"]))

    def set_compiler_profile(self, profile: str) -> None:
        profile = str(profile or "auto")
        index = self.compiler_profile.findData(profile)
        if index < 0:
            index = self.compiler_profile.findData("auto")
        blocked = self.compiler_profile.blockSignals(True)
        self.compiler_profile.setCurrentIndex(index)
        self.compiler_profile.blockSignals(blocked)
        self._update_compiler_description()

    def current_compiler_profile(self) -> str:
        return str(self.compiler_profile.currentData() or "auto")

    def set_toolchain_root(self, root: Path | str) -> None:
        self._toolchain_root = Path(root).expanduser()
        self.toolchain_root.setText(str(self._toolchain_root))

    def _compiler_changed(self, _index: int) -> None:
        self._update_compiler_description()
        self.compiler_profile_changed.emit(self.current_compiler_profile())

    def _update_compiler_description(self) -> None:
        descriptions = {
            "auto": "Detect ARM GCC first, then ADS1.2 when tcc is present, otherwise RVDS/RVCT armcc+armlink.",
            "gcc": "LuaS30 ARM GCC profile: ARMv5TE, PIC, little-endian, gcc_entry.",
            "rvds": "MRE RVDS/RVCT profile: ARM7EJ-S, --apcs=/fpic, rvct_entry.",
            "ads12": "ADS1.2 compatibility profile: tcc/armcc + armlink, ARM7EJ-S, ads_entry.",
        }
        self.compiler_description.setText(
            descriptions.get(self.current_compiler_profile(), descriptions["auto"])
        )

    def _browse_toolchain(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select ARM Toolchain Root",
            self.toolchain_root.text().strip() or str(self.engine_root),
        )
        if path:
            self.toolchain_root.setText(path)
            self._toolchain_changed()

    def _toolchain_changed(self) -> None:
        value = self.toolchain_root.text().strip()
        if not value:
            return
        self._toolchain_root = Path(value).expanduser()
        self.toolchain_root_changed.emit(str(self._toolchain_root))

    def set_compat_profile(self, profile: str) -> None:
        profile = str(profile or "auto")
        index = self.compat_profile.findData(profile)
        if index < 0:
            index = self.compat_profile.findData("auto")
        blocked = self.compat_profile.blockSignals(True)
        self.compat_profile.setCurrentIndex(index)
        self.compat_profile.blockSignals(blocked)
        self._update_compat_description()

    def current_compat_profile(self) -> str:
        return str(self.compat_profile.currentData() or "auto")

    def set_mre_sdk_root(self, root: Path | str | None) -> None:
        if root:
            self._mre_sdk_root = Path(root).expanduser()
            self.mre_sdk_root.setText(str(self._mre_sdk_root))
        else:
            self._mre_sdk_root = Path()
            self.mre_sdk_root.clear()

    def _compat_changed(self, _index: int) -> None:
        self._update_compat_description()
        self.compat_profile_changed.emit(self.current_compat_profile())

    def _update_compat_description(self) -> None:
        descriptions = {
            "auto": (
                "Prefer the real MRE SDK static-library/scatter-link path when MRE_SDK is "
                "available; otherwise use LuaS30's standalone runtime resolver."
            ),
            "standalone": (
                "No vendor MRE SDK link. Useful for portability/research, but lower confidence "
                "for strict Series 30+ retail firmware."
            ),
            "s30plus-native": (
                "High-compatibility ARM GCC path using MRE SDK headers, per*.a libraries, "
                "the SDK scatter script, gcc_entry and vm_main."
            ),
            "nokia225-rm1011": (
                "Nokia 225 Dual SIM profile: 240x320, native MRE SDK link and optional "
                "IMSI-bound install VXP. Recommended for RM-1011 hardware testing."
            ),
        }
        self.compat_description.setText(
            descriptions.get(self.current_compat_profile(), descriptions["auto"])
        )

    def _browse_mre_sdk(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select MRE SDK Root",
            self.mre_sdk_root.text().strip() or str(self.engine_root),
        )
        if path:
            self.mre_sdk_root.setText(path)
            self._mre_sdk_changed()

    def _mre_sdk_changed(self) -> None:
        value = self.mre_sdk_root.text().strip()
        self._mre_sdk_root = Path(value).expanduser() if value else Path()
        self.mre_sdk_root_changed.emit(value)

    def refresh(self) -> None:
        self.python.setText(tool_python(self.engine_root))
        self.gcc.setText(
            str(self.engine_root / "toolchain/arm-gcc/bin/arm-none-eabi-gcc.exe")
        )
        self.emu.setText(str(self.engine_root / "emulator/VXPEmu.exe"))
        self.core.setText(str(self.engine_root / "sdk/luas30/include/ls30/api.h"))
