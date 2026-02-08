@echo off
setlocal enabledelayedexpansion

REM ============================
REM Argument validation
REM ============================
if "%~1"=="" (
    echo Usage: extract_js_from_html.bat source.html target.js
    exit /b 1
)
if "%~2"=="" (
    echo Usage: extract_js_from_html.bat source.html target.js
    exit /b 1
)

REM ============================
REM Normalize paths
REM ============================
set "SRC=%~f1"
set "DST=%~f2"

REM ============================
REM Validate input
REM ============================
if not exist "%SRC%" (
    echo [ERROR] Source HTML not found: %SRC%
    exit /b 1
)

REM ============================
REM Prepare output directory
REM ============================
set "DSTDIR=%~dp2"
if not exist "%DSTDIR%" (
    mkdir "%DSTDIR%"
)

REM ============================
REM Get script directory
REM ============================
set "SCRIPTDIR=%~dp0"

REM ============================
REM Run Node.js script
REM ============================
node "%SCRIPTDIR%node\extract_js_from_html.js" ^
    --source "%SRC%" ^
    --target "%DST%"

exit /b %ERRORLEVEL%
