@echo off
rem manage-strictdoc - StrictDoc server lifecycle manager launcher.
rem Provides a menu UI (1 Start / 2 Stop / 3 Status / 4 Logs / 5 Edit config / Q).
rem Admin not required. Common MOTW / CWD handled by _lib\elevate.bat (FR-806).
rem Spec: docs/serve-spec.md (FR-101..110, FR-102 = elevate no_admin).
rem Output language: English ASCII only (per NFR-005 / ADR-008).

setlocal EnableExtensions

call "%~dp0_lib\elevate.bat" no_admin "%~f0" "%*"
if "%ERRORLEVEL%"=="99" exit /b 0
if errorlevel 1 exit /b %ERRORLEVEL%

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0manage-strictdoc.ps1" %*
set "PS_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo manage-strictdoc finished. Exit code: %PS_EXIT%
echo Log: %~dp0manage.log
echo ============================================================
pause

endlocal & exit /b %PS_EXIT%
