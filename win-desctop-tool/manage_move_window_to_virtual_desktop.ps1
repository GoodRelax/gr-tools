# ============================================================
# manage_move_window_to_virtual_desktop.ps1
#
# VERSION: 3.0.5
# DATE:    2026-03-29
# CHANGES:
#   3.0.5 - Fix: use [Environment]::GetFolderPath('MyDocuments') instead of
#           $env:USERPROFILE\Documents for AutoHotkey folder path. On systems
#           with OneDrive folder redirection, these resolve to different paths,
#           causing AHK's A_MyDocuments to not find the DLL (LoadLibrary fails).
#   3.0.4 - Fix: add PSObject.Properties guard for DisplayVersion access in
#           Get-AutoHotkeyVersion. Fix misleading log message in Invoke-Install
#           that said "Checking via winget" when actually checking registry.
#   3.0.3 - Fix: replace Where-Object with ForEach-Object + PSObject.Properties
#           check in Get-AutoHotkeyInstalled and Get-AutoHotkeyVersion.
#           Set-StrictMode -Version Latest throws PropertyNotFoundException
#           on registry entries lacking DisplayName, even with -and guard.
#   3.0.2 - Fix: add $_.DisplayName -and guard in Where-Object for registry
#           queries. Set-StrictMode -Version Latest throws PropertyNotFound
#           when registry entries lack DisplayName property.
#   3.0.1 - Fix: replace [Console]::In.DiscardBufferedData() with
#           [Console]::KeyAvailable loop. DiscardBufferedData() fails
#           when launched via .bat because Console.In is wrapped as
#           SyncTextReader which does not expose that method.
#   3.0.0 - Full rewrite from batch to PowerShell.
#           Eliminates all cmd.exe structural bugs:
#           - if/else compound block file pointer corruption
#           - %errorlevel% parse-time expansion
#           - goto :EOF corrupting for-loop state
#           - keyboard input buffer bleed-through
#           PowerShell provides clean control flow, native registry
#           access, and reliable console input flushing.
#
# PURPOSE:
#   Manages the keyboard shortcut feature that moves the active
#   window to the adjacent virtual desktop on Windows 11.
#
# SHORTCUTS MANAGED:
#   Win + Ctrl + Shift + Right Arrow  ->  Move window to next desktop
#   Win + Ctrl + Shift + Left Arrow   ->  Move window to previous desktop
#
# MENU:
#   1. Status Check  - Show installation and runtime status
#   2. Install       - Download and configure everything
#   3. Enable        - Register startup + launch script
#   4. Disable       - Remove startup + stop script
#   5. Uninstall     - Remove files (with option to remove AutoHotkey)
#   6. Exit
#
# REQUIREMENTS:
#   - Windows 11 version 24H2 or later (Build 26100.2605 or later)
#   - Internet access for Install (downloads from GitHub and winget)
#
# NOTE - PROXY:
#   Install step downloads files over HTTPS.
#   If your network requires a proxy, configure it before running Install:
#     Windows Settings > Network and Internet > Proxy
#
# LOG FILE:
#   All operations are logged to manage_move_window_to_virtual_desktop.log
#   in the same folder as this script.
#
# NO SYSTEM RESTART IS REQUIRED FOR ANY OPERATION.
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---- Define paths ----
# Use [Environment]::GetFolderPath to resolve the actual My Documents path.
# On systems with OneDrive folder redirection, $env:USERPROFILE\Documents and
# the shell "My Documents" folder point to different locations.
# AHK's A_MyDocuments uses the shell folder, so we must match it here.
$AutoHotkeyFolder              = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AutoHotkey'
$AutoHotkeyScript              = Join-Path $AutoHotkeyFolder 'move_window_to_virtual_desktop.ahk'
$VirtualDesktopAccessorDll     = Join-Path $AutoHotkeyFolder 'VirtualDesktopAccessor.dll'
$VirtualDesktopAccessorUrl     = 'https://github.com/Ciantic/VirtualDesktopAccessor/releases/download/2024-12-16-windows11/VirtualDesktopAccessor.dll'
$StartupFolder                 = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupShortcut               = Join-Path $StartupFolder 'move_window_to_virtual_desktop.lnk'
$LogFile                       = Join-Path $PSScriptRoot 'manage_move_window_to_virtual_desktop.log'

# ---- AHK script content ----
$AutoHotkeyScriptContent = @'
#Requires AutoHotkey v2.0

