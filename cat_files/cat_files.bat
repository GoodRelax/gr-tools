@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Tool Name: cat_files.bat
:: Description: Concatenates files listed in a target list with meta tags.
::              Supports recursive search and wildcard expansion.
::              Optionally converts output to UTF-8 (No BOM) and LF line endings.
::
:: Usage: cat_files.bat -i <target_list> [-o <output_file>] [-lf]
:: ============================================================================

:: --- 1. Argument Parsing ---

set "TARGET_LIST="
set "OUTPUT_FILE="
set "MODE_LF=0"

:ParseArgs
if "%~1"=="" goto :CheckArgs
if /i "%~1"=="-i" (
    set "TARGET_LIST=%~2"
    shift
    shift
    goto :ParseArgs
)
if /i "%~1"=="-o" (
    set "OUTPUT_FILE=%~2"
    shift
    shift
    goto :ParseArgs
)
if /i "%~1"=="-lf" (
    set "MODE_LF=1"
    shift
    goto :ParseArgs
)
shift
goto :ParseArgs

:CheckArgs
:: Display Help if required arguments are missing
if "%TARGET_LIST%"=="" goto :Usage
if not exist "%TARGET_LIST%" (
    echo Error: Target list file not found: %TARGET_LIST%
    goto :Usage
)

:: --- 2. Setup Output File ---

:: Set default output filename if not provided
if not defined OUTPUT_FILE (
    for %%F in ("%TARGET_LIST%") do set "LIST_NAME=%%~nF"
    set "OUTPUT_FILE=cat_!LIST_NAME!.txt"
)

:: Create empty output file to resolve absolute path
type nul > "%OUTPUT_FILE%"
for %%F in ("%OUTPUT_FILE%") do set "ABS_OUTPUT_FILE=%%~fF"

echo Input List : %TARGET_LIST%
echo Output File: %OUTPUT_FILE%

:: Escape parentheses in echo to avoid breaking the IF block
if "%MODE_LF%"=="1" (
    echo Mode       : Convert to UTF-8 ^(No BOM^) and LF
) else (
    echo Mode       : Standard ^(Binary/System Default^)
)
echo Processing...

:: --- 3. Execution Branching ---

if "%MODE_LF%"=="1" goto :ExecutePS
goto :ExecuteBat

:: ============================================================================
:: MODE A: Standard Batch Processing (Fast, preserves original encoding/CRLF)
:: ============================================================================
:ExecuteBat
:: Clear output file
type nul > "%OUTPUT_FILE%"

:: Loop through each line in the target list
for /f "usebackq delims=" %%L in ("%TARGET_LIST%") do (
    call :ProcessPatternBat "%%L"
)
goto :End

:ProcessPatternBat
set "SEARCH_PATTERN=%~1"
:: Find files recursively (/s), files only (/a-d), bare format (/b)
for /f "delims=" %%F in ('dir /b /s /a-d "%SEARCH_PATTERN%" 2^>nul') do (
    call :AppendFileBat "%%F"
)
exit /b

:AppendFileBat
set "CURRENT_FILE=%~f1"
:: Skip if the file is the output file itself
if /i "%CURRENT_FILE%" == "%ABS_OUTPUT_FILE%" exit /b

echo Reading: %CURRENT_FILE%

:: Write Meta Tag
(
    echo `````````cat_files_meta_data
    echo %CURRENT_FILE%
    echo `````````
) >> "%OUTPUT_FILE%"

:: Write Content
type "%CURRENT_FILE%" >> "%OUTPUT_FILE%"
echo.>> "%OUTPUT_FILE%"
exit /b

:: ============================================================================
:: MODE B: PowerShell Processing (UTF-8 No BOM, LF, Auto-detect Input)
:: ============================================================================
:ExecutePS
:: Set temporary script path to CURRENT DIRECTORY for easier debugging
set "PS_SCRIPT=cat_files_temp.ps1"

