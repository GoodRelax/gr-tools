# StrictDocStarter - gather-logs.ps1
# Collects log files + system diagnostics into a single zip for sharing.
# Run by gather-logs.bat. Standalone PowerShell entry point.
# Output language: English ASCII only.

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Look for log files in this order of likelihood:
#   1. Current working directory (where the user ran setup-strictdoc.bat from)
#   2. Script directory (Desktop\StrictDocStarter\)
function Find-LogDir {
    $candidates = @(
        (Get-Location).Path,
        $ScriptDir
    )
    foreach ($d in $candidates) {
        $hasAny = $false
        foreach ($f in @("setup.log", "env-report.json", "setup.config.json", "manage.log", "server.config.json")) {
            if (Test-Path (Join-Path $d $f)) { $hasAny = $true; break }
        }
        if ($hasAny) { return $d }
    }
    return $ScriptDir
}

# manage-strictdoc server logs (PID file + stdout/stderr) live under
# %LOCALAPPDATA%\StrictDocStarter\ regardless of LogDir (serve-spec FR-902).
$ServerStateDir = Join-Path $env:LOCALAPPDATA 'StrictDocStarter'

$LogDir = Find-LogDir
Write-Host "Looking for logs in: $LogDir"

# --- Build diagnostics.txt ----------------------------------------------------

$diagPath = Join-Path $LogDir "diagnostics.txt"
$lines = New-Object System.Collections.Generic.List[string]
function Add-Section {
    param([string]$Title)
    $lines.Add("")
    $lines.Add("=== $Title ===")
}
function Add-Line {
    param([string]$Text = "")
    $lines.Add($Text)
}
function Try-Capture {
    param([string]$Label, [scriptblock]$Script)
    Add-Line "$Label :"
    try {
        $output = & $Script 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($output)) {
            Add-Line "  (no output)"
        } else {
            foreach ($l in ($output -split "`r?`n")) {
                if ($l) { Add-Line "  $l" }
            }
        }
    } catch {
        Add-Line "  ERROR: $($_.Exception.Message)"
    }
}

Add-Line "StrictDocStarter diagnostics report"
Add-Line "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Add-Line "Script:    $($MyInvocation.MyCommand.Path)"
Add-Line "LogDir:    $LogDir"
Add-Line "CWD:       $((Get-Location).Path)"

Add-Section "Operating System"
Try-Capture "Windows version (CIM)" { Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture | Format-List }
Add-Line "OSVersion : $([System.Environment]::OSVersion.Version)"
Add-Line "Is64bitOS : $([System.Environment]::Is64BitOperatingSystem)"

Add-Section "PowerShell"
Add-Line "PSVersion : $($PSVersionTable.PSVersion)"
Add-Line "PSEdition : $($PSVersionTable.PSEdition)"
Add-Line "Host      : $($Host.Name) $($Host.Version)"

Add-Section "Execution Policy"
Try-Capture "Get-ExecutionPolicy -List" { Get-ExecutionPolicy -List | Format-Table -AutoSize }

Add-Section "Current user / Privilege"
Add-Line "UserName  : $env:USERNAME"
Add-Line "UserDomain: $env:USERDOMAIN"
$isAdmin = $false
try {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object Security.Principal.WindowsPrincipal($id)
    $isAdmin = $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {}
Add-Line "IsAdmin   : $isAdmin"

Add-Section "winget"
Try-Capture "winget --version" { winget --version }
Try-Capture "winget list (top 20)" { winget list --accept-source-agreements 2>&1 | Select-Object -First 25 }

Add-Section "Existing tool versions"
foreach ($cmd in @("git", "python", "py", "node", "code", "gh", "rg", "jq", "claude", "strictdoc", "pwsh")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Try-Capture "$cmd --version" { & $cmd --version 2>&1 | Select-Object -First 3 }
    } else {
        Add-Line "$cmd : (not on PATH)"
    }
}

Add-Section "VS Code extensions"
$codeCmd = Get-Command code -ErrorAction SilentlyContinue
if ($codeCmd) {
    Try-Capture "code --list-extensions --show-versions" { code --list-extensions --show-versions 2>&1 }
} else {
    Add-Line "(code not on PATH)"
}

Add-Section "Proxy / Network"
try {
    $ie = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction Stop
    Add-Line "IE ProxyEnable  : $($ie.ProxyEnable)"
    Add-Line "IE ProxyServer  : $($ie.ProxyServer)"
    Add-Line "IE AutoConfigURL: $($ie.AutoConfigURL)"
} catch {
    Add-Line "(failed to read IE proxy settings: $($_.Exception.Message))"
}
Add-Line "env:HTTP_PROXY  : $env:HTTP_PROXY"
Add-Line "env:HTTPS_PROXY : $env:HTTPS_PROXY"
Try-Capture "netsh winhttp show proxy" { netsh winhttp show proxy }

