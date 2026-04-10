@echo off
REM Zeus PDF — Windows Build Script
REM Usage: Double-click or run from project folder
REM Output: dist\ZeusPDF_Setup_v1.0_Windows.exe

setlocal EnableDelayedExpansion

set VERSION=1.0
set APP_NAME=Zeus PDF
set EXE_NAME=ZeusPDF_Setup_v%VERSION%_Windows.exe

echo.
echo ============================================================
echo   Zeus PDF v%VERSION% -- Windows Build
echo ============================================================
echo.

REM ── 1. Find Python ───────────────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo Using: %%i
echo.

REM ── 2. Install dependencies ───────────────────────────────────────
echo [2/5] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies ready.
echo.

REM ── 3. Validate entry point ───────────────────────────────────────
echo [3/5] Validating project...
if not exist "main.py" (
    echo ERROR: main.py not found. Run from the Zeus PDF project folder.
    pause
    exit /b 1
)
echo Entry point OK.
echo.

REM ── 4. Clean old builds ───────────────────────────────────────────
echo [4/5] Cleaning old builds...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
echo Clean done.
echo.

REM ── 5. Build with PyInstaller ─────────────────────────────────────
echo [5/5] Building ZeusPDF.exe...
echo (First build may take 3-6 minutes)
echo.

if exist "ZeusPDF.spec" (
    python -m PyInstaller ZeusPDF.spec --noconfirm
) else (
    set ICONFLAG=
    if exist "assets\zeuspdf.ico" set ICONFLAG=--icon=assets\zeuspdf.ico

    python -m PyInstaller ^
        --onedir ^
        --windowed ^
        --name ZeusPDF ^
        --hidden-import PySide6 ^
        --hidden-import PySide6.QtCore ^
        --hidden-import PySide6.QtWidgets ^
        --hidden-import PySide6.QtGui ^
        --hidden-import PySide6.QtPrintSupport ^
        --hidden-import fitz ^
        --hidden-import sqlite3 ^
        --hidden-import pypdf ^
        --hidden-import openpyxl ^
        --collect-all PySide6 ^
        --collect-all fitz ^
        !ICONFLAG! ^
        main.py
)

if not exist "dist\ZeusPDF" (
    echo ERROR: PyInstaller build failed -- dist\ZeusPDF not found.
    pause
    exit /b 1
)
echo.
echo [OK] App built: dist\ZeusPDF\ZeusPDF.exe

REM ── 6. Build Inno Setup installer ────────────────────────────────
echo.
echo [Bonus] Building Windows installer...

REM Try common Inno Setup locations
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "!ISCC!"=="" (
    echo WARNING: Inno Setup not found. Skipping installer creation.
    echo Download from https://jrsoftware.org/isdl.php
    echo The raw app is at dist\ZeusPDF\ZeusPDF.exe
) else (
    "!ISCC!" ZeusPDF_Installer.iss
    if errorlevel 1 (
        echo WARNING: Inno Setup build failed.
    ) else (
        echo [OK] Installer: Output\%EXE_NAME%
    )
)

echo.
echo ============================================================
echo   BUILD COMPLETE
echo   App:       dist\ZeusPDF\ZeusPDF.exe
echo   Installer: Output\%EXE_NAME%
echo ============================================================
echo.
pause
