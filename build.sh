#!/usr/bin/env bash
# Zeus PDF — macOS Build Script
# Usage: bash build.sh
# Output: dist/ZeusPDF_v<version>_Mac.dmg
# Version is read from pdfstudio/__version__.py (single source of truth).

set -euo pipefail

# Pull version from the package — avoids drift.
VERSION=$(python3 -c "import runpy; ns=runpy.run_path('pdfstudio/__version__.py'); print(ns['__version__'])")
APP_NAME="Zeus PDF"
DMG_NAME="ZeusPDF_v${VERSION}_Mac.dmg"

echo ""
echo "============================================================"
echo "  Zeus PDF v${VERSION} — macOS Build"
echo "============================================================"
echo ""

# ── 1. Locate Python 3.10+ ─────────────────────────────────────────
echo "[1/7] Checking Python..."
if [ -x "/opt/homebrew/bin/python3.12" ]; then
    PY="/opt/homebrew/bin/python3.12"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PY="/opt/homebrew/bin/python3"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "ERROR: Python 3 not found. Install via Homebrew: brew install python"
    exit 1
fi
echo "Using: $($PY --version) at $PY"
echo ""

# ── 2. Install / upgrade dependencies ─────────────────────────────
echo "[2/7] Installing dependencies..."
$PY -m pip install --upgrade pip --break-system-packages --quiet 2>/dev/null || \
$PY -m pip install --upgrade pip --quiet || true

for pkg in PySide6 PyMuPDF pypdf Pillow pyinstaller; do
    $PY -m pip install --upgrade "$pkg" --break-system-packages --quiet 2>/dev/null || \
    $PY -m pip install --upgrade "$pkg" --quiet || \
    echo "  WARNING: $pkg install failed (may already be present)"
done

# pyHanko is optional — signing still works without cert-based signing
$PY -m pip install --upgrade pyHanko pyhanko-certvalidator cryptography \
    --break-system-packages --quiet 2>/dev/null || \
    echo "  INFO: pyHanko not installed — certificate signing will be unavailable"

echo "Dependencies ready."
echo ""

# ── 3. Validate entry point ────────────────────────────────────────
echo "[3/7] Validating project..."
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found. Run this script from the Zeus PDF project folder."
    exit 1
fi
echo "Entry point OK."
echo ""

# ── 4. Create assets folder if missing ────────────────────────────
mkdir -p assets

# ── 5. Clean old build artifacts ──────────────────────────────────
echo "[4/7] Cleaning old builds..."
rm -rf build dist
echo "Clean done."
echo ""

# ── 6. Build with PyInstaller ─────────────────────────────────────
echo "[5/7] Building Zeus PDF.app..."
echo "(First build may take 3-6 minutes)"
echo ""

export MACOSX_DEPLOYMENT_TARGET=12.0

if [ -f "ZeusPDF.spec" ]; then
    $PY -m PyInstaller ZeusPDF.spec --noconfirm
else
    # Fallback: build without spec file
    ICONFLAG=""
    [ -f "assets/zeuspdf.icns" ] && ICONFLAG="--icon=assets/zeuspdf.icns"

    $PY -m PyInstaller \
        --onedir \
        --windowed \
        --name "ZeusPDF" \
        --hidden-import PySide6 \
        --hidden-import PySide6.QtCore \
        --hidden-import PySide6.QtWidgets \
        --hidden-import PySide6.QtGui \
        --hidden-import PySide6.QtPrintSupport \
        --hidden-import fitz \
        --hidden-import sqlite3 \
        --hidden-import pypdf \
        --collect-all PySide6 \
        --collect-all fitz \
        $ICONFLAG \
        --osx-bundle-identifier "com.verchertechnologies.pdfstudio" \
        main.py
fi

APP_BUNDLE="dist/Zeus PDF.app"
if [ ! -d "$APP_BUNDLE" ]; then
    # PyInstaller without BUNDLE uses the name directly
    APP_BUNDLE="dist/ZeusPDF.app"
fi

if [ ! -d "$APP_BUNDLE" ]; then
    echo "ERROR: Build failed — .app bundle not found in dist/"
    exit 1
fi
echo ""
echo "✅  App bundle: $APP_BUNDLE"

# ── 7. Fix PySide6 symlinks for code signing ──────────────────────
echo ""
echo "[6/7] Fixing PySide6 bundle symlinks..."
FWDIR="$APP_BUNDLE/Contents/Frameworks/PySide6"
RESDIR="$APP_BUNDLE/Contents/Resources/PySide6"

for name in Assistant Designer Linguist; do
    dot_app="$FWDIR/${name}__dot__app"
    link_app="$FWDIR/${name}.app"
    real_app="$RESDIR/${name}.app"
    if [ -L "$link_app" ] && [ -d "$dot_app" ]; then
        if [ -d "$real_app" ]; then
            rm -f "$dot_app/Contents/Info.plist"
            cp "$real_app/Contents/Info.plist" "$dot_app/Contents/Info.plist" 2>/dev/null || true
            rm -rf "$dot_app/Contents/Resources"
            cp -r "$real_app/Contents/Resources" "$dot_app/Contents/Resources" 2>/dev/null || true
        fi
        rm "$link_app"
        cp -r "$dot_app" "$link_app"
        rm -rf "$dot_app"
        echo "  Fixed: ${name}.app"
    fi
done
echo "Symlinks fixed."

# ── 8. Code sign (ad-hoc) ─────────────────────────────────────────
echo ""
xattr -cr "$APP_BUNDLE"
codesign --force --deep --sign - "$APP_BUNDLE" 2>&1 && \
    echo "✅  Code signed." || \
    echo "WARNING: Code signing failed (app still works via right-click → Open)."

# ── 9. Package as DMG ─────────────────────────────────────────────
echo ""
echo "[7/7] Creating DMG..."
DMG_PATH="dist/${DMG_NAME}"

hdiutil create \
    -volname "Zeus PDF" \
    -srcfolder "$APP_BUNDLE" \
    -ov \
    -format UDZO \
    "$DMG_PATH" && echo "✅  DMG: $DMG_PATH" || \
    echo "WARNING: DMG creation failed (app bundle still usable)."

# Copy to website/assets if present
[ -d "website/assets" ] && cp "$DMG_PATH" "website/assets/" 2>/dev/null && \
    echo "✅  Copied DMG to website/assets/" || true

echo ""
echo "============================================================"
echo "  BUILD COMPLETE"
echo "  App:  $APP_BUNDLE"
echo "  DMG:  $DMG_PATH"
echo "============================================================"
echo ""
