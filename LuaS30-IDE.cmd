@echo off
rem Visible console launcher (for debugging). Desktop icon uses LuaS30-IDE.vbs (hidden).
setlocal
cd /d "%~dp0"
start "" "%~dp0run.bat" %*
