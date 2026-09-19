@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem LuaS30 IDE Smart Launcher (kieu VXPEngine: subroutine)
rem
rem So phien ban duoc DOC TRUC TIEP tu file VERSION o goc repo luc
rem chay (khong hard-code o day nua), dung cho banner + log.
rem
rem Commands:
rem   run.bat              chay Studio (mac dinh)
rem   run.bat deps         cai dat lai thu vien Python
rem   run.bat check        kiem tra moi truong
rem   run.bat menu         mo menu tac vu
rem   run.bat help         huong dan
rem
rem Flags (dung kem lenh tren):
rem   --offline            khong bao gio truy cap mang
rem   --online             cho phep tai package khi can
rem   --deps-only          chi chuan bi moi truong roi thoat
rem   --force-deps         cai lai thu vien du da du
rem
rem Per-user directories:
rem   App data:  %%APPDATA%%\LuaS30IDE
rem   Projects:  Documents\LuaS30 Projects\<project_name>
rem ============================================================

set "ROOT_DIR=%~dp0"
set "COMMAND="
set "FROM_MENU=0"
set "RC=0"
set "DEP_MODE=auto"
set "DEPS_ONLY=0"
set "FORCE_DEPS=0"
set "STUDIO_ARGS="
set "USE_BUNDLED=0"
set "BUNDLED_PY=%ROOT_DIR%python\python.exe"
set "BASE_PY="
set "BASE_PY_ARGS="
set "VENV_PY="

chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
rem Isolate child Python from host PYTHON* hijacks / leftover project paths.
set "PYTHONPATH="
set "PYTHONHOME="
set "PYTHONSTARTUP="

rem Doc phien ban hien hanh tu file VERSION (dong dau tien). Mac dinh an toan
rem neu thieu file de banner/log khong trong trang.
set "APP_VERSION=0.0.0"
if exist "%ROOT_DIR%VERSION" set /p APP_VERSION=<"%ROOT_DIR%VERSION"

if /I "%~1"=="deps"  ( set "COMMAND=deps"  & shift & goto :parse_args )
if /I "%~1"=="check" ( set "COMMAND=check" & shift & goto :parse_args )
if /I "%~1"=="menu"  ( set "COMMAND=menu"  & shift & goto :parse_args )
if /I "%~1"=="help"  ( set "COMMAND=help"  & shift & goto :parse_args )
if /I "%~1"=="--help" ( set "COMMAND=help" & shift & goto :parse_args )
if /I "%~1"=="-h"     ( set "COMMAND=help" & shift & goto :parse_args )

:parse_args
if "%~1"=="" goto :dispatch
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

:dispatch
if "%COMMAND%"=="deps"  goto :run_deps
if "%COMMAND%"=="check" goto :run_check
if "%COMMAND%"=="menu"  goto :menu
if "%COMMAND%"=="help"  goto :help
goto :run_studio

rem ==================== Commands ====================

