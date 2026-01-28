# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from PyInstaller.utils.hooks import collect_all

# Collect PaddleOCR and dependencies
datas = []
binaries = []
hiddenimports = [
    'paddle', 
    'paddleocr', 
    'imghdr', 
    'imgaug', 
    'shapely', 
    'pyclipper', 
    'scipy.special.cython_special',
    'skimage',
    'skimage.feature._orb_descriptor_positions',
    'skimage.filters.edges',
]

# Helper to collect complex packages
tmp_ret = collect_all('paddleocr')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('pyclipper')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Add config file
datas += [('src/config/config.yaml', 'src/config')]

# Add bundled models
datas += [('models', 'models')]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
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
    [],
    exclude_binaries=True,
    name='PDF_OCR_Splitter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to True if you want to see console output for debug
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF_OCR_Splitter',
)
