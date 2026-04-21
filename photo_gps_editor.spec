# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


project_root = Path(SPECPATH)


def existing_datas():
    datas = [
        (str(project_root / "assets"), "assets"),
    ]

    if sys.platform.startswith("linux"):
        exiftool_script = Path("/usr/bin/exiftool")
        exiftool_image_lib = Path("/usr/share/perl5/Image")
        exiftool_file_lib = Path("/usr/share/perl5/File")

        if exiftool_script.exists():
            datas.append((str(exiftool_script), "tools/linux"))
        if exiftool_image_lib.exists():
            datas.append((str(exiftool_image_lib), "tools/linux/lib/Image"))
        if exiftool_file_lib.exists():
            datas.append((str(exiftool_file_lib), "tools/linux/lib/File"))

    windows_exiftool = project_root / "tools" / "windows" / "exiftool.exe"
    if windows_exiftool.exists():
        datas.append((str(windows_exiftool), "tools/windows"))

    return datas


a = Analysis(
    ["app.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=existing_datas(),
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name="Photo GPS Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Photo GPS Editor",
)
