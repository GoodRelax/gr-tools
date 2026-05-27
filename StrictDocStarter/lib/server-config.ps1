# lib/server-config.ps1 - server.config.json gen / load / validate / editor launch.
# Functions: Initialize-ServerConfig, Get-ServerConfig, Open-EditorForConfig,
#            Expand-UserPlaceholdersInString.
# Spec: FR-201..213 (config management), FR-208 (Expand-UserPlaceholders).
# Output language: English ASCII only (per NFR-005 / ADR-008).
#
# NOTE: dot-sourced from manage-strictdoc.ps1 (not a module). Functions are
#       visible at the caller scope.

function Expand-UserPlaceholdersInString {
    # FR-208: replace <user> with $env:USERNAME.
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    return $Text -replace '<user>', $env:USERNAME
}

function Expand-PathPlaceholders {
    # Extended placeholder expansion. Supports:
    #   <user>          -> $env:USERNAME (FR-208)
    #   <starter_root>  -> absolute path of manage-strictdoc.bat's folder
    # The second placeholder lets server.config.template.json point at the
    # bundled samples (samples/hello-strictdoc) regardless of where the
    # user extracted the ZIP -- unzip and "press 1 to Start" just works.
    #
    # Note: use String.Replace() (literal, not regex) for $StarterRoot because
    # Windows paths contain backslashes which would be interpreted as escapes
    # by the -replace operator.
    param(
        [string]$Text,
        [string]$StarterRoot
    )
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    $expanded = $Text -replace '<user>', $env:USERNAME
    if (-not [string]::IsNullOrEmpty($StarterRoot)) {
        $expanded = $expanded.Replace('<starter_root>', $StarterRoot)
    }
    return $expanded
}

function Read-FileNoBom {
    param([Parameter(Mandatory)] [string]$Path)
    # Read UTF-8, strip BOM if present (FR-204 / Mi4).
    $raw = Get-Content -Raw -Encoding UTF8 -Path $Path -ErrorAction Stop
    if ($null -ne $raw -and $raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) {
        $raw = $raw.Substring(1)
    }
    return $raw
}

