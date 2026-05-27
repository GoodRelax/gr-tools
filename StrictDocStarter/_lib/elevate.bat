@echo off
rem StrictDocStarter/_lib/elevate.bat - common UAC elevation + MOTW strip + CWD normalize.
rem
rem Usage from each caller .bat:
rem
rem   call "<relpath>\_lib\elevate.bat" <MODE> "%~f0" "%*"
rem   if "%ERRORLEVEL%"=="99" exit /b 0           rem UAC re-launch in progress
rem   if errorlevel 1 exit /b %ERRORLEVEL%        rem elevate.bat failed
rem
rem MODE is one of:
rem   need_admin  - require admin; if not elevated, re-launch caller via UAC
rem   no_admin    - admin not required; skip elevation check
rem
rem The third arg is the caller's full path (%~f0); the fourth is the caller's
rem original args, wrapped as a single quoted string ("%*").
rem
rem Spec refs: FR-806, FR-807 (this script consolidates patterns previously
rem duplicated across setup-strictdoc.bat / gather-logs.bat / vm-tests\*.bat).
rem Output language: English ASCII only (ADR-008).

setlocal EnableExtensions

set "MODE=%~1"
set "CALLER=%~2"
set "CALLER_ARGS=%~3"

if not defined MODE   goto :usage
if not defined CALLER goto :usage
if /i not "%MODE%"=="need_admin" if /i not "%MODE%"=="no_admin" goto :usage

rem ---- Compute StrictDocStarter root (parent of this _lib folder) ---------------------
rem STARTER_ROOT is used for MOTW stripping so a single recursive Unblock-File
rem covers StrictDocStarter/, StrictDocStarter/lib/, StrictDocStarter/_lib/, and StrictDocStarter/vm-tests/.
for %%I in ("%~dp0..") do set "STARTER_ROOT=%%~fI"

rem ---- Step 1: admin check + self-elevation (need_admin only) ----------------
if /i "%MODE%"=="need_admin" (
    rem NOTE: 'if errorlevel 1' (not 'if %ERRORLEVEL% NEQ 0') so the comparison
    rem sees the runtime value set by 'net session', not the parse-time value
    rem at the start of this if-block (classic batch trap).
    net session >nul 2>&1
    if errorlevel 1 (
        echo Requesting administrator privileges via UAC...
        powershell.exe -ExecutionPolicy Bypass -NoProfile -Command ^
            "Start-Process -FilePath cmd -ArgumentList '/c','\"%CALLER%\" %CALLER_ARGS%' -Verb RunAs"
        endlocal & exit /b 99
    )
)

rem ---- Step 2: Mark-of-the-Web strip on the entire StrictDocStarter tree --------------
rem Clipboard transfer (e.g., into a Hyper-V VM) tags transferred files as
rem "downloaded"; PowerShell can refuse to load them despite Bypass policy.
echo Stripping Mark-of-the-Web under %STARTER_ROOT% ...
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command ^
    "try { Get-ChildItem -Path '%STARTER_ROOT%' -Recurse -File -Include *.ps1,*.psm1,*.bat -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue; Write-Host '  done.' } catch { Write-Host ('  warning: ' + $_.Exception.Message) }"

rem ---- Step 3: Normalize CWD to caller's directory ---------------------------
rem After UAC re-launch via 'Start-Process -Verb RunAs', the new admin cmd
rem inherits CWD=System32. Force CWD back to caller's folder so output files
rem (setup.config.json / setup.log / env-report.json) land next to caller.
rem The 'endlocal & cd /d "..."' idiom: cmd parses the whole line first
rem (expanding %CALLER_DIR% to its value), then runs endlocal (clearing the
rem var), then cd /d with the literal path. cd /d after endlocal persists.
for %%I in ("%CALLER%") do set "CALLER_DIR=%%~dpI"
endlocal & cd /d "%CALLER_DIR%" & exit /b 0

:usage
echo Usage: call elevate.bat ^<need_admin^|no_admin^> "%%~f0" "%%*"
endlocal & exit /b 2
