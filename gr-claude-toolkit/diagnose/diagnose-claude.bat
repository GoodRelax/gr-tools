@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ============================================================
REM  Claude Ecosystem Diagnostic Tool v1.0
REM  All checks: C1-C11
REM  ASCII only. Read-only. No admin required.
REM ============================================================

REM --- Setup ---
set "SCRIPT_DIR=%~dp0"
set "SUMMARY_FILE=%SCRIPT_DIR%diagnosis-summary.txt"
set "JSON_FILE=%SCRIPT_DIR%diagnosis-for-claude.json"
set "TIMESTAMP="
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set "TIMESTAMP=%%a"
set "TIMESTAMP_ISO="
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz'"') do set "TIMESTAMP_ISO=%%a"
set "MACHINE_NAME=%COMPUTERNAME%"
set "USER_NAME=%USERNAME%"

set /a OK_COUNT=0
set /a WARN_COUNT=0
set /a ERR_COUNT=0

echo =============================================================
echo   Claude Ecosystem Diagnostic Tool v1.0
echo =============================================================
echo.

REM ============================================================
REM  C1: Desktop MSIX Installation
REM ============================================================
set "C1_STATUS=MISSING"
set "C1_VERSION="
set "C1_PACKAGE="
set "C1_PUBLISHER="
set "C1_LOCATION="
set "C1_WARN="

set /p="Checking [C1] Desktop Installation...    " <nul

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "@(Get-AppxPackage *Claude* 2>$null).Count"') do set "C1_PKG_COUNT=%%a"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-AppxPackage *Claude* 2>$null).Version"') do set "C1_VERSION=%%a"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-AppxPackage *Claude* 2>$null).PackageFamilyName"') do set "C1_PACKAGE=%%a"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-AppxPackage *Claude* 2>$null).Publisher"') do set "C1_PUBLISHER=%%a"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$p=(Get-AppxPackage *Claude* 2>$null).Publisher; $p -replace [char]34,([char]92+[char]34)"') do set "C1_PUB_J=%%a"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-AppxPackage *Claude* 2>$null).InstallLocation"') do set "C1_LOCATION=%%a"

if not defined C1_VERSION (
    set "C1_STATUS=MISSING"
    set /a ERR_COUNT+=1
    goto :C1_DONE
)
set "C1_STATUS=OK"
set /a OK_COUNT+=1

if defined C1_PKG_COUNT if !C1_PKG_COUNT! GTR 1 (
    set "C1_STATUS=WARNING"
    set "C1_WARN=Multiple Claude packages found"
    set /a OK_COUNT-=1
    set /a WARN_COUNT+=1
)

:C1_DONE
if "!C1_STATUS!"=="OK" echo OK [v!C1_VERSION!]
if "!C1_STATUS!"=="WARNING" echo WARNING [v!C1_VERSION!]
if "!C1_STATUS!"=="MISSING" echo MISSING

REM ============================================================
REM  C2: CLI Installation
REM ============================================================
set "C2_STATUS=MISSING"
set "C2_VERSION="
set "C2_PATH="
set "C2_FOUND=0"
set "C2_WARN="
set "C2_AGENT_VERSIONS="
set "C2_AGENT_WARN="
set "C2_AGENT_COUNT=0"

set /p="Checking [C2] CLI Installation...        " <nul

for /f "tokens=*" %%p in ('where claude 2^>nul') do (
    set /a C2_FOUND+=1
    if !C2_FOUND! equ 1 set "C2_PATH=%%p"
)

if !C2_FOUND! equ 0 (
    set "C2_STATUS=MISSING"
    set /a ERR_COUNT+=1
    goto :C2_DONE
)

for /f "tokens=1" %%v in ('claude --version 2^>nul') do (
    if not defined C2_VERSION set "C2_VERSION=%%v"
)

set "C2_STATUS=OK"
set /a OK_COUNT+=1

if !C2_FOUND! GTR 1 (
    set "C2_STATUS=WARNING"
    set "C2_WARN=Multiple claude in PATH: !C2_FOUND! locations"
    set /a OK_COUNT-=1
    set /a WARN_COUNT+=1
)

REM Check Desktop Agent Mode binaries
set "C2_AGENT_DIR=%APPDATA%\Claude\claude-code"
if exist "!C2_AGENT_DIR!" (
    for /d %%d in ("!C2_AGENT_DIR!\*") do (
        if exist "%%d\claude.exe" (
            set /a C2_AGENT_COUNT+=1
            set "C2_AGENT_VERSIONS=!C2_AGENT_VERSIONS! %%~nxd"
        )
    )
)
if !C2_AGENT_COUNT! GTR 1 (
    if "!C2_STATUS!"=="OK" (
        set "C2_STATUS=WARNING"
        set /a OK_COUNT-=1
        set /a WARN_COUNT+=1
    )
    set "C2_AGENT_WARN=Old Agent binaries:!C2_AGENT_VERSIONS!"
)

:C2_DONE
if "!C2_STATUS!"=="OK" echo OK [v!C2_VERSION!]
if "!C2_STATUS!"=="WARNING" echo WARNING [v!C2_VERSION!]
if "!C2_STATUS!"=="MISSING" echo MISSING

REM ============================================================
REM  C3: VS Code Extension
REM ============================================================
set "C3_STATUS=SKIP"
set "C3_EXT_FOUND=false"
set "C3_WARN="
set "C3_EMBEDDED_VER="
set "C3_FOLDER="

set /p="Checking [C3] VS Code Extension...       " <nul

