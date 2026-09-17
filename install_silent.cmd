@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"

set "MSI="
for %%F in ("%~dp0LuaS30IDE-*.msi") do set "MSI=%%~fF"
if not defined MSI (
  echo [ERROR] No LuaS30IDE-*.msi next to this script.
  exit /b 1
)

echo [1/2] Installing LuaS30 IDE in the background (no UI)...
msiexec /i "%MSI%" /qn /norestart /l*v "%TEMP%\LuaS30IDE-install.log"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [ERROR] msiexec failed with code %RC%.
  echo         Log: %TEMP%\LuaS30IDE-install.log
  exit /b %RC%
)

set "VBS=%LOCALAPPDATA%\Programs\LuaS30 IDE\LuaS30-IDE.vbs"
echo [2/2] Launching LuaS30 IDE...
if exist "%VBS%" (
  wscript.exe "%VBS%"
) else (
  echo [WARN] Launcher not found at "%VBS%"; open the Start Menu shortcut instead.
)

echo [OK] Install finished.
exit /b 0
