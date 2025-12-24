"""
Configuration management for DesktopAutoSort.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


def get_config_dir() -> str:
    """Get the configuration directory path (data subdirectory)."""
    # Use 'data' subdirectory in program directory for portability
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(app_dir, "data")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_settings_file() -> str:
    """Get the settings file path."""
    return os.path.join(get_config_dir(), "settings.json")


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.settings_file = get_settings_file()
        self._data: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load settings from file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}
        else:
            self._data = {}
    
    def save(self):
        """Save settings to file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value."""
        self._data[key] = value
    
    def get_classifier_data(self) -> Optional[Dict]:
        """Get classifier configuration."""
        return self.get("classifier")
    
    def set_classifier_data(self, data: Dict):
        """Set classifier configuration."""
        self.set("classifier", data)
    
    def get_layout_data(self) -> Optional[Dict]:
        """Get layout manager configuration."""
        return self.get("layout")
    
    def set_layout_data(self, data: Dict):
        """Set layout manager configuration."""
        self.set("layout", data)
    
    def get_monitor_mode(self) -> str:
        """Get monitor mode setting."""
        return self.get("monitor_mode", "primary")
    
    def set_monitor_mode(self, mode: str):
        """Set monitor mode setting."""
        self.set("monitor_mode", mode)
    
    def get_current_preset(self) -> str:
        """Get current preset ID."""
        return self.get("current_preset", "default")
    
    def set_current_preset(self, preset_id: str):
        """Set current preset ID."""
        self.set("current_preset", preset_id)