:run_studio
call :setup_dirs
if errorlevel 1 goto :failed
call :preflight
if errorlevel 1 goto :failed
call :ensure_runtime
if errorlevel 1 goto :failed
if "!DEPS_ONLY!"=="1" (
    echo(
    echo [LuaS30] Moi truong da san sang.
    echo State : !DEP_STATE!
    echo Changes: !DEP_LOG!
    set "RC=0"
    goto :task_done
)
call :validate_sources
if errorlevel 1 goto :failed
call :check_toolchain
call :check_emulator
call :write_env_report
rem GPU cu / driver loi: set LUAS30_SOFTWARE_GL=1 de ve do hoa mem.
if /I "%LUAS30_SOFTWARE_GL%"=="1" (
    set "QT_OPENGL=software"
    set "QT_QUICK_BACKEND=software"
    echo [LuaS30] Software OpenGL ... ON
    >>"!LOG!" echo Software OpenGL enabled via LUAS30_SOFTWARE_GL
)
echo [8/8] Starting LuaS30 Studio...
echo ------------------------------------------------------------
echo Log         : !LOG!
echo Dependency  : !DEP_STATE!
echo Change log  : !DEP_LOG!
echo Projects    : !LUAS30_PROJECTS!
echo ------------------------------------------------------------
>>"!LOG!" echo Launching Studio
set "STUDIO_ENTRY=%ROOT_DIR%studio\main.py"
if not exist "!STUDIO_ENTRY!" set "STUDIO_ENTRY=%ROOT_DIR%studio\main.pyc"
"!VENV_PY!" "!STUDIO_ENTRY!" !STUDIO_ARGS! 2>>"!LOG!"
set "APP_EXIT=!ERRORLEVEL!"
if not "!APP_EXIT!"=="0" (
    echo(
    echo ============================================================
    echo [ERROR] LuaS30 Studio stopped unexpectedly.
    echo Exit code: !APP_EXIT!
    echo Log: !LOG!
    echo ============================================================
    call :popup "LuaS30 Studio stopped unexpectedly. See log."
    pause
    set "RC=!APP_EXIT!"
    goto :task_done
)
set "RC=0"
goto :task_done

:run_deps
call :setup_dirs
if errorlevel 1 goto :failed
call :preflight
if errorlevel 1 goto :failed
call :ensure_venv
if errorlevel 1 goto :failed
call :install_deps
if errorlevel 1 goto :failed
echo(
echo [LuaS30] Da cai dat xong thu vien Python.
set "RC=0"
goto :task_done

:run_check
call :setup_dirs
if errorlevel 1 goto :failed
call :preflight
if errorlevel 1 goto :failed
call :ensure_runtime
if errorlevel 1 goto :failed
echo [LuaS30] Dang kiem tra moi truong...
set "TOOL_SCRIPT=tools\env_check.py"
if not exist "!TOOL_SCRIPT!" set "TOOL_SCRIPT=tools\env_check.pyc"
if exist "!TOOL_SCRIPT!" (
    "!VENV_PY!" "!TOOL_SCRIPT!" --root "%CD%" --write "!LUAS30_APPDATA!\logs\environment.json" >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo [LuaS30] [WARN] Moi truong co canh bao. Xem: !LUAS30_APPDATA!\logs\environment.json
    ) else (
        echo [LuaS30] Moi truong ... READY
    )
) else (
    echo [LuaS30] [WARN] Khong tim thay tools\env_check.py
)
echo Log         : !LOG!
echo Dependency  : !DEP_STATE!
set "RC=0"
goto :task_done

:menu
set "FROM_MENU=1"
cls
echo(
echo ============================================================
echo   LuaS30 IDE - Launcher
echo ============================================================
echo(
echo   [1] Chay LuaS30 Studio
echo   [2] Cai dat lai thu vien Python
echo   [3] Kiem tra moi truong
echo   [0] Thoat
echo(
set "CHOICE="
set /p "CHOICE=Chon [1]: "
if not defined CHOICE set "CHOICE=1"
if "%CHOICE%"=="1" goto :run_studio
if "%CHOICE%"=="2" goto :run_deps
if "%CHOICE%"=="3" goto :run_check
if "%CHOICE%"=="0" goto :success
echo Lua chon khong hop le: %CHOICE%
pause
goto :menu

:help
echo(
echo Cach dung:
echo   run.bat              Chay LuaS30 Studio
echo   run.bat deps         Cai dat lai thu vien Python
echo   run.bat check        Kiem tra moi truong
echo   run.bat menu         Mo menu tac vu
echo   run.bat help         Huong dan nay
echo(
echo Co the dung kem:
echo   --offline            Khong bao gio truy cap mang
echo   --online             Cho phep tai package khi can
echo   --deps-only          Chi chuan bi moi truong roi thoat
echo   --force-deps         Cai lai thu vien du da du
set "RC=0"
goto :finish

rem ==================== Subroutines ====================

:preflight
rem Kiem tra dieu kien chay tren moi may Windows: 64-bit, Win10+, du dia.
if /I "%PROCESSOR_ARCHITECTURE%"=="AMD64" goto :preflight_os
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    echo [WARN] Windows ARM64: chay qua gia lap x64, hieu nang co the giam.
    >>"!LOG!" echo WARN: ARM64 emulation
    goto :preflight_os
)
echo [ERROR] May nay dung Windows 32-bit. LuaS30 IDE chi ho tro Windows 64-bit.
>>"!LOG!" echo ERROR: 32-bit Windows blocked
set "FAIL_MSG=Windows 32-bit is not supported. LuaS30 IDE needs 64-bit Windows 10 or newer."
exit /b 1
:preflight_os
set "WIN_BUILD=0"
for /f "usebackq delims=" %%B in (`powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).BuildNumber" 2^>nul`) do set "WIN_BUILD=%%B"
if "!WIN_BUILD!"=="0" (
    echo       [WARN] Khong xac dinh duoc ban Windows; bo qua kiem tra OS.
    goto :preflight_disk
)
if !WIN_BUILD! LSS 10240 (
    echo [ERROR] Windows build !WIN_BUILD! qua cu. Can Windows 10 tro len.
    >>"!LOG!" echo ERROR: Windows build !WIN_BUILD! unsupported
    set "FAIL_MSG=Windows 10 or newer is required. This machine is too old."
    exit /b 1
)
echo       Windows build !WIN_BUILD! ... OK
:preflight_disk
set "FREE_GB=-1"
del "%TEMP%\luas30_disk.txt" >nul 2>&1
powershell -NoProfile -Command "$p='!LUAS30_APPDATA!'; $d=(Get-Item $p).PSDrive; [math]::Floor($d.Free/1GB)" > "%TEMP%\luas30_disk.txt" 2>nul
if exist "%TEMP%\luas30_disk.txt" set /p FREE_GB=<"%TEMP%\luas30_disk.txt"
del "%TEMP%\luas30_disk.txt" >nul 2>&1
if "!FREE_GB!"=="-1" (
    echo       [WARN] Khong doc duoc dung luong dia; bo qua kiem tra.
    exit /b 0
)
if !FREE_GB! LSS 2 (
    echo [ERROR] O dia con !FREE_GB! GB trong; can it nhat 2 GB cho thu vien.
    >>"!LOG!" echo ERROR: disk full, only !FREE_GB! GB free
    set "FAIL_MSG=Not enough disk space. Free at least 2 GB then run again."
    exit /b 1
)
echo       Dia trong !FREE_GB! GB ... OK
exit /b 0

:setup_dirs
if defined _SETUP_DONE exit /b 0
set "LUAS30_APPDATA=%APPDATA%\LuaS30IDE"
set "LUAS30_DOCUMENTS=%USERPROFILE%\Documents"
for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('MyDocuments')" 2^>nul`) do (
    if not "%%D"=="" set "LUAS30_DOCUMENTS=%%D"
)
set "LUAS30_PROJECTS=!LUAS30_DOCUMENTS!\LuaS30 Projects"

rem App data: migrate LuaS30Engine -> LuaS30IDE (once).
rem Projects: migrate Documents\LuaS30IDE|LuaS30Engine -> "LuaS30 Projects".
if not exist "!LUAS30_APPDATA!" if exist "%APPDATA%\LuaS30Engine" (
    echo       Migrating "%APPDATA%\LuaS30Engine" -^> "LuaS30IDE" ...
    move "%APPDATA%\LuaS30Engine" "!LUAS30_APPDATA!" >nul 2>&1
)
if not exist "!LUAS30_APPDATA!" if exist "%APPDATA%\LuaS30Engine" set "LUAS30_APPDATA=%APPDATA%\LuaS30Engine"

if not exist "!LUAS30_PROJECTS!" if exist "!LUAS30_DOCUMENTS!\LuaS30IDE" (
    echo       Migrating "!LUAS30_DOCUMENTS!\LuaS30IDE" -^> "LuaS30 Projects" ...
    move "!LUAS30_DOCUMENTS!\LuaS30IDE" "!LUAS30_PROJECTS!" >nul 2>&1
)
if not exist "!LUAS30_PROJECTS!" if exist "!LUAS30_DOCUMENTS!\LuaS30Engine" (
    echo       Migrating "!LUAS30_DOCUMENTS!\LuaS30Engine" -^> "LuaS30 Projects" ...
    move "!LUAS30_DOCUMENTS!\LuaS30Engine" "!LUAS30_PROJECTS!" >nul 2>&1
)
if not exist "!LUAS30_PROJECTS!" if exist "!LUAS30_DOCUMENTS!\LuaS30IDE" set "LUAS30_PROJECTS=!LUAS30_DOCUMENTS!\LuaS30IDE"
if not exist "!LUAS30_PROJECTS!" if exist "!LUAS30_DOCUMENTS!\LuaS30Engine" set "LUAS30_PROJECTS=!LUAS30_DOCUMENTS!\LuaS30Engine"

for %%D in (
    "!LUAS30_APPDATA!"
    "!LUAS30_APPDATA!\config"
    "!LUAS30_APPDATA!\logs"
    "!LUAS30_APPDATA!\cache"
    "!LUAS30_APPDATA!\temp"
    "!LUAS30_APPDATA!\backups"
    "!LUAS30_APPDATA!\venv"
    "!LUAS30_PROJECTS!"
) do if not exist "%%~D" mkdir "%%~D" >nul 2>&1

set "LOG=!LUAS30_APPDATA!\logs\launcher.log"
set "DEP_LOG=!LUAS30_APPDATA!\logs\dependency_changes.log"
set "DEP_STATE=!LUAS30_APPDATA!\config\dependency_state.json"
set "PIP_CACHE_DIR=!LUAS30_APPDATA!\cache\pip"

>>"!LOG!" echo(
>>"!LOG!" echo ============================================================
>>"!LOG!" echo LuaS30 IDE !APP_VERSION! Smart Launcher
>>"!LOG!" echo Started: %DATE% %TIME%
>>"!LOG!" echo Engine: %CD%
>>"!LOG!" echo AppData: !LUAS30_APPDATA!
>>"!LOG!" echo Projects: !LUAS30_PROJECTS!
>>"!LOG!" echo Dependency mode requested: !DEP_MODE!

cls
echo ============================================================
echo               LuaS30 IDE !APP_VERSION! VS Code-style Studio
echo ============================================================
echo AppData : !LUAS30_APPDATA!
echo Projects: !LUAS30_PROJECTS!
echo Mode    : !DEP_MODE!
echo ------------------------------------------------------------
set "_SETUP_DONE=1"
exit /b 0

:find_python
rem Tim Python theo thu tu uu tien (kieu VXPEngine): py -3.x -> duong dan
rem cai dat quen thuoc -> where python. Yeu cau >= 3.10.
set "BASE_PY="
set "BASE_PY_ARGS="
for %%V in (3.12 3.13 3.11 3.10) do (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 if not defined BASE_PY (
        set "BASE_PY=py"
        set "BASE_PY_ARGS=-%%V"
    )
)
if not defined BASE_PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined BASE_PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined BASE_PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined BASE_PY if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined BASE_PY if exist "C:\Python312\python.exe" set "BASE_PY=C:\Python312\python.exe"
if not defined BASE_PY if exist "C:\Python313\python.exe" set "BASE_PY=C:\Python313\python.exe"
if not defined BASE_PY if exist "C:\Python311\python.exe" set "BASE_PY=C:\Python311\python.exe"
if not defined BASE_PY if exist "C:\Python310\python.exe" set "BASE_PY=C:\Python310\python.exe"
if not defined BASE_PY (
    where python >nul 2>&1
    if not errorlevel 1 set "BASE_PY=python"
)
if not defined BASE_PY (
    echo [ERROR] Khong tim thay Python 3.10 tro len.
    echo Hay cai Python tu python.org, bat tuy chon Add Python to PATH, roi chay lai.
    >>"!LOG!" echo ERROR: Python not found
    set "FAIL_MSG=Python 3.10+ was not found. Install Python from python.org (Add to PATH) then run again."
    exit /b 1
)
echo [LuaS30] Su dung Python: !BASE_PY! !BASE_PY_ARGS!
"!BASE_PY!" !BASE_PY_ARGS! -c "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,10) else 9)" > "%TEMP%\luas30_pyver.txt" 2>>"!LOG!"
if errorlevel 1 (
    echo [ERROR] Can Python 3.10 tro len.
    >>"!LOG!" echo ERROR: Python version too old
    set "FAIL_MSG=Python 3.10 or newer is required. Update Python then run again."
    exit /b 1
)
set /p PY_VERSION=<"%TEMP%\luas30_pyver.txt"
echo       System Python !PY_VERSION! ... OK
>>"!LOG!" echo System Python !PY_VERSION! OK
exit /b 0

:ensure_venv
rem Python kem theo (ban cai single-file) duoc uu tien: khong can venv,
rem thu vien cai thang vao python\Lib\site-packages (offline).
if exist "%BUNDLED_PY%" (
    "%BUNDLED_PY%" -c "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,10) else 9)" > "%TEMP%\luas30_pyver.txt" 2>>"!LOG!"
    if not errorlevel 1 (
        set "USE_BUNDLED=1"
        set "VENV_PY=%BUNDLED_PY%"
        set /p PY_VERSION=<"%TEMP%\luas30_pyver.txt"
        echo [1/8] Bundled Python !PY_VERSION! ... OK
        >>"!LOG!" echo Bundled Python !PY_VERSION! OK
        goto :ensure_pip_bundled
    )
    echo       [WARN] Python kem theo qua cu; thu Python he thong...
    >>"!LOG!" echo WARN: bundled Python unusable, fallback to system
)
set "USE_BUNDLED=0"
set "VENV_PY=!LUAS30_APPDATA!\venv\Scripts\python.exe"
if exist "!VENV_PY!" (
    "!VENV_PY!" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 9)" >nul 2>&1
    if not errorlevel 1 exit /b 0
    echo [LuaS30] venv bi hong hoac sai ban Python; dang tao lai...
    >>"!LOG!" echo WARN: venv broken, recreating
    rmdir /s /q "!LUAS30_APPDATA!\venv" >>"!LOG!" 2>&1
)
call :find_python
if errorlevel 1 exit /b 1
echo [2/8] Dang tao moi truong tai "!LUAS30_APPDATA!\venv" ...
"%BASE_PY%" %BASE_PY_ARGS% -m venv "!LUAS30_APPDATA!\venv" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tao duoc moi truong venv.
    echo Xem: !LOG!
    >>"!LOG!" echo ERROR: venv initialization failed
    set "FAIL_MSG=Could not create the isolated environment. See launcher log in AppData."
    exit /b 1
)
set "VENV_PY=!LUAS30_APPDATA!\venv\Scripts\python.exe"
if not exist "!VENV_PY!" (
    echo [ERROR] Khong tao duoc moi truong venv.
    >>"!LOG!" echo ERROR: venv python missing after create
    set "FAIL_MSG=Could not create the isolated environment. See launcher log in AppData."
    exit /b 1
)
rem ensurepip is local/offline; only run when pip is missing.
"!VENV_PY!" -m pip --version >nul 2>>"!LOG!"
if errorlevel 1 (
    echo       pip missing; bootstrapping from Python installation...
    "!VENV_PY!" -m ensurepip --upgrade >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo [ERROR] pip is unavailable and ensurepip could not repair it.
        >>"!LOG!" echo ERROR: pip unavailable
        set "FAIL_MSG=pip is unavailable. Reinstall Python with pip enabled, then run again."
        exit /b 1
    )
)
echo       venv + pip ... OK
exit /b 0

:ensure_pip_bundled
"!VENV_PY!" -m pip --version >nul 2>>"!LOG!"
if not errorlevel 1 (
    echo       bundled Python + pip ... OK
    exit /b 0
)
echo       pip missing; bootstrapping offline from bundled files...
"!VENV_PY!" "%ROOT_DIR%python\bootstrap\get-pip.py" --no-index --find-links "%ROOT_DIR%python\bootstrap" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo [ERROR] pip is unavailable and offline bootstrap failed.
    >>"!LOG!" echo ERROR: bundled pip bootstrap failed
    set "FAIL_MSG=pip is unavailable. Reinstall LuaS30 IDE (full package)."
    exit /b 1
)
echo       bundled Python + pip ... OK
exit /b 0

:install_deps
echo [3/8] Checking Python library versions...
set "DEP_FORCE_ARG="
if "!FORCE_DEPS!"=="1" set "DEP_FORCE_ARG=--force"
set "TOOL_SCRIPT=tools\dependency_manager.py"
if not exist "!TOOL_SCRIPT!" set "TOOL_SCRIPT=tools\dependency_manager.pyc"
if not exist "!TOOL_SCRIPT!" (
    echo [ERROR] Khong tim thay tools\dependency_manager.py
    >>"!LOG!" echo ERROR: dependency manager missing
    set "FAIL_MSG=IDE files are incomplete. Reinstall LuaS30 IDE."
    exit /b 1
)
rem Bundled offline wheels (single-file installer ships vendor\wheels).
set "WHEELS_ARG="
if exist "%ROOT_DIR%vendor\wheels" set "WHEELS_ARG=--find-links "%ROOT_DIR%vendor\wheels""
"!VENV_PY!" "!TOOL_SCRIPT!" ^
    --requirements "requirements-studio.txt" ^
    --python "!VENV_PY!" ^
    --mode "!DEP_MODE!" ^
    --changes-log "!DEP_LOG!" ^
    --launcher-log "!LOG!" ^
    --state-json "!DEP_STATE!" ^
    !WHEELS_ARG! ^
    !DEP_FORCE_ARG!
set "DEP_EXIT=!ERRORLEVEL!"
if not "!DEP_EXIT!"=="0" (
    echo(
    echo ============================================================
    echo [ERROR] Moi truong Python chua du thu vien can thiet.
    echo Requested mode : !DEP_MODE!
    echo Dependency state: !DEP_STATE!
    if /I "!DEP_MODE!"=="offline" (
        echo Offline mode never downloads packages.
        echo Connect once and run normally to install missing libraries.
    ) else (
        echo If the network is unavailable you can still run:
        echo   run.bat --offline
        echo provided all required packages are already installed.
    )
    echo ============================================================
    >>"!LOG!" echo ERROR: dependency manager returned !DEP_EXIT!
    set "FAIL_MSG=Python libraries are missing. Connect to Internet once and run again."
    exit /b !DEP_EXIT!
)
"!VENV_PY!" -c "import PySide6; from PySide6.QtCore import qVersion; print('PySide6',PySide6.__version__,'Qt',qVersion())" > "%TEMP%\luas30_qtver.txt" 2>>"!LOG!"
if errorlevel 1 (
    echo [WARN] PySide6 import that bai; kiem tra Visual C++ runtime...
    call :ensure_vc_redist
    if not errorlevel 1 (
        "!VENV_PY!" -c "import PySide6; from PySide6.QtCore import qVersion; print('PySide6',PySide6.__version__,'Qt',qVersion())" > "%TEMP%\luas30_qtver.txt" 2>>"!LOG!"
    )
)
if not exist "%TEMP%\luas30_qtver.txt" (
    echo [ERROR] PySide6 is unavailable after dependency validation.
    echo Xem: !LOG!
    >>"!LOG!" echo ERROR: PySide6 unavailable
    set "FAIL_MSG=PySide6 is unavailable. If offline install fails, install vc_redist.x64 then run again."
    exit /b 1
)
"!VENV_PY!" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PySide6 is unavailable after dependency validation.
    echo Xem: !LOG!
    >>"!LOG!" echo ERROR: PySide6 unavailable
    set "FAIL_MSG=PySide6 is unavailable. If offline install fails, install vc_redist.x64 then run again."
    del "%TEMP%\luas30_qtver.txt" >nul 2>&1
    exit /b 1
)
set /p QT_VERSION=<"%TEMP%\luas30_qtver.txt"
echo       !QT_VERSION! ... OK
>>"!LOG!" echo !QT_VERSION! OK
>>"!LOG!" echo Dependency state: !DEP_STATE!
>>"!LOG!" echo Dependency changes: !DEP_LOG!
exit /b 0

:ensure_vc_redist
rem PySide6/Qt6 can Visual C++ runtime. Tu tai va cai online neu thieu.
if exist "%SystemRoot%\System32\vcruntime140_1.dll" exit /b 0
if exist "%SystemRoot%\System32\vcruntime140.dll" exit /b 0
echo       Thieu Visual C++ runtime; dang tai tu Microsoft...
>>"!LOG!" echo WARN: vcruntime missing, trying online install
set "VCREDIST=%TEMP%\luas30_vc_redist.x64.exe"
del "!VCREDIST!" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '!VCREDIST!' -TimeoutSec 180" >>"!LOG!" 2>&1
if errorlevel 1 (
    echo       [WARN] Khong tai duoc vc_redist; can mang hoac cai tay.
    >>"!LOG!" echo WARN: vc_redist download failed
    del "!VCREDIST!" >nul 2>&1
    exit /b 1
)
echo       Dang cai Visual C++ runtime...
"!VCREDIST!" /quiet /norestart >>"!LOG!" 2>&1
del "!VCREDIST!" >nul 2>&1
if exist "%SystemRoot%\System32\vcruntime140.dll" (
    echo       Visual C++ runtime ... OK
    >>"!LOG!" echo vc_redist installed
    exit /b 0
)
echo       [WARN] Cai vc_redist xong nhung van thieu DLL.
>>"!LOG!" echo WARN: vc_redist install did not provide DLL
exit /b 1

:ensure_runtime
call :ensure_venv
if errorlevel 1 exit /b 1
"!VENV_PY!" -c "import PySide6" >nul 2>&1
if not errorlevel 1 exit /b 0
echo [LuaS30] Dang cai cac thu vien Python con thieu...
call :install_deps
if errorlevel 1 exit /b 1
exit /b 0

:validate_sources
echo [4/8] Validating LuaS30 runtime and IDE source...
set "TOOL_SCRIPT=tools\validate_tree.py"
if not exist "!TOOL_SCRIPT!" set "TOOL_SCRIPT=tools\validate_tree.pyc"
if exist "!TOOL_SCRIPT!" (
    "!VENV_PY!" "!TOOL_SCRIPT!" >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo [ERROR] LuaS30 Native SDK/runtime validation failed.
        >>"!LOG!" echo ERROR: validate_tree.py failed
        set "FAIL_MSG=IDE files failed validation. Reinstall LuaS30 IDE."
        exit /b 1
    )
)
set "TOOL_SCRIPT=tools\validate_native_sdk.py"
if not exist "!TOOL_SCRIPT!" set "TOOL_SCRIPT=tools\validate_native_sdk.pyc"
if exist "!TOOL_SCRIPT!" (
    "!VENV_PY!" "!TOOL_SCRIPT!" >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo [ERROR] LuaS30 Native SDK/runtime validation failed.
        >>"!LOG!" echo ERROR: validate_native_sdk.py failed
        set "FAIL_MSG=IDE files failed validation. Reinstall LuaS30 IDE."
        exit /b 1
    )
)
if exist "studio\main.py" (
    "!VENV_PY!" -m compileall -q "studio" "tools" >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo [ERROR] Python source validation failed.
        >>"!LOG!" echo ERROR: compileall failed
        set "FAIL_MSG=IDE files failed validation. Reinstall LuaS30 IDE."
        exit /b 1
    )
)
echo       LuaS30 Native SDK / Lua 5.1 / Studio source ... OK
exit /b 0