; Load VirtualDesktopAccessor.dll
VirtualDesktopAccessorPath := A_MyDocuments . "\AutoHotkey\VirtualDesktopAccessor.dll"
hVirtualDesktopAccessor    := DllCall("LoadLibrary", "Str", VirtualDesktopAccessorPath, "Ptr")

; Get function pointers from VirtualDesktopAccessor.dll
GetCurrentDesktopNumberFunctionPointer   := DllCall("GetProcAddress", "Ptr", hVirtualDesktopAccessor, "AStr", "GetCurrentDesktopNumber",   "Ptr")
MoveWindowToDesktopNumberFunctionPointer := DllCall("GetProcAddress", "Ptr", hVirtualDesktopAccessor, "AStr", "MoveWindowToDesktopNumber", "Ptr")
GoToDesktopNumberFunctionPointer         := DllCall("GetProcAddress", "Ptr", hVirtualDesktopAccessor, "AStr", "GoToDesktopNumber",         "Ptr")

; Win + Ctrl + Shift + Right Arrow : move active window to next virtual desktop
#^+Right::
{
    currentDesktopNumber := DllCall(GetCurrentDesktopNumberFunctionPointer, "Int")
    activeWindowHandle   := WinExist("A")
    DllCall(MoveWindowToDesktopNumberFunctionPointer, "Ptr", activeWindowHandle, "Int", currentDesktopNumber + 1)
    DllCall(GoToDesktopNumberFunctionPointer, "Int", currentDesktopNumber + 1)
}

; Win + Ctrl + Shift + Left Arrow : move active window to previous virtual desktop
#^+Left::
{
    currentDesktopNumber := DllCall(GetCurrentDesktopNumberFunctionPointer, "Int")
    activeWindowHandle   := WinExist("A")
    DllCall(MoveWindowToDesktopNumberFunctionPointer, "Ptr", activeWindowHandle, "Int", currentDesktopNumber - 1)
    DllCall(GoToDesktopNumberFunctionPointer, "Int", currentDesktopNumber - 1)
}
'@

# ============================================================
# FUNCTION: Write-Log
#   Writes timestamped message to both console and log file.
# ============================================================
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy/MM/dd HH:mm:ss.ff'
    $line = "[$timestamp] $Message"
    Write-Host "  $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# ============================================================
# FUNCTION: Get-AutoHotkeyInstalled
#   Returns $true if AutoHotkey is found in registry.
#   Checks HKLM first, then HKCU.
#   Uses registry directly to avoid winget source update hang.
# ============================================================
function Get-AutoHotkeyInstalled {
    $registryPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($path in $registryPaths) {
        $found = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue |
                 ForEach-Object {
                     if ($_.PSObject.Properties['DisplayName'] -and $_.DisplayName -match 'AutoHotkey') { $_ }
                 } |
                 Select-Object -First 1
        if ($found) {
            $version = if ($found.PSObject.Properties['DisplayVersion']) { $found.DisplayVersion } else { 'unknown' }
            Write-Log "AutoHotkey detection result: installed ($($found.DisplayName) $version)"
            return $true
        }
    }
    Write-Log 'AutoHotkey detection result: not installed'
    return $false
}

# ============================================================
# FUNCTION: Get-AutoHotkeyVersion
#   Returns version string or empty string if not found.
# ============================================================
function Get-AutoHotkeyVersion {
    $registryPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($path in $registryPaths) {
        $found = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue |
                 ForEach-Object {
                     if ($_.PSObject.Properties['DisplayName'] -and $_.DisplayName -match 'AutoHotkey') { $_ }
                 } |
                 Select-Object -First 1
        if ($found -and $found.PSObject.Properties['DisplayVersion']) {
            return $found.DisplayVersion
        }
    }
    return ''
}

# ============================================================
# FUNCTION: Read-MenuChoice
#   Flushes keyboard input buffer, then reads user input.
# ============================================================
function Read-MenuChoice {
    param([string]$Prompt)
    # Flush buffered keyboard input accumulated during long operations.
    # [Console]::In.DiscardBufferedData() is unavailable when launched via .bat
    # (Console.In is wrapped as SyncTextReader). Use KeyAvailable loop instead.
    while ([Console]::KeyAvailable) { [Console]::ReadKey($true) | Out-Null }
    Write-Host -NoNewline $Prompt
    return [Console]::ReadLine()
}

