# -*- mode: python ; coding: utf-8 -*-

# pynacl (libsodium) tem extensão C nativa (_sodium.pyd) e binário libsodium.dll
# que NÃO são pegos automaticamente pelo PyInstaller. collect_all garante que
# datas, binaries e hiddenimports do pacote `nacl` entrem no .exe.
from PyInstaller.utils.hooks import collect_all

_nacl_datas, _nacl_binaries, _nacl_hiddenimports = collect_all('nacl')

# certifi: bundle do cacert.pem (roots embutidos). Garante que o app valide
# HTTPS com os certificados do certifi em vez do repositorio do Windows —
# evita o erro "certificate has expired" em PCs sem os roots novos da
# Let's Encrypt (ver app/config.py).
_certifi_datas, _certifi_binaries, _certifi_hiddenimports = collect_all('certifi')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[*_nacl_binaries, *_certifi_binaries],
    datas=[('logo.png', '.'), *_nacl_datas, *_certifi_datas],
    hiddenimports=[
        'app',
        'app.app_shell',
        'app.config',
        'app.hooks_input',
        'app.main',
        'app.mega_uploader',
        'app.monitor',
        'app.subtarefas',
        'app.validador_pix',
        'app.win32_utils',
        'app.segredos',
        'certifi',
        *_nacl_hiddenimports,
        *_certifi_hiddenimports,
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
    # UPX explicitamente desabilitado. Hoje o PC de build nem tem UPX no
    # PATH (PyInstaller silenciosamente pula), então isso é só defensivo
    # para o caso de alguém instalar UPX: compressão da python*.dll é
    # historicamente associada a falsos positivos de antivírus.
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
