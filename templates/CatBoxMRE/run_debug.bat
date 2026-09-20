@echo off
cd /d "%~dp0"
py -3 tools\bundle_main.py
py -3 tools\validate_project.py
py -3 tools\smoke_test.py
pause
