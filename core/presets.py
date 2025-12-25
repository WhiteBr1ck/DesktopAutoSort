"""
Preset configurations for desktop icon grouping.
Each preset defines a set of groups with specific merge settings.
"""

from typing import List, Dict, Callable
from .classifier import IconGroup, Classifier
import copy


# Preset definitions
PRESETS: Dict[str, Dict] = {
    "default": {
        "name": "默认模式",
        "description": "系统图标+快捷方式合并，办公文档分类独立",
        "groups": [
            {"name": "系统图标", "is_system_group": True, "priority": 0, "merge_group": "系统"},
            {"name": "快捷方式", "is_shortcut_group": True, "priority": 1, "merge_group": "系统"},
            {"name": "程序", "extensions": [".exe", ".msi", ".bat", ".cmd", ".ps1"], "priority": 2, "merge_group": ""},
            {"name": "文件夹", "is_folder_group": True, "priority": 3, "merge_group": ""},
            {"name": "PDF", "extensions": [".pdf"], "priority": 4, "merge_group": ""},
            {"name": "Word", "extensions": [".doc", ".docx"], "priority": 5, "merge_group": ""},
            {"name": "Excel", "extensions": [".xls", ".xlsx", ".csv"], "priority": 6, "merge_group": ""},
            {"name": "PPT", "extensions": [".ppt", ".pptx"], "priority": 7, "merge_group": ""},
            {"name": "文本", "extensions": [".txt", ".rtf", ".md"], "priority": 8, "merge_group": ""},
            {"name": "图片", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"], "priority": 9, "merge_group": ""},
            {"name": "视频", "extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts", ".rmvb"], "priority": 10, "merge_group": ""},
            {"name": "音频", "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"], "priority": 11, "merge_group": ""},
            {"name": "压缩包", "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"], "priority": 12, "merge_group": ""},
            {"name": "网页", "extensions": [".html", ".htm", ".xml", ".xhtml", ".css", ".js"], "priority": 13, "merge_group": ""},
            {"name": "其他", "extensions": [], "priority": 999, "merge_group": ""},
        ]
    },
    
    "compact": {
        "name": "紧凑模式",
        "description": "系统图标+快捷方式合并，文档合并，媒体文件合并",
        "groups": [
            {"name": "系统图标", "is_system_group": True, "priority": 0, "merge_group": "系统"},
            {"name": "快捷方式", "is_shortcut_group": True, "priority": 1, "merge_group": "系统"},
            {"name": "文件夹", "is_folder_group": True, "priority": 2, "merge_group": ""},
            {"name": "文档", "extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"], "priority": 3, "merge_group": "文档"},
            {"name": "图片", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"], "priority": 4, "merge_group": "媒体"},
            {"name": "视频", "extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"], "priority": 5, "merge_group": "媒体"},
            {"name": "音频", "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"], "priority": 6, "merge_group": "媒体"},
            {"name": "压缩包", "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"], "priority": 7, "merge_group": ""},
            {"name": "程序", "extensions": [".exe", ".msi", ".bat", ".cmd", ".ps1"], "priority": 8, "merge_group": ""},
            {"name": "其他", "extensions": [], "priority": 999, "merge_group": ""},
        ]
    },
    
    "by_extension": {
        "name": "按扩展名 (智能)",
        "description": "扫描桌面，自动为每种扩展名创建独立分组",
        "dynamic": True,  # Special flag indicating this preset is generated dynamically
        "groups": []  # Will be generated at runtime
    },
    
    "minimal": {
        "name": "极简模式",
        "description": "系统图标+快捷方式合并，其他所有文件合并为一组",
        "groups": [
            {"name": "系统图标", "is_system_group": True, "priority": 0, "merge_group": "系统"},
            {"name": "快捷方式", "is_shortcut_group": True, "priority": 1, "merge_group": "系统"},
            {"name": "文件夹", "is_folder_group": True, "priority": 2, "merge_group": "文件"},
            {"name": "文档", "extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"], "priority": 3, "merge_group": "文件"},
            {"name": "图片", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"], "priority": 4, "merge_group": "文件"},
            {"name": "视频", "extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"], "priority": 5, "merge_group": "文件"},
            {"name": "音频", "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"], "priority": 6, "merge_group": "文件"},
            {"name": "压缩包", "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"], "priority": 7, "merge_group": "文件"},
            {"name": "程序", "extensions": [".exe", ".msi", ".bat", ".cmd", ".ps1"], "priority": 8, "merge_group": "文件"},
            {"name": "其他", "extensions": [], "priority": 999, "merge_group": "文件"},
        ]
    },
}


def get_preset_names() -> List[str]:
    """Get list of available preset names."""
    return list(PRESETS.keys())


def get_preset_info(preset_id: str) -> Dict:
    """Get preset name and description."""
    if preset_id in PRESETS:
        return {
            "id": preset_id,
            "name": PRESETS[preset_id]["name"],
            "description": PRESETS[preset_id]["description"]
        }
    return None


def get_all_presets_info() -> List[Dict]:
    """Get info for all presets."""
    return [get_preset_info(p) for p in PRESETS.keys()]


def apply_preset(classifier: Classifier, preset_id: str) -> bool:
    """Apply a preset to the classifier."""
    if preset_id not in PRESETS:
        return False
    
    preset = PRESETS[preset_id]
    classifier.groups = []
    
    # Handle dynamic presets
    if preset.get("dynamic"):
        if preset_id == "by_extension":
            _apply_dynamic_extension_preset(classifier)
            return True
        return False
    
    # Handle static presets
    for g_data in preset["groups"]:
        group = IconGroup(
            name=g_data["name"],
            extensions=set(g_data.get("extensions", [])),
            enabled=g_data.get("enabled", True),
            is_folder_group=g_data.get("is_folder_group", False),
            is_shortcut_group=g_data.get("is_shortcut_group", False),
            is_system_group=g_data.get("is_system_group", False),
            priority=g_data.get("priority", 50),
            start_from_right=False,
            merge_group=g_data.get("merge_group", "")
        )
        classifier.groups.append(group)
    
    return True


