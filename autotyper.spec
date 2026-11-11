# -*- mode: python ; coding: utf-8 -*-
"""Windows build for Auto Typer 1.0.0. One file opens the app window."""

a = Analysis(
    ["windows_app.py"],
    pathex=[],
    binaries=[],
    datas=[("web", "web")],
    hiddenimports=["desktop"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["webview", "pythonnet", "clr_loader", "cffi", "clr"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutoTyper-1.0.0-windows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
