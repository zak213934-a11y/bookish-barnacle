# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

project_dir = os.path.abspath(os.path.dirname(__file__))
entry = os.path.join(project_dir, 'anime_prompt_generator_gui_pro.py')

# Bundle all text files in ./data into the executable
# (On Windows, PyInstaller expects SRC;DEST with ';')
datas = [(os.path.join(project_dir, 'data'), 'data')]

hiddenimports = []
# ttkbootstrap is optional in the app; include it if installed so the EXE works either way.
hiddenimports += collect_submodules('ttkbootstrap') if os.path.exists(os.path.join(project_dir, '.venv')) else []


a = Analysis(
    [entry],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Genv3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
