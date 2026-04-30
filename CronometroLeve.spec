# -*- mode: python ; coding: utf-8 -*-

# pynacl (libsodium) tem extensão C nativa (_sodium.pyd) e binário libsodium.dll
# que NÃO são pegos automaticamente pelo PyInstaller. collect_all garante que
# datas, binaries e hiddenimports do pacote `nacl` entrem no .exe.
from PyInstaller.utils.hooks import collect_all

_nacl_datas, _nacl_binaries, _nacl_hiddenimports = collect_all('nacl')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_nacl_binaries,
    datas=[('logo.png', '.'), *_nacl_datas],
    hiddenimports=[
        'app',
        'app.app_shell',
        'app.config',
        'app.hooks_input',
        'app.main',
        'app.mega_uploader',
        'app.monitor',
        'app.subtarefas',
        'app.win32_utils',
        'app.segredos',
        *_nacl_hiddenimports,
    ],
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
    name='CronometroLeve',
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
