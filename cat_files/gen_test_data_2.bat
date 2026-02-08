@echo off
setlocal
cd /d "%~dp0"

:: ============================================================================
:: Script Name: gen_test_data.bat
:: Description: Generates nested test data for cat_files.bat
::              - Strictly ASCII source code.
::              - Creates deep directory structures.
::              - Scatters files (SJIS/UTF-8) with Japanese names.
:: ============================================================================

set "TEST_ROOT=test_data"
set "PS_SCRIPT=%TEMP%\gen_nested_%RANDOM%.ps1"

:: --- 1. Clean and Setup Directories ---
echo [INFO] Cleaning up previous test data...
if exist "%TEST_ROOT%" rmdir /s /q "%TEST_ROOT%"
mkdir "%TEST_ROOT%"

:: --- 2. Generate PowerShell Script ---
echo [INFO] Generating PowerShell script to: %PS_SCRIPT%

:: Call the subroutine to write the PS script safely
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
echo  Created nested structure in '%TEST_ROOT%'.
echo  Target List: %TEST_ROOT%\target_list.txt
echo.
echo  [Command to Test]
echo  cat_files.bat -i %TEST_ROOT%\target_list.txt -o %TEST_ROOT%\merged_nested.txt -lf
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
echo # "Kaisou" (Hierarchy/Layer)
echo $strLayer = [string][char]0x968e + [string][char]0x5c64
echo.
echo # --- Define Encodings ---
echo $encSJIS = [System.Text.Encoding]::GetEncoding(932)
echo $encUTF8 = [System.Text.UTF8Encoding]$false
echo.
echo # --- Create Directories ---
echo $dirs = @(
echo     "src",
echo     "src/components",
echo     "src/components/legacy",
echo     "logs/2024/04"
echo )
echo foreach ($d in $dirs) {
echo     $p = Join-Path "%TEST_ROOT%" $d
echo     New-Item -ItemType Directory -Path $p -Force ^| Out-Null
echo     Write-Host "Created Dir: $p"
echo }
echo.
echo # --- Create Base Files ---
echo.
echo # 1. Root: Shift-JIS / CRLF / Japanese Name
echo $f1Name = "root_" + $strJP + ".txt"
echo $p1 = Join-Path "%TEST_ROOT%" $f1Name
echo $c1 = "Type: Root File" + "`r`n" + "Enc: SJIS" + "`r`n" + "Text: " + $strJP
echo [System.IO.File]::WriteAllText($p1, $c1, $encSJIS)
echo.
echo # 2. Deep Nested: UTF-8 / LF
echo $f2Name = "deep_" + $strLayer + ".txt"
echo $p2 = Join-Path "%TEST_ROOT%" "src/components/legacy/$f2Name"
echo $c2 = "Type: Deep File" + "`n" + "Enc: UTF-8" + "`n" + "Text: " + $strLayer
echo [System.IO.File]::WriteAllText($p2, $c2, $encUTF8)
echo.
echo # 3. Mid Level: Shift-JIS (Copy of Root)
echo $p3 = Join-Path "%TEST_ROOT%" "src/mid_sjis.txt"
echo Copy-Item -Path $p1 -Destination $p3
echo.
echo # 4. Log Dir: UTF-8 Log file
echo $p4 = Join-Path "%TEST_ROOT%" "logs/2024/04/app.log"
echo $c4 = "TIMESTAMP [INFO] App started." + "`n" + "Text: " + $strJP
echo [System.IO.File]::WriteAllText($p4, $c4, $encUTF8)
echo.
echo # --- Generate Target List ---
echo # We use wildcards to test recursive search capabilities
echo $listPath = Join-Path "%TEST_ROOT%" "target_list.txt"
echo $listC = ""
echo $listC += "%TEST_ROOT%\*.txt" + "`r`n" 
echo $listC += "%TEST_ROOT%\src\*.txt" + "`r`n"
echo $listC += "%TEST_ROOT%\logs\**\*.log" 
echo [System.IO.File]::WriteAllText($listPath, $listC, $encSJIS)
echo Write-Host "Created List: $listPath"
exit /b
