# StrictDocStarter - gather-test-logs.ps1
# Collects per-scenario test logs (test-results/*.log) plus the latest
# StrictDocStarter log/config and a fresh diagnostics.txt into a single zip.
# Output language: English ASCII only.

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}

# This script lives under StrictDocStarter/vm-tests/ .
#   $OnboardRoot (= parent) holds setup.log, env-report.json, setup.config.json
#   $ScriptDir holds test-results/
$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$OnboardRoot   = Split-Path -Parent $ScriptDir
$WorkDir       = $OnboardRoot
$TestResultDir = Join-Path $ScriptDir "test-results"
Write-Host "StrictDocStarter root:      $OnboardRoot"
Write-Host "test-results dir:  $TestResultDir (exists=$(Test-Path $TestResultDir))"

# ---- Build diagnostics.txt (reuse the same shape as gather-logs.ps1) -------

$diagPath = Join-Path $WorkDir "diagnostics.txt"
$lines = New-Object System.Collections.Generic.List[string]
function Add-Section { param([string]$Title) $lines.Add(""); $lines.Add("=== $Title ===") }
function Add-Line { param([string]$Text = "") $lines.Add($Text) }
function Try-Capture {
    param([string]$Label, [scriptblock]$Script)
    Add-Line "$Label :"
    try {
        $output = & $Script 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($output)) {
            Add-Line "  (no output)"
        } else {
            foreach ($l in ($output -split "`r?`n")) { if ($l) { Add-Line "  $l" } }
        }
    } catch { Add-Line "  ERROR: $($_.Exception.Message)" }
}

Add-Line "StrictDocStarter test diagnostics report"
Add-Line "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Add-Line "Script:    $($MyInvocation.MyCommand.Path)"
Add-Line "WorkDir:   $WorkDir"

Add-Section "Operating System"
Try-Capture "Windows version (CIM)" { Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture | Format-List }
Add-Line "OSVersion : $([System.Environment]::OSVersion.Version)"

Add-Section "PowerShell"
Add-Line "PSVersion : $($PSVersionTable.PSVersion)"
Add-Line "PSEdition : $($PSVersionTable.PSEdition)"

Add-Section "Current user / Privilege"
Add-Line "UserName  : $env:USERNAME"
$isAdmin = $false
try {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object Security.Principal.WindowsPrincipal($id)
    $isAdmin = $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {}
Add-Line "IsAdmin   : $isAdmin"

Add-Section "Tool versions (post-test)"
foreach ($cmd in @("git", "python", "py", "node", "code", "gh", "rg", "jq", "claude", "strictdoc", "pwsh", "wt")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Try-Capture "$cmd --version" { & $cmd --version 2>&1 | Select-Object -First 3 }
    } else {
        Add-Line "$cmd : (not on PATH)"
    }
}

Add-Section "VS Code extensions (post-test)"
if (Get-Command code -ErrorAction SilentlyContinue) {
    Try-Capture "code --list-extensions --show-versions" { code --list-extensions --show-versions 2>&1 }
} else {
    Add-Line "(code not on PATH)"
}

Add-Section "Test scenario logs available"
if (Test-Path $TestResultDir) {
    Try-Capture "Get-ChildItem $TestResultDir" { Get-ChildItem $TestResultDir | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize }
} else {
    Add-Line "(test-results directory not found - did run-tests.bat run?)"
}

Add-Section "WorkDir contents"
Try-Capture "Get-ChildItem $WorkDir" { Get-ChildItem $WorkDir | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize }

try {
    $lines -join "`r`n" | Set-Content -Path $diagPath -Encoding UTF8 -ErrorAction Stop
    Write-Host "Wrote: $diagPath"
} catch {
    Write-Host "Failed to write diagnostics.txt: $($_.Exception.Message)" -ForegroundColor Red
}

# ---- Bundle to zip ---------------------------------------------------------

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipName   = "StrictDocStarter-test-result-$timestamp.zip"
$zipPath   = Join-Path $env:TEMP $zipName

$collect = @()
foreach ($name in @("setup.log", "setup.config.json", "diagnostics.txt", "env-report.json")) {
    $p = Join-Path $WorkDir $name
    if (Test-Path $p) { $collect += $p }
}
if (Test-Path $TestResultDir) {
    Get-ChildItem $TestResultDir -File | ForEach-Object { $collect += $_.FullName }
}

if ($collect.Count -eq 0) {
    Write-Host "No files to collect." -ForegroundColor Yellow
    if (-not $env:NONINTERACTIVE_GATHER) { $null = Read-Host "Press Enter to close" }
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
    if (-not $env:NONINTERACTIVE_GATHER) { $null = Read-Host "Press Enter to close" }
    exit 1
}

try {
    Start-Process "explorer.exe" -ArgumentList "/select,`"$zipPath`""
} catch {
    Write-Host "Could not open Explorer; manually navigate to: $zipPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next step: select $zipName in Explorer and Ctrl+C to copy to host clipboard." -ForegroundColor Cyan
if (-not $env:NONINTERACTIVE_GATHER) { $null = Read-Host "Press Enter to close" }
exit 0
