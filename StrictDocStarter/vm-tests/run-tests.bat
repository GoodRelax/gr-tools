@echo off
rem StrictDocStarter - automated test runner.
rem Runs multiple scenarios (idempotency, partial uninstall variants) and
rem reports pass/fail per scenario.
rem
rem Prerequisite: setup-strictdoc.bat has already been run successfully at least once,
rem so all tools are installed on this VM.
rem
rem Usage: double-click run-tests.bat (or invoke from elevated shell).
rem        run-tests.bat dryrun       - plan-only mode, no uninstall/install
rem
rem Admin required (winget uninstall in real-run mode). Common elevation /
rem MOTW / CWD handled by _lib\elevate.bat (FR-806).
rem Output language: English ASCII only.

setlocal EnableExtensions

call "%~dp0..\_lib\elevate.bat" need_admin "%~f0" "%*"
if "%ERRORLEVEL%"=="99" exit /b 0
if errorlevel 1 exit /b %ERRORLEVEL%

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0run-tests.ps1" %*
set "PS_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo Test runner finished. Exit code: %PS_EXIT%
echo (0 = all PASS, 1 = at least one FAIL)
echo ============================================================
pause

endlocal & exit /b %PS_EXIT%