:: Generate PowerShell script by calling a subroutine
:: This avoids syntax errors caused by parenthesis/quotes conflict in blocks
call :GeneratePS > "%PS_SCRIPT%"

:: Execute the temporary PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -InputListPath "%TARGET_LIST%" -OutputPath "%ABS_OUTPUT_FILE%"

:: Cleanup (Delete the temp file)
:: If you want to inspect the PS1 file, comment out the next line
del "%PS_SCRIPT%"
goto :End

:: ----------------------------------------------------------------------------
:: Subroutine: Generate PowerShell Content
:: ----------------------------------------------------------------------------
:GeneratePS
echo param(
echo     [string]$InputListPath,
echo     [string]$OutputPath
echo )
echo.
echo $ErrorActionPreference = "Stop"
echo.
echo # Define Encodings
echo # Output: UTF-8 No BOM
echo $EncUTF8NoBOM = New-Object System.Text.UTF8Encoding($false)
echo # Detection: UTF-8 Strict (throws error on invalid bytes)
echo $EncUTF8Strict = New-Object System.Text.UTF8Encoding($false, $true)
echo # Fallback: Shift-JIS (CP932)
echo $EncSJIS = [System.Text.Encoding]::GetEncoding(932)
echo.
echo # Initialize Output File
echo [System.IO.File]::WriteAllText($OutputPath, "", $EncUTF8NoBOM)
echo.
echo # Read Target List
echo $patterns = Get-Content -Path $InputListPath
echo.
echo foreach ($pattern in $patterns) {
echo     if ([string]::IsNullOrWhiteSpace($pattern)) { continue }
echo     # Resolve Wildcards recursively
echo     try {
echo         $files = Get-ChildItem -Path $pattern -Recurse -File -ErrorAction SilentlyContinue
echo     } catch { continue }
echo.
echo     foreach ($file in $files) {
echo         $fullPath = $file.FullName
echo         # Skip if input is same as output
echo         if ($fullPath -eq $OutputPath) { continue }
echo         Write-Host "Reading: $fullPath"
echo.
echo         # --- Auto-Detect Encoding Logic ---
echo         $content = $null
echo         try {
echo             # Try strict UTF-8 first
echo             $content = [System.IO.File]::ReadAllText($fullPath, $EncUTF8Strict)
echo         } catch {
echo             # If fails, assume Shift-JIS
echo             $content = [System.IO.File]::ReadAllText($fullPath, $EncSJIS)
echo         }
echo.
echo         # --- Normalize Line Endings to LF ---
echo         $content = $content -replace "`r`n", "`n"
echo         $content = $content -replace "`r", "`n"
echo.
echo         # --- Create Meta Tag ---
echo         # FIX: Use single quotes for backticks to prevent PS escape issues
echo         $metaTag  = '`````````cat_files_meta_data' + "`n"
echo         $metaTag += "$fullPath`n"
echo         $metaTag += '`````````'
echo.
echo         # --- Append to Output ---
echo         [System.IO.File]::AppendAllText($OutputPath, $metaTag + "`n", $EncUTF8NoBOM)
echo         [System.IO.File]::AppendAllText($OutputPath, $content + "`n", $EncUTF8NoBOM)
echo     }
echo }
exit /b

:: ============================================================================
:: Usage / End
:: ============================================================================
:Usage
echo.
echo Usage: cat_files.bat -i ^<target_list^> [-o ^<output_file^>] [-lf]
echo.
echo Options:
echo   -i   : Path to the text file containing the list of files/patterns.
echo   -o   : (Optional) Path to the output file.
echo          Default: cat_^<target_list^>.txt
echo   -lf  : (Optional) Convert output to UTF-8 (No BOM) and LF line endings.
echo          Attempts to auto-detect input encoding (UTF-8 Strict or Shift-JIS).
echo.
echo Example:
echo   cat_files.bat -i list.txt
echo   cat_files.bat -i list.txt -o merged.txt -lf
echo.
exit /b 1

:End
echo Done.
exit /b 0
