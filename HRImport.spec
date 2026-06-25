# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for the HR Import GUI.

Build locally:   pyinstaller HRImport.spec
Output:          dist/HR Import.exe   (Windows)
                 dist/HR Import.app   (macOS)

PyInstaller cannot cross-compile: build each OS's artifact on that OS. The
GitHub Actions workflow (.github/workflows/build.yml) does this automatically.
"""
import sys
from PyInstaller.utils.hooks import collect_all

# tenants.json is read-only config and is bundled inside the app.
# dont_suspend.csv is intentionally NOT bundled — it is user-editable, sensitive,
# git-ignored, and resolved next to the app at runtime (see resources.py).
datas = [("tenants.json", ".")]
binaries = []
hiddenimports = []

# tkinterdnd2 ships native tkdnd binaries + Tcl scripts that PyInstaller does not
# pick up automatically; collect_all gathers them so drag-and-drop works.
_dnd_datas, _dnd_binaries, _dnd_hidden = collect_all("tkinterdnd2")
datas += _dnd_datas
binaries += _dnd_binaries
hiddenimports += _dnd_hidden

a = Analysis(
    ["App.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # macOS: onedir build wrapped into a .app bundle (onefile + .app is
    # deprecated in PyInstaller). The .app is still a single draggable item.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="HR Import",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,          # GUI app: no console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="HR Import",
    )
    app = BUNDLE(
        coll,
        name="HR Import.app",
        icon=None,
        bundle_identifier="aero.joby.hrimport",
    )
else:
    # Windows/Linux: a single self-contained executable for download-and-run.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="HR Import",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,          # GUI app: no console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
