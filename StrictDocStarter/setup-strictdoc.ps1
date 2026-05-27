# StrictDocStarter - main dispatcher
# Spec: setup-spec.md (Ch 3.2 / 3.5)
# Subcommands: auto, check, config, install, clone, all, dryrun, help
# Output language: English ASCII only (per ADR-008).
#
# UAC self-elevation is now performed by setup-strictdoc.bat, not this script.
# This script assumes it is already running as administrator when an
# admin-required subcommand is invoked, and prints a clear error if not.

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "",

    [string]$ConfigPath  = "",
    [string]$LogPath     = "",
    [switch]$SkipCheck,
    [switch]$ForceConfig,
    [switch]$NonInteractive
)

# FR-803: no argument means 'auto'
if ([string]::IsNullOrWhiteSpace($Command)) { $Command = "auto" }

$ErrorActionPreference = "Stop"

# Force UTF-8 console output so our (English-only) messages render cleanly
# and any system error text does not mojibake when redirected.
try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

# Top-level trap: catch ANY error not handled by an inner try/catch and
# show it before the script terminates. This is the last line of defence
# against silent crashes (e.g. parse-time errors during dot-source).
trap {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "[TRAP] Uncaught error - script will terminate." -ForegroundColor Red
    Write-Host "  Message: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.InvocationInfo) {
        Write-Host "  At: $($_.InvocationInfo.PositionMessage)" -ForegroundColor DarkGray
    }
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "PS Version: $($PSVersionTable.PSVersion)"
    try { Write-Host "Script:     $($MyInvocation.MyCommand.Path)" } catch {}
    try { Write-Host "CWD:        $((Get-Location).Path)" } catch {}
    Write-Host ""
    if (-not $NonInteractive) {
        $null = Read-Host "Press Enter to close this window"
    }
    exit 99
}

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
$script:OnboardRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:LibDir      = Join-Path $script:OnboardRoot "lib"
$script:WorkDir     = (Get-Location).Path

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $script:WorkDir "setup.config.json"
}
if (-not $LogPath) {
    $LogPath = Join-Path $script:WorkDir "setup.log"
}
$script:EnvReportPath = Join-Path $script:WorkDir "env-report.json"

