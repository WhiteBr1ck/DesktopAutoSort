"""
Auto-start utilities for Windows.
Uses registry to enable/disable auto-start on login.
"""

import sys
import os

try:
    import winreg
except ImportError:
    winreg = None

APP_NAME = "DesktopAutoSort"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_exe_path() -> str:
    """Get the path to the executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return sys.executable
    else:
        # Running as script - use pythonw to avoid console
        return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


def is_autostart_enabled() -> bool:
    """Check if autostart is currently enabled."""
    if winreg is None:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_PATH,
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def enable_autostart() -> bool:
    """Enable autostart on Windows login."""
    if winreg is None:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_PATH,
            0, winreg.KEY_SET_VALUE
        )
        exe_path = get_exe_path()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to enable autostart: {e}")
        return False


def disable_autostart() -> bool:
    """Disable autostart on Windows login."""
    if winreg is None:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_PATH,
            0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass  # Already disabled
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to disable autostart: {e}")
        return False


def set_autostart(enabled: bool) -> bool:
    """Set autostart state."""
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
