@echo off
rem =============================================================================
rem  drawio-uml.bat
rem    Turn one or more model JSON files into a draw.io UML diagram (.drawio),
rem    Markdown node/edge tables (.md), and SVG + PNG exports.
rem
rem  Usage:
rem    * Drag and drop one or more model JSON files onto this file, OR
rem    * drawio-uml.bat MODEL.json [MORE.json ...] [--cluster KEY] [-c KEY]
rem
rem  For each MODEL.json, written next to it with the same base name:
rem    MODEL.drawio        diagram            (scripts\draw.py)
rem    MODEL.md            node/edge tables   (scripts\table.py; -c/--cluster filters)
rem    MODEL.drawio.svg    vector export      (draw.io CLI)
rem    MODEL.drawio.png    raster export      (draw.io CLI)
rem
rem  draw always renders the whole model; -c / --cluster narrows only the table.
rem  Requires python on PATH and Graphviz (dot + neato/fdp); SVG/PNG also need
rem  draw.io desktop installed.
rem =============================================================================
setlocal enabledelayedexpansion

set "HERE=%~dp0"
set "DRAW=%HERE%scripts\draw.py"
set "TABLE=%HERE%scripts\table.py"
set "DRAWIO=C:\Program Files\draw.io\draw.io.exe"

set "CLUSTER="
set "FILES="
:parse
if "%~1"=="" goto run
if /i "%~1"=="-c"        (set "CLUSTER=%~2" & shift & shift & goto parse)
if /i "%~1"=="--cluster" (set "CLUSTER=%~2" & shift & shift & goto parse)
set "FILES=!FILES! "%~1""
shift
goto parse

:run
if "!FILES!"=="" (
    echo drawio-uml: turn a model JSON into a .drawio diagram + .md tables, plus svg and png.
    echo.
    echo   Drag and drop model JSON files onto this file, or run:
    echo       %~nx0 MODEL.json [MORE.json ...] [--cluster KEY] [-c KEY]
    echo.
    echo   Each output is written next to its input with the same base name.
    echo.
    pause
    exit /b 2
)

set "COPT="
if not "!CLUSTER!"=="" set "COPT=--cluster !CLUSTER!"

set "RC=0"
for %%F in (!FILES!) do (
    echo === %%~nxF ===
    python "%DRAW%" "%%~F" "%%~dpnF.drawio"
    if errorlevel 1 (
        echo   [draw failed]
        set "RC=1"
    ) else (
        python "%TABLE%" "%%~F" "%%~dpnF.md" !COPT!
        if errorlevel 1 (
            echo   [table failed]
            set "RC=1"
        ) else (
            if exist "%DRAWIO%" (
                "%DRAWIO%" -x -f svg -e -b 12 -o "%%~dpnF.drawio.svg" "%%~dpnF.drawio" >nul 2>&1
                "%DRAWIO%" -x -f png -e -b 12 -o "%%~dpnF.drawio.png" "%%~dpnF.drawio" >nul 2>&1
                echo   wrote .drawio .md .drawio.svg .drawio.png
            ) else (
                echo   wrote .drawio .md   [draw.io not found; skipped svg/png]
            )
        )
    )
)

echo.
echo Done.
pause
exit /b %RC%