# Commands that require Administrator (FR-603, narrowed for usability)
$script:AdminRequired = @("install", "clone", "all", "auto")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Test-Administrator {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object Security.Principal.WindowsPrincipal($id)
    return $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Show-Help {
    Write-Host "StrictDocStarter - StrictDoc environment setup"
    Write-Host ""
    Write-Host "Usage: setup-strictdoc.bat [<subcommand>] [options]"
    Write-Host ""
    Write-Host "Subcommands:"
    Write-Host "  (none)         Same as 'auto' (full automated setup with one yes prompt)"
    Write-Host "  auto           Probe env, show plan, ask one 'yes', run all phases"
    Write-Host "  check          Detect tools, proxy, SSL inspection. Writes env-report.json"
    Write-Host "  config         Generate setup.config.json from template (Python dialog, edit, yes)"
    Write-Host "  install        Install tools per setup.config.json    [Phase A only]"
    Write-Host "  clone          Clone repository and create junction   [stub]"
    Write-Host "  all            check -> config -> install -> clone (power-user flow)"
    Write-Host "  dryrun         Enumerate planned actions without executing"
    Write-Host "  help           Show this help"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -ConfigPath <path>     Override setup.config.json location"
    Write-Host "  -LogPath <path>        Override setup.log location"
    Write-Host "  -SkipCheck             Skip 'check' inside 'all' / 'dryrun'"
    Write-Host "  -ForceConfig           Regenerate setup.config.json even if it exists"
    Write-Host "  -NonInteractive        Skip prompts (auto/config use defaults)"
}

function Import-OnboardLogger {
    Import-Module (Join-Path $script:LibDir "logger.psm1") -Force -DisableNameChecking
}

# NOTE: do NOT wrap dot-sourcing in a function -- it would scope the loaded
# function names to the helper, not the script. We dot-source inline below.

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
$cmd = $Command.ToLower()

# Help is special - no logger, no admin
if ($cmd -eq "help" -or $cmd -eq "-h" -or $cmd -eq "--help" -or $cmd -eq "/?") {
    Show-Help
    exit 0
}

# Admin precondition (FR-603). UAC elevation is now handled by setup-strictdoc.bat.
# If we somehow got here without admin for an admin-required cmd, fail loudly.
if ($script:AdminRequired -contains $cmd) {
    if (-not (Test-Administrator)) {
        Write-Host ""
        Write-Host "[ERROR] '$cmd' requires Administrator privileges, but this" -ForegroundColor Red
        Write-Host "        PowerShell session is not elevated." -ForegroundColor Red
        Write-Host ""
        Write-Host "Run setup-strictdoc.bat (double-click) instead of invoking setup-strictdoc.ps1" -ForegroundColor Yellow
        Write-Host "directly - setup-strictdoc.bat handles UAC elevation automatically." -ForegroundColor Yellow
        if (-not $NonInteractive) {
            Write-Host ""
            $null = Read-Host "Press Enter to close this window"
        }
        exit 4
    }
}

# Load logger and start transcript.
# Wrap in an outer try/catch so that even pre-transcript failures (bad path,
# missing logger.psm1, Start-Transcript denial, etc.) get reported on screen
# with a guaranteed pause, instead of the window closing silently.
$script:LoggerLoaded   = $false
$script:TranscriptOn   = $false
$script:HadException   = $false
$script:EarlyError     = $null

try {
    Import-OnboardLogger
    $script:LoggerLoaded = $true
    Start-OnboardLog -LogPath $LogPath
    $script:TranscriptOn = $true
} catch {
    $script:EarlyError = $_
    Write-Host ""
    Write-Host "[FATAL] Failed to initialize logging:" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  At: $($_.InvocationInfo.PositionMessage)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Diagnostic info:"
    Write-Host "  OnboardRoot: $script:OnboardRoot"
    Write-Host "  LibDir:      $script:LibDir"
    Write-Host "  WorkDir:     $script:WorkDir"
    Write-Host "  LogPath:     $LogPath"
    Write-Host "  PS Version:  $($PSVersionTable.PSVersion)"
    Write-Host ""
    if (-not $NonInteractive) {
        $null = Read-Host "Press Enter to close this window"
    }
    exit 3
}

try {
    Write-OnboardInfo "StrictDocStarter starting: command='$cmd' cwd='$script:WorkDir'"

    # Load all lib files at script scope so their functions are visible here.
    . (Join-Path $script:LibDir "check.ps1")
    . (Join-Path $script:LibDir "config.ps1")
    . (Join-Path $script:LibDir "install.ps1")
    . (Join-Path $script:LibDir "clone.ps1")
    . (Join-Path $script:LibDir "proxy.ps1")
    . (Join-Path $script:LibDir "auto.ps1")

    # FR-1002: defensively refresh $env:Path from registry so a re-run of
    # this script after a prior install in the SAME shell session sees the
    # latest winget setx updates without needing a shell restart.
    if ($script:AdminRequired -contains $cmd) {
        Update-PathFromRegistry
    }

    switch ($cmd) {

        "auto" {
            $ok = Invoke-Auto -NonInteractive:$NonInteractive -ConfigPath $ConfigPath
            if (-not $ok) { exit 1 }
        }

        "check" {
            $ok = Invoke-Check -OutputPath $script:EnvReportPath
            if (-not $ok) { exit 1 }
        }

        "config" {
            $ok = Invoke-Config -ConfigPath $ConfigPath -EnvReportPath $script:EnvReportPath -ForceConfig:$ForceConfig -NonInteractive:$NonInteractive
            if (-not $ok) { exit 1 }
        }

        "install" {
            $ok = Invoke-Install -ConfigPath $ConfigPath
            if (-not $ok) { exit 1 }
        }

        "clone" {
            $ok = Invoke-Clone -ConfigPath $ConfigPath
            if (-not $ok) { exit 1 }
        }

        "all" {

            if (-not $SkipCheck) {
                $ok = Invoke-Check -OutputPath $script:EnvReportPath
                if (-not $ok) { Write-OnboardError "check failed - aborting 'all'"; exit 1 }
            } else {
                Write-OnboardSkip "check (skipped via -SkipCheck)"
            }

            $ok = Invoke-Config -ConfigPath $ConfigPath -EnvReportPath $script:EnvReportPath -ForceConfig:$ForceConfig -NonInteractive:$NonInteractive
            if (-not $ok) { Write-OnboardError "config failed - aborting 'all'"; exit 1 }

            $ok = Invoke-Install -ConfigPath $ConfigPath
            if (-not $ok) { Write-OnboardWarn "install reported failure (MVP stub)" }

            $ok = Invoke-Clone -ConfigPath $ConfigPath
            if (-not $ok) { Write-OnboardWarn "clone reported failure (MVP stub)" }

            Write-OnboardStep "Summary"
            Write-OnboardOk "StrictDocStarter 'all' run completed (with MVP stubs for install/clone)."
        }

        "dryrun" {
            Write-OnboardStep "Dry run (no side effects)"

            if (-not $SkipCheck) {
                Write-OnboardInfo "Would run: check -> writes env-report.json"
            }

            # Resolve a config to use for planning. If setup.config.json is
            # missing, copy the template into a temp file (with <user>
            # expanded) so the plan reflects realistic defaults.
            if (-not (Test-Path $ConfigPath)) {
                Write-OnboardInfo "Would run: config -> generate setup.config.json (asks Python version)"
                Write-OnboardWarn "setup.config.json not found - using template defaults (host probe still applies)"
                $tmpCfg = Join-Path $env:TEMP "StrictDocStarter-dryrun-$([guid]::NewGuid()).json"
                try {
                    Copy-Item -Path (Join-Path $script:OnboardRoot "setup.config.template.json") -Destination $tmpCfg -Force
                    $planConfigPath = $tmpCfg
                } catch {
                    $planConfigPath = $ConfigPath
                }
            } else {
                $planConfigPath = $ConfigPath
            }

            # Build the unified plan via Build-AutoPlan (same path as 'auto'),
            # which probes the host so already-installed tools show as 'skip'.
            $planCfg = $null
            try {
                $planCfg = Get-Content $planConfigPath -Raw | ConvertFrom-Json
                $planCfg = Expand-UserPlaceholders $planCfg
            } catch {
                Write-OnboardWarn "Could not parse plan config: $($_.Exception.Message)"
            }

            if ($planCfg) {
                $pyVer = if ($planCfg.python -and $planCfg.python.version) { [string]$planCfg.python.version } else { "3.13" }
                $plan  = Build-AutoPlan -PythonVersion $pyVer -Config $planCfg
                Show-AutoPlan -Plan $plan

                # FR-700: surface proxy detection in dryrun too, so the user
                # is aware of the install-time gotcha without running 'auto'.
                Show-ProxyWarningIfDetected
            }

            if ($planConfigPath -ne $ConfigPath -and (Test-Path $planConfigPath)) {
                Remove-Item -Path $planConfigPath -Force -ErrorAction SilentlyContinue
            }

            Write-OnboardOk "Dry run completed (no side effects)."
        }

        default {
            Write-OnboardError "Unknown command: '$Command'"
            Show-Help
            exit 1
        }
    }

} catch {
    # Try the logger first; fall back to plain Write-Host if the logger broke.
    $errMsg = "Unhandled exception: $($_.Exception.Message)"
    try {
        Write-OnboardError $errMsg
    } catch {
        Write-Host "[ERROR] $errMsg" -ForegroundColor Red
    }
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    Write-Host "  At: $($_.InvocationInfo.PositionMessage)" -ForegroundColor DarkGray
    $script:HadException = $true
} finally {
    if ($script:TranscriptOn) {
        try { Stop-OnboardLog } catch {}
    }

    # Keep the window open so the user can read the summary or error.
    # Always pause when something went wrong (HadException), regardless of cmd.
    $needPause = (-not $NonInteractive) -and (
        $script:HadException -or ($cmd -in @("auto", "install", "clone", "all"))
    )
    if ($needPause) {
        Write-Host ""
        if ($script:TranscriptOn) {
            Write-Host "Log saved to: $LogPath" -ForegroundColor DarkGray
        } else {
            Write-Host "(No transcript was started - run gather-logs.bat for diagnostics)" -ForegroundColor DarkGray
        }
        $null = Read-Host "Press Enter to close this window"
    }

    if ($script:HadException) { exit 1 }
}
