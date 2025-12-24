"""
File classification engine for desktop icons.
Handles file type detection and custom grouping rules.
"""

import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json


@dataclass
class IconGroup:
    """Represents a group of icons."""
    name: str
    extensions: Set[str]  # Lowercase extensions with dot, e.g. {".pdf", ".doc"}
    enabled: bool = True
    is_folder_group: bool = False  # Special flag for folder group
    is_shortcut_group: bool = False  # Special flag for shortcut group
    is_system_group: bool = False  # Special flag for system icons (Recycle Bin, This PC)
    priority: int = 0  # Lower number = higher priority (processed first)
    start_from_right: bool = False  # Whether to start from right side
    merge_group: str = ""  # Groups with same merge_group value are combined into one column
    
    def matches(self, extension: str, is_folder: bool, is_system: bool = False) -> bool:
        """Check if a file matches this group."""
        if not self.enabled:
            return False
        if self.is_system_group:
            return is_system
        if self.is_folder_group:
            return is_folder and not is_system
        if self.is_shortcut_group:
            return extension.lower() == ".lnk" and not is_system
        return extension.lower() in self.extensions and not is_system


# Default groups with their extensions
DEFAULT_GROUPS = [
    IconGroup(
        name="快捷方式",
        extensions={".lnk"},
        is_shortcut_group=True,
        priority=0
    ),
    IconGroup(
        name="文件夹",
        extensions=set(),
        is_folder_group=True,
        priority=1
    ),
    IconGroup(
        name="文档",
        extensions={".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", 
                   ".txt", ".rtf", ".odt", ".ods", ".odp"},
        priority=2
    ),
    IconGroup(
        name="图片",
        extensions={".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
                   ".ico", ".tiff", ".tif", ".psd", ".ai", ".raw"},
        priority=3
    ),
    IconGroup(
        name="视频",
        extensions={".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
                   ".m4v", ".mpg", ".mpeg", ".3gp"},
        priority=4
    ),
    IconGroup(
        name="音频",
        extensions={".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
                   ".aiff", ".ape"},
        priority=5
    ),
    IconGroup(
        name="压缩包",
        extensions={".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
                   ".iso", ".cab"},
        priority=6
    ),
    IconGroup(
        name="程序",
        extensions={".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs"},
        priority=7
    ),
    IconGroup(
        name="系统图标",
        extensions=set(),
        is_system_group=True,
        priority=8
    ),
    IconGroup(
        name="其他",
        extensions=set(),  # Catch-all group
        priority=999
    ),
]



class Classifier:
    """Classifies desktop icons into groups."""
    
    def __init__(self):
        self.groups: List[IconGroup] = []
        self._load_default_groups()
    
    def _load_default_groups(self):
        """Load default groups."""
        import copy
        self.groups = [copy.deepcopy(g) for g in DEFAULT_GROUPS]
    
    def add_group(self, name: str, extensions: Set[str], priority: int = 50,
                  start_from_right: bool = False) -> IconGroup:
        """Add a custom group."""
        group = IconGroup(
            name=name,
            extensions={ext.lower() if ext.startswith(".") else f".{ext.lower()}" 
                       for ext in extensions},
            priority=priority,
            start_from_right=start_from_right
        )
        self.groups.append(group)
        self._sort_groups()
        return group
    
    def remove_group(self, name: str) -> bool:
        """Remove a group by name."""
        for i, group in enumerate(self.groups):
            if group.name == name:
                del self.groups[i]
                return True
        return False
    
    def get_group(self, name: str) -> Optional[IconGroup]:
        """Get a group by name."""
        for group in self.groups:
            if group.name == name:
                return group
        return None
    
    def set_group_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a group."""
        group = self.get_group(name)
        if group:
            group.enabled = enabled
            return True
        return False
    
    def set_group_priority(self, name: str, priority: int) -> bool:
        """Set the priority of a group (affects display order)."""
        group = self.get_group(name)
        if group:
            group.priority = priority
            self._sort_groups()
            return True
        return False
    
    def set_group_start_side(self, name: str, start_from_right: bool) -> bool:
        """Set whether a group starts from the right side."""
        group = self.get_group(name)
        if group:
            group.start_from_right = start_from_right
            return True
        return False
    
    def _sort_groups(self):
        """Sort groups by priority."""
        self.groups.sort(key=lambda g: g.priority)
    
    def classify(self, extension: str, is_folder: bool, is_system: bool = False) -> str:
        """Classify a file into a group, returns group name."""
        for group in self.groups:
            if group.matches(extension, is_folder, is_system):
                return group.name
        return "其他"  # Fallback
    
    def classify_icons(self, icons) -> Dict[str, list]:
        """Classify a list of DesktopIcon objects into groups.
        
        Returns:
            Dict mapping group name to list of icons
        """
        result: Dict[str, list] = {}
        
        # Initialize all enabled groups
        for group in self.groups:
            if group.enabled:
                result[group.name] = []
        
        # Classify each icon
        for icon in icons:
            # Pass is_system_icon flag for proper classification
            is_system = getattr(icon, 'is_system_icon', False)
            group_name = self.classify(icon.extension, icon.is_folder, is_system)
            if group_name in result:
                result[group_name].append(icon)
        
        # Remove ALL empty groups to avoid empty columns
        result = {k: v for k, v in result.items() if v}
        
        return result
    
    def get_enabled_groups(self) -> List[IconGroup]:
        """Get all enabled groups in priority order."""
        return [g for g in self.groups if g.enabled]
    
    def to_dict(self) -> Dict:
        """Convert classifier state to dictionary for saving."""
        return {
            "groups": [
                {
                    "name": g.name,
                    "extensions": list(g.extensions),
                    "enabled": g.enabled,
                    "is_folder_group": g.is_folder_group,
                    "is_shortcut_group": g.is_shortcut_group,
                    "is_system_group": g.is_system_group,
                    "priority": g.priority,
                    "start_from_right": g.start_from_right,
                    "merge_group": g.merge_group
                }
                for g in self.groups
            ]
        }
    
    def from_dict(self, data: Dict):
        """Load classifier state from dictionary."""
        if "groups" not in data:
            return
        
        self.groups = []
        for g_data in data["groups"]:
            group = IconGroup(
                name=g_data["name"],
                extensions=set(g_data.get("extensions", [])),
                enabled=g_data.get("enabled", True),
                is_folder_group=g_data.get("is_folder_group", False),
                is_shortcut_group=g_data.get("is_shortcut_group", False),
                is_system_group=g_data.get("is_system_group", False),
                priority=g_data.get("priority", 50),
                start_from_right=g_data.get("start_from_right", False),
                merge_group=g_data.get("merge_group", "")
            )
            self.groups.append(group)
        
        self._sort_groups()

