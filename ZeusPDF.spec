# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Zeus PDF — macOS and Windows

import sys
from pathlib import Path

block_cipher = None

# Optional icon — skip gracefully if not present
_icns = 'assets/zeuspdf.icns'
_ico  = 'assets/zeuspdf.ico'
ICON_MAC = _icns if Path(_icns).exists() else None
ICON_WIN = _ico  if Path(_ico).exists()  else None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),          # logo PNGs bundled into the app
        ('pdfstudio', 'pdfstudio'),    # source package (for frozen path resolution)
    ],
    hiddenimports=[
        # PySide6
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
        # PyMuPDF
        'fitz',
        'fitz.fitz',
        # stdlib
        'sqlite3',
        'csv',
        'hashlib',
        'secrets',
        'logging',
        'shutil',
        'io',
        # reportlab (optional, future)
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        # pypdf
        'pypdf',
        # pyHanko (optional — signing)
        'pyhanko',
        'pyhanko.sign',
        'pyhanko.sign.signers',
        'pyhanko.sign.fields',
        'pyhanko.pdf_utils',
        'pyhanko.pdf_utils.reader',
        'pyhanko.pdf_utils.incremental_writer',
        'pyhanko_certvalidator',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZeusPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_MAC if sys.platform == 'darwin' else ICON_WIN,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ZeusPDF',
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Zeus PDF.app',
        icon=ICON_MAC,
        bundle_identifier='com.verchertechnologies.zeuspdf',
        info_plist={
            'CFBundleName': 'Zeus PDF',
            'CFBundleDisplayName': 'Zeus PDF',
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'PDF Document',
                    'CFBundleTypeExtensions': ['pdf'],
                    'CFBundleTypeRole': 'Editor',
                    'LSHandlerRank': 'Alternate',
                }
            ],
        },
    )
