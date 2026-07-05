# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Slicer Profile Converter.

Builds a single-file, windowed executable with the app icon embedded, on
Windows, macOS and Linux. Build with:

    pyinstaller build.spec --noconfirm
"""
import os
import sys

block_cipher = None

# Platform-aware icon selection.
if sys.platform.startswith("win"):
    app_icon = os.path.join("docs", "icon.ico")
elif sys.platform == "darwin":
    app_icon = os.path.join("docs", "icon.icns")
else:
    app_icon = os.path.join("docs", "icon.png")

# Bundle the PNG icon so the running app can set its window icon.
datas = [(os.path.join("docs", "icon.png"), "docs")]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SlicerProfileConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

# macOS: wrap into a proper .app bundle so the Dock icon shows.
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Slicer Profile Converter.app",
        icon=app_icon,
        bundle_identifier="com.netspecs.slicerprofileconverter",
    )
