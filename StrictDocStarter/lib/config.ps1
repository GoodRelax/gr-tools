# StrictDocStarter - lib/config.ps1
# Generates setup.config.json from template, asks Python version, opens editor,
# waits for 'yes' confirmation. (Spec FR-201 to FR-207, ADR-009)

function Read-PythonVersionChoice {
    Write-Host ""
    Write-Host "Python version to install:"
    Write-Host "  [1] 3.13   (recommended, stable as of spec)"
    Write-Host "  [2] latest (auto-detect newest in winget, less reproducible)"
    Write-Host "  [3] custom (type version like 3.12 or 3.14)"
    $choice = Read-Host "Choose (1-3) [default: 1]"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

    switch ($choice.Trim()) {
        "1" { return "3.13" }
        "2" { return "latest" }
        "3" {
            $custom = Read-Host "Type Python version (e.g. 3.14)"
            if ([string]::IsNullOrWhiteSpace($custom)) { return "3.13" }
            return $custom.Trim()
        }
        default {
            Write-OnboardWarn "Invalid choice. Defaulting to 3.13."
            return "3.13"
        }
    }
}

function Merge-EnvReportHints {
    param(
        [Parameter(Mandatory)] $Config,
        [Parameter(Mandatory)] [string]$EnvReportPath
    )
    if (-not (Test-Path $EnvReportPath)) { return $Config }
    try {
        $env = Get-Content $EnvReportPath -Raw | ConvertFrom-Json
        if ($env.recommended_proxy_mode) {
            $Config.proxy.mode = [string]$env.recommended_proxy_mode
            Write-OnboardInfo "Applied recommended proxy mode from env-report.json: $($env.recommended_proxy_mode)"
        }
        if ($env.proxy -and $env.proxy.ie_proxy_server) {
            # Best-effort: parse host:port
            $parts = ([string]$env.proxy.ie_proxy_server) -split ':'
            if ($parts.Count -ge 1 -and $parts[0]) { $Config.proxy.host = $parts[0] }
            if ($parts.Count -ge 2 -and $parts[1]) {
                $portVal = 0
                if ([int]::TryParse($parts[1], [ref]$portVal)) { $Config.proxy.port = $portVal }
            }
        }
        if ($env.proxy -and $env.proxy.ssl_inspection_detected -and $env.proxy.cert_issuer) {
            Write-OnboardWarn "SSL inspection detected by 'check'. You may need to set proxy.ca_cert_path."
        }
    } catch {
        Write-OnboardWarn "Failed to read env-report.json: $($_.Exception.Message)"
    }
    return $Config
}

function Expand-UserPlaceholders {
    param([Parameter(Mandatory)] $Config)
    $u = $env:USERNAME
    if (-not $u) { return $Config }
    if ($Config.paths -and $Config.paths.clone_target) {
        $Config.paths.clone_target = ([string]$Config.paths.clone_target) -replace '<user>', $u
    }
    if ($Config.vault -and $Config.vault.path) {
        $Config.vault.path = ([string]$Config.vault.path) -replace '<user>', $u
    }
    return $Config
}

function Show-AbortGuidance {
    # FR-209: shared abort message used by both auto.ps1 (Read-YesConfirmation)
    # and config.ps1 (edit-then-yes confirm). Prints reason + absolute config
    # path + re-run command + idempotency note. All lines use Write-StrictDocStarter*
    # so they land in setup.log (FR-501) with the same [WARN]/[INFO]
    # prefixes -- grep/log analysis stays consistent.
    # ASCII only (ADR-008 / NFR-006).
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$ConfigPath,
        [string]$Reason = "'yes' not entered"
    )
    # Resolve to absolute path so users can copy-paste. Two-stage fallback:
    # (1) Resolve-Path if file exists, (2) [System.IO.Path]::GetFullPath for
    # the non-existent / racy case. Final fallback: the input string as-is.
    $absPath = $ConfigPath
    try {
        if (Test-Path $ConfigPath) {
            $absPath = (Resolve-Path $ConfigPath -ErrorAction Stop).Path
        } else {
            $absPath = [System.IO.Path]::GetFullPath($ConfigPath)
        }
    } catch {
        try { $absPath = [System.IO.Path]::GetFullPath($ConfigPath) } catch {}
    }
    Write-OnboardWarn "Aborted - $Reason."
    Write-OnboardInfo "To customize installation:"
    Write-OnboardInfo "  1. Edit setup.config.json (path shown below)"
    Write-OnboardInfo "  2. Re-run setup-strictdoc.bat (idempotent - already-installed tools are skipped)"
    Write-OnboardInfo "Config: $absPath"
}

