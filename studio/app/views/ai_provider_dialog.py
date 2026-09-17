from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from app.services.ai_provider_service import (
    AIConnectionTestThread, PROVIDER_DEFAULTS, ProviderConfig, environment_key,
)
from app.services.ai_credential_store import AICredentialStore
from app.ui.icons import apply_icon


class _DialogTitleBar(QFrame):
    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self.dialog = dialog
        self._drag_origin: QPoint | None = None
        self.setObjectName("AIProviderTitleBar")
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 7, 7, 7)
        title = QLabel("AI Provider Settings")
        title.setObjectName("AIProviderTitle")
        row.addWidget(title)
        row.addStretch(1)
        close = QToolButton()
        close.setObjectName("AIProviderClose")
        apply_icon(close, "close", 13)
        close.clicked.connect(dialog.reject)
        row.addWidget(close)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = (
                event.globalPosition().toPoint()
                - self.dialog.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.dialog.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)


class AIProviderDialog(QDialog):
    applied = Signal(object, str, bool)

    def __init__(
        self,
        config: ProviderConfig,
        session_api_key: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("AIProviderDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(590)
        self.setMaximumWidth(720)
        self._test_worker: AIConnectionTestThread | None = None
        self._initial = config
        self.credential_store = AICredentialStore()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("AIProviderCard")
        outer.addWidget(card)
        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(self))

        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(18, 16, 18, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)

        self.provider = QComboBox()
        for key, data in PROVIDER_DEFAULTS.items():
            self.provider.addItem(data["label"], key)
        self.model = QLineEdit()
        self.base_url = QLineEdit()
        saved_key = self.credential_store.load_key(config.provider)
        self.api_key = QLineEdit(session_api_key or saved_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("API key for the selected provider")
        self.remember_key = QCheckBox("Save API key to local JSON (ai_credentials.json)")
        self.remember_key.setChecked(bool(saved_key) or bool(session_api_key) or bool(PROVIDER_DEFAULTS.get(config.provider, {}).get("env")))
        self.remember_key.setToolTip("Stores the key locally outside project folders. The JSON file is plaintext on disk.")
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 600)
        self.timeout.setSuffix(" s")

        self.enable_shell = QCheckBox("Allow AI shell requests")
        self.enable_edits = QCheckBox("Allow AI code-change proposals")
        self.show_reasoning = QCheckBox("Show reasoning summary / activity trace")

        form.addRow("Provider", self.provider)
        form.addRow("Model", self.model)
        form.addRow("Base URL", self.base_url)
        form.addRow("API key", self.api_key)
        form.addRow("", self.remember_key)
        form.addRow("Timeout", self.timeout)
        form.addRow("", self.enable_shell)
        form.addRow("", self.enable_edits)
        form.addRow("", self.show_reasoning)

        self.key_hint = QLabel()
        self.key_hint.setObjectName("AIProviderHint")
        self.key_hint.setWordWrap(True)
        form.addRow("", self.key_hint)

        self.test_status = QLabel("Connection not tested")
        self.test_status.setObjectName("AIProviderTestStatus")
        form.addRow("Connection", self.test_status)
        root.addWidget(body)

        footer = QFrame()
        footer.setObjectName("AIProviderFooter")
        row = QHBoxLayout(footer)
        row.setContentsMargins(18, 10, 18, 14)
        row.setSpacing(7)

        self.test_button = QPushButton("Test Connection")
        self.test_button.setObjectName("AIProviderTest")
        apply_icon(self.test_button, "connect", 13)
        self.test_button.clicked.connect(self.test_connection)
        row.addWidget(self.test_button)
        row.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setObjectName("AIProviderCancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)

        apply = QPushButton("Apply")
        apply.setObjectName("AIProviderApply")
        apply.clicked.connect(self.apply_settings)
        row.addWidget(apply)

        save = QPushButton("Save & Close")
        save.setObjectName("AIProviderSave")
        apply_icon(save, "save", 13)
        save.clicked.connect(self.save_and_close)
        save.setDefault(True)
        row.addWidget(save)
        root.addWidget(footer)

        self.provider.currentIndexChanged.connect(self._provider_changed)
        self._load(config)

    def _load(self, config: ProviderConfig) -> None:
        index = self.provider.findData(config.provider)
        self.provider.setCurrentIndex(max(0, index))
        self.model.setText(config.model)
        self.base_url.setText(config.base_url)
        self.timeout.setValue(int(config.timeout))
        self.enable_shell.setChecked(bool(config.enable_shell))
        self.enable_edits.setChecked(bool(config.enable_code_edits))
        self.show_reasoning.setChecked(bool(config.show_reasoning))
        self._update_hint()

    def _provider_changed(self, _index: int) -> None:
        key = str(self.provider.currentData() or "openai")
        defaults = ProviderConfig.defaults(key)
        self.model.setText(defaults.model)
        self.base_url.setText(defaults.base_url)
        saved_key = self.credential_store.load_key(key)
        self.api_key.setText(saved_key)
        self.remember_key.setChecked(bool(saved_key) or bool(PROVIDER_DEFAULTS.get(key, {}).get("env")))
        self.test_status.setText("Connection not tested")
        self.test_status.setProperty("state", "idle")
        self._repolish(self.test_status)
        self._update_hint()

    @staticmethod
    def _repolish(widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _update_hint(self) -> None:
        key = str(self.provider.currentData() or "openai")
        env = PROVIDER_DEFAULTS[key]["env"]
        saved = self.credential_store.has_key(key)
        if not env:
            self.key_hint.setText("Local provider: no API key is required by default.")
        elif saved:
            self.key_hint.setText(
                f"A saved key exists in {self.credential_store.path}. Uncheck the JSON option and Apply to remove it."
            )
        elif environment_key(key):
            self.key_hint.setText(
                f"{env} is available. You can still save a different key to local JSON for this provider."
            )
        else:
            self.key_hint.setText(
                f"Set {env} in the environment or enter a key. JSON storage is local plaintext outside the project folder."
            )

    def config(self) -> ProviderConfig:
        key = str(self.provider.currentData() or "openai")
        defaults = ProviderConfig.defaults(key)
        return ProviderConfig(
            provider=key,
            model=self.model.text().strip() or defaults.model,
            base_url=self.base_url.text().strip() or defaults.base_url,
            timeout=int(self.timeout.value()),
            enable_shell=self.enable_shell.isChecked(),
            enable_code_edits=self.enable_edits.isChecked(),
            show_reasoning=self.show_reasoning.isChecked(),
        )

    def apply_settings(self) -> None:
        self.applied.emit(
            self.config(),
            self.api_key.text().strip(),
            self.remember_key.isChecked(),
        )
        self.test_status.setText("Settings applied")
        self.test_status.setProperty("state", "ok")
        self._repolish(self.test_status)

    def save_and_close(self) -> None:
        self.apply_settings()
        self.accept()

    def test_connection(self) -> None:
        if self._test_worker and self._test_worker.isRunning():
            return
        self.test_button.setEnabled(False)
        self.test_status.setText("Testing...")
        self.test_status.setProperty("state", "busy")
        self._repolish(self.test_status)
        self._test_worker = AIConnectionTestThread(
            self.config(),
            self.api_key.text().strip(),
            self,
        )
        self._test_worker.succeeded.connect(self._test_ok)
        self._test_worker.failed.connect(self._test_failed)
        self._test_worker.finished.connect(self._test_finished)
        self._test_worker.start()

    def _test_ok(self, message: str) -> None:
        self.test_status.setText("Connected" + (f" · {message}" if message else ""))
        self.test_status.setProperty("state", "ok")
        self._repolish(self.test_status)

    def _test_failed(self, message: str) -> None:
        self.test_status.setText("Failed · " + message[:240])
        self.test_status.setProperty("state", "error")
        self._repolish(self.test_status)

    def _test_finished(self) -> None:
        self.test_button.setEnabled(True)
        worker = self._test_worker
        self._test_worker = None
        if worker:
            worker.deleteLater()
