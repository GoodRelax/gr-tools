# lib/server-process.ps1 - StrictDoc server lifecycle (start / stop / status / logs).
# Functions: Get-ServerState, Invoke-StartAction, Invoke-StopAction,
#            Show-ServerStatusDetail, Show-ServerLogs, Show-MenuHeader.
# Spec: FR-301..312 (start), FR-401..411 (stop), FR-501..509 (5-state),
#       FR-601..604 (logs), FR-701..706 (PID/log paths), FR-901..905 (errors).
# Output language: English ASCII only (per NFR-005 / ADR-008).
#
# IMPORTANT (Glossary, 1.7 Constraints):
#   - $pid is a PowerShell RESERVED automatic variable (current process PID).
#     Use $serverPid for the strictdoc server process PID.
#   - $host is also reserved; use $bindHost / $urlHost for server host strings.

function Get-LocalAppDataDir {
    $dir = Join-Path $env:LOCALAPPDATA 'StrictDocStarter'
    if (-not (Test-Path $dir)) {
        # FR-310: auto-create on first start.
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
    return $dir
}

# B1: pre-quote argument if it contains whitespace.
# PowerShell 5.1 Start-Process -ArgumentList @(...) does NOT auto-quote
# array elements containing spaces -- e.g. "C:\My Project" becomes 2 args.
function Quote-ArgIfNeeded {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return $Value }
    if ($Value -match '\s') { return '"' + $Value + '"' }
    return $Value
}

# M3: resolve strictdoc to an absolute path so Start-Process CreateProcess
# does not fail in unusual PATH/venv states. Returns $null if not found.
function Resolve-StrictDocExecutable {
    $cmd = Get-Command strictdoc -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return $null }
    return $cmd.Source
}

