@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem LuaS30 IDE 1.15.0 Smart Launcher
rem
rem Modes:
rem   run.bat              automatic; network is touched only if a
rem                        dependency is missing/out of range
rem   run.bat --offline    never access the network
rem   run.bat --online     allow required package downloads
rem   run.bat --deps-only  validate/update environment then exit
rem   run.bat --force-deps force pip upgrade for declared libraries
rem
rem Per-user directories:
rem   App data:  %%APPDATA%%\LuaS30IDE
rem   Projects:  Documents\LuaS30IDE\<project_name>
rem ============================================================

set "DEP_MODE=auto"
set "DEPS_ONLY=0"
set "FORCE_DEPS=0"
set "STUDIO_ARGS="

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--offline" (
    set "DEP_MODE=offline"
    shift
    goto :parse_args
)
if /I "%~1"=="/offline" (
    set "DEP_MODE=offline"
    shift
    goto :parse_args
)
if /I "%~1"=="--online" (
    set "DEP_MODE=online"
    shift
    goto :parse_args
)
if /I "%~1"=="/online" (
    set "DEP_MODE=online"
    shift
    goto :parse_args
)
if /I "%~1"=="--deps-only" (
    set "DEPS_ONLY=1"
    shift
    goto :parse_args
)
if /I "%~1"=="--force-deps" (
    set "FORCE_DEPS=1"
    shift
    goto :parse_args
)
set "STUDIO_ARGS=!STUDIO_ARGS! "%~1""
shift
goto :parse_args

:args_done
set "LUAS30_APPDATA=%APPDATA%\LuaS30IDE"
set "LUAS30_DOCUMENTS=%USERPROFILE%\Documents"
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('MyDocuments')" 2^>nul`) do (
    if not "%%D"=="" set "LUAS30_DOCUMENTS=%%D"
)
set "LUAS30_PROJECTS=%LUAS30_DOCUMENTS%\LuaS30IDE"

rem ============================================================
rem Doi ten thu muc du lieu cu LuaS30Engine -> LuaS30IDE (mot lan).
rem
rem Phai chay TRUOC vong mkdir ben duoi: neu khong, thu muc rong ten moi
rem duoc tao truoc va se chan viec doi ten.
rem
rem An toan: chi doi khi ten moi CHUA ton tai. Neu `move` that bai thi
rem quay ve dung ten cu -- tha o lai ten cu con hon tro vao thu muc rong
rem va lam mo coi cau hinh + du an.
rem ============================================================
if not exist "%LUAS30_APPDATA%" if exist "%APPDATA%\LuaS30Engine" (
    echo       Migrating "%APPDATA%\LuaS30Engine" -^> "LuaS30IDE" ...
    move "%APPDATA%\LuaS30Engine" "%LUAS30_APPDATA%" >nul 2>&1
)
if not exist "%LUAS30_APPDATA%" if exist "%APPDATA%\LuaS30Engine" set "LUAS30_APPDATA=%APPDATA%\LuaS30Engine"

if not exist "%LUAS30_PROJECTS%" if exist "%LUAS30_DOCUMENTS%\LuaS30Engine" (
    echo       Migrating "%LUAS30_DOCUMENTS%\LuaS30Engine" -^> "LuaS30IDE" ...
    move "%LUAS30_DOCUMENTS%\LuaS30Engine" "%LUAS30_PROJECTS%" >nul 2>&1
)
if not exist "%LUAS30_PROJECTS%" if exist "%LUAS30_DOCUMENTS%\LuaS30Engine" set "LUAS30_PROJECTS=%LUAS30_DOCUMENTS%\LuaS30Engine"

for %%D in (
    "%LUAS30_APPDATA%"
    "%LUAS30_APPDATA%\config"
    "%LUAS30_APPDATA%\logs"
    "%LUAS30_APPDATA%\cache"
    "%LUAS30_APPDATA%\temp"
    "%LUAS30_APPDATA%\backups"
    "%LUAS30_APPDATA%\venv"
    "%LUAS30_PROJECTS%"
) do if not exist "%%~D" mkdir "%%~D" >nul 2>&1

set "LOG=%LUAS30_APPDATA%\logs\launcher.log"
set "DEP_LOG=%LUAS30_APPDATA%\logs\dependency_changes.log"
set "DEP_STATE=%LUAS30_APPDATA%\config\dependency_state.json"
set "PIP_CACHE_DIR=%LUAS30_APPDATA%\cache\pip"

>>"%LOG%" echo.
>>"%LOG%" echo ============================================================
>>"%LOG%" echo LuaS30 IDE 1.15.0 Smart Launcher
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo Engine: %CD%
>>"%LOG%" echo AppData: %LUAS30_APPDATA%
>>"%LOG%" echo Projects: %LUAS30_PROJECTS%
>>"%LOG%" echo Dependency mode requested: %DEP_MODE%

