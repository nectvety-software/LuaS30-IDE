@echo off
setlocal
if "%~1"=="" (
  echo Usage: import_from_old_engine.bat D:\path\to\lua-engine
  exit /b 2
)
set "SRC=%~f1\mre-core\gcc"
set "DST=%~dp0arm-gcc"
if not exist "%SRC%" (
  echo [ERROR] GCC toolchain not found: %SRC%
  exit /b 1
)
if exist "%DST%" rmdir /S /Q "%DST%"
xcopy /E /I /Y "%SRC%" "%DST%" >nul
rem Ghi lai nguon copy: build.py doc file nay de tu tim MRE SDK nam canh toolchain
rem (mre-core\gcc -> mre-core\sdk), nen khong phai truyen --mre-sdk bang tay nua.
> "%DST%\.import-source" echo %SRC%
echo [OK] ARM GCC copied to: %DST%
echo [OK] Recorded import source in %DST%\.import-source
echo LuaS30 itself does NOT copy or link the vendor MRE runtime archives.
