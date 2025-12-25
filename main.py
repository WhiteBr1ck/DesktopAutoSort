"""
DesktopAutoSort - Desktop Icon Organizer for Windows

A tool to organize desktop icons by file type with customizable grouping,
sorting, and layout options. Runs in the system tray for easy access.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSharedMemory, QObject, pyqtSignal

from core.desktop import DesktopIconManager
from core.classifier import Classifier
from core.layout import LayoutManager, ArrangeDirection, SortOrder
from config.settings import ConfigManager, get_config_dir
from ui.tray import TrayIcon
from ui.settings_window import SettingsWindow


class HotkeySignalHelper(QObject):
    """Helper class for thread-safe hotkey signal emission."""
    hotkey_triggered = pyqtSignal()


class DesktopAutoSort:
    """Main application class."""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Set global application icon
        self._set_app_icon()
        
        # Single instance check
        self.shared_memory = QSharedMemory("DesktopAutoSort_SingleInstance")
        if not self.shared_memory.create(1):
            QMessageBox.warning(None, "已运行", "DesktopAutoSort 已在运行中。")
            sys.exit(1)
        
        # Initialize components
        self.config = ConfigManager()
        self.desktop_manager = None
        self.classifier = Classifier()
        self.layout_manager = LayoutManager(get_config_dir())
        
        # Load saved settings
        self._load_settings()
        
        # Create UI
        self.tray = TrayIcon()
        self.settings_window = None
        
        # Connect signals
        self._connect_signals()
        
        # Update tray menu
        self._update_tray_state()
        
        # Setup global hotkey
        self._setup_hotkey()
        
        # Show settings window on startup
        self.show_settings()
    
    def _set_app_icon(self):
        """Set global application icon."""
        from PyQt6.QtGui import QIcon
        import sys
        
        # Check for icon.ico in project root
        icon_paths = ["icon.ico", "resources/icon.png", "resources/icon.ico"]
        
        # For PyInstaller bundled app, check _MEIPASS first
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        for path in icon_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                self.app.setWindowIcon(QIcon(full_path))
                break
    
    def _setup_hotkey(self):
        """Setup global hotkey for organize using global-hotkeys."""
        from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
        
        self.stop_checking_hotkeys = stop_checking_hotkeys
        self.hotkey_enabled = False
        
        # Create signal helper for thread-safe hotkey activation
        self.hotkey_signal = HotkeySignalHelper()
        self.hotkey_signal.hotkey_triggered.connect(self.organize_desktop)
        
        if self.config.is_hotkey_enabled():
            hotkey = self.config.get_hotkey()
            self._register_hotkey(hotkey)
    
    def _format_hotkey_for_global_hotkeys(self, hotkey: str) -> str:
        """Format hotkey string for global-hotkeys (uses 'control + shift + o' format)."""
        parts = hotkey.lower().split("+")
        formatted = []
        
        for part in parts:
            part = part.strip()
            if part == "ctrl":
                formatted.append("control")
            elif part == "win":
                formatted.append("windows")
            else:
                formatted.append(part)
        
        return " + ".join(formatted)
    
    def _register_hotkey(self, hotkey: str):
        """Register a global hotkey using global-hotkeys."""
        from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys, clear_hotkeys
        
        # Unregister previous hotkeys
        self._unregister_hotkey()
        
        try:
            formatted = self._format_hotkey_for_global_hotkeys(hotkey)
            
            # Define binding - [hotkey, on_press_callback, on_release_callback, actuate_on_partial_release]
            bindings = [
                [formatted, None, self._on_hotkey_triggered, True],
            ]
            
            register_hotkeys(bindings)
            start_checking_hotkeys()
            self.hotkey_enabled = True
            print(f"Registered hotkey: {hotkey} -> {formatted}")
        except Exception as e:
            print(f"Failed to register hotkey: {e}")
    
    def _unregister_hotkey(self):
        """Unregister current hotkey."""
        from global_hotkeys import clear_hotkeys, stop_checking_hotkeys
        
        if self.hotkey_enabled:
            try:
                stop_checking_hotkeys()
                clear_hotkeys()
                self.hotkey_enabled = False
            except Exception:
                pass
    
    def _on_hotkey_triggered(self):
        """Called when hotkey is pressed."""
        print("Hotkey triggered!")
        # Emit signal to trigger organize_desktop from main thread
        self.hotkey_signal.hotkey_triggered.emit()
    
    def _on_hotkey_changed(self, hotkey: str, enabled: bool):
        """Handle hotkey settings change from UI."""
        self.config.set_hotkey(hotkey)
        self.config.set_hotkey_enabled(enabled)
        self.config.save()
        
        if enabled:
            self._register_hotkey(hotkey)
        else:
            self._unregister_hotkey()
    
    def _load_settings(self):
        """Load settings from config."""
        from core.presets import apply_preset
        
        # Always apply the current preset to ensure groups match
        current_preset = self.config.get_current_preset()
        apply_preset(self.classifier, current_preset)  # Note: classifier first, then preset_id
        print(f"Applied preset: {current_preset}")
        
        # Load layout settings
        layout_data = self.config.get_layout_data()
        if layout_data:
            self.layout_manager.from_dict(layout_data)
    
    def _save_settings(self):
        """Save current settings to config."""
        self.config.set_classifier_data(self.classifier.to_dict())
        self.config.set_layout_data(self.layout_manager.to_dict())
        if self.settings_window:
            self.config.set_monitor_mode(self.settings_window.get_monitor_mode())
        self.config.save()
    
    def _connect_signals(self):
        """Connect tray signals."""
        self.tray.organize_requested.connect(self.organize_desktop)
        self.tray.save_layout_requested.connect(self.save_layout)
        self.tray.restore_layout_requested.connect(self.restore_layout)
        self.tray.settings_requested.connect(self.show_settings)
        self.tray.exit_requested.connect(self.exit_app)
        self.tray.direction_changed.connect(self._on_direction_changed)
        self.tray.sort_changed.connect(self._on_sort_changed)
        self.tray.preset_changed.connect(self._on_preset_changed)
    
    def _update_tray_state(self):
        """Update tray menu state from settings."""
        # Update direction
        self.tray.set_direction(self.layout_manager.settings.direction.value)
        
        # Update sort order
        self.tray.set_sort_order(self.layout_manager.settings.sort_order.value)
        
        # Update layouts menu
        self.tray.update_layouts_menu(self.layout_manager.get_user_layouts())
        
        # Update presets menu with current preset
        from core.presets import get_all_presets_info
        current_preset = self.config.get_current_preset()
        self.tray.update_presets_menu(get_all_presets_info(), current_preset)
    
    def _on_direction_changed(self, direction: str):
        """Handle direction change from tray."""
        self.layout_manager.settings.direction = ArrangeDirection(direction)
        self._save_settings()
    
    def _on_sort_changed(self, sort_order: str):
        """Handle sort change from tray."""
        self.layout_manager.settings.sort_order = SortOrder(sort_order)
        self._save_settings()
    
    def _on_preset_changed(self, preset_id: str):
        """Handle preset change from tray."""
        from core.presets import apply_preset
        if apply_preset(self.classifier, preset_id):
            self.config.set_current_preset(preset_id)
            self._save_settings()
            self.tray.set_current_preset(preset_id)
            # Refresh settings window if open
            if self.settings_window:
                self.settings_window.groups_tab._refresh_list()
                self.settings_window.groups_tab._refresh_presets()
    
    def _on_settings_preset_applied(self, preset_id: str):
        """Handle preset applied from settings window - sync to tray."""
        self.config.set_current_preset(preset_id)
        self._save_settings()
        self.tray.set_current_preset(preset_id)
    
    def _get_desktop_manager(self) -> DesktopIconManager:
        """Get or create desktop manager."""
        if self.desktop_manager is None:
            try:
                self.desktop_manager = DesktopIconManager()
            except RuntimeError as e:
                QMessageBox.critical(
                    None, "错误", 
                    f"无法访问桌面窗口：\n{e}\n\n请尝试重启资源管理器后再试。"
                )
                raise
        return self.desktop_manager
    
    def organize_desktop(self):
        """Organize desktop icons."""
        try:
            dm = self._get_desktop_manager()
            
            # Get current icons
            icons = dm.get_desktop_icons()
            if not icons:
                self.tray.show_message("提示", "桌面上没有找到图标。")
                return
            
            # DEBUG: Print all icons
            print("\n" + "="*60)
            print("DEBUG: organize_desktop()")
            print("="*60)
            print(f"Found {len(icons)} icons:")
            for icon in icons:
                print(f"  - {icon.name}: path={icon.path[:30] if icon.path else 'None'}..., "
                      f"ext={icon.extension}, folder={icon.is_folder}, system={icon.is_system_icon}")
            
            # Auto-save current layout
            self.layout_manager.save_layout(LayoutManager.LAST_LAYOUT_NAME, icons)
            
            # If using smart extension preset, rescan desktop for new extensions
            current_preset = self.config.get_current_preset()
            if current_preset == "by_extension":
                from core.presets import apply_preset
                apply_preset(self.classifier, "by_extension")
                print("DEBUG: Rescanned desktop for smart extension preset")
            
            # Classify icons
            classified = self.classifier.classify_icons(icons)
            
            # DEBUG: Print classification results
            print(f"\nClassification results ({len(classified)} groups with icons):")
            for group_name, group_icons in classified.items():
                print(f"  Group '{group_name}': {len(group_icons)} icons")
                for icon in group_icons:
                    print(f"    - {icon.name}")
            
            # Get monitor info
            monitor_mode = self.config.get_monitor_mode()
            if monitor_mode == "primary":
                monitor = dm.get_primary_monitor()
            else:
                monitor = dm.get_primary_monitor()
            
            if not monitor:
                self.tray.show_message("错误", "无法获取显示器信息。")
                return
            
            # DEBUG: Print monitor info
            print(f"\nMonitor: {monitor.name}, work_area={monitor.work_area}")
            
            # Get icon spacing
            spacing = dm.get_icon_spacing()
            print(f"Icon spacing: h={spacing[0]}, v={spacing[1]}")
            
            # DEBUG: Print layout settings
            print(f"\nLayout settings:")
            print(f"  direction={self.layout_manager.settings.direction}")
            print(f"  start_from_right={self.layout_manager.settings.start_from_right}")
            print(f"  margins: L={self.layout_manager.settings.margin_left}, "
                  f"T={self.layout_manager.settings.margin_top}, "
                  f"R={self.layout_manager.settings.margin_right}, "
                  f"B={self.layout_manager.settings.margin_bottom}")
            
            # Get grid origin from current icon positions
            grid_origin = dm.get_grid_origin()
            print(f"  grid_origin: ({grid_origin[0]}, {grid_origin[1]})")
            
            # Calculate new positions
            enabled_groups = self.classifier.get_enabled_groups()
            print(f"\nEnabled groups ({len(enabled_groups)}):")
            for g in enabled_groups:
                print(f"  - {g.name} (priority={g.priority})")
            
            positions = self.layout_manager.calculate_positions(
                classified, enabled_groups, monitor, spacing, grid_origin
            )
            
            # DEBUG: Print calculated positions
            print(f"\nCalculated positions ({len(positions)}):")
            # Group by x coordinate to see columns
            by_x = {}
            for name, (x, y) in sorted(positions.items(), key=lambda item: (item[1][0], item[1][1])):
                if x not in by_x:
                    by_x[x] = []
                by_x[x].append((name, y))
            
            for x in sorted(by_x.keys()):
                print(f"  Column x={x}:")
                for name, y in sorted(by_x[x], key=lambda item: item[1]):
                    print(f"    y={y}: {name}")
            
            # Apply positions
            print("\nApplying positions...")
            dm.set_icon_positions(positions)
            
            # Refresh desktop
            dm.refresh_desktop()
            print("Done!")
            print("="*60 + "\n")
            
            self.tray.show_message("完成", f"已整理 {len(icons)} 个图标。")
            
        except Exception as e:
            self.tray.show_message("错误", f"整理失败: {e}")
    
    def save_layout(self, name: str):
        """Save current layout."""
        try:
            dm = self._get_desktop_manager()
            icons = dm.get_desktop_icons()
            
            if not icons:
                self.tray.show_message("提示", "桌面上没有找到图标。")
                return
            
            self.layout_manager.save_layout(name, icons)
            self._update_tray_state()
            self.tray.show_message("已保存", f"布局 \"{name}\" 已保存。")
            
            # Refresh settings window if open
            if self.settings_window and self.settings_window.isVisible():
                self.settings_window.refresh_layouts()
                
        except Exception as e:
            self.tray.show_message("错误", f"保存失败: {e}")
    
    def restore_layout(self, name: str):
        """Restore a saved layout."""
        try:
            layout = self.layout_manager.get_layout(name)
            if not layout:
                self.tray.show_message("错误", f"找不到布局 \"{name}\"。")
                return
            
            dm = self._get_desktop_manager()
            dm.set_icon_positions(layout.positions)
            dm.refresh_desktop()
            
            display_name = name if not name.startswith("_") else "上次布局"
            self.tray.show_message("已恢复", f"布局 \"{display_name}\" 已恢复。")
            
        except Exception as e:
            self.tray.show_message("错误", f"恢复失败: {e}")
    
    def show_settings(self):
        """Show settings window."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                self.classifier, self.layout_manager
            )
            self.settings_window.settings_changed.connect(self._save_settings)
            self.settings_window.layout_restored.connect(self.restore_layout)
            self.settings_window.organize_requested.connect(self.organize_desktop)
            self.settings_window.set_monitor_mode(self.config.get_monitor_mode())
            # Sync preset selection between settings and tray
            self.settings_window.groups_tab.preset_applied.connect(self._on_settings_preset_applied)
            # Connect hotkey settings
            self.settings_window.hotkey_tab.hotkey_changed.connect(self._on_hotkey_changed)
            # Load saved hotkey values
            self.settings_window.hotkey_tab.set_hotkey(self.config.get_hotkey())
            self.settings_window.hotkey_tab.set_enabled(self.config.is_hotkey_enabled())
        
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
    
    def exit_app(self):
        """Exit the application."""
        self._save_settings()
        self._unregister_hotkey()
        self.tray.hide()
        self.app.quit()
        # Force exit in case background threads are still running
        import os
        os._exit(0)
    
    def run(self):
        """Run the application."""
        return self.app.exec()


def main():
    """Application entry point."""
    app = DesktopAutoSort()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
