from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class Diagnostic:
    line: int
    column: int
    length: int
    severity: Severity
    message: str


class LuaSyntaxAnalyzer:
    """Fast editor-side Lua diagnostics.

    This is intentionally a lightweight structural analyzer, not a replacement for the
    Lua 5.1 compiler. It catches the mistakes that are most useful while typing and does
    not add another runtime dependency to LuaS30 Studio.
    """

    OPEN_PAREN = {"(": ")", "[": "]", "{": "}"}
    CLOSE_PAREN = {v: k for k, v in OPEN_PAREN.items()}

    def analyze(self, source: str) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        clean_lines = self._strip_strings_and_comments(source, diagnostics)
        self._check_brackets(clean_lines, diagnostics)
        self._check_blocks(clean_lines, diagnostics)
        return self._dedupe(sorted(diagnostics, key=lambda d: (d.line, d.column, d.message)))

    def _strip_strings_and_comments(self, source: str, diagnostics: list[Diagnostic]) -> list[str]:
        lines = source.splitlines()
        out: list[str] = []
        long_comment = False
        long_comment_start = 0
        for line_no, line in enumerate(lines, 1):
            chars = list(line)
            i = 0
            quote: str | None = None
            quote_start = 0
            while i < len(chars):
                if long_comment:
                    end = line.find("]]", i)
                    if end < 0:
                        for j in range(i, len(chars)):
                            chars[j] = " "
                        i = len(chars)
                        continue
                    for j in range(i, min(len(chars), end + 2)):
                        chars[j] = " "
                    long_comment = False
                    i = end + 2
                    continue
                if quote:
                    if chars[i] == "\\":
                        chars[i] = " "
                        if i + 1 < len(chars):
                            chars[i + 1] = " "
                        i += 2
                        continue
                    if chars[i] == quote:
                        chars[i] = " "
                        quote = None
                        i += 1
                        continue
                    chars[i] = " "
                    i += 1
                    continue
                if line.startswith("--[[", i):
                    for j in range(i, min(len(chars), i + 4)):
                        chars[j] = " "
                    long_comment = True
                    long_comment_start = line_no
                    i += 4
                    continue
                if line.startswith("--", i):
                    for j in range(i, len(chars)):
                        chars[j] = " "
                    break
                if chars[i] in ('"', "'"):
                    quote = chars[i]
                    quote_start = i + 1
                    chars[i] = " "
                    i += 1
                    continue
                i += 1
            if quote:
                diagnostics.append(Diagnostic(
                    line_no, quote_start, 1, Severity.ERROR,
                    "Unterminated string literal",
                ))
            out.append("".join(chars))
        if long_comment:
            diagnostics.append(Diagnostic(
                max(1, long_comment_start), 1, 4, Severity.ERROR,
                "Unterminated multiline comment --[[ ... ]]",
            ))
        return out

    def _check_brackets(self, lines: list[str], diagnostics: list[Diagnostic]) -> None:
        stack: list[tuple[str, int, int]] = []
        for line_no, line in enumerate(lines, 1):
            for col, ch in enumerate(line, 1):
                if ch in self.OPEN_PAREN:
                    stack.append((ch, line_no, col))
                elif ch in self.CLOSE_PAREN:
                    if not stack or stack[-1][0] != self.CLOSE_PAREN[ch]:
                        diagnostics.append(Diagnostic(
                            line_no, col, 1, Severity.ERROR, f"Unexpected '{ch}'",
                        ))
                    else:
                        stack.pop()
        for ch, line_no, col in stack[-20:]:
            diagnostics.append(Diagnostic(
                line_no, col, 1, Severity.ERROR,
                f"Missing closing '{self.OPEN_PAREN[ch]}'",
            ))

    def _check_blocks(self, lines: list[str], diagnostics: list[Diagnostic]) -> None:
        stack: list[tuple[str, int, int]] = []
        for line_no, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue
            # Close first so an `end` never gets mistaken for a word in another rule.
            if re.match(r"^end\b", line):
                if not stack or stack[-1][0] == "repeat":
                    diagnostics.append(Diagnostic(line_no, 1, 3, Severity.ERROR, "Unexpected 'end'"))
                else:
                    stack.pop()
                continue
            if re.match(r"^until\b", line):
                if not stack or stack[-1][0] != "repeat":
                    diagnostics.append(Diagnostic(line_no, 1, 5, Severity.ERROR, "'until' without matching 'repeat'"))
                else:
                    stack.pop()
                continue
            if re.match(r"^(?:local\s+)?function\b", line) or re.search(r"=\s*function\b", line):
                if not re.search(r"\bend\s*$", line):
                    stack.append(("function", line_no, 1))
                continue
            if re.match(r"^if\b.*\bthen\s*$", line):
                stack.append(("if", line_no, 1))
                continue
            if re.match(r"^for\b.*\bdo\s*$", line):
                stack.append(("for", line_no, 1))
                continue
            if re.match(r"^while\b.*\bdo\s*$", line):
                stack.append(("while", line_no, 1))
                continue
            if re.match(r"^repeat\b", line):
                stack.append(("repeat", line_no, 1))
                continue
            if re.match(r"^do\s*$", line):
                stack.append(("do", line_no, 1))
                continue

            if re.match(r"^else\b", line) or re.match(r"^elseif\b", line):
                if not stack or stack[-1][0] != "if":
                    diagnostics.append(Diagnostic(
                        line_no, 1, max(4, len(line.split()[0])), Severity.ERROR,
                        f"'{line.split()[0]}' without matching 'if'",
                    ))

        for kind, line_no, col in stack[-20:]:
            closer = "until" if kind == "repeat" else "end"
            diagnostics.append(Diagnostic(
                line_no, col, max(1, len(kind)), Severity.ERROR,
                f"Block '{kind}' is not closed; expected '{closer}'",
            ))

    @staticmethod
    def _dedupe(items: list[Diagnostic]) -> list[Diagnostic]:
        seen: set[tuple[int, int, str]] = set()
        out: list[Diagnostic] = []
        for d in items:
            key = (d.line, d.column, d.message)
            if key not in seen:
                seen.add(key)
                out.append(d)
        return out
