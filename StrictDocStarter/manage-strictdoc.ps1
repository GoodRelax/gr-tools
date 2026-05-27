# manage-strictdoc.ps1 - StrictDoc server lifecycle menu loop dispatcher.
# Menu: 1 Start / 2 Stop / 3 Status / 4 Logs / 5 Edit config / Q Quit.
# Spec: docs/serve-spec.md (FR-101..110, ADR-101..112).
# Output language: English ASCII only (per NFR-005 / ADR-008).
#
# IMPORTANT (Glossary): $pid and $host are PowerShell reserved automatic
#                       variables. Do NOT shadow them.

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}

$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManageLog    = Join-Path $ScriptDir 'manage.log'
$ConfigPath   = Join-Path $ScriptDir 'server.config.json'
$TemplatePath = Join-Path $ScriptDir 'server.config.template.json'
$LibDir       = Join-Path $ScriptDir 'lib'

# Import logger module (existing, shared with setup-strictdoc).
Import-Module (Join-Path $LibDir 'logger.psm1') -Force -DisableNameChecking

# Dot-source server-config + server-process libraries (FR-209 / FR-301 etc.).
. (Join-Path $LibDir 'server-config.ps1')
. (Join-Path $LibDir 'server-process.ps1')

# ---- FR-110 / ADR-112: two-instance detection via Start-Transcript lock ----
$script:TranscriptStarted = $false
try {
    Start-Transcript -Path $ManageLog -Append -ErrorAction Stop | Out-Null
    $script:TranscriptStarted = $true
} catch {
    Write-Host "[ERROR] Another manage-strictdoc session appears to be running (cannot lock manage.log). Close it first, then retry." -ForegroundColor Red
    Write-Host "        ($($_.Exception.Message))" -ForegroundColor DarkGray
    exit 1
}

function Stop-ManageTranscriptIfStarted {
    if ($script:TranscriptStarted) {
        try { Stop-Transcript -ErrorAction SilentlyContinue | Out-Null } catch {}
        $script:TranscriptStarted = $false
    }
}

# ---- FR-201..203: initial config bootstrap ----
if (-not (Test-Path $ConfigPath)) {
    try {
        Initialize-ServerConfig -TemplatePath $TemplatePath -ConfigPath $ConfigPath -StarterRoot $ScriptDir
        Write-Host "[INFO]  Created $ConfigPath from template."
        Write-Host ""
        Write-Host "Opening editor for initial setup..."
        Open-EditorForConfig -Path $ConfigPath
        Write-Host ""
        $null = Read-Host "Press Enter when you have saved the config"
    } catch {
        Write-Host "[ERROR] Failed to initialize config: $($_.Exception.Message)" -ForegroundColor Red
        Stop-ManageTranscriptIfStarted
        exit 1
    }
}

# Mi3: define helper once, outside the loop.
function Invoke-WithReturnPrompt {
    param([scriptblock]$Action)
    & $Action
    Write-Host ""
    $null = Read-Host "Press Enter to return to menu"
}

# ---- FR-104..105 / FR-806: menu loop ----
$quit = $false
$finalState = $null
while (-not $quit) {
    # FR-209: reload + validate every iteration.
    $configResult = Get-ServerConfig -Path $ConfigPath -StarterRoot $ScriptDir
    $config       = $configResult.Config
    $validation   = $configResult.Validation
    $serverState  = $null
    if ($validation.Ok) {
        $serverState = Get-ServerState -Config $config
    }

    # FR-806: Clear-Host before redraw.
    Clear-Host

    Show-MenuHeader -ConfigPath $ConfigPath -Config $config -Validation $validation -ServerState $serverState

    Write-Host ""
    if (-not $validation.Ok) {
        # FR-803: degraded menu (5 + Q only).
        Write-Host "  5. Edit config   - open server.config.json in default editor"
        Write-Host "  Q. Quit"
        Write-Host ""
        $sel = Read-Host "Select [5/Q]"
    } else {
        Write-Host "  1. Start         - launch server in background + open browser"
        Write-Host "  2. Stop          - terminate the running server"
        Write-Host "  3. Status        - re-check status (refresh)"
        Write-Host "  4. Logs          - show last 50 lines of server log"
        Write-Host "  5. Edit config   - open server.config.json in default editor"
        Write-Host "  Q. Quit"
        Write-Host ""
        $sel = Read-Host "Select [1/2/3/4/5/Q]"
    }

    # M2: defend against $null (Read-Host on closed stdin / pipe input).
    $sel = "$sel".Trim().ToUpperInvariant()

    switch ($sel) {
        '1' {
            if (-not $validation.Ok) {
                Write-Host "[WARN]  Fix config first (menu 5)." -ForegroundColor Yellow
                Start-Sleep -Milliseconds 800
            } else {
                Invoke-WithReturnPrompt { Invoke-StartAction -Config $config -ServerState $serverState }
            }
        }
        '2' {
            if (-not $validation.Ok) {
                Write-Host "[WARN]  Fix config first (menu 5)." -ForegroundColor Yellow
                Start-Sleep -Milliseconds 800
            } else {
                Invoke-WithReturnPrompt { Invoke-StopAction -Config $config -ServerState $serverState }
            }
        }
        '3' {
            if (-not $validation.Ok) {
                Write-Host "[WARN]  Fix config first (menu 5)." -ForegroundColor Yellow
                Start-Sleep -Milliseconds 800
            } else {
                Invoke-WithReturnPrompt { Show-ServerStatusDetail -Config $config -ServerState $serverState }
            }
        }
        '4' {
            if (-not $validation.Ok) {
                Write-Host "[WARN]  Fix config first (menu 5)." -ForegroundColor Yellow
                Start-Sleep -Milliseconds 800
            } else {
                Invoke-WithReturnPrompt { Show-ServerLogs -Config $config }
            }
        }
        '5' {
            Open-EditorForConfig -Path $ConfigPath
            Write-Host "[INFO]  Editor launched. Save in editor, then continue."
            Write-Host ""
            $null = Read-Host "Press Enter to return to menu (config will be reloaded)"
        }
        'Q' {
            $quit = $true
            $finalState = $serverState
        }
        default {
            if ($validation.Ok) {
                Write-Host "[WARN]  Invalid selection. Choose [1/2/3/4/5/Q]." -ForegroundColor Yellow
            } else {
                Write-Host "[WARN]  Invalid selection. Choose [5/Q]." -ForegroundColor Yellow
            }
            Start-Sleep -Milliseconds 800
        }
    }
}

# ---- FR-107: warn if server still running on quit ----
if ($null -ne $finalState -and ($finalState.Status -eq 'RUNNING' -or $finalState.Status -eq 'STARTING')) {
    Write-Host ""
    Write-Host "[INFO]  Server is still running (PID $($finalState.Pid) on port $($finalState.Port)). Use 'Stop' next time to terminate it."
}

Stop-ManageTranscriptIfStarted
exit 0
