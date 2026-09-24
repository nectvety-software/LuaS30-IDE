#!/usr/bin/env python3
"""validate_keypad_emulation.py — bàn phím giả lập của shell Nokia 225.

Một phím bấm đi qua **ba bảng** trước khi app Lua nhận được. Lệch một bảng là
phím **im lặng đi sai** — không exception, không log, chỉ thấy "game không nghe
phím":

  1. `doc/ai/Keypad.md` §0 — 21 tên phím Lua (`up`…`#`). Runtime chỉ gửi tên
     chữ thường qua `engine.keypressed`/`engine.keyreleased`.
  2. `MRE_KEY_*` trong IDE ↔ enum `MreKey` của VXPEmu
     (`VXPEmu/src/emulator/InputManager.h`).
  3. `_MRE_TO_VK` ↔ `KeyboardMapping::loadDefaults`
     (`VXPEmu/src/ui/KeyboardMapping.cpp`): IDE gửi virtual-key Windows, Qt của
     VXPEmu dịch ngược về Qt key rồi tra bảng mặc định đó.

Ngoài ra còn kiểm **cơ chế giữ phím**: hợp đồng §2.1 bắt buộc có cặp
pressed/released, nên nút trên vỏ máy phải GIỮ được (press → WM_KEYDOWN,
release → WM_KEYUP), không chỉ `clicked` (down+up tức thời). Thiếu nửa này thì
bảng `held` phía Lua không bao giờ thấy "đang giữ" ⇒ điều hướng kiểu giữ để chạy
không hoạt động trong giả lập.

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/validate_keypad_emulation.py

Đối chiếu nguồn VXPEmu là TUỲ CHỌN: tìm theo `LUAS30_VXPEMU_SRC` rồi
`D:/MRE/VXPEmu`; không thấy thì in SKIP cho riêng phần đó, các phần còn lại vẫn
chạy. Chỉ dựng widget ngoài màn hình + gọi hàm gửi phím giả — KHÔNG mở VXPEmu,
KHÔNG gửi phím thật vào cửa sổ nào.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

errors: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool) -> None:
    if not ok:
        errors.append(label)


# --------------------------------------------------------- 1. Hợp đồng tài liệu
doc = (ROOT / "doc/ai/Keypad.md").read_text(encoding="utf-8")
block = re.search(r"Tập tên phím duy nhất được phép dùng.*?```text\n(.*?)```", doc, re.S)
check("doc/ai/Keypad.md §0 không còn khối 'Tập tên phím duy nhất'", block is not None)
DOC_NAMES: list[str] = []
if block:
    for line in block.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        DOC_NAMES.extend(line.split())
check(f"tài liệu phải có 21 tên phím, đang có {len(DOC_NAMES)}", len(DOC_NAMES) == 21)

# --------------------------------------------- 2. Nguồn chân lý của VXPEmu
def find_emulator_source() -> Path | None:
    candidates = [os.environ.get("LUAS30_VXPEMU_SRC"), "D:/MRE/VXPEmu", "C:/MRE/VXPEmu"]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if (path / "src/ui/KeyboardMapping.cpp").is_file():
            return path
    return None


EMU = find_emulator_source()
EMU_MRE_ENUM: dict[str, int] = {}
EMU_DEFAULTS: dict[int, str] = {}          # mre code -> Qt key name
if EMU is None:
    notes.append("SKIP đối chiếu nguồn VXPEmu: không thấy KeyboardMapping.cpp "
                 "(đặt LUAS30_VXPEMU_SRC nếu nó nằm chỗ khác)")
else:
    header = (EMU / "src/emulator/InputManager.h").read_text(encoding="utf-8", errors="replace")
    for name, value in re.findall(r"(MRE_KEY_[A-Z0-9_]+)\s*=\s*(0x[0-9A-Fa-f]+)", header):
        EMU_MRE_ENUM[name] = int(value, 16)
    check("enum MreKey của VXPEmu không đọc được", len(EMU_MRE_ENUM) >= 20)

    mapping = (EMU / "src/ui/KeyboardMapping.cpp").read_text(encoding="utf-8", errors="replace")
    table = re.search(r"defaults\[\]\s*=\s*\{(.*?)\n    \};", mapping, re.S)
    check("bảng KeyboardMapping::loadDefaults của VXPEmu không đọc được", table is not None)
    if table:
        for qt_key, mre in re.findall(r"\{\s*Qt::(\w+),\s*(0x[0-9A-Fa-f]+)", table.group(1)):
            EMU_DEFAULTS[int(mre, 16)] = qt_key

# ------------------------------------------------------------- 3. Shell của IDE
from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent, QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from app.core import native_window  # noqa: E402
from app.widgets import vxp_emu_window as shell  # noqa: E402

app = QApplication.instance() or QApplication([])

# VXPEmu map mã MRE -> Qt key; IDE phải gửi đúng virtual-key để Qt ra Qt key đó
# (VK_OEM_2 = phím "/?" -> Qt::Key_Slash; VK_SHIFT -> Qt::Key_Shift; '#' = Shift+3).
EXPECTED_VK = {
    0x30: 0x30, 0x31: 0x31, 0x32: 0x32, 0x33: 0x33, 0x34: 0x34,
    0x35: 0x35, 0x36: 0x36, 0x37: 0x37, 0x38: 0x38, 0x39: 0x39,
    0x2A: 0x6A, 0x23: 0x33,
    0x100: 0x26, 0x101: 0x28, 0x102: 0x25, 0x103: 0x27,
    0x104: 0x0D, 0x105: 0xBF, 0x106: 0x10, 0x107: 0x1B, 0x108: 0x08,
}
check(f"_MRE_TO_VK phải có đủ 21 phím, đang có {len(native_window._MRE_TO_VK)}",
      len(native_window._MRE_TO_VK) == 21)
for code, vk in EXPECTED_VK.items():
    check(f"_MRE_TO_VK[{code:#x}] = {native_window._MRE_TO_VK.get(code, -1):#x}, phải là {vk:#x}",
          native_window._MRE_TO_VK.get(code) == vk)

# `#` không gửi được qua cửa sổ (Qt chỉ ra Qt::Key_NumberSign khi Shift THẬT đang
# giữ, mà PostMessage không đổi được; còn VK_SHIFT thì VXPEmu hiểu thành phím mềm
# phải). Phải chặn TƯỜNG MINH: gửi mò sẽ ra '3' — sai phím mà im lặng.
NOT_INJECTABLE = getattr(native_window, "MRE_KEYS_NOT_INJECTABLE", None)
check("native_window thiếu MRE_KEYS_NOT_INJECTABLE", NOT_INJECTABLE is not None)
check("MRE_KEYS_NOT_INJECTABLE phải đúng bằng {0x23}",
      set(NOT_INJECTABLE or ()) == {0x23})
for code in (0x23,):
    check(f"send_key_down({code:#x}) phải từ chối, không được gửi mò",
          native_window.send_key_down(0xDEAD, code) is False)
check("send_key_up(0x23) phải từ chối", native_window.send_key_up(0xDEAD, 0x23) is False)
check("is_injectable(0x23) phải là False", native_window.is_injectable(0x23) is False)
check("is_injectable(0x2A) phải là True", native_window.is_injectable(0x2A) is True)
check("is_injectable(0x100) phải là True",
      native_window.is_injectable(native_window.MRE_KEY_UP) is True)

# ---------------------------------------------- 4. Bảng tên phím + bố cục nút
pad = shell.PhoneKeypad()
NAMES: dict[int, str] = dict(getattr(pad, "MRE_KEY_NAMES", None) or {})
QT_TO_MRE: dict[int, int] = dict(getattr(shell, "_QT_TO_MRE", None) or {})
check("shell thiếu bảng bàn phím thật _QT_TO_MRE", len(QT_TO_MRE) == 21)
if not NAMES:
    errors.append("PhoneKeypad chưa phơi MRE_KEY_NAMES (bảng tên phím Lua)")
check(f"shell phải phơi đủ 21 phím, đang có {len(NAMES)}", len(NAMES) == 21)
check("tên phím của shell khác tài liệu §0",
      set(NAMES.values()) == set(DOC_NAMES))
check("shell phải dựng đủ 21 nút", len(pad.buttons) == 21)
BUTTON_CODES = [getattr(b, "_code", None) for b in pad.buttons]
check("mã MRE của các nút phải khớp MRE_KEY_NAMES",
      None not in BUTTON_CODES and sorted(BUTTON_CODES) == sorted(NAMES))

for name, value in (
    ("MRE_KEY_UP", 0x100), ("MRE_KEY_DOWN", 0x101), ("MRE_KEY_LEFT", 0x102),
    ("MRE_KEY_RIGHT", 0x103), ("MRE_KEY_OK", 0x104), ("MRE_KEY_LEFT_SOFT", 0x105),
    ("MRE_KEY_RIGHT_SOFT", 0x106), ("MRE_KEY_BACK", 0x107), ("MRE_KEY_CLEAR", 0x108),
):
    check(f"{name} phải là {value:#x}", getattr(native_window, name, None) == value)
    if EMU_MRE_ENUM:
        check(f"{name} lệch enum MreKey của VXPEmu ({EMU_MRE_ENUM.get(name)})",
              EMU_MRE_ENUM.get(name) == value)

if EMU_DEFAULTS:
    check("tập mã MRE của VXPEmu lệch shell",
          set(EMU_DEFAULTS) == set(EXPECTED_VK))
    for code, qt_name in sorted(EMU_DEFAULTS.items()):
        # `qt_name` đã ở dạng "Key_Up" (lấy từ `Qt::Key_Up` trong nguồn VXPEmu).
        qt_key = getattr(Qt.Key, qt_name, None)
        check(f"VXPEmu map {qt_name} -> {code:#x} nhưng shell không gửi ra Qt key đó",
              qt_key is not None and QT_TO_MRE.get(int(qt_key)) == code)
    notes.append(f"đã đối chiếu nguồn VXPEmu: {EMU}")

# Tooltip phải nói tên Lua: lập trình viên nhìn nút là biết app nhận tên gì.
for button in pad.buttons:
    code = getattr(button, "_code", None)
    expected = NAMES.get(code)
    check(f"nút {code} không có tên phím Lua trong MRE_KEY_NAMES",
          bool(expected))
    check(f"tooltip nút {expected!r} không mở đầu bằng tên phím Lua",
          bool(expected) and button.toolTip().startswith(f"{expected} "))

# Nút `#` vẫn phải có trên vỏ máy (điện thoại thật có phím này), nhưng tooltip
# phải nói rõ nó chỉ chạy trên máy thật — nếu không người dùng bấm mà không hiểu
# vì sao không có gì xảy ra.
hash_button = next((b for b in pad.buttons if getattr(b, "_code", None) == 0x23), None)
check("vỏ máy thiếu nút `#`", hash_button is not None)
check("tooltip nút `#` phải nói rõ chỉ chạy trên máy thật",
      hash_button is not None and "máy thật" in hash_button.toolTip())

# ------------------------------------------------------- 5. Hành vi giữ phím
sent: list[tuple[str, int]] = []


def fake_down(_hwnd: int, code: int) -> bool:
    sent.append(("down", code))
    return True


def fake_up(_hwnd: int, code: int) -> bool:
    sent.append(("up", code))
    return True


def fake_tap(_hwnd: int, code: int) -> None:
    """Bản cũ gửi phím bằng `send_key` (down+up tức thời) — ghi lại để thấy rõ
    vì sao nút bấm không tạo được trạng thái ĐANG GIỮ."""
    sent.append(("tap", code))


native_window.send_key_down = fake_down
native_window.send_key_up = fake_up
native_window.send_key = fake_tap
shell.native_window.send_key_down = fake_down
shell.native_window.send_key_up = fake_up
shell.native_window.send_key = fake_tap

host = QWidget()
host.show()
window = shell.VxpEmuWindow()
window._hwnd = 0x1234          # giả lập đã nhúng cửa sổ VXPEmu
keypad = window.body.keypad


def key_for(code: int):
    probe = getattr(keypad, "key_for", None)
    if callable(probe):
        return probe(code)
    for candidate in keypad.buttons:
        if getattr(candidate, "_code", None) == code:
            return candidate
    return None


def held_codes() -> list[int]:
    probe = getattr(keypad, "held_codes", None)
    return list(probe()) if callable(probe) else []


def window_held() -> set[int]:
    return set(getattr(window, "_held_keys", set()))


def release_all() -> None:
    probe = getattr(window, "release_all_keys", None)
    if callable(probe):
        probe()


def mouse(button, kind: QEvent.Type, x: float, y: float) -> None:
    if button is None:          # bản cũ không có `key_for` -> tránh sendEvent(None)
        errors.append("không tìm thấy nút bàn phím cho mã MRE cần kiểm")
        return
    point = QPointF(x, y)
    event = QMouseEvent(kind, point, point, Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(button, event)


def key(widget, kind: QEvent.Type, qt_key, auto_repeat: bool = False) -> None:
    event = QKeyEvent(kind, qt_key, Qt.KeyboardModifier.NoModifier, "", auto_repeat)
    QApplication.sendEvent(widget, event)


# 5a. Mọi phím: một lần bấm = đúng một down rồi một up.
for button in keypad.buttons:
    code = getattr(button, "_code", None)
    if code is None:
        errors.append("nút bàn phím không mang mã MRE (_code)")
        continue
    label = NAMES.get(code, hex(code))
    sent.clear()
    mouse(button, QEvent.Type.MouseButtonPress, 5, 5)
    check(f"bấm phím {label!r} không gửi WM_KEYDOWN", sent == [("down", code)])
    mouse(button, QEvent.Type.MouseButtonRelease, 5, 5)
    check(f"nhả phím {label!r} không gửi WM_KEYUP",
          sent == [("down", code), ("up", code)])

# 5b. GIỮ: down chỉ gửi một lần, trạng thái giữ được ghi nhận.
up_button = key_for(native_window.MRE_KEY_UP)
sent.clear()
mouse(up_button, QEvent.Type.MouseButtonPress, 5, 5)
check("giữ phím up không vào trạng thái đang giữ", held_codes() == [0x100])
check("giữ phím up không ghi nhận ở cửa sổ", window_held() == {0x100})
mouse(up_button, QEvent.Type.MouseButtonPress, 5, 5)
check("bấm lặp khi đang giữ lại gửi thêm WM_KEYDOWN", sent == [("down", 0x100)])
mouse(up_button, QEvent.Type.MouseButtonRelease, 5, 5)
check("nhả phím up không gửi WM_KEYUP", sent == [("down", 0x100), ("up", 0x100)])
check("nhả rồi mà vẫn còn giữ", held_codes() == [])

# 5c. Nhả ra ngoài nút (Qt tự giữ chuột) vẫn phải nhả phím.
sent.clear()
mouse(up_button, QEvent.Type.MouseButtonPress, 5, 5)
mouse(up_button, QEvent.Type.MouseButtonRelease, 400, 400)
check("nhả chuột ngoài nút làm kẹt phím", sent == [("down", 0x100), ("up", 0x100)])

# 5d. Giả lập dừng khi đang giữ: không được để phím kẹt trong app.
sent.clear()
mouse(key_for(native_window.MRE_KEY_LEFT), QEvent.Type.MouseButtonPress, 5, 5)
window.process_stopped(0)
check("dừng giả lập mà không nhả phím đang giữ", sent == [("down", 0x102), ("up", 0x102)])
check("dừng giả lập mà còn giữ phím", window_held() == set())
check("dừng giả lập mà nút vẫn ở trạng thái giữ", held_codes() == [])

# 5e. Chưa nhúng cửa sổ thì không gửi gì và không kẹt trạng thái.
window._hwnd = None
sent.clear()
mouse(up_button, QEvent.Type.MouseButtonPress, 5, 5)
mouse(up_button, QEvent.Type.MouseButtonRelease, 5, 5)
check("chưa có cửa sổ VXPEmu mà vẫn gửi phím", sent == [])
check("chưa có cửa sổ VXPEmu mà kẹt trạng thái giữ", window_held() == set())
window._hwnd = 0x1234

# 5f. Bàn phím thật của máy: cùng bảng mặc định của VXPEmu.
for qt_key, expected in (
    (Qt.Key.Key_Up, 0x100), (Qt.Key.Key_Down, 0x101), (Qt.Key.Key_Left, 0x102),
    (Qt.Key.Key_Right, 0x103), (Qt.Key.Key_Return, 0x104), (Qt.Key.Key_Slash, 0x105),
    (Qt.Key.Key_Shift, 0x106), (Qt.Key.Key_Escape, 0x107), (Qt.Key.Key_Backspace, 0x108),
    (Qt.Key.Key_5, 0x35), (Qt.Key.Key_0, 0x30), (Qt.Key.Key_Asterisk, 0x2A),
    (Qt.Key.Key_NumberSign, 0x23),
):
    sent.clear()
    key(window, QEvent.Type.KeyPress, qt_key)
    check(f"bàn phím thật: {qt_key} không gửi down {expected:#x}", sent == [("down", expected)])
    key(window, QEvent.Type.KeyRelease, qt_key)
    check(f"bàn phím thật: {qt_key} không gửi up {expected:#x}",
          sent == [("down", expected), ("up", expected)])

sent.clear()
key(window, QEvent.Type.KeyPress, Qt.Key.Key_Up, auto_repeat=True)
check("tự lặp của bàn phím thật lại gửi thêm down", sent == [])

# 5g. Mất focus khi đang giữ phím -> nhả hết (Alt+Tab).
sent.clear()
key(window, QEvent.Type.KeyPress, Qt.Key.Key_Left)
release_all()
check("mất focus mà không nhả phím đang giữ",
      sent == [("down", 0x102), ("up", 0x102)])
check("mất focus mà còn giữ phím", window_held() == set())

if notes:
    for note in notes:
        print("  " + note)

if errors:
    print("FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: shell phơi đủ 21 phím của doc/ai/Keypad.md §0, tooltip nêu tên Lua")
print("PASS: mã MRE + virtual-key khớp bảng mặc định của VXPEmu")
print("PASS: nút GIỮ được (press → down, release → up), nhả ngoài nút/mất focus/dừng giả lập đều nhả")
print("PASS: bàn phím thật của máy đi cùng bảng phím với VXPEmu")
