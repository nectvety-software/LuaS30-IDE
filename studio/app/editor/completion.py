from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QCompleter


LUA_KEYWORDS = [
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
    "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
    "until", "while",
]

LUA_BUILTINS = [
    "assert", "collectgarbage", "dofile", "error", "getfenv", "getmetatable", "ipairs",
    "load", "loadfile", "loadstring", "module", "next", "pairs", "pcall", "print",
    "rawequal", "rawget", "rawset", "require", "select", "setfenv", "setmetatable",
    "tonumber", "tostring", "type", "unpack", "xpcall",
    "coroutine.create", "coroutine.resume", "coroutine.running", "coroutine.status",
    "coroutine.wrap", "coroutine.yield",
    "math.abs", "math.ceil", "math.floor", "math.max", "math.min", "math.random",
    "math.sqrt", "string.byte", "string.char", "string.find", "string.format",
    "string.gsub", "string.len", "string.lower", "string.match", "string.sub",
    "string.upper", "table.concat", "table.insert", "table.remove", "table.sort",
]

ENGINE_API = [
    "color", "clear", "rect", "frame", "line", "text", "set_font", "text_width",
    "font_height", "image", "image_region", "flush", "file_exists", "file_write",
    "file_read", "file_delete", "audio_play", "audio_stop", "audio_set_volume",
    "audio_is_playing", "tick_ms", "log", "exit", "W", "H", "version",
    "has_audio", "has_files", "has_images", "load", "update", "draw", "keypressed",
    "keyreleased", "pause", "resume", "quit",
]

SNIPPETS = {
    "function": "function name()\n    \nend",
    "if": "if condition then\n    \nend",
    "for": "for i = 1, count do\n    \nend",
    "while": "while condition do\n    \nend",
    "engine.load": "function engine.load()\n    \nend",
    "engine.update": "function engine.update(dt)\n    \nend",
    "engine.draw": "function engine.draw()\n    \nend",
    "engine.keypressed": "function engine.keypressed(key)\n    \nend",
}


@dataclass(slots=True)
class CompletionContext:
    prefix: str
    engine_member: bool


class LuaCompletionController:
    """Small, dependency-free completion engine for Lua 5.1 + LuaS30 APIs."""

    LOCAL_SYMBOL_RE = re.compile(
        r"\b(?:local\s+)?(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\b"
    )

    def __init__(self, editor) -> None:
        self.editor = editor
        self.model = QStringListModel(editor)
        self.completer = QCompleter(self.model, editor)
        self.completer.setWidget(editor)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.activated[str].connect(self._insert_completion)
        self.document_symbols: set[str] = set()
        self.project_symbols: set[str] = set()
        self._last_context = CompletionContext("", False)

    def refresh_document_symbols(self, text: str) -> None:
        symbols: set[str] = set()
        for line in text.splitlines():
            code = line.split("--", 1)[0]
            for match in re.finditer(r"\blocal\s+([A-Za-z_][A-Za-z0-9_]*)", code):
                symbols.add(match.group(1))
            for match in re.finditer(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_\.:]*)", code):
                symbols.add(match.group(1))
            for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", code):
                symbols.add(match.group(1))
        self.document_symbols = symbols

    def set_project_symbols(self, names: list[str]) -> None:
        self.project_symbols = set(names)

    def context(self) -> CompletionContext:
        cursor = self.editor.textCursor()
        text = cursor.block().text()[:cursor.positionInBlock()]
        member = re.search(r"\b(?:engine|mre)\.([A-Za-z_][A-Za-z0-9_]*)?$", text)
        if member:
            return CompletionContext(member.group(1) or "", True)
        word = re.search(r"([A-Za-z_][A-Za-z0-9_\.]*)$", text)
        return CompletionContext(word.group(1) if word else "", False)

    def show(self, force: bool = False) -> None:
        ctx = self.context()
        self._last_context = ctx
        if not force and not ctx.engine_member and len(ctx.prefix) < 2:
            self.completer.popup().hide()
            return
        if ctx.engine_member:
            items = sorted(ENGINE_API)
        else:
            items = sorted(set(LUA_KEYWORDS + LUA_BUILTINS + list(self.document_symbols) + list(self.project_symbols) + [
                "engine", "mre", "engine.load", "engine.update", "engine.draw",
                "engine.keypressed", "engine.keyreleased",
            ]))
        self.model.setStringList(items)
        self.completer.setCompletionPrefix(ctx.prefix)
        popup = self.completer.popup()
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        rect = self.editor.cursorRect()
        rect.setWidth(max(260, popup.sizeHintForColumn(0) + 32))
        self.completer.complete(rect)

    def popup_visible(self) -> bool:
        return self.completer.popup().isVisible()

    def _insert_completion(self, completion: str) -> None:
        cursor = self.editor.textCursor()
        ctx = self.context()
        prefix = ctx.prefix
        if prefix:
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.KeepAnchor, len(prefix))
        cursor.insertText(completion)
        self.editor.setTextCursor(cursor)
