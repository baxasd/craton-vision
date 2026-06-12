# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata, collect_submodules

# This spec file is designed to be run from the PROJECT ROOT.
# Example: pyinstaller --clean tools/windows/build.spec
project_root = os.path.abspath(os.getcwd())

# Add project root to sys.path so PyInstaller can find the 'core' package
if project_root not in sys.path:
    sys.path.insert(0, project_root)

block_cipher = None

# Pre-collect mediapipe dependencies (capture side)
try:
    datas_mp, binaries_mp, hiddenimports_mp = collect_all('mediapipe')
    datas_mp += copy_metadata("mediapipe")
except Exception as e:
    print(f"Warning: Failed to collect mediapipe via collect_all: {e}")
    datas_mp, binaries_mp, hiddenimports_mp = [], [], []

# Pre-collect streamlit and the scientific stack (Workbench / analysis side).
# Streamlit reads its own package metadata at runtime, so it must be copied in.
try:
    datas_wb, binaries_wb, hiddenimports_wb = collect_all('streamlit')
    datas_wb += copy_metadata("streamlit")
except Exception as e:
    print(f"Warning: Failed to collect streamlit via collect_all: {e}")
    datas_wb, binaries_wb, hiddenimports_wb = [], [], []

for _pkg in ('pandas', 'numpy', 'scipy', 'sklearn', 'plotly'):
    try:
        hiddenimports_wb += collect_submodules(_pkg)
    except Exception as e:
        print(f"Warning: Failed to collect submodules for {_pkg}: {e}")

# Streamlit runs the dashboard from a script path, so the entry module and its
# engine are shipped as data files under 'core/' for the frozen launcher to find.
datas_wb += [
    (os.path.join(project_root, 'core', 'workbench_main.py'), 'core'),
    (os.path.join(project_root, 'core', 'workbench_logic.py'), 'core'),
]

# Common Analysis parameters
runtime_hooks = [os.path.join(project_root, 'tools', 'hook.py')]
manifest_path = os.path.join(project_root, 'tools', 'windows', 'manifest.xml')
icon_path = os.path.join(project_root, 'tools', 'vision.ico')

# Analysis for the console application: recorder.py
a = Analysis(
    [os.path.join(project_root, 'recorder.py')],
    pathex=[project_root],
    binaries=binaries_mp,
    datas=datas_mp,
    hiddenimports=hiddenimports_mp + ['core.camera', 'core.pose', 'core.depth', 'core.config'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Analysis for the windowed application: calibrator.py
b = Analysis(
    [os.path.join(project_root, 'calibrator.py')],
    pathex=[project_root],
    binaries=[],
    datas=[],
    hiddenimports=['core.camera', 'core.pose', 'core.depth', 'core.config', 'dearpygui.dearpygui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Analysis for the windowed application: viewer.py
c = Analysis(
    [os.path.join(project_root, 'viewer.py')],
    pathex=[project_root],
    binaries=[],
    datas=[],
    hiddenimports=['dearpygui.dearpygui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Analysis for the Workbench dashboard launcher: workbench.py
d = Analysis(
    [os.path.join(project_root, 'workbench.py')],
    pathex=[project_root],
    binaries=binaries_wb,
    datas=datas_wb,
    hiddenimports=hiddenimports_wb + ['core.workbench_main', 'core.workbench_logic'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_a = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
pyz_b = PYZ(b.pure, b.zipped_data, cipher=block_cipher)
pyz_c = PYZ(c.pure, c.zipped_data, cipher=block_cipher)
pyz_d = PYZ(d.pure, d.zipped_data, cipher=block_cipher)

# EXE for recorder.py (Console)
exe_a = EXE(
    pyz_a,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Recorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest=manifest_path,
    icon=icon_path,
    contents_directory='libs'
)

# EXE for calibrator.py (Windowed)
exe_b = EXE(
    pyz_b,
    b.scripts,
    [],
    exclude_binaries=True,
    name='Calibrator',
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
    manifest=manifest_path,
    icon=icon_path,
    contents_directory='libs'
)

# EXE for viewer.py (Windowed)
exe_c = EXE(
    pyz_c,
    c.scripts,
    [],
    exclude_binaries=True,
    name='Viewer',
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
    manifest=manifest_path,
    icon=icon_path,
    contents_directory='libs'
)

# EXE for workbench.py (Console — keeps the Streamlit server logs visible)
exe_d = EXE(
    pyz_d,
    d.scripts,
    [],
    exclude_binaries=True,
    name='Workbench',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest=manifest_path,
    icon=icon_path,
    contents_directory='libs'
)

# Bundle everything into a single distribution folder
coll = COLLECT(
    exe_a,
    a.binaries,
    a.zipfiles,
    a.datas,
    exe_b,
    b.binaries,
    b.zipfiles,
    b.datas,
    exe_c,
    c.binaries,
    c.zipfiles,
    c.datas,
    exe_d,
    d.binaries,
    d.zipfiles,
    d.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StrideLab',
)
