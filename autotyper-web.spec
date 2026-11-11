# -*- mode: python ; coding: utf-8 -*-
"""Browser build for Auto Typer 1.0.0. One file opens the app in the browser."""

a = Analysis(
    ["web.py"],
    pathex=[],
    binaries=[],
    datas=[("web", "web")],
    hiddenimports=[],
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
    name="AutoTyper-1.0.0-web",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
