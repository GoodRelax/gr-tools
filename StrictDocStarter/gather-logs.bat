@echo off
rem StrictDocStarter - log and diagnostics collector.
rem Bundles setup.log / env-report.json / setup.config.json from this folder
rem plus a fresh diagnostics.txt into %TEMP%\StrictDocStarter-result-<timestamp>.zip
rem and opens Explorer at the file. Always pauses at the end.
rem
rem Admin not required. Common elevation / MOTW / CWD handled by
rem _lib\elevate.bat (FR-806).

setlocal EnableExtensions

call "%~dp0_lib\elevate.bat" no_admin "%~f0" "%*"
if "%ERRORLEVEL%"=="99" exit /b 0
if errorlevel 1 exit /b %ERRORLEVEL%

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0gather-logs.ps1"
set "PS_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo gather-logs finished. Exit code: %PS_EXIT%
echo ============================================================
pause

endlocal & exit /b %PS_EXIT%