cls
echo ============================================================
echo               LuaS30 IDE 1.6.1 VS Code-style Studio
echo ============================================================
echo AppData : %LUAS30_APPDATA%
echo Projects: %LUAS30_PROJECTS%
echo Mode    : %DEP_MODE%
echo ------------------------------------------------------------
echo [1/8] Detecting Python...

set "PY_BOOT="
where py >nul 2>&1
if not errorlevel 1 set "PY_BOOT=py -3"
if not defined PY_BOOT (
    where python >nul 2>&1
    if not errorlevel 1 set "PY_BOOT=python"
)
if not defined PY_BOOT goto :no_python

%PY_BOOT% -c "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,10) else 9)" > "%TEMP%\luas30_pyver.txt" 2>>"%LOG%"
if errorlevel 1 goto :python_old
set /p PY_VERSION=<"%TEMP%\luas30_pyver.txt"
echo       Python !PY_VERSION! ... OK
>>"%LOG%" echo Python !PY_VERSION! OK

echo [2/8] Preparing isolated environment in AppData...
set "VENV_DIR=%LUAS30_APPDATA%\venv"
if not exist "!VENV_DIR!\Scripts\python.exe" (
    echo       Creating !VENV_DIR! ...
    %PY_BOOT% -m venv "!VENV_DIR!" >>"%LOG%" 2>&1
    if errorlevel 1 goto :venv_fail
)
set "VENV_PY=!VENV_DIR!\Scripts\python.exe"
if not exist "!VENV_PY!" goto :venv_fail

rem ensurepip is local/offline; only run when pip is missing.
"!VENV_PY!" -m pip --version >nul 2>>"%LOG%"
if errorlevel 1 (
    echo       pip missing; bootstrapping from Python installation...
    "!VENV_PY!" -m ensurepip --upgrade >>"%LOG%" 2>&1
    if errorlevel 1 goto :pip_fail
)
echo       venv + pip ... OK

echo [3/8] Checking Python library versions...
set "DEP_FORCE_ARG="
if "!FORCE_DEPS!"=="1" set "DEP_FORCE_ARG=--force"
"!VENV_PY!" "tools\dependency_manager.py" ^
    --requirements "requirements-studio.txt" ^
    --python "!VENV_PY!" ^
    --mode "!DEP_MODE!" ^
    --changes-log "!DEP_LOG!" ^
    --launcher-log "!LOG!" ^
    --state-json "!DEP_STATE!" ^
    !DEP_FORCE_ARG!
set "DEP_EXIT=!ERRORLEVEL!"
if not "!DEP_EXIT!"=="0" goto :dependency_fail

"!VENV_PY!" -c "import PySide6; from PySide6.QtCore import qVersion; print('PySide6',PySide6.__version__,'Qt',qVersion())" > "%TEMP%\luas30_qtver.txt" 2>>"%LOG%"
if errorlevel 1 goto :pyside_fail
set /p QT_VERSION=<"%TEMP%\luas30_qtver.txt"
echo       !QT_VERSION! ... OK
>>"%LOG%" echo !QT_VERSION! OK
>>"%LOG%" echo Dependency state: !DEP_STATE!
>>"%LOG%" echo Dependency changes: !DEP_LOG!

if "!DEPS_ONLY!"=="1" (
    echo.
    echo Environment dependencies are ready.
    echo State : !DEP_STATE!
    echo Changes: !DEP_LOG!
    exit /b 0
)

echo [4/8] Validating LuaS30 runtime and IDE source...
"!VENV_PY!" "tools\validate_tree.py" >>"%LOG%" 2>&1
if errorlevel 1 goto :validate_fail
"!VENV_PY!" "tools\validate_native_sdk.py" >>"%LOG%" 2>&1
if errorlevel 1 goto :validate_fail
"!VENV_PY!" -m compileall -q "studio" "tools" >>"%LOG%" 2>&1
if errorlevel 1 goto :compile_fail
echo       LuaS30 Native SDK / Lua 5.1 / Studio source ... OK

echo [5/8] Checking bundled ARM GCC...
set "ARM_ROOT=%CD%\toolchain\arm-gcc"
set "ARM_GCC=!ARM_ROOT!\bin\arm-none-eabi-gcc.exe"
set "ARM_READELF=!ARM_ROOT!\bin\arm-none-eabi-readelf.exe"
if not exist "!ARM_GCC!" goto :toolchain_fail
if not exist "!ARM_READELF!" goto :toolchain_fail
"!ARM_GCC!" --version > "%TEMP%\luas30_gccver.txt" 2>>"%LOG%"
if errorlevel 1 goto :toolchain_fail
set /p GCC_VERSION=<"%TEMP%\luas30_gccver.txt"
echo       !GCC_VERSION! ... OK
>>"%LOG%" echo ARM GCC: !GCC_VERSION!