where code >nul 2>&1
if !errorlevel! neq 0 (
    set "C3_STATUS=SKIP"
    set /a OK_COUNT+=1
    goto :C3_DONE
)

code --list-extensions 2>nul | findstr /i "anthropic.claude-code" >nul 2>&1
if !errorlevel! equ 0 (
    set "C3_STATUS=OK"
    set "C3_EXT_FOUND=true"
    set /a OK_COUNT+=1
) else (
    set "C3_STATUS=MISSING"
    set /a ERR_COUNT+=1
    goto :C3_DONE
)

set "C3_EXT_BASE=%USERPROFILE%\.vscode\extensions"
for /d %%d in ("!C3_EXT_BASE!\anthropic.claude-code-*") do (
    if exist "%%d\resources\native-binary\claude.exe" set "C3_FOLDER=%%~nxd"
)
if defined C3_FOLDER (
    for /f "tokens=*" %%v in ('powershell -NoProfile -Command "if('!C3_FOLDER!' -match 'claude-code-(\d+\.\d+\.\d+)'){$matches[1]}"') do set "C3_EMBEDDED_VER=%%v"
)

if defined C3_EMBEDDED_VER if defined C2_VERSION (
    if not "!C3_EMBEDDED_VER!"=="!C2_VERSION!" (
        set "C3_WARN=Version mismatch: CLI=!C2_VERSION!, VSCode=!C3_EMBEDDED_VER!"
        if "!C3_STATUS!"=="OK" (
            set "C3_STATUS=WARNING"
            set /a OK_COUNT-=1
            set /a WARN_COUNT+=1
        )
    )
)

:C3_DONE
if "!C3_STATUS!"=="OK" if defined C3_EMBEDDED_VER echo OK [embedded: v!C3_EMBEDDED_VER!]
if "!C3_STATUS!"=="OK" if not defined C3_EMBEDDED_VER echo OK
if "!C3_STATUS!"=="WARNING" echo WARNING [!C3_WARN!]
if "!C3_STATUS!"=="SKIP" echo SKIP [VS Code not found]
if "!C3_STATUS!"=="MISSING" echo MISSING [not installed]

REM ============================================================
REM  C4: Credentials
REM ============================================================
set "C4_STATUS=MISSING"
set "C4_EXISTS=false"
set "C4_SIZE=0"
set "C4_MODIFIED="
set "CRED_FILE=%USERPROFILE%\.claude\.credentials.json"

set /p="Checking [C4] Credentials...             " <nul

if not exist "%CRED_FILE%" (
    set "C4_STATUS=MISSING"
    set /a ERR_COUNT+=1
    goto :C4_DONE
)
set "C4_EXISTS=true"
for %%F in ("%CRED_FILE%") do (
    set "C4_SIZE=%%~zF"
    set "C4_MODIFIED=%%~tF"
)
if !C4_SIZE! GTR 0 (
    set "C4_STATUS=OK"
    set /a OK_COUNT+=1
) else (
    set "C4_STATUS=WARNING"
    set /a WARN_COUNT+=1
)

:C4_DONE
if "!C4_STATUS!"=="OK" echo OK
if "!C4_STATUS!"=="WARNING" echo WARNING [empty file]
if "!C4_STATUS!"=="MISSING" echo MISSING

REM ============================================================
REM  C5: Global settings.json
REM  PowerShell commands avoid pipe (|) to prevent batch parsing.
REM  Use ConvertFrom-Json(Get-Content ...) instead of ... | ConvertFrom-Json
REM ============================================================
set "C5_STATUS=MISSING"
set "C5_PATH=%USERPROFILE%\.claude\settings.json"
set "C5_ALLOW_COUNT=0"
set "C5_DENY_COUNT=0"
set "C5_ADDL_DIRS=0"
set "C5_WARN_HIGH=false"
set "C5_WARN_ONESHOT="
set "C5_WARN_PROJSPEC="

set /p="Checking [C5] Global settings.json...    " <nul

if not exist "!C5_PATH!" (
    set "C5_STATUS=MISSING"
    set /a ERR_COUNT+=1
    goto :C5_DONE
)
set "C5_STATUS=OK"
set /a OK_COUNT+=1

REM Parse counts (no pipe needed: use ConvertFrom-Json with param)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText('!C5_PATH!')); $a=@($j.permissions.allow).Count; $d=@($j.permissions.deny).Count; $ad=@($j.additionalDirectories).Count; Write-Output \"$a~$d~$ad\""') do (
    for /f "tokens=1-3 delims=~" %%x in ("%%a") do (
        set "C5_ALLOW_COUNT=%%x"
        set "C5_DENY_COUNT=%%y"
        set "C5_ADDL_DIRS=%%z"
    )
)

if !C5_ALLOW_COUNT! GEQ 15 (
    set "C5_WARN_HIGH=true"
    if "!C5_STATUS!"=="OK" (
        set "C5_STATUS=WARNING"
        set /a OK_COUNT-=1
        set /a WARN_COUNT+=1
    )
)

REM Check for oneshot commands
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText('!C5_PATH!')); $cmds=@($j.permissions.allow.Where({$_ -match 'Bash\(.*(mkdir|cp |mv |rm |touch)'})); if($cmds.Count -gt 0){$cmds -join ', '}"') do (
    set "C5_WARN_ONESHOT=%%a"
    if "!C5_STATUS!"=="OK" (
        set "C5_STATUS=WARNING"
        set /a OK_COUNT-=1
        set /a WARN_COUNT+=1
    )
)

