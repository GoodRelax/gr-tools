@echo off
setlocal
cd /d "%~dp0"

:: ============================================================================
:: Script Name: gen_test_data.bat
:: Description: Generates dummy test files for cat_files.bat
::              - Uses subroutine redirection to prevent syntax errors.
::              - Strictly ASCII source code.
::              - Creates Japanese filenames and content safely.
:: ============================================================================

set "TEST_ROOT=test_data"
set "PS_SCRIPT=%TEMP%\gen_files_%RANDOM%.ps1"

:: --- 1. Clean and Setup Directories ---
echo [INFO] Cleaning up previous test data...
if exist "%TEST_ROOT%" rmdir /s /q "%TEST_ROOT%"
mkdir "%TEST_ROOT%"

:: --- 2. Generate PowerShell Script ---
echo [INFO] Generating PowerShell script to: %PS_SCRIPT%

:: We call the label :WritePS and redirect ALL output to the file at once.
:: This avoids syntax errors with parentheses inside the code.
call :WritePS > "%PS_SCRIPT%"

:: --- 3. Execute PowerShell Script ---
echo [INFO] Executing file generation script...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PowerShell execution failed.
    echo [DEBUG] Script content was:
    type "%PS_SCRIPT%"
    pause
    exit /b 1
)

:: Clean up temp script
del "%PS_SCRIPT%"

:: --- 4. Instructions ---
echo.
echo ============================================================================
echo  GENERATION COMPLETE
echo ============================================================================
echo.
echo  Target List: %TEST_ROOT%\target_list.txt
echo.
echo  [Command to Test]
echo  cat_files.bat -i %TEST_ROOT%\target_list.txt -o %TEST_ROOT%\merged_output.txt -lf
echo.
pause
goto :EOF


:: ============================================================================
:: Subroutine: Write PowerShell Content
:: (No parentheses escaping needed here because it's not in a block)
:: ============================================================================
:WritePS
echo $ErrorActionPreference = "Stop"
echo.
echo # --- Define Japanese Strings via Unicode Hex ---
echo # "Nihongo" (Japanese)
echo $strJP = [string][char]0x65e5 + [string][char]0x672c + [string][char]0x8a9e
echo # "Tesuto" (Test)
echo $strTest = [string][char]0x30c6 + [string][char]0x30b9 + [string][char]0x30c8
echo.
echo # --- Define Encodings ---
echo $encSJIS = [System.Text.Encoding]::GetEncoding(932)
echo $encUTF8 = [System.Text.UTF8Encoding]$false
echo.
echo # --- File 1: Shift-JIS / CRLF / Japanese Filename ---
echo # Filename: test_data/sjis_file_JP.txt
echo $fname1 = "sjis_file_" + $strJP + ".txt"
echo $path1 = Join-Path "%TEST_ROOT%" $fname1
echo $content1 = "Encoding: Shift-JIS" + "`r`n" + "Content: " + $strJP + "`r`n" + "End."
echo [System.IO.File]::WriteAllText($path1, $content1, $encSJIS)
echo Write-Host "Created: $path1"
echo.
echo # --- File 2: UTF-8 / LF / Japanese Content ---
echo # Filename: test_data/utf8_file_test.txt
echo $path2 = Join-Path "%TEST_ROOT%" "utf8_file_test.txt"
echo $content2 = "Encoding: UTF-8" + "`n" + "Content: " + $strTest + "`n" + "LineEnd: LF"
echo [System.IO.File]::WriteAllText($path2, $content2, $encUTF8)
echo Write-Host "Created: $path2"
echo.
echo # --- Generate List File ---
echo # We generate the list file with Shift-JIS encoding so the Batch file can read it.
echo $listPath = Join-Path "%TEST_ROOT%" "target_list.txt"
echo $listContent = $path1 + "`r`n" + $path2
echo [System.IO.File]::WriteAllText($listPath, $listContent, $encSJIS)
echo Write-Host "Created List: $listPath"
exit /b
