# StrictDocStarter - lib/auto.ps1
# 'auto' subcommand: one-yes-and-go full setup orchestration.
# Spec refs: FR-803, FR-804, FR-805
# Implementation status:
#   Phase A: VS Code + Claude Code extension          [implemented]
#   Phase B: Git / Python / GitHub CLI via winget     [TODO]
#   Phase C: pip install strictdoc                    [TODO]
#   Phase D: git clone + junction                     [TODO]
#   Phase E: optional tools + VS Code extensions      [TODO]

function Resolve-AutoConfig {
    # Ensures setup.config.json exists. If not, generates from template silently.
    # Returns the parsed config object, or $null on failure.
    param(
        [string]$ConfigPath  = (Join-Path (Get-Location) "setup.config.json"),
        [string]$TemplatePath = (Join-Path $script:OnboardRoot "setup.config.template.json")
    )
    if (-not (Test-Path $ConfigPath)) {
        Write-OnboardInfo "setup.config.json not found - generating from template (defaults)"
        $ok = Invoke-Config -ConfigPath $ConfigPath -TemplatePath $TemplatePath -NonInteractive
        if (-not $ok) {
            Write-OnboardError "Failed to auto-generate setup.config.json"
            return $null
        }
    }
    try {
        return (Get-Content $ConfigPath -Raw | ConvertFrom-Json)
    } catch {
        Write-OnboardError "Invalid setup.config.json: $($_.Exception.Message)"
        return $null
    }
}

function Format-PlanRow {
    # FR-901/903 (ADR-012): build a structured plan step. The actual text
    # rendering -- with phase-wide name-column alignment and phase-E SKIP-
    # first sorting -- is done by Show-AutoPlan, which can see all phases
    # at once. Returning a PSCustomObject lets Show-AutoPlan compute the
    # max name length once and align every row to it.
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [ValidateSet("INSTALL","SKIP")] [string]$Action,
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Reason
    )
    return [PSCustomObject]@{
        Action = $Action
        Name   = $Name
        Reason = $Reason
    }
}

function Format-PlanRowText {
    # FR-901: render one plan step to text with a caller-supplied name width.
    # Show-AutoPlan computes NameWidth from the longest name across ALL
    # phases so columns stay aligned phase-to-phase.
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] $Step,
        [Parameter(Mandatory)] [int]$NameWidth
    )
    $tag = "[$($Step.Action)]".PadRight(9)
    $nm  = $Step.Name.PadRight($NameWidth)
    return "$tag $nm $($Step.Reason)"
}