REM Check for project-specific entries
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText('!C5_PATH!')); $ps=@($j.permissions.allow.Where({$_ -match 'Read\(//c/' -or $_ -match 'WebFetch\(https://'})); if($ps.Count -gt 0){Write-Output $ps.Count}"') do (
    set "C5_WARN_PROJSPEC=%%a project-specific entries found"
    if "!C5_STATUS!"=="OK" (
        set "C5_STATUS=WARNING"
        set /a OK_COUNT-=1
        set /a WARN_COUNT+=1
    )
)

:C5_DONE
if "!C5_STATUS!"=="OK" echo OK [!C5_ALLOW_COUNT! allow entries]
if "!C5_STATUS!"=="WARNING" echo WARNING [!C5_ALLOW_COUNT! allow entries]
if "!C5_STATUS!"=="MISSING" echo MISSING

REM ============================================================
REM  C6: Project settings.json
REM ============================================================
set "C6_STATUS=OK"
set "C6_PROJ_COUNT=0"
set "C6_PROJ_LIST="
set /a OK_COUNT+=1

set /p="Checking [C6] Project settings.json...   " <nul

set "C6_SCAN_DIRS=%USERPROFILE%\OneDrive\Documents\GitHub %USERPROFILE%\Documents\GitHub %USERPROFILE%\source\repos %USERPROFILE%\projects"
set "C6_DONE_DIRS="

REM Always scan current directory first
if exist "!CD!" (
    set "C6_DONE_DIRS=!CD!;"
    for /d %%P in ("!CD!\*") do (
        if exist "%%P\.claude\settings.json" (
            set /a C6_PROJ_COUNT+=1
            set "C6_TEMP_PATH=%%P\.claude\settings.json"
            for /f "tokens=*" %%a in ('powershell -NoProfile -Command "try{@(ConvertFrom-Json([IO.File]::ReadAllText($env:C6_TEMP_PATH)).permissions.allow).Count}catch{0}"') do (
                set "C6_PROJ_LIST=!C6_PROJ_LIST!%%P [%%a entries]; "
            )
        )
    )
)

REM Scan additional directories, skip if same as current dir
for %%D in (!C6_SCAN_DIRS!) do (
    if exist "%%D" (
        echo !C6_DONE_DIRS! | findstr /i /c:"%%D;" >nul 2>&1
        if !errorlevel! neq 0 (
            set "C6_DONE_DIRS=!C6_DONE_DIRS!%%D;"
            for /d %%P in ("%%D\*") do (
                if exist "%%P\.claude\settings.json" (
                    set /a C6_PROJ_COUNT+=1
                    set "C6_TEMP_PATH=%%P\.claude\settings.json"
                    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "try{@(ConvertFrom-Json([IO.File]::ReadAllText($env:C6_TEMP_PATH)).permissions.allow).Count}catch{0}"') do (
                        set "C6_PROJ_LIST=!C6_PROJ_LIST!%%P [%%a entries]; "
                    )
                )
            )
        )
    )
)

echo OK [!C6_PROJ_COUNT! projects found]

REM ============================================================
REM  C7: Desktop Config
REM ============================================================
set "C7_STATUS=MISSING"
set "C7_PATH=%APPDATA%\Claude\claude_desktop_config.json"
set "C7_MCP_COUNT=0"
set "C7_MCP_NAMES="

set /p="Checking [C7] Desktop Config...          " <nul

if not exist "!C7_PATH!" (
    set "C7_STATUS=OK"
    set /a OK_COUNT+=1
    goto :C7_DONE
)

set "C7_STATUS=OK"
set /a OK_COUNT+=1

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText($env:C7_PATH)); if($j.mcpServers){$n=$j.mcpServers.PSObject.Properties.Name; $c=$n.Count; $s=$n -join ','; Write-Output ($c.ToString()+'~'+$s)}else{Write-Output '0~'}"') do (
    for /f "tokens=1,* delims=~" %%x in ("%%a") do (
        set "C7_MCP_COUNT=%%x"
        set "C7_MCP_NAMES=%%y"
    )
)

:C7_DONE
if "!C7_STATUS!"=="OK" echo OK [!C7_MCP_COUNT! MCP servers]

REM ============================================================
REM  C8: PATH Check
REM ============================================================
set "C8_STATUS=OK"
set "C8_NPM_IN_PATH=false"
set "C8_NPM_PATH="
set "C8_NODE_IN_PATH=false"
set "C8_NODE_PATH="
set "C8_WARN1="
set "C8_WARN2="

set /p="Checking [C8] PATH Check...              " <nul

echo !PATH! | findstr /i /c:"AppData\Roaming\npm" >nul 2>&1
if !errorlevel! equ 0 (
    set "C8_NPM_IN_PATH=true"
    set "C8_NPM_PATH=%APPDATA%\npm"
) else (
    set "C8_WARN1=npm global path not in PATH"
)

echo !PATH! | findstr /i /c:"nodejs" >nul 2>&1
if !errorlevel! equ 0 (
    set "C8_NODE_IN_PATH=true"
    for /f "tokens=*" %%p in ('where node 2^>nul') do (
        if not defined C8_NODE_PATH set "C8_NODE_PATH=%%~dpp"
    )
    if defined C8_NODE_PATH set "C8_NODE_PATH=!C8_NODE_PATH:~0,-1!"
) else (
    set "C8_WARN2=Node.js not in PATH"
)

if defined C8_WARN1 set "C8_STATUS=WARNING"
if defined C8_WARN2 set "C8_STATUS=WARNING"

