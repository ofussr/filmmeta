# Build on Windows: py -m PyInstaller --clean --noconfirm FilmMeta.spec
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

native_data, native_binaries, native_imports = collect_all("pyexiv2")
application_data = collect_data_files("filmmeta")

a = Analysis(
    ["run_filmmeta.py"],
    pathex=[SPECPATH],
    binaries=native_binaries,
    datas=native_data + application_data,
    hiddenimports=native_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FilmMeta",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(Path(SPECPATH) / "filmmeta/resources/filmmeta.ico")
    if sys.platform == "win32"
    else None,
)
