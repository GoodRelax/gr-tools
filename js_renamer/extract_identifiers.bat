@echo off
setlocal enabledelayedexpansion

REM ============================
REM Argument validation
REM ============================
if "%~1"=="" (
    echo Usage: extract_identifiers.bat source.js output.tsv
    exit /b 1
)
if "%~2"=="" (
    echo Usage: extract_identifiers.bat source.js output.tsv
    exit /b 1
)

REM ============================
REM Normalize paths
REM ============================
set "SRC=%~f1"
set "OUT=%~f2"

REM ============================
REM Validate input
REM ============================
if not exist "%SRC%" (
    echo [ERROR] Source JS not found: %SRC%
    exit /b 1
)

REM ============================
REM Prepare output directory
REM ============================
set "OUTDIR=%~dp2"
if not exist "%OUTDIR%" (
    mkdir "%OUTDIR%"
)

REM ============================
REM Get script directory
REM ============================
set "SCRIPTDIR=%~dp0"

REM ============================
REM Run Node.js script
REM ============================
node "%SCRIPTDIR%node\extract_identifiers.js" ^
    --source "%SRC%" ^
    --output "%OUT%"

exit /b %ERRORLEVEL%
