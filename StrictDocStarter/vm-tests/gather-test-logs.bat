@echo off
rem StrictDocStarter - test-specific log collector.
rem Bundles test-results/*.log (per-scenario StrictDocStarter logs from run-tests.bat)
rem plus the latest setup.log / setup.config.json and a fresh diagnostics.txt
rem into %TEMP%\StrictDocStarter-test-result-<timestamp>.zip and opens Explorer.
rem
rem Use after running run-tests.bat. For the basic case (only setup-strictdoc.bat run),
rem use gather-logs.bat instead.
rem
rem Admin not required. Common elevation / MOTW / CWD handled by
rem _lib\elevate.bat (FR-806).
rem Output language: English ASCII only.

setlocal EnableExtensions

call "%~dp0..\_lib\elevate.bat" no_admin "%~f0" "%*"
if "%ERRORLEVEL%"=="99" exit /b 0
if errorlevel 1 exit /b %ERRORLEVEL%

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0gather-test-logs.ps1"
set "PS_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo gather-test-logs finished. Exit code: %PS_EXIT%
echo ============================================================
pause

endlocal & exit /b %PS_EXIT%