if "!C8_STATUS!"=="OK" (
    set /a OK_COUNT+=1
    echo OK
) else (
    set /a WARN_COUNT+=1
    echo WARNING
)

REM ============================================================
REM  C9: claude.exe Binary Scan
REM ============================================================
set "C9_STATUS=OK"
set "C9_TOTAL=0"
set "C9_NPM=0"
set "C9_AGENT=0"
set "C9_VSCODE=0"
set "C9_UNKNOWN=0"
set "C9_WARN="

set /p="Checking [C9] Binary Scan...             " <nul

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "foreach($f in (Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter claude.exe -ErrorAction SilentlyContinue -Force)){$f.FullName}"') do (
    set /a C9_TOTAL+=1
    set "C9_CAT=unknown"

    echo "%%a" | findstr /i /c:"AppData\Roaming\npm" >nul 2>&1
    if !errorlevel! equ 0 (
        set "C9_CAT=npm_cli"
        set /a C9_NPM+=1
    )
    echo "%%a" | findstr /i /c:"AppData\Roaming\Claude\claude-code" >nul 2>&1
    if !errorlevel! equ 0 (
        set "C9_CAT=desktop_agent"
        set /a C9_AGENT+=1
    )
    echo "%%a" | findstr /i /c:".vscode\extensions\anthropic.claude-code" >nul 2>&1
    if !errorlevel! equ 0 (
        set "C9_CAT=vscode_ext"
        set /a C9_VSCODE+=1
    )

    if "!C9_CAT!"=="unknown" set /a C9_UNKNOWN+=1
)

set /a OK_COUNT+=1

if !C9_AGENT! GTR 1 (
    set "C9_STATUS=WARNING"
    set "C9_WARN=Old desktop_agent binaries: !C9_AGENT! found"
    set /a OK_COUNT-=1
    set /a WARN_COUNT+=1
)
if !C9_UNKNOWN! GTR 0 (
    if "!C9_STATUS!"=="OK" (
        set "C9_STATUS=WARNING"
        set /a OK_COUNT-=1
        set /a WARN_COUNT+=1
    )
    set "C9_WARN=!C9_WARN! Unknown binaries: !C9_UNKNOWN!"
)

if "!C9_STATUS!"=="OK" echo OK [!C9_TOTAL! binaries]
if "!C9_STATUS!"=="WARNING" echo WARNING [!C9_TOTAL! binaries]

REM ============================================================
REM  C10: Proxy Environment Variables
REM  SECURITY: Never output proxy values (may contain passwords)
REM ============================================================
set "C10_STATUS=OK"
set "C10_HTTP_SET=false"
set "C10_HTTPS_SET=false"
set "C10_NOPROXY_SET=false"
set "C10_HTTP_LC_SET=false"
set "C10_HTTPS_LC_SET=false"
set "C10_NOPROXY_LC_SET=false"
set "C10_HTTP_VALID="
set "C10_HTTPS_VALID="
set "C10_WARN_FORMAT="
set "C10_CASE_MISMATCH=false"

set /p="Checking [C10] Proxy Settings...         " <nul

if defined HTTP_PROXY set "C10_HTTP_SET=true"
if defined HTTPS_PROXY set "C10_HTTPS_SET=true"
if defined NO_PROXY set "C10_NOPROXY_SET=true"
if defined http_proxy set "C10_HTTP_LC_SET=true"
if defined https_proxy set "C10_HTTPS_LC_SET=true"
if defined no_proxy set "C10_NOPROXY_LC_SET=true"

REM Format validation via PowerShell (value stays inside PS)
if "!C10_HTTP_SET!"=="true" (
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$v=$env:HTTP_PROXY;if($v -match '://\S+' -or $v -match '\S+:\d+'){'true'}else{'false'}"') do set "C10_HTTP_VALID=%%a"
    if "!C10_HTTP_VALID!"=="false" (
        set "C10_WARN_FORMAT=HTTP_PROXY format invalid"
        set "C10_STATUS=WARNING"
    )
)
if "!C10_HTTPS_SET!"=="true" (
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$v=$env:HTTPS_PROXY;if($v -match '://\S+' -or $v -match '\S+:\d+'){'true'}else{'false'}"') do set "C10_HTTPS_VALID=%%a"
    if "!C10_HTTPS_VALID!"=="false" (
        set "C10_WARN_FORMAT=!C10_WARN_FORMAT! HTTPS_PROXY format invalid"
        set "C10_STATUS=WARNING"
    )
)

REM Check case mismatch
if "!C10_HTTP_SET!"=="true" if "!C10_HTTP_LC_SET!"=="false" set "C10_CASE_MISMATCH=true"
if "!C10_HTTP_SET!"=="false" if "!C10_HTTP_LC_SET!"=="true" set "C10_CASE_MISMATCH=true"
if "!C10_HTTPS_SET!"=="true" if "!C10_HTTPS_LC_SET!"=="false" set "C10_CASE_MISMATCH=true"
if "!C10_HTTPS_SET!"=="false" if "!C10_HTTPS_LC_SET!"=="true" set "C10_CASE_MISMATCH=true"

if "!C10_CASE_MISMATCH!"=="true" set "C10_STATUS=WARNING"

if "!C10_STATUS!"=="WARNING" (
    set /a WARN_COUNT+=1
) else (
    set /a OK_COUNT+=1
)

if "!C10_STATUS!"=="OK" echo OK
if "!C10_STATUS!"=="WARNING" echo WARNING