function Build-AutoPlan {
    [CmdletBinding()]
    param(
        [string]$PythonVersion = "3.13",
        $Config = $null
    )

    Write-OnboardInfo "Building plan (probing installed tools)..."

    # Probe current state without side effects.
    $cc       = Get-ClaudeCodeStatus
    $required = Get-RequiredToolsStatus

    $plan = [ordered]@{
        PhaseA = [ordered]@{
            Name  = "Phase A: Claude Code (VS Code extension)     [REQUIRED]"
            Steps = @()
        }
        PhaseB = [ordered]@{
            Name  = "Phase B: Required tools (Git / Python / gh)  [REQUIRED]"
            Steps = @()
        }
        PhaseC = [ordered]@{
            Name  = "Phase C: StrictDoc (pip install strictdoc)   [REQUIRED]"
            Steps = @()
        }
        PhaseD = [ordered]@{
            Name  = "Phase D: git clone + Obsidian junction       [OPTIONAL]"
            Steps = @()
        }
        PhaseE = [ordered]@{
            Name  = "Phase E: Optional tools + VS Code extensions [OPTIONAL]"
            Steps = @()
        }
    }

    # Phase A: required.
    if ($cc.VSCodeInstalled) {
        $plan.PhaseA.Steps += Format-PlanRow -Action SKIP    -Name "VS Code"               -Reason "already installed"
    } else {
        $plan.PhaseA.Steps += Format-PlanRow -Action INSTALL -Name "VS Code"               -Reason "required"
    }
    if ($cc.CCExtensionInstalled) {
        $plan.PhaseA.Steps += Format-PlanRow -Action SKIP    -Name "Claude Code extension" -Reason "already installed"
    } else {
        $plan.PhaseA.Steps += Format-PlanRow -Action INSTALL -Name "Claude Code extension" -Reason "required"
    }

    # Phase B: required.
    if ($required.git.Installed) {
        $plan.PhaseB.Steps += Format-PlanRow -Action SKIP    -Name "Git"                   -Reason "already installed"
    } else {
        $plan.PhaseB.Steps += Format-PlanRow -Action INSTALL -Name "Git"                   -Reason "required"
    }
    if ($required.python.Installed) {
        $plan.PhaseB.Steps += Format-PlanRow -Action SKIP    -Name "Python"                -Reason "already installed"
    } else {
        $plan.PhaseB.Steps += Format-PlanRow -Action INSTALL -Name "Python $PythonVersion" -Reason "required"
    }
    if ($required.gh.Installed) {
        $plan.PhaseB.Steps += Format-PlanRow -Action SKIP    -Name "GitHub CLI"            -Reason "already installed"
    } else {
        $plan.PhaseB.Steps += Format-PlanRow -Action INSTALL -Name "GitHub CLI"            -Reason "required"
    }

    # Phase C: required.
    if (Test-StrictDocInstalled) {
        $plan.PhaseC.Steps += Format-PlanRow -Action SKIP    -Name "strictdoc" -Reason "already installed"
    } else {
        $plan.PhaseC.Steps += Format-PlanRow -Action INSTALL -Name "strictdoc" -Reason "required (pip install strictdoc)"
    }

    # Phase D: optional (skipped when URL empty / skip_clone=true).
    if ($Config) {
        $skipClone = $false
        if ($Config.options.PSObject.Properties.Name -contains "skip_clone") {
            $skipClone = [bool]$Config.options.skip_clone
        }
        $urlEmpty = -not $Config.repository.url
        if ($skipClone) {
            $plan.PhaseD.Steps += Format-PlanRow -Action SKIP -Name "Phase D" -Reason "optional, options.skip_clone=true"
        } elseif ($urlEmpty) {
            $plan.PhaseD.Steps += Format-PlanRow -Action SKIP -Name "Phase D" -Reason "optional, repository.url is empty"
        } else {
            if (Test-RepoCloned $Config.paths.clone_target) {
                $plan.PhaseD.Steps += Format-PlanRow -Action SKIP    -Name "git clone" -Reason "already cloned at $($Config.paths.clone_target)"
            } else {
                if ($Config.repository.visibility -eq "private") {
                    $plan.PhaseD.Steps += Format-PlanRow -Action INSTALL -Name "gh auth login" -Reason "browser flow (if not authenticated)"
                }
                $plan.PhaseD.Steps += Format-PlanRow -Action INSTALL -Name "git clone" -Reason "$($Config.repository.url) -> $($Config.paths.clone_target)"
            }
            $junctionFull = Join-Path $Config.vault.path $Config.vault.junction_name
            if (Test-JunctionExists $junctionFull) {
                $plan.PhaseD.Steps += Format-PlanRow -Action SKIP    -Name "junction" -Reason "already exists: $junctionFull"
            } else {
                $plan.PhaseD.Steps += Format-PlanRow -Action INSTALL -Name "junction" -Reason "$junctionFull -> $($Config.paths.clone_target)"
            }
        }
    } else {
        $plan.PhaseD.Steps += "(setup.config.json missing - will be auto-generated from template before execution)"
    }

    # Phase E: optional tools + extensions. State matrix:
    #   installed              -> SKIP, 'already installed'
    #   not installed, enabled -> INSTALL, 'optional, enabled in config'
    #   not installed, disabled-> SKIP, 'optional, disabled in config'
    if ($Config) {
        foreach ($t in $script:OptionalTools) {
            $enabled = $false
            if ($Config.options.PSObject.Properties.Name -contains $t.OptKey) {
                $enabled = [bool]$Config.options.$($t.OptKey)
            }
            $installed = Test-OptionalToolInstalled $t
            if ($installed) {
                $plan.PhaseE.Steps += Format-PlanRow -Action SKIP    -Name $t.Display -Reason "already installed"
            } elseif ($enabled) {
                $plan.PhaseE.Steps += Format-PlanRow -Action INSTALL -Name $t.Display -Reason "optional, enabled in config"
            } else {
                $plan.PhaseE.Steps += Format-PlanRow -Action SKIP    -Name $t.Display -Reason "optional, disabled in config"
            }
        }
        if ($Config.vscode -and $Config.vscode.extensions) {
            $installedExts = @()
            if (Get-VSCodeCommand) { $installedExts = Get-VSCodeInstalledExtensions }
            foreach ($ext in $Config.vscode.extensions) {
                $extId = [string]$ext
                if ($installedExts -contains $extId) {
                    $plan.PhaseE.Steps += Format-PlanRow -Action SKIP    -Name "ext: $extId" -Reason "already installed"
                } else {
                    $plan.PhaseE.Steps += Format-PlanRow -Action INSTALL -Name "ext: $extId" -Reason "optional, enabled in config"
                }
            }
        }
    } else {
        $plan.PhaseE.Steps += "(setup.config.json missing - will be auto-generated)"
    }

    return $plan
}

