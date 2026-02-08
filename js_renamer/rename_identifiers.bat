@echo off
setlocal enabledelayedexpansion

REM ============================
REM Argument validation
REM ============================
if "%~1"=="" (
    echo Usage: rename_identifiers.bat source.js modification_table.tsv target.js
    exit /b 1
)
if "%~2"=="" (
    echo Usage: rename_identifiers.bat source.js modification_table.tsv target.js
    exit /b 1
)
if "%~3"=="" (
    echo Usage: rename_identifiers.bat source.js modification_table.tsv target.js
    exit /b 1
)

REM ============================
REM Normalize paths
REM ============================
set "SRC=%~f1"
set "TBL=%~f2"
set "DST=%~f3"

REM ============================
REM Validate inputs
REM ============================
if not exist "%SRC%" (
    echo [ERROR] Source JS not found: %SRC%
    exit /b 1
)
if not exist "%TBL%" (
    echo [ERROR] TSV table not found: %TBL%
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
REM Set log path
REM ============================
set "LOGFILE=%DSTDIR%rename_identifiers.log"

REM ============================
REM Get script directory
REM ============================
set "SCRIPTDIR=%~dp0"

REM ============================
REM Run Node.js script
REM ============================
node "%SCRIPTDIR%node\rename_identifiers.js" ^
    --source "%SRC%" ^
    --table "%TBL%" ^
    --target "%DST%" ^
    --log "%LOGFILE%"

set EXITCODE=%ERRORLEVEL%

REM ============================
REM Display log
REM ============================
if exist "%LOGFILE%" (
    echo.
    echo === Log Output ===
    type "%LOGFILE%"
)

exit /b %EXITCODE%
