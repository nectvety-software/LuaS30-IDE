"""Cầu nối Win32 nhỏ dùng để nhúng và điều khiển cửa sổ VXPEmu thật.

Mô hình sao chép từ VXPEngine (app/native_window.py): VXPEmu.exe là ứng dụng
Qt độc lập, IDE tìm cửa sổ chính theo PID rồi SetParent vào màn hình Nokia 225,
phím bấm được gửi bằng WM_KEYDOWN/WM_KEYUP đã map sang virtual-key Windows.

**Bảng mã phím — nguồn chân lý nằm ở VXPEmu, không phải ở đây.** Chuỗi truyền
một phím bấm gồm ba chặng, mỗi chặng có một bảng riêng:

1. `MRE_KEY_*` (mã trong IDE) — trùng khít enum `MreKey`
   (`VXPEmu/src/emulator/InputManager.h`) và bảng `KeyboardMapping::mreKeyName`.
2. `_MRE_TO_VK` — virtual-key Windows gửi cho cửa sổ VXPEmu. Phải là VK mà Qt
   dịch ngược về đúng **Qt key** trong `KeyboardMapping::loadDefaults`
   (`VXPEmu/src/ui/KeyboardMapping.cpp`), vì VXPEmu tra bảng đó theo `event->key()`.
3. VXPEmu map Qt key → `MRE_KEY_*` → `VM_KEY_*` (`vmio.h`) rồi đẩy cho app.

Lệch một trong ba bảng thì phím **im lặng đi sai** (không lỗi, không log), nên
`tools/validate_keypad_emulation.py` đối chiếu bảng ở đây với nguồn VXPEmu.

⚠️ **`#` KHÔNG gửi được vào VXPEmu** — xem `MRE_KEYS_NOT_INJECTABLE`. Đây là
giới hạn thật của giao diện hiện tại, đã đo chứ không phải phỏng đoán.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.GetWindowLongW.argtypes = (wt.HWND, ctypes.c_int)
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = (wt.HWND, ctypes.c_int, ctypes.c_long)
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetParent.argtypes = (wt.HWND, wt.HWND)
user32.SetParent.restype = wt.HWND
user32.MoveWindow.argtypes = (wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.BOOL)
user32.PostMessageW.argtypes = (wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.GetClientRect.argtypes = (wt.HWND, ctypes.POINTER(wt.RECT))
user32.GetClientRect.restype = wt.BOOL

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_EX_TOOLWINDOW = 0x00000080
WM_KEYDOWN, WM_KEYUP, WM_CLOSE = 0x0100, 0x0101, 0x0010

# Mã MRE (enum MreKey của VXPEmu). 0x100..0x108 là nhóm điều hướng/chức năng,
# số dùng luôn mã ASCII của ký tự.
MRE_KEY_UP, MRE_KEY_DOWN, MRE_KEY_LEFT, MRE_KEY_RIGHT = 0x100, 0x101, 0x102, 0x103
MRE_KEY_OK, MRE_KEY_LEFT_SOFT, MRE_KEY_RIGHT_SOFT = 0x104, 0x105, 0x106
MRE_KEY_BACK, MRE_KEY_CLEAR = 0x107, 0x108

VK_SHIFT = 0x10
VK_BACKSPACE, VK_RETURN, VK_ESCAPE = 0x08, 0x0D, 0x1B
VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN = 0x25, 0x26, 0x27, 0x28
VK_DIGIT_3, VK_MULTIPLY = 0x33, 0x6A
VK_OEM_2 = 0xBF   # phím "/?" → Qt::Key_Slash → MRE_KEY_LEFT_SOFT

_MRE_TO_VK = {
    **{0x30 + n: 0x30 + n for n in range(10)},
    0x2A: VK_MULTIPLY, 0x23: VK_DIGIT_3,
    MRE_KEY_UP: VK_UP, MRE_KEY_DOWN: VK_DOWN, MRE_KEY_LEFT: VK_LEFT,
    MRE_KEY_RIGHT: VK_RIGHT, MRE_KEY_OK: VK_RETURN, MRE_KEY_LEFT_SOFT: VK_OEM_2,
    MRE_KEY_RIGHT_SOFT: VK_SHIFT, MRE_KEY_BACK: VK_ESCAPE, MRE_KEY_CLEAR: VK_BACKSPACE,
}

#: Phím **không gửi được** vào VXPEmu qua cửa sổ — hiện chỉ có `#`.
#:
#: `#` chỉ tới được app nếu Qt báo `Qt::Key_NumberSign`, mà Qt chỉ ra key đó khi
#: `GetKeyboardState()` thấy Shift đang giữ (bàn phím US: Shift+3). `PostMessageW`
#: không đổi được trạng thái bàn phím, và `VK_SHIFT` **không thể** gửi thay vì
#: `VK_3`: `Qt::Key_Shift` cũng nằm trong bảng `KeyboardMapping::loadDefaults`
#: nên VXPEmu hiểu thành một cú bấm `MRE_KEY_RIGHT_SOFT` (phím mềm phải) giả.
#:
#: Đã đo, không phải suy đoán — 5 cách đều hỏng:
#:   - Shift giả qua `PostMessageW`  → app nhận `3`, kèm 1 `softright` giả;
#:   - `AttachThreadInput` + `SetKeyboardState` → Qt không đọc, vẫn ra `3`;
#:   - `VK_PACKET`, `WM_CHAR`        → không có sự kiện nào tới app;
#:   - quét 35 virtual-key OEM/numpad → không VK nào cho ra `#`.
#: Cách duy nhất chạy được là `AttachThreadInput` + `SendInput` Shift thật rồi
#: gửi **đồng bộ** — nhưng chỉ ăn khoảng 6/7 lần, lần còn lại app nhận `3`
#: (sai phím mà không báo gì). Sai im lặng 15% tệ hơn không gửi gì, nên bỏ.
#:
#: Muốn `#` chạy được thì phải sửa **VXPEmu**: cho nó một đường bơm thẳng mã
#: MRE (`dispatchKeyPress`) qua message đăng ký riêng, khỏi đi vòng qua Qt.
MRE_KEYS_NOT_INJECTABLE = frozenset({0x23})


def _window_long(hwnd: int, index: int) -> int:
    return user32.GetWindowLongW(hwnd, index) & 0xFFFFFFFF


def _set_window_long(hwnd: int, index: int, value: int) -> None:
    signed = value - 0x100000000 if value >= 0x80000000 else value
    user32.SetWindowLongW(hwnd, index, signed)


def find_main_window(pid: int) -> int | None:
    result: list[int] = []

    @WNDENUMPROC
    def callback(hwnd, _lparam):
        process_id = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        if _window_long(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            result.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(callback, 0)
    return result[0] if result else None


def embed(hwnd: int, host: int, width: int, height: int) -> bool:
    try:
        style = _window_long(hwnd, GWL_STYLE)
        style = (style | WS_CHILD) & ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME |
                                        WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        _set_window_long(hwnd, GWL_STYLE, style)
        user32.SetParent(hwnd, host)
        width, height = client_size(host, width, height)
        user32.MoveWindow(hwnd, 0, 0, width, height, True)
        user32.ShowWindow(hwnd, 5)
        return True
    except OSError:
        return False


def client_size(host: int, fallback_width: int, fallback_height: int) -> tuple[int, int]:
    """Trả về kích thước pixel Win32 thật của host (tọa độ Qt có thể đã DPI-scale)."""
    rect = wt.RECT()
    if host and user32.GetClientRect(host, ctypes.byref(rect)):
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width > 0 and height > 0:
            return width, height
    return int(fallback_width), int(fallback_height)


def fit(hwnd: int, width: int, height: int, host: int = 0) -> None:
    if hwnd:
        width, height = client_size(host, width, height)
        user32.MoveWindow(hwnd, 0, 0, width, height, True)


def is_alive(hwnd: int) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


def _post_key(hwnd: int, vk: int, down: bool) -> None:
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = (scan << 16) | 1
    if not down:
        flags |= (1 << 30) | (1 << 31)
    user32.PostMessageW(hwnd, WM_KEYDOWN if down else WM_KEYUP, vk, flags & 0xFFFFFFFF)


def is_injectable(mre_code: int) -> bool:
    """Phím này có gửi được vào VXPEmu không (xem `MRE_KEYS_NOT_INJECTABLE`)."""
    return mre_code in _MRE_TO_VK and mre_code not in MRE_KEYS_NOT_INJECTABLE


def send_key_down(hwnd: int, mre_code: int) -> bool:
    """Giữ một phím MRE xuống (WM_KEYDOWN); trả về True nếu đã gửi."""
    vk = _MRE_TO_VK.get(mre_code)
    if not hwnd or vk is None or mre_code in MRE_KEYS_NOT_INJECTABLE:
        return False
    _post_key(hwnd, vk, True)
    return True


def send_key_up(hwnd: int, mre_code: int) -> bool:
    """Nhả một phím MRE (WM_KEYUP); phải ghép cặp với `send_key_down`."""
    vk = _MRE_TO_VK.get(mre_code)
    if not hwnd or vk is None or mre_code in MRE_KEYS_NOT_INJECTABLE:
        return False
    _post_key(hwnd, vk, False)
    return True


def send_key(hwnd: int, mre_code: int) -> None:
    """Bấm nhả tức thời (giữ cho tương thích); `down`+`up` rời nhau thì dùng
    `send_key_down`/`send_key_up` để app thấy được trạng thái ĐANG GIỮ."""
    if send_key_down(hwnd, mre_code):
        send_key_up(hwnd, mre_code)


def close(hwnd: int) -> None:
    if hwnd:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