REM ============================================================
REM  C11: MCP Config Files
REM ============================================================
set "C11_STATUS=OK"
set "C11_DESKTOP_EXISTS=false"
set "C11_DESKTOP_SERVERS="
set "C11_DESKTOP_JIRA=false"
set "C11_GLOBAL_EXISTS=false"
set "C11_GLOBAL_SERVERS="
set "C11_GLOBAL_JIRA=false"
set "C11_PROJ_MCP_LIST="
set "C11_JIRA_COUNT=0"

set /p="Checking [C11] MCP Config Files...       " <nul
set /a OK_COUNT+=1

REM Desktop config MCP servers
if exist "%APPDATA%\Claude\claude_desktop_config.json" (
    set "C11_DESKTOP_EXISTS=true"
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText($env:APPDATA+'\Claude\claude_desktop_config.json')); if($j.mcpServers){$j.mcpServers.PSObject.Properties.Name -join ','}"') do (
        set "C11_DESKTOP_SERVERS=%%a"
    )
    echo "!C11_DESKTOP_SERVERS!" | findstr /i "jira" >nul 2>&1
    if !errorlevel! equ 0 (
        set "C11_DESKTOP_JIRA=true"
        set /a C11_JIRA_COUNT+=1
    )
)

REM Global MCP config
set "C11_GLOBAL_PATH=%USERPROFILE%\.claude\mcp.json"
if exist "!C11_GLOBAL_PATH!" (
    set "C11_GLOBAL_EXISTS=true"
    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "$j=ConvertFrom-Json([IO.File]::ReadAllText($env:C11_GLOBAL_PATH)); if($j.mcpServers){$j.mcpServers.PSObject.Properties.Name -join ','}"') do (
        set "C11_GLOBAL_SERVERS=%%a"
    )
    echo "!C11_GLOBAL_SERVERS!" | findstr /i "jira" >nul 2>&1
    if !errorlevel! equ 0 (
        set "C11_GLOBAL_JIRA=true"
        set /a C11_JIRA_COUNT+=1
    )
)

REM Project-level .mcp.json files - reuse C6_DONE_DIRS for dedup
set "C11_DONE_DIRS="
for %%D in (!CD! !C6_SCAN_DIRS!) do (
    if exist "%%D" (
        echo !C11_DONE_DIRS! | findstr /i /c:"%%D;" >nul 2>&1
        if !errorlevel! neq 0 (
            set "C11_DONE_DIRS=!C11_DONE_DIRS!%%D;"
            for /d %%P in ("%%D\*") do (
                if exist "%%P\.mcp.json" (
                    set "C11_TEMP_PATH=%%P\.mcp.json"
                    for /f "tokens=*" %%a in ('powershell -NoProfile -Command "try{$j=ConvertFrom-Json([IO.File]::ReadAllText($env:C11_TEMP_PATH)); if($j.mcpServers){$j.mcpServers.PSObject.Properties.Name -join ','}}catch{}"') do (
                        set "C11_PROJ_MCP_LIST=!C11_PROJ_MCP_LIST!%%P [%%a]; "
                        echo "%%a" | findstr /i "jira" >nul 2>&1
                        if !errorlevel! equ 0 set /a C11_JIRA_COUNT+=1
                    )
                )
            )
        )
    )
)

if !C11_JIRA_COUNT! GTR 0 (
    echo OK [Jira: !C11_JIRA_COUNT! locations]
) else (
    echo OK
)