:check_toolchain
echo [5/8] Checking bundled ARM GCC...
set "ARM_ROOT=%CD%\toolchain\arm-gcc"
set "ARM_GCC=!ARM_ROOT!\bin\arm-none-eabi-gcc.exe"
set "ARM_READELF=!ARM_ROOT!\bin\arm-none-eabi-readelf.exe"
if not exist "!ARM_GCC!" (
    echo       [WARN] ARM GCC not installed; builds will be unavailable.
    >>"!LOG!" echo WARN: ARM GCC missing under !ARM_ROOT!
    exit /b 0
)
if not exist "!ARM_READELF!" (
    echo       [WARN] ARM readelf missing; builds may fail.
    exit /b 0
)
"!ARM_GCC!" --version > "%TEMP%\luas30_gccver.txt" 2>>"!LOG!"
if errorlevel 1 (
    echo       [WARN] ARM GCC present but failed to start.
    exit /b 0
)
set /p GCC_VERSION=<"%TEMP%\luas30_gccver.txt"
echo       !GCC_VERSION! ... OK
>>"!LOG!" echo ARM GCC: !GCC_VERSION!
exit /b 0

:check_emulator
echo [6/8] Checking bundled VXP emulator...
if not exist "emulator\VXPEmu.exe" (
    echo       [WARN] Emulator not installed; Run-in-emulator will be unavailable.
    >>"!LOG!" echo WARN: emulator missing
    exit /b 0
)
echo       VXPEmu present ... OK
>>"!LOG!" echo Emulator present
exit /b 0

