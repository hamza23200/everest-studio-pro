# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

pa_datas, pa_binaries, pa_hiddenimports = collect_all('pyaudiowpatch')
mss_datas, mss_binaries, mss_hiddenimports = collect_all('mss')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pa_binaries + mss_binaries,
    datas=pa_datas + mss_datas,
    hiddenimports=['pyaudiowpatch', 'mss', 'mss.windows', 'numpy'] + pa_hiddenimports + mss_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='EverestStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
