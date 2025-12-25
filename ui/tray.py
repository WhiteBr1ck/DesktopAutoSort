"""
System tray icon and menu for DesktopAutoSort.
"""

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QMessageBox,
    QInputDialog, QWidget
)
from PyQt6.QtGui import QIcon, QAction, QActionGroup
from PyQt6.QtCore import pyqtSignal, QObject


class TrayIcon(QObject):
    """System tray icon with context menu."""
    
    # Signals
    organize_requested = pyqtSignal()
    save_layout_requested = pyqtSignal(str)  # layout name
    restore_layout_requested = pyqtSignal(str)  # layout name
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    direction_changed = pyqtSignal(str)  # "vertical" or "horizontal"
    sort_changed = pyqtSignal(str)  # sort order value
    preset_changed = pyqtSignal(str)  # preset id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.tray_icon = QSystemTrayIcon(parent)
        self._create_menu()
        self._connect_signals()
        
        # Set default icon (will be replaced with actual icon)
        self._set_default_icon()
        
        # Show tray icon
        self.tray_icon.show()
    
    def _set_default_icon(self):
        """Set a default icon for the tray."""
        import os
        import sys
        # Try to load custom icon, fall back to system icon
        try:
            # Check for icon.ico in current directory or resources
            icon_paths = ["icon.ico", "resources/icon.png", "resources/icon.ico"]
            found_icon = False
            
            # For PyInstaller bundled app, check _MEIPASS first
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            for path in icon_paths:
                full_path = os.path.join(base_dir, path)
                if os.path.exists(full_path):
                    self.tray_icon.setIcon(QIcon(full_path))
                    found_icon = True
                    break
            
            if not found_icon:
                # Use a system icon as fallback
                icon = QApplication.style().standardIcon(
                    QApplication.style().StandardPixmap.SP_DesktopIcon
                )
                self.tray_icon.setIcon(icon)
        except Exception:
            pass
        
        self.tray_icon.setToolTip("DesktopAutoSort")
    
    def _create_menu(self):
        """Create the context menu."""
        self.menu = QMenu()
        
        # One-click organize
        self.organize_action = QAction("📁 一键整理", self.menu)
        self.organize_action.setFont(self.organize_action.font())
        self.menu.addAction(self.organize_action)
        
        self.menu.addSeparator()
        
        # Direction submenu
        self.direction_menu = QMenu("↔️ 排列方式", self.menu)
        self.direction_group = QActionGroup(self.direction_menu)
        
        self.vertical_action = QAction("竖排", self.direction_menu)
        self.vertical_action.setCheckable(True)
        self.vertical_action.setChecked(True)
        self.vertical_action.setData("vertical")
        self.direction_group.addAction(self.vertical_action)
        self.direction_menu.addAction(self.vertical_action)
        
        self.horizontal_action = QAction("横排", self.direction_menu)
        self.horizontal_action.setCheckable(True)
        self.horizontal_action.setData("horizontal")
        self.direction_group.addAction(self.horizontal_action)
        self.direction_menu.addAction(self.horizontal_action)
        
        self.menu.addMenu(self.direction_menu)
        
        # Sort submenu
        self.sort_menu = QMenu("📋 排序方式", self.menu)
        self.sort_group = QActionGroup(self.sort_menu)
        
        sort_options = [
            ("名称 (A-Z)", "name_asc"),
            ("名称 (Z-A)", "name_desc"),
            ("创建时间 (旧→新)", "created_asc"),
            ("创建时间 (新→旧)", "created_desc"),
            ("修改时间 (旧→新)", "modified_asc"),
            ("修改时间 (新→旧)", "modified_desc"),
            ("大小 (小→大)", "size_asc"),
            ("大小 (大→小)", "size_desc"),
        ]
        
        self.sort_actions = []
        for label, value in sort_options:
            action = QAction(label, self.sort_menu)
            action.setCheckable(True)
            action.setData(value)
            if value == "name_asc":
                action.setChecked(True)
            self.sort_group.addAction(action)
            self.sort_menu.addAction(action)
            self.sort_actions.append(action)
        
        self.menu.addMenu(self.sort_menu)
        
        # Preset submenu
        self.preset_menu = QMenu("🎨 预设", self.menu)
        self.menu.addMenu(self.preset_menu)
        
        self.menu.addSeparator()
        
        # Save layout
        self.save_layout_action = QAction("💾 保存当前布局...", self.menu)
        self.menu.addAction(self.save_layout_action)
        
        # Restore layout submenu (will be populated dynamically)
        self.restore_menu = QMenu("📂 恢复布局", self.menu)
        self.menu.addMenu(self.restore_menu)
        
        self.menu.addSeparator()
        
        # Exit
        self.exit_action = QAction("❌ 退出", self.menu)
        self.menu.addAction(self.exit_action)
        
        self.tray_icon.setContextMenu(self.menu)
    
    def _connect_signals(self):
        """Connect menu actions to signals."""
        # Left click to show settings
        self.tray_icon.activated.connect(self._on_activated)
        
        # Menu actions
        self.organize_action.triggered.connect(self.organize_requested.emit)
        self.exit_action.triggered.connect(self.exit_requested.emit)
        self.save_layout_action.triggered.connect(self._on_save_layout)
        
        # Direction change
        self.direction_group.triggered.connect(self._on_direction_changed)
        
        # Sort change
        self.sort_group.triggered.connect(self._on_sort_changed)
    
    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            # Left click - show settings
            self.settings_requested.emit()
    
    def _on_save_layout(self):
        """Handle save layout action."""
        name, ok = QInputDialog.getText(
            None, "保存布局", "请输入布局名称:",
        )
        if ok and name:
            self.save_layout_requested.emit(name)
    
    def _on_direction_changed(self, action):
        """Handle direction change."""
        self.direction_changed.emit(action.data())
    
    def _on_sort_changed(self, action):
        """Handle sort change."""
        self.sort_changed.emit(action.data())
    
    def update_layouts_menu(self, layouts):
        """Update the restore layouts submenu.
        
        Args:
            layouts: List of SavedLayout objects
        """
        self.restore_menu.clear()
        
        if not layouts:
            no_layouts_action = QAction("(无保存的布局)", self.restore_menu)
            no_layouts_action.setEnabled(False)
            self.restore_menu.addAction(no_layouts_action)
        else:
            for layout in layouts:
                action = QAction(layout.name, self.restore_menu)
                action.triggered.connect(
                    lambda checked, n=layout.name: self.restore_layout_requested.emit(n)
                )
                self.restore_menu.addAction(action)
    
    def set_direction(self, direction: str):
        """Set the current direction in the menu."""
        if direction == "vertical":
            self.vertical_action.setChecked(True)
        else:
            self.horizontal_action.setChecked(True)
    
    def set_sort_order(self, sort_order: str):
        """Set the current sort order in the menu."""
        for action in self.sort_actions:
            if action.data() == sort_order:
                action.setChecked(True)
                break
    
    def show_message(self, title: str, message: str, 
                     icon=QSystemTrayIcon.MessageIcon.Information):
        """Show a tray notification."""
        self.tray_icon.showMessage(title, message, icon, 2000)
    
    def update_presets_menu(self, presets, current_preset_id=None):
        """Update the presets submenu.
        
        Args:
            presets: List of dicts with 'id', 'name', 'description'
            current_preset_id: ID of the currently active preset (for checkmark)
        """
        self.preset_menu.clear()
        self.preset_actions = []  # Store actions for later updates
        
        self.preset_action_group = QActionGroup(self.preset_menu)
        self.preset_action_group.setExclusive(True)
        
        for preset in presets:
            action = QAction(f"{preset['name']}", self.preset_menu)
            action.setCheckable(True)
            action.setData(preset['id'])
            if current_preset_id and preset['id'] == current_preset_id:
                action.setChecked(True)
            action.triggered.connect(
                lambda checked, pid=preset['id']: self.preset_changed.emit(pid)
            )
            self.preset_action_group.addAction(action)
            self.preset_menu.addAction(action)
            self.preset_actions.append(action)
    
    def set_current_preset(self, preset_id: str):
        """Set the current preset checkmark in the menu."""
        if hasattr(self, 'preset_actions'):
            for action in self.preset_actions:
                action.setChecked(action.data() == preset_id)
    
    def hide(self):
        """Hide the tray icon."""
        self.tray_icon.hide()
