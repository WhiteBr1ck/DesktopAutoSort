"""
Build script for DesktopAutoSort.
Creates a standalone EXE using PyInstaller.
"""

import subprocess
import sys
import os
import shutil

def main():
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}/...")
            shutil.rmtree(folder)
    
    # Get version
    from version import VERSION
    
    # Determine architecture
    import platform
    arch = "x64" if platform.machine().endswith('64') else "x86"
    
    exe_name = f"DesktopAutoSort_v{VERSION}_{arch}"
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Single EXE file
        "--windowed",          # No console window
        "--name", exe_name,
        "--add-data", "core;core",
        "--add-data", "ui;ui",
        "--add-data", "config;config",
        "--add-data", "version.py;.",
        "main.py"
    ]
    
    # Add icon if exists
    icon_path = os.path.abspath("icon.ico")
    if os.path.exists(icon_path):
        print(f"Using icon: {icon_path}")
        cmd.extend(["--icon", icon_path])
        # Also include icon as data file for runtime use (tray icon)
        cmd.extend(["--add-data", f"{icon_path};."])
    
    print("Building EXE...")
    print(" ".join(cmd))
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("Build successful!")
        print(f"Output: dist/{exe_name}.exe")
        print("="*50)
    else:
        print("\nBuild failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
