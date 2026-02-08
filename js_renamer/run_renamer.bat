@echo off
setlocal enabledelayedexpansion

echo ========================================
echo JavaScript Renamer v3.1 (Alpha)
echo ========================================
echo.

REM ============================
REM Get script directory
REM ============================
set "SCRIPTDIR=%~dp0"

REM ============================
REM Check dependencies
REM ============================
if exist "%SCRIPTDIR%node_modules\" (
    goto :SKIP_INSTALL
)

echo [WARN] Dependencies (node_modules) not found.

REM Check if package.json exists
if not exist "%SCRIPTDIR%package.json" (
    echo [ERROR] package.json not found in the script directory.
    echo Cannot install dependencies automatically.
    cmd /k
    exit /b 1
)

REM Check if Node.js/npm is installed
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or 'npm' is not in your PATH.
    echo Please refer to README.md for installation instructions.
    cmd /k
    exit /b 1
)

REM Prompt user to install
echo.
set /p INSTALL_CONFIRM="Would you like to run 'npm install' now? (yes/no): "
if /i not "!INSTALL_CONFIRM!"=="yes" (
    echo [INFO] Installation cancelled by user.
    echo Please run 'npm install' manually before running this script.
    cmd /k
    exit /b 1
)

REM Run installation
echo.
echo [INFO] Running 'npm install'...
call npm install
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 'npm install' failed.
    echo Please check your internet connection or permissions.
    cmd /k
    exit /b 1
)
echo [SUCCESS] Dependencies installed.
echo.

:SKIP_INSTALL

REM ============================
REM Check input directory
REM ============================
if not exist "%SCRIPTDIR%input\" (
    echo [INFO] Creating input\ directory...
    mkdir "%SCRIPTDIR%input"
    echo.
    echo [ERROR] No HTML file found in input\ directory
    echo Please place exactly one .html file in the input\ folder.
    echo.
    cmd /k
    exit /b 1
)

REM ============================
REM Find HTML file in input
REM ============================
set "HTML_COUNT=0"
set "HTML_FILE="

for %%f in ("%SCRIPTDIR%input\*.html") do (
    set /a HTML_COUNT+=1
    set "HTML_FILE=%%f"
)

if %HTML_COUNT%==0 (
    echo [ERROR] No HTML file found in input\ directory
    echo Please place exactly one .html file in the input\ folder.
    cmd /k
    exit /b 1
)

if %HTML_COUNT% gtr 1 (
    echo [ERROR] Multiple HTML files found in input\ directory
    echo Please place exactly one .html file in the input\ folder.
    cmd /k
    exit /b 1
)

echo [INFO] Found HTML file: %HTML_FILE%
echo.

REM ============================
REM Create output directory
REM ============================
if not exist "%SCRIPTDIR%output\" (
    mkdir "%SCRIPTDIR%output"
)

REM ============================
REM Step 1: Extract JavaScript
REM ============================
echo [Step 1/5] Extracting JavaScript from HTML...
call "%SCRIPTDIR%extract_js_from_html.bat" ^
    "%HTML_FILE%" ^
    "%SCRIPTDIR%output\unified.js"

if errorlevel 1 (
    echo [ERROR] Failed to extract JavaScript
    cmd /k
    exit /b 1
)
echo [SUCCESS] JavaScript extracted to output\unified.js
echo.

REM ============================
REM Step 2: Extract identifiers
REM ============================
echo [Step 2/5] Extracting identifiers to TSV...
call "%SCRIPTDIR%extract_identifiers.bat" ^
    "%SCRIPTDIR%output\unified.js" ^
    "%SCRIPTDIR%output\modification_base.tsv"

if errorlevel 1 (
    echo [ERROR] Failed to extract identifiers
    cmd /k
    exit /b 1
)
echo [SUCCESS] Identifiers extracted to output\modification_base.tsv
echo.

REM ============================
REM Step 3: Copy to modification table
REM ============================
echo [Step 3/5] Creating modification table...
copy /Y "%SCRIPTDIR%output\modification_base.tsv" "%SCRIPTDIR%output\modification_table.tsv" >nul
echo [SUCCESS] Created output\modification_table.tsv
echo.

REM ============================
REM Step 4: Wait for user edit
REM ============================
echo ========================================
echo IMPORTANT: Edit TSV File
echo ========================================
echo.
echo Please edit the following file in Excel or text editor:
echo   %SCRIPTDIR%output\modification_table.tsv
echo.
echo Fill in the 'new_name' column for identifiers you want to rename.
echo Leave 'new_name' empty for identifiers you want to keep unchanged.
echo.
echo [SAFETY WARNING] Check the 'collision_type' column:
echo   * shorthand : DO NOT RENAME (Will break object structure)
echo   * export    : CAUTION (Used by external files)
echo   * global    : CAUTION (Visible to other scripts)
echo   * none      : SAFE to rename
echo.
echo ========================================
echo.

:WAIT_FOR_YES
set /p CONTINUE="Type 'yes' and press Enter to continue (or press Enter to cancel): "

if /i "%CONTINUE%"=="yes" (
    echo [INFO] Continuing with identifier renaming...
    echo.
) else (
    echo [INFO] Operation cancelled by user.
    cmd /k
    exit /b 0
)

REM ============================
REM Step 5: Rename identifiers
REM ============================
echo [Step 4/5] Renaming identifiers based on TSV...
call "%SCRIPTDIR%rename_identifiers.bat" ^
    "%SCRIPTDIR%output\unified.js" ^
    "%SCRIPTDIR%output\modification_table.tsv" ^
    "%SCRIPTDIR%output\transformed.js"

if errorlevel 1 (
    echo [ERROR] Failed to rename identifiers
    echo Please check the log file: output\rename_identifiers.log
    cmd /k
    exit /b 1
)
echo [SUCCESS] Identifiers renamed, output saved to output\transformed.js
echo.

REM ============================
REM Step 6: Reintegrate to HTML
REM ============================
echo [Step 5/5] Reintegrating JavaScript into HTML...
call "%SCRIPTDIR%reintegrate_to_html.bat" ^
    "%SCRIPTDIR%output\transformed.js" ^
    "%HTML_FILE%" ^
    "%SCRIPTDIR%output\result.html"

if errorlevel 1 (
    echo [ERROR] Failed to reintegrate JavaScript
    cmd /k
    exit /b 1
)
echo [SUCCESS] Result saved to output\result.html
echo.

REM ============================
REM Summary
REM ============================
echo ========================================
echo Renaming Complete!
echo ========================================
echo.
echo Input:  %HTML_FILE%
echo Output: %SCRIPTDIR%output\result.html
echo.
echo Intermediate files (for debugging):
echo   - output\unified.js          (extracted JavaScript)
echo   - output\modification_base.tsv   (original identifiers)
echo   - output\modification_table.tsv  (edited identifiers)
echo   - output\transformed.js      (renamed JavaScript)
echo   - output\rename_identifiers.log  (detailed log)
echo.
echo ========================================
cmd /k