function Get-EditorCommand {
    if (Get-Command code -ErrorAction SilentlyContinue) { return "code" }
    return "notepad"
}

function Invoke-Config {
    [CmdletBinding()]
    param(
        [string]$ConfigPath   = (Join-Path (Get-Location) "setup.config.json"),
        [string]$TemplatePath = $null,
        [string]$EnvReportPath = (Join-Path (Get-Location) "env-report.json"),
        [switch]$ForceConfig,
        [switch]$NonInteractive
    )

    Write-OnboardStep "Configuration"

    if (-not $TemplatePath) {
        $TemplatePath = Join-Path $script:OnboardRoot "setup.config.template.json"
    }

    if (-not (Test-Path $TemplatePath)) {
        Write-OnboardError "Template not found: $TemplatePath"
        return $false
    }

    if ((Test-Path $ConfigPath) -and -not $ForceConfig) {
        Write-OnboardSkip "setup.config.json already exists. Use -ForceConfig to regenerate."
        # Still validate it
        try {
            $null = Get-Content $ConfigPath -Raw | ConvertFrom-Json
            Write-OnboardOk "Existing config is valid JSON."
            return $true
        } catch {
            Write-OnboardError "Existing config is invalid JSON: $($_.Exception.Message)"
            return $false
        }
    }

    # Load template
    try {
        $config = Get-Content $TemplatePath -Raw | ConvertFrom-Json
    } catch {
        Write-OnboardError "Failed to parse template: $($_.Exception.Message)"
        return $false
    }

    # Python version dialog (FR-202)
    if ($NonInteractive) {
        # Keep template default
    } else {
        $pyVer = Read-PythonVersionChoice
        $config.python.version = $pyVer
    }

    # Expand <user>
    $config = Expand-UserPlaceholders $config

    # Apply env-report hints (FR-207)
    $config = Merge-EnvReportHints -Config $config -EnvReportPath $EnvReportPath

    # Save
    try {
        ($config | ConvertTo-Json -Depth 10) | Set-Content -Path $ConfigPath -Encoding UTF8 -ErrorAction Stop
        Write-OnboardOk "Wrote $ConfigPath"
    } catch {
        Write-OnboardError "Failed to write config: $($_.Exception.Message)"
        return $false
    }

    if ($NonInteractive) {
        Write-OnboardInfo "Non-interactive mode: skipping editor and confirmation."
        return $true
    }

    # Open editor (FR-203)
    $editor = Get-EditorCommand
    Write-OnboardInfo "Opening $ConfigPath in $editor (close the file when done)..."
    try {
        Start-Process -FilePath $editor -ArgumentList $ConfigPath -ErrorAction Stop | Out-Null
    } catch {
        Write-OnboardWarn "Could not start editor '$editor': $($_.Exception.Message). Edit $ConfigPath manually."
    }

    # Confirm loop (FR-209: any non-yes/non-no input loops; explicit 'no'
    # routes through Show-AbortGuidance so the user gets the path + re-run
    # instructions instead of a bare "Aborted by user.").
    while ($true) {
        $reply = Read-Host "Edit the file, then type 'yes' to confirm (or 'no' to abort)"
        if ($reply -eq "yes") { break }
        if ($reply -eq "no") {
            Show-AbortGuidance -ConfigPath $ConfigPath -Reason "'no' typed at config confirm prompt"
            return $false
        }
        Write-Host "Type 'yes' or 'no'."
    }

    # Validate after edit
    try {
        $null = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        Write-OnboardOk "Configuration confirmed (valid JSON)."
        return $true
    } catch {
        Write-OnboardError "Config is not valid JSON after edit: $($_.Exception.Message)"
        Write-OnboardError "Fix $ConfigPath and re-run 'setup-strictdoc.bat config'."
        return $false
    }
}
