# LuaS30 IDE packaging

## Single-file Setup EXE (khuyen dung)

Dong goi **duy nhat 1 file** `dist/LuaS30IDE-Setup-<version>.exe` — co trinh cai
dat wizard, bieu tuong ung dung va thu vien moi truong offline:

```bat
rem Day du (frozen exe + IDE + toolchain + emulator + wheels offline)
build_single_exe.bat

rem Bo qua frozen exe (build nhanh; chay bang run.bat/VBS)
build_single_exe.bat --skip-frozen

rem Gon nhe (core IDE + wheels; copy toolchain/emulator sau)
build_single_exe.bat --skip-frozen --skip-optional
```

Dieu kien build: `pip install pyinstaller pefile` + Internet lan dau
(wheels, Inno Setup, Python embedded duoc cache).
Quy trinh: `tools/build_frozen.py` dong `LuaS30IDE.exe` (PyInstaller
onedir, windowed, icon app) → `tools/verify_release.py` kiem tra stage
(du file, PE GUI, khong lot private key, probe `--version` + tools) →
Inno Setup ra 1 file `dist/LuaS30IDE-Setup-<version>.exe` kem `.sha256`.

Shortcut Desktop + Start Menu tro thang vao `LuaS30IDE.exe` (khong can
Python/venv/pip tren may dich; pipeline build VXP dung `python\`
kem theo). `run.bat`/`LuaS30-IDE.vbs` van giu de bao tri + chay source.

Yeu cau **luc build**: co Internet (tai wheels PySide6 + Inno Setup lan dau;
wheels duoc cache trong `vendor/wheels/`, Inno trong `dist/inno-cache/`).

May dich **cai dat**: KHONG can Internet va KHONG can cai Python truoc —
Setup da dong goi san Python 3.12 embedded (`python\`) + wheels PySide6
offline (`vendor\wheels\`). Lan chay dau `run.bat` tu bootstrap pip va cai
PySide6 offline (console hien de thay tien trinh); cac lan sau chay an.

Chay tren moi may Windows (x64, Win 10 1809+): `run.bat` tu kiem tra
64-bit / ban Windows / dia trong, tu cai Visual C++ runtime khi thieu
(co mang), bao loi ro rang bang popup neu khong du dieu kien.
RAM khuyen nghi 8 GB+. GPU cu loi hien thi: `set LUAS30_SOFTWARE_GL=1`.

`LuaS30IDE-Setup-<version>.exe` (1 file duy nhat) chua ben trong:
`studio/`, `tools/`, `engine/`, `sdk/`, `vendor/` (Lua 5.1.5 + wheels),
`templates/`, `profiles/`, `compat/`, `doc/`, `wiki/`, `app-icon/`,
`toolchain/` (ARM GCC), `emulator/` (VXPEmu), `python/` (embedded),
kem cac script `.bat`/`.vbs` khoi dong.

Cai dat:

```text
LuaS30IDE-Setup-1.0.2.exe              (wizard, tieng Anh/Viet)
LuaS30IDE-Setup-1.0.2.exe /SILENT      (nen, khong hien UI)
LuaS30IDE-Setup-1.0.2.exe /VERYSILENT  (nen, an ca progress)
```

Thu muc cai dat (per-user, khong can admin):

```text
%LOCALAPPDATA%\Programs\LuaS30 IDE\
```

Shortcut Desktop + Start Menu dung `app-icon\icon.ico`, go cai dat tai
Settings → Apps → LuaS30 IDE → Uninstall (`unins000.exe`).

## Canh bao SmartScreen "Windows protected your PC"

Nguyen nhan: file Setup **chua duoc ky so** (unknown publisher) + duoc tai tu
Internet (co Mark-of-the-Web). Day la co che bao ve cua Windows — khong co
meo code nao tat duoc canh bao nay tren may la neu file khong ky.

Cach xu ly dung, xep theo do uu tien:

1. **Ky so that (khuyen dung de phan phoi rong).** Mua chung thu so
   Code Signing OV/EV do CA tin cay cap (Sectigo, DigiCert...; EV co
   SmartScreen reputation ngay, OV can thoi gian tich luy). Build kem ky so:
   ```bat
   set LUAS30_SIGN_PASSWORD=mat-khau-pfx
   build_single_exe.bat --sign-pfx C:\certs\ten-mien.pfx
   ```
   Script tu tim `signtool.exe` (Windows SDK), ky ca Setup EXE lan
   uninstaller (`SignedUninstaller`) kem timestamp RFC3161.
   Ky le file co san: `py tools\sign_exe.py --pfx ... --file ...`
   **BAO MAT:** khong bao gio commit file `.pfx`/mat khau vao git.
   Cert **tu ky (self-signed) khong co tac dung** tren may la tru khi cai
   cert vao Trusted Publishers cua tung may — chi dung noi bo.

2. **Huong dan nguoi dung vuot canh bao (khi chua co cert).**
   Tai man hinh xanh: `More info` → `Run anyway`. Hoac go Mark-of-the-Web
   truoc khi chay: chuot phai file → Properties → tick `Unblock`,
   hoac PowerShell: `Unblock-File .\LuaS30IDE-Setup-1.0.2.exe`.
   Chep file qua USB/o LAN noi bo (khong qua trinh duyet) cung khong bi gan
   Mark-of-the-Web.

3. **Gui mau cho Microsoft** (khi file da ky ma van bi chan oan):
   <https://www.microsoft.com/en-us/wdsi/filesubmission> → chon
   "I believe this file should not have been flagged".

## Desktop / Start Menu icon

Already installed for the portable checkout:

```text
py tools\install_shortcuts.py
```

Uses `app-icon\icon.ico` and launches `LuaS30-IDE.vbs` (**hidden console** — no black terminal flash).
Debug with visible console: double-click `LuaS30-IDE.cmd` instead.

## MSI installer

WiX 3.11 binaries live under `packaging/wix/` (candle.exe, light.exe).

Build:

```bat
rem Full IDE (core + toolchain + emulator)
py tools\package_msi.py --out dist

rem Core IDE only (smaller download; copy toolchain/emulator later)
py tools\package_msi.py --out dist --skip-optional
```

Output:

```text
dist\LuaS30IDE-<version>.msi
```

### Install

Interactive:

```bat
msiexec /i "dist\LuaS30IDE-1.0.2.msi"
```

Silent / background (no UI), then auto-launch the IDE:

```bat
dist\install_silent.cmd
```

or:

```bat
msiexec /i "dist\LuaS30IDE-1.0.2.msi" /qn /norestart
```

Install root (per-user, like VXPEngine — no admin required):

```text
%LOCALAPPDATA%\Programs\LuaS30 IDE\
```

After a successful install the MSI launches `LuaS30-IDE.vbs` automatically (`AUTOLAUNCH=1`; pass `AUTOLAUNCH=0` to disable).

Shortcuts: Desktop + Start Menu → `LuaS30-IDE.vbs` (hidden) with `icon.ico`.

**Per-machine paths**

| Data | Location |
|------|----------|
| Config, venv, logs | `%APPDATA%\LuaS30IDE\` |
| Projects | `Documents\LuaS30 Projects\` |

First run builds a per-user venv under `%APPDATA%\LuaS30IDE\venv` (PySide6).

### Updates

`UpgradeCode` is stable:

```text
{A3F5C2D1-8B4E-4F7A-9C10-6E7541301D01}
```

Bump `VERSION` (e.g. `1.15.1`) and rebuild the MSI. Installing the new MSI upgrades the old product in place (MajorUpgrade). Keep the UpgradeCode unchanged forever.