echo [6/8] Checking bundled VXP emulator...
if not exist "emulator\VXPEmu.exe" goto :emulator_fail
if not exist "emulator\Qt6Core.dll" goto :emulator_fail
if not exist "emulator\Qt6Gui.dll" goto :emulator_fail
if not exist "emulator\Qt6Widgets.dll" goto :emulator_fail
if not exist "emulator\unicorn.dll" goto :emulator_fail
if not exist "emulator\platforms\qwindows.dll" goto :emulator_fail
echo       VXPEmu + Qt + Unicorn ... OK
>>"%LOG%" echo Emulator dependencies OK

echo [7/8] Writing environment report...
"!VENV_PY!" "tools\env_check.py" --root "%CD%" --write "%LUAS30_APPDATA%\logs\environment.json" >>"%LOG%" 2>&1
if errorlevel 1 (
    echo       [WARN] Environment report contains warnings.
) else (
    echo       Environment ... READY
)

echo [8/8] Starting LuaS30 Studio...
echo ------------------------------------------------------------
echo Log         : %LOG%
echo Dependency  : %DEP_STATE%
echo Change log  : %DEP_LOG%
echo Projects    : %LUAS30_PROJECTS%
echo ------------------------------------------------------------
>>"%LOG%" echo Launching Studio
"!VENV_PY!" "studio\main.py" !STUDIO_ARGS! 2>>"%LOG%"
set "APP_EXIT=!ERRORLEVEL!"
if not "!APP_EXIT!"=="0" (
    echo.
    echo ============================================================
    echo [ERROR] LuaS30 Studio stopped unexpectedly.
    echo Exit code: !APP_EXIT!
    echo Log: %LOG%
    echo ============================================================
    pause
)
exit /b !APP_EXIT!

:no_python
echo [ERROR] Python 3.10+ was not found.
echo Install Python from python.org and enable "Add Python to PATH".
>>"%LOG%" echo ERROR: Python not found
pause
exit /b 10

:python_old
echo [ERROR] Python 3.10 or newer is required.
>>"%LOG%" echo ERROR: Python version too old
pause
exit /b 11

:venv_fail
echo [ERROR] Could not create the isolated venv in:
echo   %LUAS30_APPDATA%\venv
echo See: %LOG%
>>"%LOG%" echo ERROR: venv initialization failed
pause
exit /b 12

:pip_fail
echo [ERROR] pip is unavailable and ensurepip could not repair it.
>>"%LOG%" echo ERROR: pip unavailable
pause
exit /b 18

:dependency_fail
echo.
echo ============================================================
echo [ERROR] Python environment does not satisfy requirements.
echo Requested mode : %DEP_MODE%
echo Dependency state: %DEP_STATE%
echo Change log      : %DEP_LOG%
echo.
if /I "%DEP_MODE%"=="offline" (
    echo Offline mode never downloads packages.
    echo Connect once and run normally to install missing libraries.
) else (
    echo If the network is unavailable you can still run:
    echo   run.bat --offline
    echo provided all required packages are already installed.
)
echo ============================================================
>>"%LOG%" echo ERROR: dependency manager returned !DEP_EXIT!
pause
exit /b !DEP_EXIT!

:pyside_fail
echo [ERROR] PySide6 is unavailable after dependency validation.
echo See: %LOG%
>>"%LOG%" echo ERROR: PySide6 unavailable
pause
exit /b 13

:validate_fail
echo [ERROR] LuaS30 Native SDK/runtime validation failed.
echo See: %LOG%
>>"%LOG%" echo ERROR: validate_tree.py failed
pause
exit /b 14

:compile_fail
echo [ERROR] Python source validation failed.
echo See: %LOG%
>>"%LOG%" echo ERROR: compileall failed
pause
exit /b 15

:toolchain_fail
echo [ERROR] Bundled ARM GCC is missing or cannot start.
echo Expected:
echo   toolchain\arm-gcc\bin\arm-none-eabi-gcc.exe
echo   toolchain\arm-gcc\bin\arm-none-eabi-readelf.exe
>>"%LOG%" echo ERROR: ARM GCC toolchain validation failed
pause
exit /b 16

:emulator_fail
echo [ERROR] Bundled VXP emulator is incomplete.
echo Expected emulator\VXPEmu.exe with Qt6 and Unicorn DLLs.
>>"%LOG%" echo ERROR: emulator validation failed
pause
exit /b 17
