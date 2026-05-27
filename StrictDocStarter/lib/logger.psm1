# StrictDocStarter logger module
# Wraps Start-Transcript for unified logging.
# Output language: English ASCII only (per spec ADR-008).
#
# NOTE on naming: internal symbols use the 'Onboard' prefix
# (Write-OnboardInfo, Start-OnboardLog, $script:OnboardRoot, etc.) as an
# opaque internal namespace identifier. They are not user-facing -- the log
# emits only the bracket-tag part ([INFO], [WARN], [OK], [SKIP], [ERROR]).

$script:TranscriptStarted = $false

function Start-OnboardLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$LogPath
    )
    try {
        Start-Transcript -Path $LogPath -Append -Force -ErrorAction Stop | Out-Null
        $script:TranscriptStarted = $true
    } catch {
        Write-Warning "Failed to start transcript: $($_.Exception.Message)"
    }
}

function Stop-OnboardLog {
    if ($script:TranscriptStarted) {
        try {
            Stop-Transcript -ErrorAction Stop | Out-Null
        } catch {
            # transcript may already be stopped
        }
        $script:TranscriptStarted = $false
    }
}

function Write-OnboardInfo  { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-OnboardOk    { param([string]$Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-OnboardWarn  { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-OnboardError { param([string]$Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-OnboardSkip  { param([string]$Msg) Write-Host "[SKIP]  $Msg" -ForegroundColor Gray }
function Write-OnboardStep  { param([string]$Msg) Write-Host ""; Write-Host "=== $Msg ===" -ForegroundColor Magenta }

Export-ModuleMember -Function `
    Start-OnboardLog, Stop-OnboardLog, `
    Write-OnboardInfo, Write-OnboardOk, Write-OnboardWarn, `
    Write-OnboardError, Write-OnboardSkip, Write-OnboardStep