function Show-AutoPlan {
    param($Plan)

    # FR-901: scan every step across all phases to find the longest name,
    # then use that width for every rendered row. Phase A's "Claude Code
    # extension" and Phase E's "ext: <long-vscode-id>" both end up aligned.
    $maxName = 0
    foreach ($k in $Plan.Keys) {
        foreach ($s in $Plan[$k].Steps) {
            if ($s -is [PSCustomObject] -and $s.PSObject.Properties.Name -contains "Name") {
                if ($s.Name.Length -gt $maxName) { $maxName = $s.Name.Length }
            }
        }
    }
    if ($maxName -lt 1) { $maxName = 36 }

    Write-Host ""
    Write-Host "StrictDocStarter will perform the following:"
    Write-Host ""
    foreach ($k in $Plan.Keys) {
        $phase = $Plan[$k]
        Write-Host "  $($phase.Name)"

        # FR-902: in Phase E (optional tools + extensions), present all
        # [SKIP] rows first, then all [INSTALL] rows, so the user can
        # quickly see what will actually be installed at the bottom of the
        # block. Other phases keep their original order (REQUIRED steps
        # follow a natural pre-req order).
        $steps = $phase.Steps
        if ($k -eq "PhaseE") {
            $steps = $steps | Sort-Object `
                @{Expression={
                    if ($_ -is [PSCustomObject] -and $_.PSObject.Properties.Name -contains "Action") {
                        if ($_.Action -eq "SKIP") { 0 } else { 1 }
                    } else {
                        2   # raw strings (e.g., "(setup.config.json missing...)") sort last
                    }
                }}, @{Expression={
                    if ($_ -is [PSCustomObject] -and $_.PSObject.Properties.Name -contains "Name") { $_.Name } else { [string]$_ }
                }}
        }

        foreach ($s in $steps) {
            if ($s -is [PSCustomObject] -and $s.PSObject.Properties.Name -contains "Action") {
                Write-Host "    - $(Format-PlanRowText -Step $s -NameWidth $maxName)"
            } else {
                Write-Host "    - $s"
            }
        }
        Write-Host ""
    }
}

function Read-YesConfirmation {
    param([string]$Prompt = "Proceed with the above? Type 'yes' to install, anything else to abort")
    Write-Host ""
    $reply = Read-Host $Prompt
    return ($reply -eq "yes")
}

function Invoke-PhaseA {
    Write-OnboardStep "Phase A: Claude Code (VS Code extension)"
    $allOk = $true

    if (-not (Install-VSCodeIfNeeded)) {
        Write-OnboardError "VS Code install failed; cannot proceed with extension"
        return $false
    }
    if (-not (Install-ClaudeCodeExtension)) {
        Write-OnboardWarn "Claude Code extension install reported failure"
        $allOk = $false
    }
    return $allOk
}

function Invoke-PhaseB {
    param([string]$PythonVersion = "3.13")
    Write-OnboardStep "Phase B: Required tools (Git / Python / gh)"
    $results = Install-RequiredTools -PythonVersion $PythonVersion
    $allOk = $true
    foreach ($k in $results.Keys) {
        if (-not $results[$k]) { $allOk = $false }
    }
    return $allOk
}

function Invoke-PhaseC {
    Write-OnboardStep "Phase C: StrictDoc (pip install strictdoc)"
    return Install-StrictDoc
}

function Test-PhaseDShouldSkip {
    param($Config)
    if (-not $Config) { return $true }
    # Explicit skip via config
    if ($Config.options.PSObject.Properties.Name -contains "skip_clone") {
        if ([bool]$Config.options.skip_clone) { return $true }
    }
    # Empty URL = skip
    if (-not $Config.repository.url) { return $true }
    return $false
}

function Invoke-PhaseD {
    param($Config)
    Write-OnboardStep "Phase D: git clone + Obsidian junction"
    if (-not $Config) {
        Write-OnboardError "No config available for Phase D"
        return $false
    }
    if (Test-PhaseDShouldSkip $Config) {
        Write-OnboardSkip "Phase D skipped (options.skip_clone=true or repository.url is empty)"
        return $true
    }
    $cloneOk = Invoke-GitClone -Url $Config.repository.url `
                               -Target $Config.paths.clone_target `
                               -Visibility $Config.repository.visibility
    $junctionOk = $true
    if ($cloneOk) {
        $junctionOk = Invoke-CreateJunction -VaultPath $Config.vault.path `
                                            -JunctionName $Config.vault.junction_name `
                                            -Target $Config.paths.clone_target
    } else {
        Write-OnboardWarn "Skipping junction creation because clone failed"
        $junctionOk = $false
    }
    return ($cloneOk -and $junctionOk)
}

function Invoke-PhaseE {
    param($Config)
    Write-OnboardStep "Phase E: Optional tools + VS Code extensions"
    if (-not $Config) {
        Write-OnboardError "No config available for Phase E"
        return $false
    }
    $toolResults = Install-OptionalTools -Config $Config
    Update-PathFromRegistry
    $extResults  = Install-VSCodeExtensions -Config $Config

    $allOk = $true
    foreach ($v in $toolResults.Values) { if (-not $v) { $allOk = $false } }
    foreach ($v in $extResults.Values)  { if (-not $v) { $allOk = $false } }
    return $allOk
}

function Invoke-Auto {
    [CmdletBinding()]
    param(
        [switch]$NonInteractive,
        [string]$PythonVersion = "3.13",
        [string]$ConfigPath = (Join-Path (Get-Location) "setup.config.json")
    )

    Write-OnboardStep "StrictDocStarter auto setup"

    # 1. Probe environment (silent check)
    $cc       = Get-ClaudeCodeStatus
    $required = Get-RequiredToolsStatus
    Write-OnboardInfo "Detected: VS Code=$($cc.VSCodeInstalled)  CC ext=$($cc.CCExtensionInstalled)  CC CLI=$($cc.CCCLIInstalled)"
    Write-OnboardInfo "Detected: Git=$($required.git.Installed)  Python=$($required.python.Installed)  gh=$($required.gh.Installed)"

    # 2. Resolve config (generate from template if missing, with defaults)
    $config = Resolve-AutoConfig -ConfigPath $ConfigPath

    # 3. Build and show plan
    $plan = Build-AutoPlan -PythonVersion $PythonVersion -Config $config
    Show-AutoPlan -Plan $plan

    # 3. Single yes confirmation (FR-804). FR-209: on non-yes input, show
    # the actionable abort guidance (config path + re-run command) via the
    # shared Show-AbortGuidance helper.
    # FR-700: if a proxy is detected (IE / env var / WinHTTP), emit a brief
    # warning BEFORE the yes prompt so the user can decide whether to abort
    # and configure proxies manually. Silent when no proxy detected.
    if ($NonInteractive) {
        Write-OnboardInfo "Non-interactive mode: skipping yes prompt"
    } else {
        Show-ProxyWarningIfDetected
        if (-not (Read-YesConfirmation)) {
            Show-AbortGuidance -ConfigPath $ConfigPath
            return $false
        }
    }

    # 4. Execute phases
    $summary = [ordered]@{}

    $summary["Phase A"] = Invoke-PhaseA
    $summary["Phase B"] = Invoke-PhaseB -PythonVersion $PythonVersion
    $summary["Phase C"] = Invoke-PhaseC
    $summary["Phase D"] = Invoke-PhaseD -Config $config
    $summary["Phase E"] = Invoke-PhaseE -Config $config

    # 5. Final summary (FR-504)
    Write-OnboardStep "Summary"
    foreach ($k in $summary.Keys) {
        $v = $summary[$k]
        if ($null -eq $v) {
            Write-Host "  $($k.PadRight(8)) : SKIP (not implemented)"
        } elseif ($v) {
            Write-Host "  $($k.PadRight(8)) : OK"
        } else {
            Write-Host "  $($k.PadRight(8)) : FAILED"
        }
    }

    # Overall result
    $hasFail = $false
    foreach ($v in $summary.Values) {
        if ($v -eq $false) { $hasFail = $true }
    }
    if ($hasFail) {
        Write-OnboardWarn "Some phases failed. See log for details: setup.log"
        return $false
    }
    Write-OnboardOk "Auto setup completed."
    return $true
}