def _apply_dynamic_extension_preset(classifier: Classifier):
    """Apply the dynamic 'by extension' preset by scanning desktop."""
    import os
    
    # Get desktop paths
    desktop_paths = []
    user_desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.exists(user_desktop):
        desktop_paths.append(user_desktop)
    
    public_desktop = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
    if os.path.exists(public_desktop):
        desktop_paths.append(public_desktop)
    
    # Scan for extensions
    extensions_found = set()
    for desktop_path in desktop_paths:
        try:
            for item in os.listdir(desktop_path):
                full_path = os.path.join(desktop_path, item)
                if os.path.isfile(full_path):
                    _, ext = os.path.splitext(item)
                    if ext and ext.lower() != ".lnk":  # Skip shortcuts
                        extensions_found.add(ext.lower())
        except:
            pass
    
    # Create groups
    # 1. System icons + Shortcuts (merged)
    classifier.groups.append(IconGroup(
        name="系统图标",
        extensions=set(),
        enabled=True,
        is_system_group=True,
        priority=0,
        merge_group="系统"
    ))
    classifier.groups.append(IconGroup(
        name="快捷方式",
        extensions=set(),
        enabled=True,
        is_shortcut_group=True,
        priority=1,
        merge_group="系统"
    ))
    
    # 2. Folders
    classifier.groups.append(IconGroup(
        name="文件夹",
        extensions=set(),
        enabled=True,
        is_folder_group=True,
        priority=2,
        merge_group=""
    ))
    
    # 3. Each extension as its own group
    priority = 10
    for ext in sorted(extensions_found):
        classifier.groups.append(IconGroup(
            name=ext,
            extensions={ext},
            enabled=True,
            priority=priority,
            merge_group=""
        ))
        priority += 1
    
    # 4. Catch-all for anything not matched
    classifier.groups.append(IconGroup(
        name="其他",
        extensions=set(),
        enabled=True,
        priority=999,
        merge_group=""
    ))


# Custom preset management
import os
import json

def _get_custom_presets_path() -> str:
    """Get path to custom presets file."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = os.path.join(appdata, "DesktopAutoSort")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "custom_presets.json")


def _load_custom_presets() -> Dict:
    """Load custom presets from file."""
    path = _get_custom_presets_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_custom_presets(presets: Dict):
    """Save custom presets to file."""
    path = _get_custom_presets_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def save_custom_preset(name: str, classifier: Classifier) -> bool:
    """Save current classifier configuration as a custom preset."""
    if not name:
        return False
    
    preset_id = f"custom_{name}"
    
    # Convert classifier groups to preset format
    groups_data = []
    for g in classifier.groups:
        groups_data.append({
            "name": g.name,
            "extensions": list(g.extensions),
            "enabled": g.enabled,
            "is_folder_group": g.is_folder_group,
            "is_shortcut_group": g.is_shortcut_group,
            "is_system_group": g.is_system_group,
            "priority": g.priority,
            "merge_group": g.merge_group,
            "start_from_right": g.start_from_right
        })
    
    preset = {
        "name": f"自定义: {name}",
        "description": "用户自定义预设",
        "groups": groups_data
    }
    
    # Load existing custom presets and add new one
    custom_presets = _load_custom_presets()
    custom_presets[preset_id] = preset
    _save_custom_presets(custom_presets)
    
    # Also add to in-memory PRESETS
    PRESETS[preset_id] = preset
    
    return True


def update_custom_preset(preset_id: str, classifier: Classifier) -> bool:
    """Update an existing custom preset with current classifier configuration."""
    if not preset_id or not preset_id.startswith("custom_"):
        return False
    
    if preset_id not in PRESETS:
        return False
    
    # Get existing preset to preserve name
    existing = PRESETS[preset_id]
    
    # Convert classifier groups to preset format
    groups_data = []
    for g in classifier.groups:
        groups_data.append({
            "name": g.name,
            "extensions": list(g.extensions),
            "enabled": g.enabled,
            "is_folder_group": g.is_folder_group,
            "is_shortcut_group": g.is_shortcut_group,
            "is_system_group": g.is_system_group,
            "priority": g.priority,
            "merge_group": g.merge_group,
            "start_from_right": g.start_from_right
        })
    
    preset = {
        "name": existing["name"],
        "description": existing.get("description", "用户自定义预设"),
        "groups": groups_data
    }
    
    # Load existing custom presets and update
    custom_presets = _load_custom_presets()
    custom_presets[preset_id] = preset
    _save_custom_presets(custom_presets)
    
    # Also update in-memory PRESETS
    PRESETS[preset_id] = preset
    
    return True


def delete_custom_preset(preset_id: str) -> bool:
    """Delete a custom preset."""
    if not preset_id.startswith("custom_"):
        return False
    
    custom_presets = _load_custom_presets()
    if preset_id in custom_presets:
        del custom_presets[preset_id]
        _save_custom_presets(custom_presets)
    
    if preset_id in PRESETS:
        del PRESETS[preset_id]
    
    return True


def load_custom_presets():
    """Load all custom presets into PRESETS dict."""
    custom_presets = _load_custom_presets()
    PRESETS.update(custom_presets)


# Load custom presets on module import
load_custom_presets()