# ============================================================
# FUNCTION: Show-StatusCheck
# ============================================================
function Show-StatusCheck {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Status Check'
    Write-Host '============================================================'
    Write-Host ''
    Write-Log '--- Status Check started ---'

    # AutoHotkey
    $autoHotkeyInstalled = Get-AutoHotkeyInstalled
    $autoHotkeyVersion   = Get-AutoHotkeyVersion
    if ($autoHotkeyInstalled -and $autoHotkeyVersion) {
        Write-Log "  AutoHotkey                     : Installed (version: $autoHotkeyVersion)"
    } elseif ($autoHotkeyInstalled) {
        Write-Log "  AutoHotkey                     : Installed"
    } else {
        Write-Log "  AutoHotkey                     : Not installed"
    }

    # VirtualDesktopAccessor.dll
    if (Test-Path $VirtualDesktopAccessorDll) {
        Write-Log "  VirtualDesktopAccessor.dll     : Found     ($VirtualDesktopAccessorDll)"
    } else {
        Write-Log "  VirtualDesktopAccessor.dll     : Not found  ($VirtualDesktopAccessorDll)"
    }

    # AHK script
    if (Test-Path $AutoHotkeyScript) {
        Write-Log "  move_window_to_virtual_desktop : Found     ($AutoHotkeyScript)"
    } else {
        Write-Log "  move_window_to_virtual_desktop : Not found  ($AutoHotkeyScript)"
    }

    # Startup shortcut
    if (Test-Path $StartupShortcut) {
        Write-Log "  Startup shortcut               : Registered    ($StartupShortcut)"
    } else {
        Write-Log "  Startup shortcut               : Not registered  ($StartupShortcut)"
    }

    # Running process
    $process = Get-Process -Name 'AutoHotkey64' -ErrorAction SilentlyContinue
    if ($process) {
        Write-Log "  AutoHotkey64.exe (process)     : Running"
    } else {
        Write-Log "  AutoHotkey64.exe (process)     : Not running"
    }

    Write-Log '--- Status Check completed ---'
    Write-Host ''
    Write-Host '============================================================'
    Write-Host "  Log file: $LogFile"
    Write-Host '============================================================'
    Read-Host 'Press Enter to return to menu'
}