REM ============================================================
REM  Output: Summary (diagnosis-summary.txt)
REM ============================================================
echo ============================================================= > "%SUMMARY_FILE%"
echo   Claude Ecosystem Diagnostic Report >> "%SUMMARY_FILE%"
echo   Generated: !TIMESTAMP! >> "%SUMMARY_FILE%"
echo ============================================================= >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C1] Desktop Installation >> "%SUMMARY_FILE%"
echo   Status  : !C1_STATUS! >> "%SUMMARY_FILE%"
if defined C1_VERSION echo   Version : !C1_VERSION! >> "%SUMMARY_FILE%"
if defined C1_PACKAGE echo   Package : !C1_PACKAGE! >> "%SUMMARY_FILE%"
if defined C1_PUBLISHER echo   Publisher: !C1_PUBLISHER! >> "%SUMMARY_FILE%"
if defined C1_WARN echo   Warning : !C1_WARN! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C2] CLI Installation >> "%SUMMARY_FILE%"
echo   Status  : !C2_STATUS! >> "%SUMMARY_FILE%"
if defined C2_VERSION echo   Version : !C2_VERSION! >> "%SUMMARY_FILE%"
if defined C2_PATH echo   Path    : !C2_PATH! >> "%SUMMARY_FILE%"
if defined C2_AGENT_VERSIONS echo   Agent binaries:!C2_AGENT_VERSIONS! >> "%SUMMARY_FILE%"
if defined C2_WARN echo   Warning : !C2_WARN! >> "%SUMMARY_FILE%"
if defined C2_AGENT_WARN echo   Warning : !C2_AGENT_WARN! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C3] VS Code Extension >> "%SUMMARY_FILE%"
echo   Status  : !C3_STATUS! >> "%SUMMARY_FILE%"
if "!C3_EXT_FOUND!"=="true" echo   Extension: anthropic.claude-code >> "%SUMMARY_FILE%"
if defined C3_EMBEDDED_VER echo   Embedded binary: v!C3_EMBEDDED_VER! >> "%SUMMARY_FILE%"
if defined C3_WARN echo   Warning : !C3_WARN! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C4] Credentials >> "%SUMMARY_FILE%"
echo   Status  : !C4_STATUS! >> "%SUMMARY_FILE%"
if "!C4_EXISTS!"=="true" echo   File    : EXISTS [modified: !C4_MODIFIED!] >> "%SUMMARY_FILE%"
if "!C4_EXISTS!"=="false" echo   File    : NOT FOUND >> "%SUMMARY_FILE%"
echo   Note    : Content not inspected [security] >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C5] Global settings.json >> "%SUMMARY_FILE%"
echo   Status  : !C5_STATUS! >> "%SUMMARY_FILE%"
echo   Path    : !C5_PATH! >> "%SUMMARY_FILE%"
echo   Allow entries : !C5_ALLOW_COUNT! >> "%SUMMARY_FILE%"
echo   Deny entries  : !C5_DENY_COUNT! >> "%SUMMARY_FILE%"
echo   Additional dirs: !C5_ADDL_DIRS! >> "%SUMMARY_FILE%"
if "!C5_WARN_HIGH!"=="true" echo   Warning : !C5_ALLOW_COUNT! allow entries [recommended: under 15] >> "%SUMMARY_FILE%"
if defined C5_WARN_ONESHOT echo   Warning : Oneshot commands: !C5_WARN_ONESHOT! >> "%SUMMARY_FILE%"
if defined C5_WARN_PROJSPEC echo   Warning : !C5_WARN_PROJSPEC! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C6] Project settings.json >> "%SUMMARY_FILE%"
echo   Status  : !C6_STATUS! >> "%SUMMARY_FILE%"
echo   Found   : !C6_PROJ_COUNT! projects >> "%SUMMARY_FILE%"
if defined C6_PROJ_LIST echo   Projects: !C6_PROJ_LIST! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C7] Desktop Config >> "%SUMMARY_FILE%"
echo   Status  : !C7_STATUS! >> "%SUMMARY_FILE%"
echo   Path    : !C7_PATH! >> "%SUMMARY_FILE%"
echo   MCP servers: !C7_MCP_COUNT! >> "%SUMMARY_FILE%"
if defined C7_MCP_NAMES echo   Server names: !C7_MCP_NAMES! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C8] PATH Check >> "%SUMMARY_FILE%"
echo   Status  : !C8_STATUS! >> "%SUMMARY_FILE%"
echo   npm global: !C8_NPM_PATH! [in PATH: !C8_NPM_IN_PATH!] >> "%SUMMARY_FILE%"
echo   Node.js   : !C8_NODE_PATH! [in PATH: !C8_NODE_IN_PATH!] >> "%SUMMARY_FILE%"
if defined C8_WARN1 echo   Warning : !C8_WARN1! >> "%SUMMARY_FILE%"
if defined C8_WARN2 echo   Warning : !C8_WARN2! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C9] claude.exe Binary Scan >> "%SUMMARY_FILE%"
echo   Status  : !C9_STATUS! >> "%SUMMARY_FILE%"
echo   Total: !C9_TOTAL! [npm_cli:!C9_NPM! agent:!C9_AGENT! vscode:!C9_VSCODE! unknown:!C9_UNKNOWN!] >> "%SUMMARY_FILE%"
if defined C9_WARN echo   Warning : !C9_WARN! >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C10] Proxy Settings >> "%SUMMARY_FILE%"
echo   Status     : !C10_STATUS! >> "%SUMMARY_FILE%"
echo   HTTP_PROXY : !C10_HTTP_SET! >> "%SUMMARY_FILE%"
echo   HTTPS_PROXY: !C10_HTTPS_SET! >> "%SUMMARY_FILE%"
echo   NO_PROXY   : !C10_NOPROXY_SET! >> "%SUMMARY_FILE%"
echo   Note       : Actual values not shown [security] >> "%SUMMARY_FILE%"
if defined C10_WARN_FORMAT echo   Warning : !C10_WARN_FORMAT! >> "%SUMMARY_FILE%"
if "!C10_CASE_MISMATCH!"=="true" echo   Warning : Upper/lowercase proxy vars mismatch >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo [C11] MCP Config Files >> "%SUMMARY_FILE%"
echo   Status  : !C11_STATUS! >> "%SUMMARY_FILE%"
echo   Desktop config: !C11_DESKTOP_EXISTS! [servers: !C11_DESKTOP_SERVERS!] >> "%SUMMARY_FILE%"
echo   Global MCP    : !C11_GLOBAL_EXISTS! [servers: !C11_GLOBAL_SERVERS!] >> "%SUMMARY_FILE%"
if defined C11_PROJ_MCP_LIST echo   Project MCP   : !C11_PROJ_MCP_LIST! >> "%SUMMARY_FILE%"
echo   Jira servers  : !C11_JIRA_COUNT! locations >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo ============================================================= >> "%SUMMARY_FILE%"
echo   Summary: !OK_COUNT! OK / !WARN_COUNT! WARNING / !ERR_COUNT! ERROR >> "%SUMMARY_FILE%"
echo ============================================================= >> "%SUMMARY_FILE%"

REM ============================================================
REM  Output: JSON (diagnosis-for-claude.json)
REM ============================================================
set "C1_LOC_J="
if defined C1_LOCATION set "C1_LOC_J=!C1_LOCATION:\=\\!"
set "C2_PATH_J="
if defined C2_PATH set "C2_PATH_J=!C2_PATH:\=\\!"
set "C5_PATH_J=!C5_PATH:\=\\!"
set "C7_PATH_J=!C7_PATH:\=\\!"
set "C8_NPM_J="
if defined C8_NPM_PATH set "C8_NPM_J=!C8_NPM_PATH:\=\\!"
set "C8_NODE_J="
if defined C8_NODE_PATH set "C8_NODE_J=!C8_NODE_PATH:\=\\!"

