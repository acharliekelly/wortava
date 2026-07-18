from PyInstaller.utils.hooks import collect_all, copy_metadata


datas = [
    ("config/defaults.toml", "config"),
    ("src/wortava/scenarios/*.json", "wortava/scenarios"),
]
binaries = []
hiddenimports = []

for distribution in ("typer", "rich", "obsws_python", "pythonosc", "pycaw", "comtypes"):
    collected_datas, collected_binaries, collected_imports = collect_all(distribution)
    datas += collected_datas
    binaries += collected_binaries
    hiddenimports += collected_imports

for distribution in ("typer", "rich"):
    datas += copy_metadata(distribution)

a = Analysis(
    ["src/wortava/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="wortava",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="wortava",
)