# ============================================================
# FUNCTION: Invoke-Install
# ============================================================
function Invoke-Install {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Install'
    Write-Host '============================================================'
    Write-Host ''
    Write-Host ' This step will perform the following:'
    Write-Host ''
    Write-Host '   1. Install or update AutoHotkey v2 via winget'
    Write-Host "   2. Create folder: $AutoHotkeyFolder"
    Write-Host '   3. Download VirtualDesktopAccessor.dll from GitHub'
    Write-Host '   4. Create AutoHotkey script: move_window_to_virtual_desktop.ahk'
    Write-Host '   5. Register script to auto-start at Windows login'
    Write-Host '   6. Launch the script immediately'
    Write-Host ''
    Write-Host ' NOTE - PROXY:'
    Write-Host '   Step 3 downloads from GitHub over HTTPS.'
    Write-Host '   If your network requires a proxy, cancel now and configure it first.'
    Write-Host ''
    $confirm = Read-MenuChoice 'Type "yes" to proceed, or press Enter to cancel: '
    if ($confirm -ne 'yes') {
        Write-Log 'Install cancelled by user'
        Write-Host '  Install cancelled.'
        Read-Host 'Press Enter to return to menu'
        return
    }
    Write-Log '--- Install started ---'

    # -- Step 1: AutoHotkey --
    Write-Log '[Step 1/6] Checking AutoHotkey v2 ...'
    Write-Log '  (Checking registry for installed AutoHotkey ...)'
    $autoHotkeyInstalled = Get-AutoHotkeyInstalled
    if ($autoHotkeyInstalled) {
        Write-Log '  AutoHotkey is already installed.'
        $updateChoice = Read-MenuChoice '  Update to latest version? (yes/no): '
        if ($updateChoice -ieq 'yes') {
            Write-Log '  Updating AutoHotkey ...'
            winget upgrade --id AutoHotkey.AutoHotkey --disable-interactivity --accept-source-agreements
            Write-Log '[Step 1/6] AutoHotkey updated.'
        } else {
            Write-Log '[Step 1/6] AutoHotkey update skipped by user.'
        }
    } else {
        Write-Log '  Installing AutoHotkey v2 ...'
        winget install --id AutoHotkey.AutoHotkey --disable-interactivity --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[ERROR] AutoHotkey installation failed. Exit code: $LASTEXITCODE"
            Write-Host ''
            Write-Host '[ERROR] AutoHotkey installation failed.'
            Write-Host '        Please check your internet connection and try again.'
            Write-Host "        See log for details: $LogFile"
            Read-Host 'Press Enter to return to menu'
            return
        }
        Write-Log '[Step 1/6] AutoHotkey installed successfully.'
    }

    # -- Step 2: Create folder --
    Write-Log "[Step 2/6] Preparing folder: $AutoHotkeyFolder"
    if (-not (Test-Path $AutoHotkeyFolder)) {
        New-Item -ItemType Directory -Path $AutoHotkeyFolder | Out-Null
        Write-Log "  Created: $AutoHotkeyFolder"
    } else {
        Write-Log "  Already exists: $AutoHotkeyFolder"
    }

    # -- Step 3: Download DLL --
    Write-Log '[Step 3/6] Downloading VirtualDesktopAccessor.dll ...'
    try {
        Invoke-WebRequest -Uri $VirtualDesktopAccessorUrl -OutFile $VirtualDesktopAccessorDll
    } catch {
        Write-Log "[ERROR] Download failed: $_"
        Write-Host ''
        Write-Host '[ERROR] Download failed.'
        Write-Host '        Possible causes:'
        Write-Host '          - No internet connection'
        Write-Host '          - Proxy not configured'
        Write-Host "        See log for details: $LogFile"
        Read-Host 'Press Enter to return to menu'
        return
    }
    if (-not (Test-Path $VirtualDesktopAccessorDll)) {
        Write-Log '[ERROR] Download failed - file not found after download'
        Read-Host 'Press Enter to return to menu'
        return
    }
    $dllSize = (Get-Item $VirtualDesktopAccessorDll).Length
    Write-Log "  Downloaded file size: $dllSize bytes"
    if ($dllSize -lt 1000) {
        Write-Log "[ERROR] Downloaded file is corrupt - size too small: $dllSize bytes"
        Remove-Item $VirtualDesktopAccessorDll -Force
        Write-Host '[ERROR] Downloaded file appears to be corrupt (size too small).'
        Read-Host 'Press Enter to return to menu'
        return
    }
    Write-Log '[Step 3/6] VirtualDesktopAccessor.dll downloaded successfully.'

    # -- Step 4: Create AHK script --
    Write-Log "[Step 4/6] Creating AutoHotkey script: $AutoHotkeyScript"
    Set-Content -Path $AutoHotkeyScript -Value $AutoHotkeyScriptContent -Encoding UTF8
    Write-Log '[Step 4/6] AutoHotkey script created.'

    # -- Step 5: Register startup --
    Write-Log "[Step 5/6] Registering startup shortcut: $StartupShortcut"
    $shell    = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($StartupShortcut)
    $shortcut.TargetPath = $AutoHotkeyScript
    $shortcut.Save()
    if (Test-Path $StartupShortcut) {
        Write-Log '[Step 5/6] Startup registration complete.'
    } else {
        Write-Log '[WARNING] Startup registration may have failed - shortcut not found'
        Write-Host '[WARNING] Startup registration may have failed.'
        Write-Host "          You can register manually: place a shortcut to"
        Write-Host "          $AutoHotkeyScript"
        Write-Host "          into $StartupFolder"
    }

    # -- Step 6: Launch now --
    Write-Log '[Step 6/6] Launching AutoHotkey script ...'
    # NOTE: Stop-Process below stops ALL running AutoHotkey64.exe processes.
    #       If you have other AutoHotkey scripts running, they will also be stopped.
    Get-Process -Name 'AutoHotkey64' -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Process -FilePath $AutoHotkeyScript
    Write-Log '[Step 6/6] AutoHotkey script is now running.'

    Write-Log '--- Install completed ---'
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Install complete!'
    Write-Host ''
    Write-Host '  The following shortcuts are now active:'
    Write-Host '    Win + Ctrl + Shift + Right Arrow  ->  Move window to next desktop'
    Write-Host '    Win + Ctrl + Shift + Left Arrow   ->  Move window to previous desktop'
    Write-Host ''
    Write-Host '  The script will auto-start at every Windows login.'
    Write-Host '  No system restart is required.'
    Write-Host "  Log file: $LogFile"
    Write-Host '============================================================'
    Write-Host ''
    Read-Host 'Press Enter to return to menu'
}

