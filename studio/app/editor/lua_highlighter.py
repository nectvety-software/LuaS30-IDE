from __future__ import annotations

import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument


class LuaHighlighter(QSyntaxHighlighter):
    """Lua 5.1-oriented syntax highlighter with multiline comment support."""

    KEYWORDS = (
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
        "until", "while",
    )
    BUILTINS = (
        "assert", "collectgarbage", "dofile", "error", "getfenv", "getmetatable", "ipairs",
        "load", "loadfile", "loadstring", "module", "next", "pairs", "pcall", "print",
        "rawequal", "rawget", "rawset", "require", "select", "setfenv", "setmetatable",
        "tonumber", "tostring", "type", "unpack", "xpcall", "coroutine", "math", "string",
        "table", "engine", "mre",
    )

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        def fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(italic)
            return f

        keyword = fmt("#65a8ff", bold=True)
        builtin = fmt("#65d6c2")
        number = fmt("#e9b96e")
        string = fmt("#a6df78")
        comment = fmt("#718096", italic=True)
        function_name = fmt("#e7c769")
        field = fmt("#b4a7ff")

        kw_pattern = r"\b(?:" + "|".join(map(re.escape, self.KEYWORDS)) + r")\b"
        bi_pattern = r"\b(?:" + "|".join(map(re.escape, self.BUILTINS)) + r")\b"
        self.rules.extend([
            (QRegularExpression(kw_pattern), keyword),
            (QRegularExpression(bi_pattern), builtin),
            (QRegularExpression(r"(?<![\w.])(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"), number),
            (QRegularExpression(r'"(?:\\.|[^"\\])*"'), string),
            (QRegularExpression(r"'(?:\\.|[^'\\])*'"), string),
            (QRegularExpression(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_\.:]*)"), function_name),
            (QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*\s*(?=\()"), function_name),
            (QRegularExpression(r"(?<=\.)[A-Za-z_][A-Za-z0-9_]*"), field),
            (QRegularExpression(r"--(?!\[\[).*$"), comment),
        ])
        self.multiline_comment_format = comment
        self.comment_start = QRegularExpression(r"--\[\[")
        self.comment_end = QRegularExpression(r"\]\]")

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        for pattern, text_format in self.rules:
            match_it = pattern.globalMatch(text)
            while match_it.hasNext():
                match = match_it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                if length > 0:
                    self.setFormat(start, length, text_format)

        self.setCurrentBlockState(0)
        continuing_comment = self.previousBlockState() == 1
        if continuing_comment:
            start_index = 0
        else:
            start_match = self.comment_start.match(text)
            start_index = start_match.capturedStart()

        while start_index >= 0:
            search_from = start_index if continuing_comment else start_index + 4
            end_match = self.comment_end.match(text, search_from)
            end_index = end_match.capturedStart()
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + end_match.capturedLength()
            self.setFormat(start_index, comment_length, self.multiline_comment_format)
            if end_index == -1:
                break
            continuing_comment = False
            next_match = self.comment_start.match(text, start_index + comment_length)
            start_index = next_match.capturedStart()
