# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for EOM Hub."""

import os
from pathlib import Path

block_cipher = None

# Paths
spec_dir = Path(SPECPATH)
src_dir = spec_dir / 'src'
frontend_dist = spec_dir / 'frontend' / 'dist'

# Collect all source files
a = Analysis(
    [str(src_dir / 'app.py')],
    pathex=[str(spec_dir), str(src_dir)],
    binaries=[],
    datas=[
        (str(frontend_dist), 'frontend/dist'),
        (str(spec_dir / 'tools_config.json'), '.'),
    ],
    hiddenimports=[
        'eel',
        'bottle',
        'gevent',
        'gevent.ssl',
        'gevent.socket',
        'gevent.threading',
        'gevent.select',
        'geventwebsocket',
        'geventwebsocket.handler',
        'geventwebsocket.websocket',
        'src',
        'src.api',
        'src.api.tools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
    ],
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
    name='EOMHub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_dir / 'web' / 'icons' / 'icon.ico') if (spec_dir / 'web' / 'icons' / 'icon.ico').exists() else None,
    version_info=None,
)