# ============================================================
# FUNCTION: Invoke-Enable
# ============================================================
function Invoke-Enable {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Enable'
    Write-Host '============================================================'
    Write-Host ''
    Write-Log '--- Enable started ---'

    # Check prerequisites
    if (-not (Test-Path $AutoHotkeyScript)) {
        Write-Log "[ERROR] AutoHotkey script not found: $AutoHotkeyScript"
        Write-Host '[ERROR] AutoHotkey script not found. Please run Install first.'
        Read-Host 'Press Enter to return to menu'
        return
    }
    if (-not (Test-Path $VirtualDesktopAccessorDll)) {
        Write-Log "[ERROR] DLL not found: $VirtualDesktopAccessorDll"
        Write-Host '[ERROR] VirtualDesktopAccessor.dll not found. Please run Install first.'
        Read-Host 'Press Enter to return to menu'
        return
    }

    # Register startup
    Write-Log '[Step 1/2] Registering startup ...'
    if (Test-Path $StartupShortcut) {
        Write-Log '  Startup already registered.'
    } else {
        $shell    = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($StartupShortcut)
        $shortcut.TargetPath = $AutoHotkeyScript
        $shortcut.Save()
        if (Test-Path $StartupShortcut) {
            Write-Log '  Startup registration complete.'
        } else {
            Write-Log '[WARNING] Startup registration may have failed.'
        }
    }

    # Launch script
    Write-Log '[Step 2/2] Launching AutoHotkey script ...'
    # NOTE: Stop-Process below stops ALL running AutoHotkey64.exe processes.
    #       If you have other AutoHotkey scripts running, they will also be stopped.
    Get-Process -Name 'AutoHotkey64' -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Process -FilePath $AutoHotkeyScript
    Write-Log 'AutoHotkey script launched.'

    Write-Log '--- Enable completed ---'
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Enabled.'
    Write-Host ' Shortcuts are now active and will auto-start at Windows login.'
    Write-Host "  Log file: $LogFile"
    Write-Host '============================================================'
    Write-Host ''
    Read-Host 'Press Enter to return to menu'
}

# ============================================================
# FUNCTION: Invoke-Disable
# ============================================================
function Invoke-Disable {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Disable'
    Write-Host '============================================================'
    Write-Host ''
    Write-Log '--- Disable started ---'

    # Remove startup registration
    Write-Log '[Step 1/2] Removing startup registration ...'
    if (Test-Path $StartupShortcut) {
        Remove-Item $StartupShortcut -Force
        Write-Log '  Startup shortcut removed.'
    } else {
        Write-Log '  Startup shortcut not found - nothing to remove.'
    }

    # Stop running process
    Write-Log '[Step 2/2] Stopping AutoHotkey process ...'
    $process = Get-Process -Name 'AutoHotkey64' -ErrorAction SilentlyContinue
    if ($process) {
        $process | Stop-Process -Force
        Write-Log '  AutoHotkey process stopped successfully.'
    } else {
        Write-Log '  AutoHotkey process was not running.'
    }

    Write-Log '--- Disable completed ---'
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Disabled.'
    Write-Host ' Shortcuts are no longer active and will not start at login.'
    Write-Host ' Your files are preserved. Run Enable to re-activate.'
    Write-Host "  Log file: $LogFile"
    Write-Host '============================================================'
    Write-Host ''
    Read-Host 'Press Enter to return to menu'
}

