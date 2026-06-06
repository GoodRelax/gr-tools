@echo off
:: ============================================================
:: manage_move_window_to_virtual_desktop.bat
::
:: VERSION: 3.0.0
:: DATE:    2026-03-29
::
:: PURPOSE:
::   Launcher for manage_move_window_to_virtual_desktop.ps1
::   Double-click this file to start the management menu.
::
:: REQUIREMENTS:
::   manage_move_window_to_virtual_desktop.ps1 must exist
::   in the same folder as this file.
:: ============================================================

set ScriptPath=%~dp0manage_move_window_to_virtual_desktop.ps1

if not exist "%ScriptPath%" (
    echo [ERROR] Script not found: %ScriptPath%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%ScriptPath%"
