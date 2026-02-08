@echo off
setlocal
cd /d "%~dp0"

:: ============================================================================
:: Script Name: gen_test_data.bat (Fixed Version)
:: Description: Generates EVIL test data for cat_files.bat
::              - Strictly ASCII source code.
::              - Fixes DirectoryNotFoundException by ensuring correct path assembly.
::              - Includes JAPANESE characters (filenames & content).
::              - Includes SPACES in directory and file names.
::              - Includes DEEP nesting and MIXED encodings.
:: ============================================================================

set "TEST_ROOT=test_data"
set "PS_SCRIPT=%TEMP%\gen_evil_%RANDOM%.ps1"

:: --- 1. Clean and Setup Directories ---
echo [INFO] Cleaning up previous test data...
if exist "%TEST_ROOT%" rmdir /s /q "%TEST_ROOT%"
mkdir "%TEST_ROOT%"

:: --- 2. Generate PowerShell Script ---
echo [INFO] Generating PowerShell script to: %PS_SCRIPT%
call :WritePS > "%PS_SCRIPT%"

:: --- 3. Execute PowerShell Script ---
echo [INFO] Executing file generation script...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PowerShell execution failed.
    echo [DEBUG] Script content was:
    type "%PS_SCRIPT%"
    cmd /k
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
echo  cat_files.bat -i "%TEST_ROOT%\target_list.txt" -o "%TEST_ROOT%\merged result.txt" -lf
echo.
cmd /k
goto :EOF


:: ============================================================================
:: Subroutine: Write PowerShell Content
:: ============================================================================
:WritePS
echo $ErrorActionPreference = "Stop"
echo.
echo # --- Define Strings via Unicode Hex ---
echo # "Nihongo" (Japanese)
echo $strJP = [string][char]0x65e5 + [string][char]0x672c + [string][char]0x8a9e
echo.
echo # --- Define Encodings ---
echo $encSJIS = [System.Text.Encoding]::GetEncoding(932)
echo $encUTF8 = [System.Text.UTF8Encoding]$false
echo.
echo # --- Define Directory Paths (Construct variables first to avoid array errors) ---
echo $dirRoot = "%TEST_ROOT%"
echo $dirProg = Join-Path $dirRoot "Program Data"
echo $dirApp  = Join-Path $dirProg "My App"
echo $dirUser = Join-Path $dirRoot "User Files"
echo # "User Files/Documents [Japanese]" - Note the space handling
echo $dirDocs = Join-Path $dirUser ("Documents " + $strJP)
echo.
echo # --- Create Directories ---
echo # We use -Force, so parent directories are created automatically
echo $targetDirs = @($dirApp, $dirDocs)
echo.
echo foreach ($d in $targetDirs) {
echo     New-Item -ItemType Directory -Path $d -Force ^| Out-Null
echo     Write-Host "Created Dir: $d"
echo }
echo.
echo # --- Create Files ---
echo.
echo # 1. File with SPACES (Shift-JIS)
echo $f1Name = "Config File.ini"
echo $p1 = Join-Path $dirApp $f1Name
echo $c1 = "[Settings]" + "`r`n" + "Path=C:\Program Files\App" + "`r`n" + "Note=" + $strJP
echo [System.IO.File]::WriteAllText($p1, $c1, $encSJIS)
echo Write-Host "Created: $p1"
echo.
echo # 2. File with SPACES and Japanese Name (UTF-8)
echo $f2Name = "Read Me " + $strJP + ".txt"
echo $p2 = Join-Path $dirDocs $f2Name
echo $c2 = "This is a readme." + "`n" + "File Name contains spaces."
echo [System.IO.File]::WriteAllText($p2, $c2, $encUTF8)
echo Write-Host "Created: $p2"
echo.
echo # 3. Deeply Nested Space File (UTF-8)
echo $p3 = Join-Path $dirUser "secret log.log"
echo $c3 = "Secret log content."
echo [System.IO.File]::WriteAllText($p3, $c3, $encUTF8)
echo Write-Host "Created: $p3"
echo.
echo # --- Generate Target List ---
echo # The list itself will contain paths with spaces.
echo $listPath = Join-Path $dirRoot "target_list.txt"
echo $listC = ""
echo # Add patterns using the generated root path
echo $listC += (Join-Path $dirProg "**\*.ini") + "`r`n"
echo $listC += (Join-Path $dirUser "**\*.txt") + "`r`n"
echo $listC += $p3
echo [System.IO.File]::WriteAllText($listPath, $listC, $encSJIS)
echo Write-Host "Created List: $listPath"
exit /b
