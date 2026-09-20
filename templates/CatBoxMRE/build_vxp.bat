@echo off
setlocal
cd /d "%~dp0"
py -3 tools\check_nokia225_config.py || goto :err
py -3 tools\bundle_main.py || goto :err
py -3 tools\validate_project.py || goto :err
py -3 tools\smoke_test.py || goto :err
py -3 tools\make_release.py || goto :err
echo.
echo [OK] VXP-ready package created.
if exist "%MRE_BUILD_CMD%" (
  echo [INFO] Invoking external MRE builder...
  call "%MRE_BUILD_CMD%" main.lua
) else (
  echo [INFO] MRE_BUILD_CMD not set. Source is VXP-ready; binary .vxp was not compiled here.
)
exit /b 0
:err
echo [ERROR] Build failed.
exit /b 1