function Write-FileUtf8NoBom {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Content
    )
    # Write UTF-8 without BOM (PowerShell 5.1 compatibility).
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Initialize-ServerConfig {
    param(
        [Parameter(Mandatory)] [string]$TemplatePath,
        [Parameter(Mandatory)] [string]$ConfigPath,
        [string]$StarterRoot = ''
    )
    if (-not (Test-Path $TemplatePath)) {
        throw "Template not found: $TemplatePath"
    }
    # FR-201: copy template + expand placeholders + write UTF-8 BOM-less.
    # Placeholders: <user> (FR-208) and <starter_root> (samples auto-default).
    #
    # The template is JSON, so when substituting into the raw text we MUST
    # escape backslashes (Windows path separator) to \\ -- otherwise valid
    # Windows paths like 'C:\Users\good_' produce invalid JSON (\U is not a
    # valid JSON escape) and ConvertFrom-Json fails.
    $raw = Read-FileNoBom -Path $TemplatePath
    $userJson = $env:USERNAME
    $rootJson = if ([string]::IsNullOrEmpty($StarterRoot)) { '' } else { $StarterRoot.Replace('\', '\\') }
    $expanded = $raw.Replace('<user>', $userJson)
    if (-not [string]::IsNullOrEmpty($rootJson)) {
        $expanded = $expanded.Replace('<starter_root>', $rootJson)
    }
    Write-FileUtf8NoBom -Path $ConfigPath -Content $expanded
}

function New-ValidationResult {
    param(
        [bool]$Ok = $false,
        [string]$ErrorField = '',
        [string]$ErrorMessage = ''
    )
    return [pscustomobject]@{
        Ok           = $Ok
        ErrorField   = $ErrorField
        ErrorMessage = $ErrorMessage
    }
}

function Test-HostIsValid {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
    $isIPv4  = $Value -match '^\d{1,3}(\.\d{1,3}){3}$'
    $isLocal = ($Value -eq 'localhost')
    # M6: IPv6 requires at least one ':' to avoid matching bare hex tokens
    # like 'a' or ':'. Common literals such as '::', '::1', 'fe80::1' all
    # contain at least one ':' and only hex/':' chars.
    $isIPv6  = ($Value -match '^[0-9a-fA-F:]+$') -and ($Value.Contains(':'))
    return ($isIPv4 -or $isLocal -or $isIPv6)
}

function Get-ServerConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Path,
        [string]$StarterRoot = ''
    )

    $result = [pscustomobject]@{
        Config     = $null
        Validation = New-ValidationResult
    }

    if (-not (Test-Path $Path)) {
        $result.Validation = New-ValidationResult -ErrorField 'file' -ErrorMessage "config not found: $Path"
        return $result
    }

    # FR-204: read UTF-8, strip BOM, parse JSON.
    try {
        $raw = Read-FileNoBom -Path $Path
        $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        $result.Validation = New-ValidationResult -ErrorField 'parse' -ErrorMessage "JSON parse failed: $($_.Exception.Message)"
        return $result
    }

    # FR-208: expand <user> + <starter_root> on path fields before any
    # Test-Path / Start-Process invocation.
    $projectPath = Expand-PathPlaceholders -Text $parsed.project_path -StarterRoot $StarterRoot
    $outputPath  = Expand-PathPlaceholders -Text $parsed.output_path  -StarterRoot $StarterRoot

    # Coerce port to int (template may store as JSON number, but defend against string).
    $portValue = 0
    if ($null -ne $parsed.port) {
        [int]::TryParse($parsed.port.ToString(), [ref]$portValue) | Out-Null
    }

    $openBrowser = $false
    if ($parsed.PSObject.Properties['open_browser']) {
        $openBrowser = [bool]$parsed.open_browser
    }

    $config = [pscustomobject]@{
        project_path = $projectPath
        host         = $parsed.host
        port         = $portValue
        open_browser = $openBrowser
        output_path  = $outputPath
    }
    $result.Config = $config

    # FR-210: validation rules.
    if ([string]::IsNullOrWhiteSpace($projectPath)) {
        $result.Validation = New-ValidationResult -ErrorField 'project_path' -ErrorMessage "project_path is empty"
        return $result
    }
    if (-not (Test-Path $projectPath -PathType Container)) {
        $result.Validation = New-ValidationResult -ErrorField 'project_path' -ErrorMessage "project_path does not exist or is not a directory: $projectPath"
        return $result
    }
    if (-not (Test-HostIsValid -Value $config.host)) {
        $result.Validation = New-ValidationResult -ErrorField 'host' -ErrorMessage "host must be IPv4, localhost, or IPv6 literal (got: $($config.host))"
        return $result
    }
    if ($config.port -lt 1024 -or $config.port -gt 65535) {
        $result.Validation = New-ValidationResult -ErrorField 'port' -ErrorMessage "port must be an integer between 1024 and 65535 (got: $($config.port))"
        return $result
    }
    # open_browser: any value coerces to bool; no further check.
    # output_path: optional, no existence check (strictdoc will create).

    $result.Validation = New-ValidationResult -Ok $true
    return $result
}

function Open-EditorForConfig {
    param([Parameter(Mandatory)] [string]$Path)
    # FR-202 / FR-212: 'code' (with HasExited check) -> 'notepad' fallback.

    $codeCmd = Get-Command code -ErrorAction SilentlyContinue
    if ($codeCmd) {
        $eap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $proc = Start-Process -FilePath code -ArgumentList '--reuse-window', $Path -PassThru -ErrorAction Stop
            Start-Sleep -Seconds 1
            if ($null -ne $proc -and $proc.HasExited -and $proc.ExitCode -ne 0) {
                Write-Host "[INFO] 'code' exited with non-zero (code $($proc.ExitCode)). Falling back to notepad."
            } else {
                $ErrorActionPreference = $eap
                return
            }
        } catch {
            Write-Host "[INFO] 'code' launch failed: $($_.Exception.Message). Falling back to notepad."
        }
        $ErrorActionPreference = $eap
    }
    try {
        Start-Process -FilePath notepad -ArgumentList $Path -ErrorAction Stop | Out-Null
    } catch {
        Write-Host "[ERROR] Failed to launch any editor: $($_.Exception.Message)" -ForegroundColor Red
    }
}