# Mi4: shared helper for opening the StrictDoc URL in default browser.
function Open-BrowserForConfig {
    param($Config)
    $url = Get-BrowserOpenUrl -Config $Config
    try {
        Start-Process $url -ErrorAction Stop
        Write-Host "[INFO]  Opened browser at $url"
    } catch {
        Write-Host "[WARN]  Failed to open browser: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Get-PidFilePath    { param([int]$Port) Join-Path (Get-LocalAppDataDir) ("server-{0}.pid"     -f $Port) }
function Get-StdoutLogPath  { param([int]$Port) Join-Path (Get-LocalAppDataDir) ("server-{0}.log"     -f $Port) }
function Get-StderrLogPath  { param([int]$Port) Join-Path (Get-LocalAppDataDir) ("server-{0}.err.log" -f $Port) }

function Read-PidFile {
    # FR-704: read 1-line integer, trailing newline tolerant.
    param([Parameter(Mandatory)] [string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    try {
        $line = (Get-Content -Path $Path -TotalCount 1 -ErrorAction Stop)
        if ($null -eq $line) { return $null }
        $trimmed = $line.ToString().Trim()
        $parsedPid = 0
        if ([int]::TryParse($trimmed, [ref]$parsedPid)) {
            return $parsedPid
        }
    } catch {}
    return $null
}

function Test-ProcessIsStrictdoc {
    # FR-403 + FR-905: CommandLine contains "strictdoc" (case-insensitive).
    # WMI failure / empty CommandLine -> treat as NOT strictdoc (safe side).
    param([int]$ProcessId)
    try {
        $procInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        if ($null -eq $procInfo) { return $false }
        $cmdLine = $procInfo.CommandLine
        if ([string]::IsNullOrEmpty($cmdLine)) { return $false }
        return ($cmdLine -match '(?i)strictdoc')
    } catch {
        return $false
    }
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)
    try {
        $procInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        if ($null -ne $procInfo) { return $procInfo.CommandLine }
    } catch {}
    return '<unavailable>'
}

function Get-PortOwner {
    # FR-402 / FR-506: returns @{ Pid; Name } or $null if no LISTEN, or
    # @{ Pid=0; Name='<unknown owner>' } if LISTEN but OwningProcess not available.
    # M1: when host=0.0.0.0 LISTENs on both IPv4 and IPv6, multiple rows can be
    # returned; pick the first row that has a valid OwningProcess.
    param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($null -eq $conns) { return $null }
        $validConn = $conns | Where-Object {
            $null -ne $_.OwningProcess -and [int]$_.OwningProcess -gt 0
        } | Select-Object -First 1
        if ($null -ne $validConn) {
            $ownerPid = [int]$validConn.OwningProcess
            $procName = '<unknown>'
            try {
                $p = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
                if ($null -ne $p) { $procName = $p.ProcessName }
            } catch {}
            return [pscustomobject]@{ Pid = $ownerPid; Name = $procName }
        }
        # No row has a usable OwningProcess but there IS a LISTEN -- unknown owner.
        $anyConn = $conns | Select-Object -First 1
        if ($null -ne $anyConn) {
            return [pscustomobject]@{ Pid = 0; Name = '<unknown owner>' }
        }
        return $null
    } catch {
        return $null
    }
}

function Get-ServerState {
    # FR-501..506: returns one of RUNNING / STARTING / STOPPED / STALE_PID_FILE / OTHER_OWNS_PORT.
    param($Config)

    $port = [int]$Config.port
    $pidFile = Get-PidFilePath -Port $port
    $serverPid = Read-PidFile -Path $pidFile
    $portOwner = Get-PortOwner -Port $port

    $state = [pscustomobject]@{
        Status      = 'STOPPED'
        Pid         = $null
        Port        = $port
        Uptime      = $null
        ElapsedSecs = $null
        LogPath     = Get-StdoutLogPath -Port $port
        ErrLogPath  = Get-StderrLogPath -Port $port
        OwnerName   = $null
        Detail      = ''
    }

    if ($null -ne $serverPid) {
        # PID file exists; classify by process + port state.
        $proc = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
        if ($null -eq $proc) {
            $state.Status = 'STALE_PID_FILE'
            $state.Pid = $serverPid
            $state.Detail = "PID $serverPid does not exist"
            return $state
        }
        if (-not (Test-ProcessIsStrictdoc -ProcessId $serverPid)) {
            $state.Status = 'STALE_PID_FILE'
            $state.Pid = $serverPid
            $state.Detail = "PID $serverPid is not a strictdoc process"
            return $state
        }
        # PID alive + strictdoc; check LISTEN.
        $portListening = ($null -ne $portOwner -and $portOwner.Pid -eq $serverPid)
        if ($portListening) {
            $state.Status = 'RUNNING'
            $state.Pid = $serverPid
            try { $state.Uptime = (Get-Date) - $proc.StartTime } catch {}
            return $state
        }
        # Not LISTEN yet: STARTING if <30s, STALE otherwise (FR-503 / FR-505).
        $elapsed = 9999
        try { $elapsed = [int]((Get-Date) - $proc.StartTime).TotalSeconds } catch {}
        if ($elapsed -lt 30) {
            $state.Status = 'STARTING'
            $state.Pid = $serverPid
            $state.ElapsedSecs = $elapsed
            return $state
        } else {
            $state.Status = 'STALE_PID_FILE'
            $state.Pid = $serverPid
            $state.Detail = "process alive but not listening (elapsed ${elapsed}s)"
            return $state
        }
    }

    # No PID file.
    if ($null -ne $portOwner) {
        $state.Status = 'OTHER_OWNS_PORT'
        $state.Pid = $portOwner.Pid
        $state.OwnerName = $portOwner.Name
        return $state
    }

    return $state
}

function Format-Uptime {
    param($Span)
    if ($null -eq $Span) { return '00:00:00' }
    if ($Span.Days -gt 0) {
        return ("{0}.{1:D2}:{2:D2}:{3:D2}" -f $Span.Days, $Span.Hours, $Span.Minutes, $Span.Seconds)
    }
    return ("{0:D2}:{1:D2}:{2:D2}" -f $Span.Hours, $Span.Minutes, $Span.Seconds)
}

function Get-BrowserOpenUrl {
    # FR-307 / FR-308: 0.0.0.0 and :: get rewritten to 127.0.0.1.
    param($Config)
    $urlHost = $Config.host
    if ($urlHost -eq '0.0.0.0' -or $urlHost -eq '::') { $urlHost = '127.0.0.1' }
    return ("http://{0}:{1}/" -f $urlHost, $Config.port)
}

function Show-MenuHeader {
    param(
        [Parameter(Mandatory)] [string]$ConfigPath,
        $Config,
        $Validation,
        $ServerState
    )
    $line = '=' * 60
    Write-Host $line
    Write-Host "                StrictDocStarter Server Menu"
    Write-Host $line
    Write-Host "Config:  $ConfigPath"
    if ($null -ne $Config) {
        Write-Host "Project: $($Config.project_path)"
        Write-Host "Host:    $($Config.host)"
        Write-Host "Port:    $($Config.port)"
    }
    if ($null -ne $Validation -and -not $Validation.Ok) {
        Write-Host ""
        Write-Host "[CONFIG ERROR] $($Validation.ErrorField): $($Validation.ErrorMessage)" -ForegroundColor Red
        return
    }
    if ($null -eq $ServerState) { return }
    $tag = "[$($ServerState.Status)]"
    switch ($ServerState.Status) {
        'RUNNING' {
            $up = Format-Uptime -Span $ServerState.Uptime
            Write-Host "Status:  $tag PID $($ServerState.Pid) (uptime: $up)" -ForegroundColor Green
        }
        'STARTING' {
            Write-Host "Status:  $tag PID $($ServerState.Pid) (waiting for LISTEN, $($ServerState.ElapsedSecs)s/30s)" -ForegroundColor Yellow
        }
        'STOPPED' {
            Write-Host "Status:  $tag" -ForegroundColor Gray
        }
        'STALE_PID_FILE' {
            Write-Host "Status:  $tag $($ServerState.Detail)" -ForegroundColor Yellow
        }
        'OTHER_OWNS_PORT' {
            $owner = $ServerState.OwnerName
            if ([string]::IsNullOrEmpty($owner)) { $owner = '<unknown owner>' }
            $ownerPid = $ServerState.Pid
            $pidText = if ($ownerPid -gt 0) { "PID $ownerPid" } else { 'PID unknown' }
            Write-Host "Status:  $tag port $($ServerState.Port) is in use by $owner ($pidText)" -ForegroundColor Yellow
        }
    }
}

function Wait-ForPortListen {
    # FR-303 (a): wait up to 30s for LISTEN.
    param([int]$Port, [int]$TimeoutSec = 30)
    for ($i = 0; $i -lt $TimeoutSec; $i++) {
        if ($null -ne (Get-PortOwner -Port $Port)) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Wait-ForHttpReady {
    # FR-303 (b): wait up to 5s for HTTP response (any status code counts as ready).
    param([string]$BindHost, [int]$Port, [int]$TimeoutSec = 5)
    $urlHost = $BindHost
    if ($urlHost -eq '0.0.0.0' -or $urlHost -eq '::') { $urlHost = '127.0.0.1' }
    $url = ("http://{0}:{1}/" -f $urlHost, $Port)
    for ($i = 0; $i -lt $TimeoutSec; $i++) {
        try {
            $null = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            return $true
        } catch {
            # 4xx / 5xx responses are still "server responding" -> ready.
            if ($null -ne $_.Exception -and $null -ne $_.Exception.Response) {
                return $true
            }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Start-StrictDocServerProcess {
    # FR-301..311.
    param($Config)
    $port      = [int]$Config.port
    $stdoutLog = Get-StdoutLogPath -Port $port
    $stderrLog = Get-StderrLogPath -Port $port
    $pidFile   = Get-PidFilePath  -Port $port

    $null = Get-LocalAppDataDir  # ensure dir (FR-310)

    # FR-309: append separator line BEFORE Start-Process (race avoidance).
    $sep = ("=== Server started {0} ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    try { Add-Content -Path $stdoutLog -Value $sep -Encoding UTF8 -ErrorAction SilentlyContinue } catch {}

    # M3: resolve strictdoc absolute path to avoid CreateProcess PATH issues.
    $strictdocExe = Resolve-StrictDocExecutable
    if ($null -eq $strictdocExe) {
        Write-Host "[ERROR] strictdoc not found on PATH. Run setup-strictdoc.bat first, or activate the venv that has strictdoc installed." -ForegroundColor Red
        return $false
    }

    # FR-301 + B1: launch strictdoc with separate stdout/stderr redirect.
    # Pre-quote path args because PowerShell 5.1 Start-Process -ArgumentList
    # does NOT auto-quote array elements containing whitespace.
    $argList = @(
        'server',
        (Quote-ArgIfNeeded $Config.project_path),
        '--host', $Config.host,
        '--port', $port.ToString()
    )
    if (-not [string]::IsNullOrWhiteSpace($Config.output_path)) {
        $argList += @('--output-path', (Quote-ArgIfNeeded $Config.output_path))
    }

    $eap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $proc = $null
    try {
        $proc = Start-Process -FilePath $strictdocExe `
            -ArgumentList $argList `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError  $stderrLog `
            -PassThru -ErrorAction Stop
    } catch {
        Write-Host "[ERROR] Failed to launch strictdoc: $($_.Exception.Message)" -ForegroundColor Red
        $ErrorActionPreference = $eap
        return $false
    }
    $ErrorActionPreference = $eap

    if ($null -eq $proc) {
        Write-Host "[ERROR] Start-Process returned null (strictdoc launch failed)" -ForegroundColor Red
        return $false
    }

    # FR-302: write PID file with trailing newline (Set-Content adds newline by default).
    try {
        Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII -ErrorAction Stop
    } catch {
        Write-Host "[ERROR] Failed to write PID file: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }

    Write-Host "[INFO]  strictdoc launched (PID $($proc.Id)). Waiting for port $port to LISTEN..."

    # FR-303 (a): port LISTEN.
    if (-not (Wait-ForPortListen -Port $port -TimeoutSec 30)) {
        Write-Host "[WARN]  Timeout waiting for server to listen. Check Logs (menu 4) for details." -ForegroundColor Yellow
        return $false
    }

    # pip-generated 'strictdoc.exe' is a launcher that spawns python.exe as a
    # child; the child owns the LISTEN socket. After LISTEN is confirmed,
    # update the PID file to point at the actual listener so subsequent
    # Status / Stop track the correct process (FR-302 amendment).
    $listenerOwner = Get-PortOwner -Port $port
    if ($null -ne $listenerOwner -and $listenerOwner.Pid -gt 0 -and $listenerOwner.Pid -ne $proc.Id) {
        if (Test-ProcessIsStrictdoc -ProcessId $listenerOwner.Pid) {
            try {
                Set-Content -Path $pidFile -Value $listenerOwner.Pid -Encoding ASCII -ErrorAction Stop
                Write-Host "[INFO]  Listener is child process; PID file updated to $($listenerOwner.Pid)."
            } catch {
                Write-Host "[WARN]  Failed to update PID file to listener PID: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }

    Write-Host "[INFO]  Port $port is LISTENing. Verifying HTTP response..."

    # FR-303 (b): HTTP response.
    if (-not (Wait-ForHttpReady -BindHost $Config.host -Port $port -TimeoutSec 5)) {
        Write-Host "[WARN]  Timeout waiting for HTTP response (TCP open but app not ready). Check Logs (menu 4)." -ForegroundColor Yellow
        return $false
    }

    Write-Host "[OK]    Server started (PID $($proc.Id) on port $port)." -ForegroundColor Green

    # FR-307: open browser if configured.
    if ($Config.open_browser) {
        Open-BrowserForConfig -Config $Config
    }
    return $true
}

function Stop-StrictDocServerProcess {
    # FR-401..411.
    param($Config, [int]$KnownPid = 0)

    $port    = [int]$Config.port
    $pidFile = Get-PidFilePath -Port $port

    $serverPid = 0
    if ($KnownPid -gt 0) {
        $serverPid = $KnownPid
    } else {
        $fromFile = Read-PidFile -Path $pidFile  # FR-401
        if ($null -ne $fromFile) {
            $serverPid = $fromFile
        } else {
            # FR-402: port-based fallback.
            $owner = Get-PortOwner -Port $port
            if ($null -ne $owner -and $owner.Pid -gt 0) {
                $serverPid = $owner.Pid
                Write-Host "[INFO]  PID file missing; using port-based fallback (PID $serverPid)."
            }
        }
    }

    if ($serverPid -le 0) {
        # FR-411
        Write-Host "[INFO]  Server is not running."
        return $true
    }

    # FR-403 / FR-404: identity check.
    if (-not (Test-ProcessIsStrictdoc -ProcessId $serverPid)) {
        $cmdLine = Get-ProcessCommandLine -ProcessId $serverPid
        Write-Host "[WARN]  PID $serverPid is not a strictdoc process (CommandLine: $cmdLine). Aborting stop." -ForegroundColor Yellow
        Write-Host "        To recover, delete the stale PID file manually: $pidFile" -ForegroundColor DarkGray
        return $false
    }

    # FR-405: try graceful Stop-Process (no -Force).
    Write-Host "[INFO]  Stopping strictdoc (PID $serverPid)..."
    $eap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    Stop-Process -Id $serverPid -ErrorAction SilentlyContinue
    $ErrorActionPreference = $eap

    # FR-406: wait up to 5s.
    $stopped = $false
    for ($i = 0; $i -lt 5; $i++) {
        Start-Sleep -Seconds 1
        if (-not (Get-Process -Id $serverPid -ErrorAction SilentlyContinue)) { $stopped = $true; break }
    }

    if (-not $stopped) {
        # FR-407: -Force retry, up to 3s.
        Write-Host "[INFO]  Not gone after 5s. Retrying with -Force..."
        Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt 3; $i++) {
            Start-Sleep -Seconds 1
            if (-not (Get-Process -Id $serverPid -ErrorAction SilentlyContinue)) { $stopped = $true; break }
        }
    }

    if (-not $stopped) {
        # FR-408: leave PID file in place.
        Write-Host "[ERROR] Failed to stop PID $serverPid even with -Force. Investigate manually." -ForegroundColor Red
        return $false
    }

    # FR-409: delete PID file.
    if (Test-Path $pidFile) {
        Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK]    Server stopped (PID $serverPid)." -ForegroundColor Green
    return $true
}

function Invoke-StartAction {
    # Dispatches Start (menu 1) based on current state.
    param($Config, $ServerState)

    switch ($ServerState.Status) {
        'RUNNING' {
            # FR-305: 3-choice prompt.
            Write-Host "[INFO]  Already running (PID $($ServerState.Pid) on port $($Config.port))."
            $rawChoice = Read-Host "[R]estart / [O]pen browser / [C]ancel"
            # M2: defend against $null.
            $choice = "$rawChoice".Trim().ToUpperInvariant()
            switch ($choice) {
                'R' {
                    if (Stop-StrictDocServerProcess -Config $Config -KnownPid $ServerState.Pid) {
                        $null = Start-StrictDocServerProcess -Config $Config
                    }
                }
                'O' {
                    Open-BrowserForConfig -Config $Config
                }
                default {
                    Write-Host "[INFO]  Cancelled."
                }
            }
        }
        'STARTING' {
            Write-Host "[INFO]  Server is still starting (PID $($ServerState.Pid), $($ServerState.ElapsedSecs)s elapsed). Use Status (menu 3) to refresh."
        }
        'STOPPED' {
            $null = Start-StrictDocServerProcess -Config $Config
        }
        'STALE_PID_FILE' {
            # FR-312: auto-cleanup.
            Write-Host "[INFO]  Stale PID file detected. Cleaning up and starting fresh."
            $pidFile = Get-PidFilePath -Port $Config.port
            if (Test-Path $pidFile) {
                Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
            }
            $null = Start-StrictDocServerProcess -Config $Config
        }
        'OTHER_OWNS_PORT' {
            # FR-306
            $owner = $ServerState.OwnerName
            if ([string]::IsNullOrEmpty($owner)) { $owner = '<unknown owner>' }
            $pidText = if ($ServerState.Pid -gt 0) { "PID $($ServerState.Pid)" } else { 'PID unknown' }
            Write-Host "[WARN]  Port $($Config.port) is occupied by '$owner' ($pidText). Cannot start. Edit config (menu 5) to use a different port." -ForegroundColor Yellow
        }
        default {
            Write-Host "[ERROR] Unknown server state: $($ServerState.Status)" -ForegroundColor Red
        }
    }
}

function Invoke-StopAction {
    param($Config, $ServerState)

    if ($ServerState.Status -eq 'STOPPED') {
        Write-Host "[INFO]  Server is not running."
        return
    }
    if ($ServerState.Status -eq 'OTHER_OWNS_PORT') {
        Write-Host "[INFO]  Port is owned by another process (not strictdoc). Nothing to stop here."
        return
    }
    $null = Stop-StrictDocServerProcess -Config $Config -KnownPid ([int]$ServerState.Pid)
}

function Show-ServerStatusDetail {
    # FR-508.
    param($Config, $ServerState)
    Write-Host "Server state details:"
    Write-Host "  Status: $($ServerState.Status)"
    Write-Host "  Port:   $($ServerState.Port)"
    if ($null -ne $ServerState.Pid -and $ServerState.Pid -gt 0) {
        Write-Host "  PID:    $($ServerState.Pid)"
    }
    if ($ServerState.Status -eq 'RUNNING' -and $null -ne $ServerState.Uptime) {
        Write-Host "  Uptime: $(Format-Uptime -Span $ServerState.Uptime)"
    }
    if ($ServerState.Status -eq 'STARTING') {
        Write-Host "  Waiting LISTEN: $($ServerState.ElapsedSecs)s elapsed (30s timeout)"
    }
    if (-not [string]::IsNullOrEmpty($ServerState.OwnerName)) {
        Write-Host "  Owner:  $($ServerState.OwnerName)"
    }
    Write-Host "  Log:    $($ServerState.LogPath)"
    Write-Host "  Errlog: $($ServerState.ErrLogPath)"
    if (-not [string]::IsNullOrEmpty($ServerState.Detail)) {
        Write-Host "  Note:   $($ServerState.Detail)"
    }
}

function Show-ServerLogs {
    # FR-601..604.
    param($Config)
    $port      = [int]$Config.port
    $stdoutLog = Get-StdoutLogPath -Port $port
    $stderrLog = Get-StderrLogPath -Port $port

    if (-not (Test-Path $stdoutLog)) {
        Write-Host "[INFO]  No log file yet at $stdoutLog. Start the server first."
        return
    }

    Write-Host "--- $stdoutLog (last 50 lines) ---"
    try { Get-Content -Path $stdoutLog -Tail 50 -ErrorAction Stop } catch {
        Write-Host "[WARN]  Failed to read stdout log: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    if ((Test-Path $stderrLog) -and (Get-Item $stderrLog).Length -gt 0) {
        Write-Host ""
        Write-Host "--- $stderrLog (last 20 lines) ---"
        try { Get-Content -Path $stderrLog -Tail 20 -ErrorAction Stop } catch {
            Write-Host "[WARN]  Failed to read stderr log: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}