:write_env_report
echo [7/8] Writing environment report...
set "TOOL_SCRIPT=tools\env_check.py"
if not exist "!TOOL_SCRIPT!" set "TOOL_SCRIPT=tools\env_check.pyc"
if exist "!TOOL_SCRIPT!" (
    "!VENV_PY!" "!TOOL_SCRIPT!" --root "%CD%" --write "!LUAS30_APPDATA!\logs\environment.json" >>"!LOG!" 2>&1
    if errorlevel 1 (
        echo       [WARN] Environment report contains warnings.
    ) else (
        echo       Environment ... READY
    )
)
exit /b 0

rem Hien hop thoai loi ngay ca khi launcher chay an (shortcut .vbs).
:popup
powershell -NoProfile -ExecutionPolicy Bypass -Command "(New-Object -ComObject WScript.Shell).Popup('%~1',0,'LuaS30 IDE',48)" >nul 2>&1
exit /b 0

:failed
if not defined FAIL_MSG set "FAIL_MSG=LuaS30 IDE failed to start. See launcher log in AppData."
call :popup "!FAIL_MSG!"
set "FAIL_MSG="
set "RC=1"
if "%FROM_MENU%"=="0" pause
goto :task_done

:success
set "RC=0"

:task_done
if "%FROM_MENU%"=="1" (
    echo(
    pause
    goto :menu
)
goto :finish

:finish
exit /b %RC%
