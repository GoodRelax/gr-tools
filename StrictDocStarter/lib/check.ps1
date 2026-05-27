# StrictDocStarter - lib/check.ps1
# Environment / proxy / SSL inspection detection.
# Writes env-report.json.
# All output is English ASCII only (per spec ADR-008).

function Get-WindowsVersionString {
    return [System.Environment]::OSVersion.Version.ToString()
}

function Get-PowerShellVersionString {
    return $PSVersionTable.PSVersion.ToString()
}

function Test-WingetAvailable {
    return [bool](Get-Command winget -ErrorAction SilentlyContinue)
}

function Get-WingetVersionString {
    try {
        $out = & winget --version 2>$null
        if ($out) { return ($out -replace '^v', '').Trim() }
    } catch {}
    return $null
}

function Get-IEProxySettings {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try {
        $s = Get-ItemProperty -Path $regPath -ErrorAction Stop
        return [pscustomobject]@{
            Enabled = [bool]($s.ProxyEnable -eq 1)
            Server  = if ($s.ProxyServer) { [string]$s.ProxyServer } else { "" }
            PacUrl  = if ($s.AutoConfigURL) { [string]$s.AutoConfigURL } else { "" }
        }
    } catch {
        return [pscustomobject]@{ Enabled = $false; Server = ""; PacUrl = "" }
    }
}

function Get-WinHTTPProxyString {
    try {
        $out = (& netsh winhttp show proxy 2>&1) -join "`n"
        if ($out) { return $out.Trim() }
    } catch {}
    return ""
}

function Get-ProxyHint {
    # FR-700: detect a proxy from IE settings / env vars / WinHTTP.
    # Returns the first hit as a single short string (suitable for one [WARN]
    # line). Returns $null if no proxy is detected anywhere -- the caller
    # MUST treat $null as "stay silent".
    # Priority order: IE proxy server > env HTTP_PROXY > env HTTPS_PROXY >
    # WinHTTP > IE PAC URL.
    $ie = Get-IEProxySettings
    if ($ie.Enabled -and $ie.Server) {
        return "IE proxy: $($ie.Server)"
    }
    if ($env:HTTP_PROXY)  { return "env HTTP_PROXY: $env:HTTP_PROXY" }
    if ($env:HTTPS_PROXY) { return "env HTTPS_PROXY: $env:HTTPS_PROXY" }
    $wh = Get-WinHTTPProxyString
    if ($wh -and ($wh -notmatch '(?i)Direct access')) {
        # WinHTTP output is multi-line; collapse to one line, take first
        # non-empty meaningful line for compactness.
        $line = ($wh -split "`r?`n" | Where-Object { $_ -and ($_ -notmatch '^\s*$') } | Select-Object -First 1)
        return "WinHTTP: $line"
    }
    if ($ie.PacUrl) { return "IE PAC URL: $($ie.PacUrl)" }
    return $null
}

function Show-ProxyWarningIfDetected {
    # FR-700: if a proxy is detected, emit 3 [WARN] lines (English ASCII /
    # ADR-008) pointing the user at README. Silent when no proxy detected.
    # Used by both 'auto' (just before Read-YesConfirmation) and 'dryrun'.
    $hint = Get-ProxyHint
    if (-not $hint) { return }
    Write-OnboardWarn "Proxy detected ($hint)."
    Write-OnboardWarn "StrictDocStarter does NOT configure proxies for git/pip/winget/code in v1.0."
    Write-OnboardWarn "See README 'Proxy / Corporate Network' for details and workarounds."
}

function Get-ExistingToolVersion {
    param([string]$Command, [string]$VersionArg = "--version")
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        return $null
    }
    try {
        # Capture all, then pick first -- piping to `Select -First 1` would
        # TerminateProcess the upstream exe (rg/jq/pwsh exhibit this) and
        # set $LASTEXITCODE=-1 even on success. See run-tests.ps1 Test-CmdWorks.
        $all = & $Command $VersionArg 2>&1
        $out = $all | Where-Object { $_ } | Select-Object -First 1
        if ($out) { return ([string]$out).Trim() }
    } catch {}
    return ""
}

function Get-ProxyAuthMethods {
    param([string]$ProxyServer)
    if (-not $ProxyServer) { return @() }
    try {
        $req = [System.Net.HttpWebRequest]::Create("http://www.microsoft.com/")
        $req.Method = "HEAD"
        $req.Timeout = 5000
        $req.Proxy = New-Object System.Net.WebProxy("http://$ProxyServer", $true)
        try {
            $resp = $req.GetResponse()
            $resp.Close()
            return @()
        } catch [System.Net.WebException] {
            $resp = $_.Exception.Response
            if ($resp -and [int]$resp.StatusCode -eq 407) {
                $headers = $resp.Headers.GetValues("Proxy-Authenticate")
                if ($headers) {
                    $methods = @()
                    foreach ($h in $headers) {
                        $m = ($h -split '\s+')[0].Trim()
                        if ($m -and ($methods -notcontains $m)) { $methods += $m }
                    }
                    return $methods
                }
            }
            return @()
        }
    } catch {
        return @()
    }
}

