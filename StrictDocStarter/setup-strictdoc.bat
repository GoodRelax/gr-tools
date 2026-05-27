@echo off
rem StrictDocStarter - launcher.
rem UAC self-elevation, MOTW stripping, and CWD normalization are factored
rem into _lib\elevate.bat (FR-806). This file just decides whether admin is
rem required (based on subcommand), delegates the setup, runs setup-strictdoc.ps1,
rem and guarantees a final pause so the window never closes silently.
rem Output language: English ASCII only (per ADR-008).

setlocal EnableExtensions

rem ---- Step 1: Decide whether elevation is needed ----------------------------
rem Subcommands that do not need admin privileges (run without UAC).
set "NEED_ADMIN=need_admin"
set "ARG1=%~1"
if /i "%ARG1%"=="help"   set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="-h"     set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="--help" set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="/?"     set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="check"  set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="config" set "NEED_ADMIN=no_admin"
if /i "%ARG1%"=="dryrun" set "NEED_ADMIN=no_admin"

rem ---- Step 2: Common elevation + MOTW + CWD via _lib\elevate.bat ------------
call "%~dp0_lib\elevate.bat" %NEED_ADMIN% "%~f0" "%*"
if "%ERRORLEVEL%"=="99" exit /b 0
if errorlevel 1 exit /b %ERRORLEVEL%

rem ---- Step 3: Run setup-strictdoc.ps1 ------------------------------------------------
echo.
echo Launching setup-strictdoc.ps1 ...
echo.
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup-strictdoc.ps1" %*
set "PS_EXIT=%ERRORLEVEL%"

rem ---- Step 4: Guaranteed pause -----------------------------------------------
echo.
echo ============================================================
echo setup-strictdoc.ps1 finished. Exit code: %PS_EXIT%
if not "%PS_EXIT%"=="0" (
    echo Something went wrong. See messages above.
    echo If logs were produced, run gather-logs.bat to bundle them.
) else (
    echo Log: %~dp0setup.log
)
echo ============================================================
pause

endlocal & exit /b %PS_EXIT%
