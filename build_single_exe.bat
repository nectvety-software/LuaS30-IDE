@echo off
rem LuaS30 IDE - dong goi DUY NHAT 1 file Setup EXE (Inno Setup).
rem Ket qua: dist\LuaS30IDE-Setup-<version>.exe (+ .sha256)
rem   Cai dat:  LuaS30IDE-Setup-1.0.1.exe
rem   Im lang:  LuaS30IDE-Setup-1.0.1.exe /SILENT
rem
rem Quy trinh: frozen exe (PyInstaller) -> stage -> verify -> Setup.
rem Them --skip-frozen de bo qua buoc frozen (build nhanh, dung run.bat).
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=D:\Program\Python\python.exe"
if not exist "%PY%" set "PY=python"
set "SKIP_FROZEN=0"
for %%A in (%*) do if /I "%%A"=="--skip-frozen" set "SKIP_FROZEN=1"
if "%SKIP_FROZEN%"=="0" (
    echo [1/2] Build frozen LuaS30IDE.exe ...
    "%PY%" "tools\build_frozen.py" --out dist\frozen
    if errorlevel 1 exit /b %ERRORLEVEL%
) else (
    echo [1/2] Bo qua frozen exe (--skip-frozen).
)
echo [2/2] Build Setup EXE ...
"%PY%" "tools\package_single_exe.py" --out dist %*
exit /b %ERRORLEVEL%
