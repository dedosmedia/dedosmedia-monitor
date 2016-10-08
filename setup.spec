# -*- mode: python -*-

block_cipher = pyi_crypto.PyiBlockCipher(key='1234567890123456')


a = Analysis(['setup.py'],
             pathex=['I:\\Dropbox\\DedosMedia\\keshot\\dedosmedia-monitor'],
             binaries=None,
             datas=[( './config', 'config' )],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='setup',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='setup')
