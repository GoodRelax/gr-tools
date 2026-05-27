# StrictDocStarter - lib/clone.ps1
# Repository clone + Obsidian vault junction.
# Spec refs: FR-401 to FR-404

function Test-RepoCloned {
    param([string]$Target)
    if (-not (Test-Path $Target)) { return $false }
    return (Test-Path (Join-Path $Target ".git"))
}

function Test-JunctionExists {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    try {
        $item = Get-Item $Path -Force -ErrorAction Stop
        return ($item.LinkType -eq "Junction")
    } catch {
        return $false
    }
}

function Invoke-GhAuthIfNeeded {
    # Best-effort gh auth check for private repos. Skips silently if gh not installed.
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-OnboardWarn "gh CLI not installed; cannot pre-auth for private repos"
        return $true  # let git try anyway
    }
    & gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OnboardSkip "gh already authenticated"
        return $true
    }
    Write-OnboardInfo "Running 'gh auth login' (browser flow)..."
    & gh auth login
    return ($LASTEXITCODE -eq 0)
}

function Invoke-GitClone {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Url,
        [Parameter(Mandatory)] [string]$Target,
        [string]$Visibility = "public"
    )

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-OnboardError "git not found on PATH; cannot clone"
        return $false
    }

    if (Test-RepoCloned $Target) {
        Write-OnboardSkip "Repository already cloned at: $Target"
        return $true
    }
    if (Test-Path $Target) {
        Write-OnboardError "Target exists but is not a git repo: $Target"
        return $false
    }

    if ($Visibility -eq "private") {
        if (-not (Invoke-GhAuthIfNeeded)) {
            Write-OnboardError "gh authentication failed; aborting clone"
            return $false
        }
    }

    $parent = Split-Path -Parent $Target
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Write-OnboardInfo "git clone $Url -> $Target"

    # Disable interactive credential prompts for this process. Otherwise, if
    # the URL points to a non-existent or auth-protected repo, Git Credential
    # Manager will pop up a GUI sign-in dialog and block the script. Users
    # without a GitHub account would have no way to proceed.
    $oldGitTerm  = $env:GIT_TERMINAL_PROMPT
    $oldGcmInt   = $env:GCM_INTERACTIVE
    $env:GIT_TERMINAL_PROMPT = "0"
    $env:GCM_INTERACTIVE     = "Never"

    # Temporarily relax ErrorActionPreference so that git's stderr progress
    # messages ("Cloning into ...") are not treated as terminating errors.
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        & git clone $Url $Target 2>&1 | ForEach-Object { Write-Host "  $_" }
        $exit = $LASTEXITCODE
        if ($exit -ne 0) {
            Write-OnboardError "git clone failed (exit $exit). If you do not have a GitHub account or the URL is wrong, edit setup.config.json or set options.skip_clone=true."
            return $false
        }
    } catch {
        Write-OnboardError "git clone threw: $($_.Exception.Message)"
        return $false
    } finally {
        $env:GIT_TERMINAL_PROMPT = $oldGitTerm
        $env:GCM_INTERACTIVE     = $oldGcmInt
        $ErrorActionPreference   = $oldEAP
    }
    Write-OnboardOk "Cloned to $Target"
    return $true
}

function Invoke-CreateJunction {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$VaultPath,
        [Parameter(Mandatory)] [string]$JunctionName,
        [Parameter(Mandatory)] [string]$Target
    )

    $junctionFull = Join-Path $VaultPath $JunctionName

    if (Test-JunctionExists $junctionFull) {
        Write-OnboardSkip "Junction already exists: $junctionFull"
        return $true
    }
    if (Test-Path $junctionFull) {
        Write-OnboardWarn "Path exists but is not a junction: $junctionFull (skip)"
        return $false
    }
    if (-not (Test-Path $Target)) {
        Write-OnboardError "Junction target does not exist: $Target"
        return $false
    }

    if (-not (Test-Path $VaultPath)) {
        Write-OnboardInfo "Creating vault parent: $VaultPath"
        New-Item -ItemType Directory -Path $VaultPath -Force | Out-Null
    }

    Write-OnboardInfo "Creating junction: $junctionFull -> $Target"
    try {
        New-Item -ItemType Junction -Path $junctionFull -Target $Target -ErrorAction Stop | Out-Null
        Write-OnboardOk "Junction created"
        return $true
    } catch {
        Write-OnboardError "Junction creation failed: $($_.Exception.Message)"
        return $false
    }
}

function Get-ClonePlan {
    [CmdletBinding()]
    param(
        [string]$ConfigPath = (Join-Path (Get-Location) "setup.config.json")
    )
    if (-not (Test-Path $ConfigPath)) {
        return @("(setup.config.json not found - run 'setup-strictdoc.bat config' first)")
    }
    try {
        $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    } catch {
        return @("(invalid setup.config.json: $($_.Exception.Message))")
    }

    # Phase D skip semantics (mirror Test-PhaseDShouldSkip in lib/auto.ps1).
    # Must run before any Test-Path call: the template ships with '<user>'
    # placeholders which are invalid Windows filename chars.
    $skipClone = $false
    if ($cfg.options.PSObject.Properties.Name -contains "skip_clone") {
        $skipClone = [bool]$cfg.options.skip_clone
    }
    if ($skipClone) {
        return @("Phase D skipped (options.skip_clone=true)")
    }
    if (-not $cfg.repository.url) {
        return @("Phase D skipped (repository.url is empty)")
    }

    # Expand <user> so Test-Path / Join-Path work safely.
    $u = $env:USERNAME
    $cloneTarget  = ([string]$cfg.paths.clone_target) -replace '<user>', $u
    $vaultPath    = ([string]$cfg.vault.path) -replace '<user>', $u
    $junctionName = [string]$cfg.vault.junction_name

    $plan = @()
    if (Test-RepoCloned $cloneTarget) {
        $plan += "git clone already done at $cloneTarget - skip"
    } else {
        if ($cfg.repository.visibility -eq "private") {
            $plan += "gh auth login (browser flow, if not already authenticated)"
        }
        $plan += "git clone $($cfg.repository.url) $cloneTarget"
    }
    $junctionFull = Join-Path $vaultPath $junctionName
    if (Test-JunctionExists $junctionFull) {
        $plan += "junction $junctionFull already exists - skip"
    } else {
        $plan += "mklink /J `"$junctionFull`" `"$cloneTarget`""
    }
    return $plan
}

function Invoke-Clone {
    [CmdletBinding()]
    param(
        [string]$ConfigPath = (Join-Path (Get-Location) "setup.config.json"),
        [switch]$DryRun
    )
    Write-OnboardStep "Clone"

    if ($DryRun) {
        $plan = Get-ClonePlan -ConfigPath $ConfigPath
        Write-OnboardInfo "Planned clone actions:"
        foreach ($line in $plan) { Write-Host "  - $line" }
        return $true
    }

    if (-not (Test-Path $ConfigPath)) {
        Write-OnboardError "setup.config.json not found: $ConfigPath"
        return $false
    }
    try {
        $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    } catch {
        Write-OnboardError "Invalid setup.config.json: $($_.Exception.Message)"
        return $false
    }

    $cloneOk = Invoke-GitClone -Url $cfg.repository.url -Target $cfg.paths.clone_target -Visibility $cfg.repository.visibility
    $junctionOk = Invoke-CreateJunction -VaultPath $cfg.vault.path -JunctionName $cfg.vault.junction_name -Target $cfg.paths.clone_target
    return ($cloneOk -and $junctionOk)
}
