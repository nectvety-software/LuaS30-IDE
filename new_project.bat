@echo off
setlocal EnableExtensions
if "%~1"=="" (
  echo Usage: new_project.bat PROJECT_NAME
  echo.
  echo Project is created automatically in:
  echo   Documents\LuaS30 Projects\PROJECT_NAME
  exit /b 2
)

set "PROJECT_NAME=%~1"
set "DOCS=%USERPROFILE%\Documents"
for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('MyDocuments')" 2^>nul`) do (
  if not "%%D"=="" set "DOCS=%%D"
)
set "PROJECTS_ROOT=%DOCS%\LuaS30 Projects"
set "DEST=%PROJECTS_ROOT%\%PROJECT_NAME%"

rem Migrate older project roots if the new folder does not exist yet.
if not exist "%PROJECTS_ROOT%" if exist "%DOCS%\LuaS30IDE" (
  move "%DOCS%\LuaS30IDE" "%PROJECTS_ROOT%" >nul 2>&1
)
if not exist "%PROJECTS_ROOT%" if exist "%DOCS%\LuaS30Engine" (
  move "%DOCS%\LuaS30Engine" "%PROJECTS_ROOT%" >nul 2>&1
)
if not exist "%PROJECTS_ROOT%" if exist "%DOCS%\LuaS30IDE" set "PROJECTS_ROOT=%DOCS%\LuaS30IDE"
if not exist "%PROJECTS_ROOT%" if exist "%DOCS%\LuaS30Engine" set "PROJECTS_ROOT=%DOCS%\LuaS30Engine"
if not exist "%PROJECTS_ROOT%" set "DEST=%PROJECTS_ROOT%\%PROJECT_NAME%"

if not exist "%PROJECTS_ROOT%" mkdir "%PROJECTS_ROOT%" >nul 2>&1
if exist "%DEST%" (
  echo [ERROR] Project already exists:
  echo   %DEST%
  exit /b 1
)

xcopy /E /I /Y "%~dp0templates\basic" "%DEST%" >nul
if errorlevel 1 (
  echo [ERROR] Could not copy project template.
  exit /b 3
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='%DEST%\project.json'; if(Test-Path $p){ $j=Get-Content -Raw $p ^| ConvertFrom-Json; $j.name='%PROJECT_NAME%'; $j ^| ConvertTo-Json -Depth 16 ^| Set-Content -Encoding UTF8 $p }" >nul 2>&1

echo [OK] Project created:
echo   %DEST%
exit /b 0