echo { > "%JSON_FILE%"
echo   "format_version": "1.0", >> "%JSON_FILE%"
echo   "generated_at": "!TIMESTAMP_ISO!", >> "%JSON_FILE%"
echo   "machine_name": "!MACHINE_NAME!", >> "%JSON_FILE%"
echo   "username": "!USER_NAME!", >> "%JSON_FILE%"
echo   "diagnostics": { >> "%JSON_FILE%"
echo     "C1_desktop": { >> "%JSON_FILE%"
echo       "status": "!C1_STATUS!", >> "%JSON_FILE%"
echo       "version": "!C1_VERSION!", >> "%JSON_FILE%"
echo       "package_family": "!C1_PACKAGE!", >> "%JSON_FILE%"
echo       "install_location": "!C1_LOC_J!", >> "%JSON_FILE%"
echo       "publisher": "!C1_PUB_J!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C2_cli": { >> "%JSON_FILE%"
echo       "status": "!C2_STATUS!", >> "%JSON_FILE%"
echo       "version": "!C2_VERSION!", >> "%JSON_FILE%"
echo       "path": "!C2_PATH_J!", >> "%JSON_FILE%"
echo       "duplicate_count": !C2_FOUND!, >> "%JSON_FILE%"
echo       "desktop_agent_count": !C2_AGENT_COUNT!, >> "%JSON_FILE%"
echo       "desktop_agent_versions": "!C2_AGENT_VERSIONS!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C3_vscode_extension": { >> "%JSON_FILE%"
echo       "status": "!C3_STATUS!", >> "%JSON_FILE%"
echo       "extension_id": "anthropic.claude-code", >> "%JSON_FILE%"
echo       "extension_found": !C3_EXT_FOUND!, >> "%JSON_FILE%"
echo       "embedded_binary_version": "!C3_EMBEDDED_VER!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C4_credentials": { >> "%JSON_FILE%"
echo       "status": "!C4_STATUS!", >> "%JSON_FILE%"
echo       "file_exists": !C4_EXISTS!, >> "%JSON_FILE%"
echo       "file_size_bytes": !C4_SIZE!, >> "%JSON_FILE%"
echo       "last_modified": "!C4_MODIFIED!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C5_global_settings": { >> "%JSON_FILE%"
echo       "status": "!C5_STATUS!", >> "%JSON_FILE%"
echo       "path": "!C5_PATH_J!", >> "%JSON_FILE%"
echo       "allow_count": !C5_ALLOW_COUNT!, >> "%JSON_FILE%"
echo       "deny_count": !C5_DENY_COUNT!, >> "%JSON_FILE%"
echo       "additional_dirs_count": !C5_ADDL_DIRS!, >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C6_project_settings": { >> "%JSON_FILE%"
echo       "status": "!C6_STATUS!", >> "%JSON_FILE%"
echo       "projects_found": !C6_PROJ_COUNT!, >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C7_desktop_config": { >> "%JSON_FILE%"
echo       "status": "!C7_STATUS!", >> "%JSON_FILE%"
echo       "path": "!C7_PATH_J!", >> "%JSON_FILE%"
echo       "mcp_server_count": !C7_MCP_COUNT!, >> "%JSON_FILE%"
echo       "mcp_server_names": "!C7_MCP_NAMES!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C8_path": { >> "%JSON_FILE%"
echo       "status": "!C8_STATUS!", >> "%JSON_FILE%"
echo       "npm_global_in_path": !C8_NPM_IN_PATH!, >> "%JSON_FILE%"
echo       "npm_global_path": "!C8_NPM_J!", >> "%JSON_FILE%"
echo       "nodejs_in_path": !C8_NODE_IN_PATH!, >> "%JSON_FILE%"
echo       "nodejs_path": "!C8_NODE_J!", >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C9_binary_scan": { >> "%JSON_FILE%"
echo       "status": "!C9_STATUS!", >> "%JSON_FILE%"
echo       "total_binaries": !C9_TOTAL!, >> "%JSON_FILE%"
echo       "npm_cli": !C9_NPM!, >> "%JSON_FILE%"
echo       "desktop_agent": !C9_AGENT!, >> "%JSON_FILE%"
echo       "vscode_extension": !C9_VSCODE!, >> "%JSON_FILE%"
echo       "unknown": !C9_UNKNOWN!, >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C10_proxy": { >> "%JSON_FILE%"
echo       "status": "!C10_STATUS!", >> "%JSON_FILE%"
echo       "http_proxy_set": !C10_HTTP_SET!, >> "%JSON_FILE%"
echo       "https_proxy_set": !C10_HTTPS_SET!, >> "%JSON_FILE%"
echo       "no_proxy_set": !C10_NOPROXY_SET!, >> "%JSON_FILE%"
echo       "http_proxy_lowercase_set": !C10_HTTP_LC_SET!, >> "%JSON_FILE%"
echo       "https_proxy_lowercase_set": !C10_HTTPS_LC_SET!, >> "%JSON_FILE%"
echo       "no_proxy_lowercase_set": !C10_NOPROXY_LC_SET!, >> "%JSON_FILE%"
echo       "case_mismatch": !C10_CASE_MISMATCH!, >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     }, >> "%JSON_FILE%"
echo     "C11_mcp_config": { >> "%JSON_FILE%"
echo       "status": "!C11_STATUS!", >> "%JSON_FILE%"
echo       "desktop_config_exists": !C11_DESKTOP_EXISTS!, >> "%JSON_FILE%"
echo       "desktop_servers": "!C11_DESKTOP_SERVERS!", >> "%JSON_FILE%"
echo       "desktop_has_jira": !C11_DESKTOP_JIRA!, >> "%JSON_FILE%"
echo       "global_mcp_exists": !C11_GLOBAL_EXISTS!, >> "%JSON_FILE%"
echo       "global_servers": "!C11_GLOBAL_SERVERS!", >> "%JSON_FILE%"
echo       "global_has_jira": !C11_GLOBAL_JIRA!, >> "%JSON_FILE%"
echo       "jira_found_count": !C11_JIRA_COUNT!, >> "%JSON_FILE%"
echo       "warnings": [] >> "%JSON_FILE%"
echo     } >> "%JSON_FILE%"
echo   }, >> "%JSON_FILE%"
echo   "summary": { >> "%JSON_FILE%"
echo     "ok_count": !OK_COUNT!, >> "%JSON_FILE%"
echo     "warning_count": !WARN_COUNT!, >> "%JSON_FILE%"
echo     "error_count": !ERR_COUNT! >> "%JSON_FILE%"
echo   } >> "%JSON_FILE%"
echo } >> "%JSON_FILE%"

REM ============================================================
REM  Display final result
REM ============================================================
echo.
echo =============================================================
echo   Result: !OK_COUNT! OK / !WARN_COUNT! WARNING / !ERR_COUNT! ERROR
echo =============================================================
echo.
echo Output files:
echo   Summary : %SUMMARY_FILE%
echo   Log     : %JSON_FILE%
echo.

REM ============================================================
REM  A1: Show proxy environment variables on screen
REM  SECURITY: Values shown on screen only, NOT written to files
REM ============================================================
echo =============================================================
echo   Optional Actions
echo =============================================================
echo.
set "A1_INPUT="
set /p "A1_INPUT=[A1] Show proxy values on screen? (yes/no): "
if /i "!A1_INPUT!"=="yes" (
    echo.
    echo   --- Proxy Environment Variables ---
    if defined HTTP_PROXY (
        echo   HTTP_PROXY  = !HTTP_PROXY!
    ) else (
        echo   HTTP_PROXY  = [not set]
    )
    if defined HTTPS_PROXY (
        echo   HTTPS_PROXY = !HTTPS_PROXY!
    ) else (
        echo   HTTPS_PROXY = [not set]
    )
    if defined NO_PROXY (
        echo   NO_PROXY    = !NO_PROXY!
    ) else (
        echo   NO_PROXY    = [not set]
    )
    if defined http_proxy (
        echo   http_proxy  = !http_proxy!
    ) else (
        echo   http_proxy  = [not set]
    )
    if defined https_proxy (
        echo   https_proxy = !https_proxy!
    ) else (
        echo   https_proxy = [not set]
    )
    if defined no_proxy (
        echo   no_proxy    = !no_proxy!
    ) else (
        echo   no_proxy    = [not set]
    )
    echo   -----------------------------------
    echo.
) else (
    echo   Skipped.
    echo.
)

REM ============================================================
REM  A2: Open MCP config folder in Explorer
REM ============================================================
set "A2_INPUT="
set /p "A2_INPUT=[A2] Open MCP config folder in Explorer? (yes/no): "
if /i "!A2_INPUT!"=="yes" (
    echo.
    echo   Available MCP config locations:
    set "A2_COUNT=0"
    if "!C11_DESKTOP_EXISTS!"=="true" (
        set /a A2_COUNT+=1
        set "A2_1=%APPDATA%\Claude"
        echo     1. Desktop config: %APPDATA%\Claude
    )
    if "!C11_GLOBAL_EXISTS!"=="true" (
        set /a A2_COUNT+=1
        call set "A2_%%A2_COUNT%%=%USERPROFILE%\.claude"
        echo     !A2_COUNT!. Global MCP: %USERPROFILE%\.claude
    )
    REM Collect project MCP folders
    set "A2_PROJ_DIRS="
    for %%D in (!CD! !C6_SCAN_DIRS!) do (
        if exist "%%D" (
            for /d %%P in ("%%D\*") do (
                if exist "%%P\.mcp.json" (
                    set /a A2_COUNT+=1
                    call set "A2_%%A2_COUNT%%=%%P"
                    echo     !A2_COUNT!. Project MCP: %%P
                )
            )
        )
    )
    if !A2_COUNT! equ 0 (
        echo     No MCP config locations found.
        echo.
    ) else (
        echo     0. Exit
        echo.
:A2_LOOP
        set "A2_PICK="
        set /p "A2_PICK=  Enter number (0 to exit): "
        if "!A2_PICK!"=="0" goto :A2_EXIT
        call set "A2_TARGET=%%A2_!A2_PICK!%%"
        if defined A2_TARGET (
            echo   Opening: !A2_TARGET!
            explorer.exe "!A2_TARGET!"
            echo.
        ) else (
            echo   Invalid number.
            echo.
        )
        goto :A2_LOOP
:A2_EXIT
        echo   Done.
        echo.
    )
) else (
    echo   Skipped.
    echo.
)

echo =============================================================
echo   Done. Press any key to exit.
echo =============================================================
pause >nul
endlocal
