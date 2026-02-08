@echo off
setlocal enabledelayedexpansion

REM ============================
REM Argument validation
REM ============================
if "%~1"=="" (
    echo Usage: reintegrate_to_html.bat transformed.js source.html output.html
    exit /b 1
)
if "%~2"=="" (
    echo Usage: reintegrate_to_html.bat transformed.js source.html output.html
    exit /b 1
)
if "%~3"=="" (
    echo Usage: reintegrate_to_html.bat transformed.js source.html output.html
    exit /b 1
)

REM ============================
REM Normalize paths
REM ============================
set "JS=%~f1"
set "SRC=%~f2"
set "DST=%~f3"

REM ============================
REM Validate inputs
REM ============================
if not exist "%JS%" (
    echo [ERROR] Transformed JS not found: %JS%
    exit /b 1
)
if not exist "%SRC%" (
    echo [ERROR] Source HTML not found: %SRC%
    exit /b 1
)

REM ============================
REM Prepare output directory
REM ============================
set "DSTDIR=%~dp3"
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
node "%SCRIPTDIR%node\reintegrate_to_html.js" ^
    --js "%JS%" ^
    --source "%SRC%" ^
    --target "%DST%"

exit /b %ERRORLEVEL%