function Test-SSLInspection {
    # Inspect the TLS certificate issuer for a well-known site.
    # If the issuer is not a recognized public CA, suspect SSL inspection.
    $result = [pscustomobject]@{
        Detected = $false
        Issuer   = ""
    }
    try {
        $req = [System.Net.HttpWebRequest]::Create("https://www.microsoft.com/")
        $req.Method = "HEAD"
        $req.Timeout = 5000
        $issuerHolder = [pscustomobject]@{ Value = "" }
        $cb = {
            param($snd, $cert, $chain, $err)
            $issuerHolder.Value = $cert.Issuer
            return $true
        }
        $oldCb = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
        try {
            [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $cb
            $resp = $req.GetResponse()
            $resp.Close()
        } finally {
            [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $oldCb
        }
        $result.Issuer = $issuerHolder.Value
        $knownPublic = @(
            "DigiCert", "Microsoft", "GlobalSign", "Sectigo", "Let's Encrypt",
            "GeoTrust", "Entrust", "Amazon", "Google Trust"
        )
        $matched = $false
        foreach ($k in $knownPublic) {
            if ($issuerHolder.Value -match [regex]::Escape($k)) { $matched = $true; break }
        }
        if (-not $matched -and $issuerHolder.Value) {
            $result.Detected = $true
        }
    } catch {
        # Best-effort only
    }
    return $result
}

function Invoke-Check {
    [CmdletBinding()]
    param(
        [string]$OutputPath = (Join-Path (Get-Location) "env-report.json")
    )

    Write-OnboardStep "Environment check"

    $winVer = Get-WindowsVersionString
    $psVer  = Get-PowerShellVersionString
    $wingetOk = Test-WingetAvailable
    $wingetVer = if ($wingetOk) { Get-WingetVersionString } else { $null }

    $ie = Get-IEProxySettings
    $winhttp = Get-WinHTTPProxyString
    $envProxy = if ($env:HTTP_PROXY) { $env:HTTP_PROXY } else { "" }

    $authMethods = @()
    if ($ie.Enabled -and $ie.Server) {
        Write-OnboardInfo "Probing proxy authentication methods..."
        $authMethods = Get-ProxyAuthMethods -ProxyServer $ie.Server
    }

    Write-OnboardInfo "Probing SSL inspection..."
    $ssl = Test-SSLInspection

    $recommended = "none"
    if ($ie.Enabled) {
        if ($authMethods.Count -gt 0 -and ($authMethods -contains "NTLM" -or $authMethods -contains "Negotiate")) {
            $recommended = "local"
        } else {
            $recommended = "env"
        }
    }

    $report = [ordered]@{
        "_comment"          = "Generated by 'setup-strictdoc.bat check'. Do not edit by hand."
        windows_version     = $winVer
        powershell_version  = $psVer
        winget_available    = $wingetOk
        winget_version      = $wingetVer

        proxy = [ordered]@{
            ie_proxy_server         = $ie.Server
            ie_proxy_enabled        = $ie.Enabled
            pac_url                 = $ie.PacUrl
            winhttp_proxy           = $winhttp
            env_http_proxy          = $envProxy
            auth_methods            = $authMethods
            ssl_inspection_detected = $ssl.Detected
            cert_issuer             = $ssl.Issuer
        }

        recommended_proxy_mode = $recommended

        existing_tools = [ordered]@{
            git    = Get-ExistingToolVersion "git"
            python = Get-ExistingToolVersion "python"
            node   = Get-ExistingToolVersion "node"
            vscode = Get-ExistingToolVersion "code"
            gh     = Get-ExistingToolVersion "gh"
            rg     = Get-ExistingToolVersion "rg"
            jq     = Get-ExistingToolVersion "jq"
        }
    }

    try {
        $json = $report | ConvertTo-Json -Depth 10
        Set-Content -Path $OutputPath -Value $json -Encoding UTF8 -ErrorAction Stop
        Write-OnboardOk "Wrote $OutputPath"
    } catch {
        Write-OnboardError "Failed to write env-report.json: $($_.Exception.Message)"
        return $false
    }

    # Print summary
    Write-Host ""
    Write-Host "  Windows:       $winVer"
    Write-Host "  PowerShell:    $psVer"
    Write-Host "  winget:        $(if ($wingetOk) { $wingetVer } else { 'NOT FOUND' })"
    if ($ie.Enabled) {
        Write-Host "  Proxy:         $($ie.Server) (enabled)"
        if ($authMethods.Count -gt 0) {
            Write-Host "  Auth methods:  $($authMethods -join ', ')"
        }
    } else {
        Write-Host "  Proxy:         (none)"
    }
    Write-Host "  SSL inspection: $(if ($ssl.Detected) { 'DETECTED (' + $ssl.Issuer + ')' } else { 'none' })"
    Write-Host "  Recommended proxy mode: $recommended"
    Write-Host ""
    Write-Host "Existing tools:"
    foreach ($k in $report.existing_tools.Keys) {
        $v = $report.existing_tools[$k]
        $label = $k.PadRight(8)
        if ($v) {
            Write-Host "  $label : $v"
        } else {
            Write-Host "  $label : (not installed)"
        }
    }
    Write-Host ""

    # FR-107: refuse to run on Windows older than 11
    $verObj = [Version]$winVer
    if ($verObj.Major -lt 10 -or ($verObj.Major -eq 10 -and $verObj.Build -lt 22000)) {
        Write-OnboardError "Windows 11 or later required. Detected: $winVer"
        return $false
    }
    if (-not $wingetOk) {
        Write-OnboardError "winget not found. StrictDocStarter requires winget."
        return $false
    }

    return $true
}