Add-Section "Environment variables (relevant subset)"
foreach ($v in @("USERNAME", "USERPROFILE", "TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PATH")) {
    $val = [System.Environment]::GetEnvironmentVariable($v)
    if ($v -eq "PATH" -and $val) {
        Add-Line "$v :"
        foreach ($p in ($val -split ';')) { if ($p) { Add-Line "  $p" } }
    } else {
        Add-Line "$v : $val"
    }
}

Add-Section "StrictDocStarter folder contents"
Try-Capture "Get-ChildItem $ScriptDir -Recurse" { Get-ChildItem $ScriptDir -Recurse | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize }

Add-Section "Log directory contents"
Try-Capture "Get-ChildItem $LogDir" { Get-ChildItem $LogDir | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize }

Add-Section "manage-strictdoc state (%LOCALAPPDATA%\StrictDocStarter)"
if (Test-Path $ServerStateDir) {
    Try-Capture "Get-ChildItem $ServerStateDir" { Get-ChildItem $ServerStateDir | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize }
    foreach ($pidFile in (Get-ChildItem -Path $ServerStateDir -Filter "server-*.pid" -File -ErrorAction SilentlyContinue)) {
        Try-Capture "Get-Content $($pidFile.Name)" { Get-Content -Path $pidFile.FullName -ErrorAction SilentlyContinue }
    }
} else {
    Add-Line "(no manage-strictdoc state directory yet)"
}

Add-Section "Recent Windows event log: PowerShell"
try {
    $events = Get-WinEvent -LogName "Windows PowerShell" -MaxEvents 30 -ErrorAction Stop
    foreach ($e in $events) {
        Add-Line ("{0} [{1}] {2}" -f $e.TimeCreated, $e.LevelDisplayName, ($e.Message -split "`r?`n")[0])
    }
} catch {
    Add-Line "(no events or access denied: $($_.Exception.Message))"
}

# Write diagnostics file
try {
    $lines -join "`r`n" | Set-Content -Path $diagPath -Encoding UTF8 -ErrorAction Stop
    Write-Host "Wrote: $diagPath"
} catch {
    Write-Host "Failed to write diagnostics.txt: $($_.Exception.Message)" -ForegroundColor Red
}

# --- Bundle to zip ------------------------------------------------------------

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipName   = "StrictDocStarter-result-$timestamp.zip"
$zipPath   = Join-Path $env:TEMP $zipName

$collect = @()
foreach ($name in @("setup.log", "env-report.json", "setup.config.json", "diagnostics.txt", "manage.log", "server.config.json")) {
    $p = Join-Path $LogDir $name
    if (Test-Path $p) { $collect += $p }
}

# Include server-side files under %LOCALAPPDATA%\StrictDocStarter\ (FR-902).
if (Test-Path $ServerStateDir) {
    foreach ($pattern in @("server-*.log", "server-*.err.log", "server-*.pid")) {
        Get-ChildItem -Path $ServerStateDir -Filter $pattern -File -ErrorAction SilentlyContinue |
            ForEach-Object { $collect += $_.FullName }
    }
}

if ($collect.Count -eq 0) {
    Write-Host "No files to collect (not even diagnostics.txt was created)." -ForegroundColor Yellow
    if (-not $env:NONINTERACTIVE_GATHER) {
        $null = Read-Host "Press Enter to close"
    }
    exit 1
}

try {
    Compress-Archive -Path $collect -DestinationPath $zipPath -Force -ErrorAction Stop
    Write-Host ""
    Write-Host "Bundled the following into:"
    Write-Host "  $zipPath" -ForegroundColor Green
    foreach ($f in $collect) { Write-Host "  - $(Split-Path -Leaf $f)" }
} catch {
    Write-Host "Compress-Archive failed: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $env:NONINTERACTIVE_GATHER) {
        $null = Read-Host "Press Enter to close"
    }
    exit 1
}

# Open Explorer with the zip selected (so user can Ctrl+C it to clipboard)
try {
    Start-Process "explorer.exe" -ArgumentList "/select,`"$zipPath`""
} catch {
    Write-Host "Could not open Explorer; manually navigate to: $zipPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next step: select $zipName in Explorer and Ctrl+C to copy to host clipboard." -ForegroundColor Cyan
if (-not $env:NONINTERACTIVE_GATHER) {
    $null = Read-Host "Press Enter to close"
}
exit 0
