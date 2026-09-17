@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if "%~1"=="" (
  echo Usage: build_only.bat PROJECT_DIR [TOOLCHAIN_DIR]
  exit /b 2
)
set "PROJECT=%~f1"
set "TOOLCHAIN=%~f2"
if not defined TOOLCHAIN set "TOOLCHAIN=%CD%\toolchain\arm-gcc"
set "PY=%APPDATA%\LuaS30IDE\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%APPDATA%\LuaS30Engine\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "tools\build.py" --project "%PROJECT%" --toolchain "%TOOLCHAIN%" --no-run
exit /b %ERRORLEVEL%