# ============================================================
# FUNCTION: Invoke-Uninstall
# ============================================================
function Invoke-Uninstall {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Uninstall'
    Write-Host '============================================================'
    Write-Host ''
    Write-Host ' Choose uninstall scope:'
    Write-Host ''
    Write-Host '   a. Remove script and DLL only (keep AutoHotkey)'
    Write-Host '   b. Remove script, DLL, and AutoHotkey'
    Write-Host '   c. Back to menu'
    Write-Host ''
    $uninstallChoice = Read-MenuChoice 'Enter choice (a/b/c): '
    Write-Log "Uninstall choice: $uninstallChoice"

    if ($uninstallChoice -ieq 'c') { return }
    if ($uninstallChoice -inotmatch '^[ab]$') {
        Write-Log "[ERROR] Invalid uninstall choice: $uninstallChoice"
        Write-Host '[ERROR] Invalid choice.'
        Read-Host 'Press Enter to try again'
        Invoke-Uninstall
        return
    }

    $confirm = Read-MenuChoice 'Type "yes" to proceed, or press Enter to cancel: '
    if ($confirm -ne 'yes') {
        Write-Log 'Uninstall cancelled by user'
        Write-Host '  Uninstall cancelled.'
        Read-Host 'Press Enter to return to menu'
        return
    }
    Write-Log "--- Uninstall started (scope: $uninstallChoice) ---"

    # Step 1: Stop running process
    Write-Log '[Step 1] Stopping AutoHotkey process ...'
    Get-Process -Name 'AutoHotkey64' -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Log '  Done.'

    # Step 2: Remove startup registration
    Write-Log '[Step 2] Removing startup registration ...'
    if (Test-Path $StartupShortcut) {
        Remove-Item $StartupShortcut -Force
        Write-Log '  Removed.'
    } else {
        Write-Log '  Not found. Nothing to remove.'
    }

    # Step 3: Remove AHK script
    Write-Log '[Step 3] Removing AutoHotkey script ...'
    if (Test-Path $AutoHotkeyScript) {
        Remove-Item $AutoHotkeyScript -Force
        Write-Log "  Removed: $AutoHotkeyScript"
    } else {
        Write-Log '  Not found. Nothing to remove.'
    }

    # Step 4: Remove DLL
    Write-Log '[Step 4] Removing VirtualDesktopAccessor.dll ...'
    if (Test-Path $VirtualDesktopAccessorDll) {
        Remove-Item $VirtualDesktopAccessorDll -Force
        Write-Log "  Removed: $VirtualDesktopAccessorDll"
    } else {
        Write-Log '  Not found. Nothing to remove.'
    }

    # Step 5: Remove folder if empty
    Write-Log '[Step 5] Checking if AutoHotkey folder is empty ...'
    if (Test-Path $AutoHotkeyFolder) {
        $remainingItems = Get-ChildItem -Path $AutoHotkeyFolder -ErrorAction SilentlyContinue
        if ($remainingItems.Count -eq 0) {
            Remove-Item $AutoHotkeyFolder -Force
            Write-Log "  Folder removed: $AutoHotkeyFolder"
        } else {
            Write-Log "  Folder not empty, kept: $AutoHotkeyFolder"
        }
    }

    # Step 6: Uninstall AutoHotkey if option b
    if ($uninstallChoice -ieq 'b') {
        Write-Log '[Step 6] Uninstalling AutoHotkey via winget ...'
        Write-Log '  (Uninstalling via winget - this may take up to 2 minutes ...)'
        winget uninstall --id AutoHotkey.AutoHotkey --disable-interactivity
        Write-Log "  winget uninstall completed. Exit code: $LASTEXITCODE"
    }

    Write-Log '--- Uninstall completed ---'
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Uninstall complete.'
    Write-Host "  Log file: $LogFile"
    Write-Host '============================================================'
    Write-Host ''
    Read-Host 'Press Enter to return to menu'
}

# ============================================================
# MAIN: Initialize log and show menu loop
# ============================================================
Add-Content -Path $LogFile -Value '============================================================' -Encoding UTF8
Add-Content -Path $LogFile -Value " Session started: $(Get-Date -Format 'yyyy/MM/dd HH:mm:ss')" -Encoding UTF8
Add-Content -Path $LogFile -Value '============================================================' -Encoding UTF8

while ($true) {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' Move Window to Virtual Desktop - Management Menu'
    Write-Host '============================================================'
    Write-Host ''
    Write-Host '   1. Status Check'
    Write-Host '   2. Install'
    Write-Host '   3. Enable'
    Write-Host '   4. Disable'
    Write-Host '   5. Uninstall'
    Write-Host '   6. Exit'
    Write-Host ''
    Write-Host "   Log file: $LogFile"
    Write-Host ''

    $menuChoice = Read-MenuChoice 'Enter choice (1-6): '
    Write-Log "Menu choice entered: $menuChoice"

    switch ($menuChoice) {
        '1' { Show-StatusCheck }
        '2' { Invoke-Install }
        '3' { Invoke-Enable }
        '4' { Invoke-Disable }
        '5' { Invoke-Uninstall }
        '6' {
            Write-Log '--- Session ended ---'
            Write-Host ''
            Write-Host '  Goodbye.'
            Write-Host ''
            exit 0
        }
        default {
            Write-Log "[ERROR] Invalid menu choice: $menuChoice"
            Write-Host ''
            Write-Host '[ERROR] Invalid choice. Please enter 1 to 6.'
            Read-Host 'Press Enter to continue'
        }
    }
}
