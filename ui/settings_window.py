"""
Settings window for DesktopAutoSort.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QComboBox,
    QSpinBox, QMessageBox, QInputDialog, QAbstractItemView,
    QSplitter, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QIcon

from core.classifier import IconGroup, Classifier
from core.layout import LayoutManager, ArrangeDirection, SortOrder
from core.presets import get_all_presets_info, apply_preset, save_custom_preset, delete_custom_preset, update_custom_preset


class GroupEditWidget(QWidget):
    """Widget for editing a single group."""
    
    group_changed = pyqtSignal()
    
    def __init__(self, group: IconGroup, parent=None):
        super().__init__(parent)
        self.group = group
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Enabled checkbox
        self.enabled_cb = QCheckBox("启用此分组")
        self.enabled_cb.setChecked(self.group.enabled)
        self.enabled_cb.toggled.connect(self._on_changed)
        layout.addRow(self.enabled_cb)
        
        # Group name
        self.name_edit = QLineEdit(self.group.name)
        self.name_edit.textChanged.connect(self._on_changed)
        layout.addRow("分组名称:", self.name_edit)
        
        # Extensions (if not folder/shortcut/system group)
        if not self.group.is_folder_group and not self.group.is_shortcut_group and not self.group.is_system_group:
            self.ext_edit = QLineEdit(", ".join(sorted(self.group.extensions)))
            self.ext_edit.setPlaceholderText("例如: .pdf, .doc, .txt")
            self.ext_edit.textChanged.connect(self._on_changed)
            layout.addRow("扩展名:", self.ext_edit)
        else:
            self.ext_edit = None
            if self.group.is_folder_group:
                type_label = "文件夹"
            elif self.group.is_system_group:
                type_label = "系统图标 (回收站、此电脑等)"
            else:
                type_label = "快捷方式 (.lnk)"
            layout.addRow("类型:", QLabel(type_label))
        
        # Merge group - for combining groups into same column
        self.merge_group_edit = QLineEdit(self.group.merge_group)
        self.merge_group_edit.setPlaceholderText("留空为独立列，相同值的分组合并显示")
        self.merge_group_edit.textChanged.connect(self._on_changed)
        layout.addRow("合并标识:", self.merge_group_edit)
        
        # Hint for merge group
        hint = QLabel("提示: 设置相同合并标识的分组会显示在同一列中")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addRow(hint)
        
        # Start side
        self.start_right_cb = QCheckBox("从右侧开始排列")
        self.start_right_cb.setChecked(self.group.start_from_right)
        self.start_right_cb.toggled.connect(self._on_changed)
        layout.addRow(self.start_right_cb)
    
    def _on_changed(self):
        """Handle any change."""
        self.group.enabled = self.enabled_cb.isChecked()
        self.group.name = self.name_edit.text()
        self.group.start_from_right = self.start_right_cb.isChecked()
        self.group.merge_group = self.merge_group_edit.text().strip()
        
        if self.ext_edit:
            # Parse extensions
            ext_text = self.ext_edit.text()
            extensions = set()
            for ext in ext_text.split(","):
                ext = ext.strip().lower()
                if ext:
                    if not ext.startswith("."):
                        ext = "." + ext
                    extensions.add(ext)
            self.group.extensions = extensions
        
        self.group_changed.emit()


class GroupsTab(QWidget):
    """Tab for managing groups."""
    
    groups_changed = pyqtSignal()  # Signal to notify when groups change
    preset_applied = pyqtSignal(str)  # Signal when a preset is applied (preset_id)
    
    def __init__(self, classifier: Classifier, parent=None):
        super().__init__(parent)
        self.classifier = classifier
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Preset selector at top
        preset_group = QGroupBox("快速预设")
        preset_layout = QVBoxLayout(preset_group)
        
        # Preset selection row
        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("选择预设:"))
        self.preset_combo = QComboBox()
        self._refresh_presets()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        select_row.addWidget(self.preset_combo, 1)
        
        self.delete_preset_btn = QPushButton("删除")
        self.delete_preset_btn.clicked.connect(self._on_delete_preset)
        select_row.addWidget(self.delete_preset_btn)
        
        preset_layout.addLayout(select_row)
        
        # Update current preset button (for custom presets)
        update_row = QHBoxLayout()
        self.update_preset_btn = QPushButton("覆盖当前预设")
        self.update_preset_btn.setToolTip("将当前配置保存到选中的自定义预设（覆盖）")
        self.update_preset_btn.clicked.connect(self._on_update_preset)
        self.update_preset_btn.setEnabled(False)  # Disabled until custom preset selected
        update_row.addWidget(self.update_preset_btn)
        update_row.addStretch()
        preset_layout.addLayout(update_row)
        
        # Save as new preset row
        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("另存为新预设:"))
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText("输入预设名称")
        save_row.addWidget(self.preset_name_edit, 1)
        
        self.save_preset_btn = QPushButton("保存")
        self.save_preset_btn.clicked.connect(self._on_save_preset)
        save_row.addWidget(self.save_preset_btn)
        
        preset_layout.addLayout(save_row)
        
        main_layout.addWidget(preset_group)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - group list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("分组列表 (拖拽可调整顺序):"))
        
        self.group_list = QListWidget()
        self.group_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.group_list.currentRowChanged.connect(self._on_group_selected)
        self.group_list.model().rowsMoved.connect(self._on_groups_reordered)
        left_layout.addWidget(self.group_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加分组")
        self.add_btn.clicked.connect(self._on_add_group)
        btn_layout.addWidget(self.add_btn)
        
        self.add_spacer_btn = QPushButton("添加间隔")
        self.add_spacer_btn.clicked.connect(self._on_add_spacer)
        btn_layout.addWidget(self.add_spacer_btn)
        
        self.remove_btn = QPushButton("删除分组")
        self.remove_btn.clicked.connect(self._on_remove_group)
        btn_layout.addWidget(self.remove_btn)
        left_layout.addLayout(btn_layout)
        
        content_layout.addWidget(left_widget)
        
        # Right side - group editor
        self.edit_container = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_container)
        self.edit_layout.setContentsMargins(0, 0, 0, 0)
        
        self.edit_placeholder = QLabel("选择一个分组进行编辑")
        self.edit_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_layout.addWidget(self.edit_placeholder)
        
        content_layout.addWidget(self.edit_container)
        
        main_layout.addLayout(content_layout)
        
        # Populate list
        self._refresh_list()
        self._skip_preset_change = False  # Flag to skip preset change during refresh
    
    def _on_preset_combo_changed(self):
        """Handle preset combo selection change - apply preset directly."""
        if self._skip_preset_change:
            return
            
        preset_id = self.preset_combo.currentData()
        if not preset_id:
            return
        
        # Update button state
        is_custom = preset_id.startswith("custom_")
        self.update_preset_btn.setEnabled(is_custom)
        
        # Apply preset directly
        apply_preset(self.classifier, preset_id)
        self._refresh_list()
        self.groups_changed.emit()
        self.preset_applied.emit(preset_id)
    
    def _refresh_presets(self):
        """Refresh the preset combo box."""
        self._skip_preset_change = True
        self.preset_combo.clear()
        presets = get_all_presets_info()
        for p in presets:
            self.preset_combo.addItem(f"{p['name']} - {p['description']}", p['id'])
        self._skip_preset_change = False
    
    def _on_save_preset(self):
        """Save current configuration as a custom preset."""
        name = self.preset_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入预设名称")
            return
        
        if save_custom_preset(name, self.classifier):
            QMessageBox.information(self, "成功", f"预设 \"{name}\" 已保存")
            self.preset_name_edit.clear()
            self._refresh_presets()
        else:
            QMessageBox.warning(self, "错误", "保存预设失败")
    
    def _on_update_preset(self):
        """Update the currently selected custom preset."""
        preset_id = self.preset_combo.currentData()
        if not preset_id or not preset_id.startswith("custom_"):
            QMessageBox.warning(self, "错误", "只能更新自定义预设")
            return
        
        preset_name = self.preset_combo.currentText().split(" - ")[0]
        reply = QMessageBox.question(
            self, "覆盖预设",
            f"确定要覆盖预设 \"{preset_name}\" 吗？\n当前的分组设置将保存到该预设。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if update_custom_preset(preset_id, self.classifier):
                QMessageBox.information(self, "成功", f"预设 \"{preset_name}\" 已更新")
            else:
                QMessageBox.warning(self, "错误", "更新预设失败")
    
    def _on_delete_preset(self):
        """Delete selected custom preset."""
        preset_id = self.preset_combo.currentData()
        if not preset_id:
            return
        
        if not preset_id.startswith("custom_"):
            QMessageBox.warning(self, "错误", "只能删除自定义预设")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个自定义预设吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if delete_custom_preset(preset_id):
                self._refresh_presets()
                QMessageBox.information(self, "成功", "预设已删除")
            else:
                QMessageBox.warning(self, "错误", "删除预设失败")
    
    def _refresh_list(self):
        """Refresh the group list."""
        self.group_list.clear()
        for group in self.classifier.groups:
            item = QListWidgetItem(group.name)
            item.setData(Qt.ItemDataRole.UserRole, group)
            if not group.enabled:
                item.setForeground(Qt.GlobalColor.gray)
            self.group_list.addItem(item)
    
    def _on_group_selected(self, row):
        """Handle group selection."""
        if row < 0:
            return
        
        item = self.group_list.item(row)
        group = item.data(Qt.ItemDataRole.UserRole)
        
        # Clear edit area
        while self.edit_layout.count():
            child = self.edit_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add editor
        editor = GroupEditWidget(group)
        editor.group_changed.connect(lambda: self._on_group_changed(row))
        self.edit_layout.addWidget(editor)
        self.edit_layout.addStretch()
    
    def _on_group_changed(self, row):
        """Handle group change."""
        item = self.group_list.item(row)
        group = item.data(Qt.ItemDataRole.UserRole)
        item.setText(group.name)
        if not group.enabled:
            item.setForeground(Qt.GlobalColor.gray)
        else:
            item.setForeground(Qt.GlobalColor.black)
    
    def _on_groups_reordered(self):
        """Handle group reordering."""
        # Rebuild classifier groups based on list order
        new_groups = []
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            group = item.data(Qt.ItemDataRole.UserRole)
            group.priority = i
            new_groups.append(group)
        self.classifier.groups = new_groups
    
    def _on_add_group(self):
        """Add a new custom group."""
        name, ok = QInputDialog.getText(self, "添加分组", "分组名称:")
        if ok and name:
            group = self.classifier.add_group(name, set(), priority=len(self.classifier.groups))
            self._refresh_list()
            # Select the new group
            self.group_list.setCurrentRow(self.group_list.count() - 1)
    
    def _on_add_spacer(self):
        """Add an empty spacer group."""
        # Find unique name for spacer
        spacer_count = sum(1 for g in self.classifier.groups if g.name.startswith("─ 间隔"))
        name = f"─ 间隔 {spacer_count + 1} ─"
        
        group = self.classifier.add_group(name, set(), priority=len(self.classifier.groups))
        self._refresh_list()
        # Select the new group
        self.group_list.setCurrentRow(self.group_list.count() - 1)
        self.groups_changed.emit()
    
    def _on_remove_group(self):
        """Remove selected group."""
        row = self.group_list.currentRow()
        if row < 0:
            return
        
        item = self.group_list.item(row)
        group = item.data(Qt.ItemDataRole.UserRole)
        
        # Don't allow removing built-in groups
        if group.is_folder_group or group.is_shortcut_group:
            QMessageBox.warning(self, "无法删除", "内置分组无法删除，但可以禁用。")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分组 \"{group.name}\" 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.classifier.remove_group(group.name)
            self._refresh_list()


class ArrangeTab(QWidget):
    """Tab for arrangement settings."""
    
    def __init__(self, layout_manager: LayoutManager, parent=None):
        super().__init__(parent)
        self.layout_manager = layout_manager
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Direction group
        dir_group = QGroupBox("排列方向")
        dir_layout = QVBoxLayout(dir_group)
        
        self.direction_group = QButtonGroup(self)
        
        self.vertical_radio = QRadioButton("竖排 (从上到下，然后下一列)")
        self.vertical_radio.setChecked(
            self.layout_manager.settings.direction == ArrangeDirection.VERTICAL
        )
        self.direction_group.addButton(self.vertical_radio)
        dir_layout.addWidget(self.vertical_radio)
        
        self.horizontal_radio = QRadioButton("横排 (从左到右，然后下一行)")
        self.horizontal_radio.setChecked(
            self.layout_manager.settings.direction == ArrangeDirection.HORIZONTAL
        )
        self.direction_group.addButton(self.horizontal_radio)
        dir_layout.addWidget(self.horizontal_radio)
        
        layout.addWidget(dir_group)
        
        # Sort group
        sort_group = QGroupBox("排序方式")
        sort_layout = QVBoxLayout(sort_group)
        
        self.sort_combo = QComboBox()
        sort_options = [
            ("名称 (A-Z)", SortOrder.NAME_ASC),
            ("名称 (Z-A)", SortOrder.NAME_DESC),
            ("创建时间 (旧→新)", SortOrder.CREATED_ASC),
            ("创建时间 (新→旧)", SortOrder.CREATED_DESC),
            ("修改时间 (旧→新)", SortOrder.MODIFIED_ASC),
            ("修改时间 (新→旧)", SortOrder.MODIFIED_DESC),
            ("文件大小 (小→大)", SortOrder.SIZE_ASC),
            ("文件大小 (大→小)", SortOrder.SIZE_DESC),
        ]
        
        current_sort = self.layout_manager.settings.sort_order
        for i, (label, value) in enumerate(sort_options):
            self.sort_combo.addItem(label, value)
            if value == current_sort:
                self.sort_combo.setCurrentIndex(i)
        
        sort_layout.addWidget(self.sort_combo)
        layout.addWidget(sort_group)
        
        layout.addStretch()
        
        # Connect signals
        self.vertical_radio.toggled.connect(self._on_settings_changed)
        self.horizontal_radio.toggled.connect(self._on_settings_changed)
        self.sort_combo.currentIndexChanged.connect(self._on_settings_changed)
    
    def _on_settings_changed(self):
        """Update settings when changed."""
        if self.vertical_radio.isChecked():
            self.layout_manager.settings.direction = ArrangeDirection.VERTICAL
        else:
            self.layout_manager.settings.direction = ArrangeDirection.HORIZONTAL
        
        self.layout_manager.settings.sort_order = self.sort_combo.currentData()


class MonitorTab(QWidget):
    """Tab for monitor settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor_mode = "primary"  # "all", "primary", or "select"
        self.selected_monitors = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Monitor mode
        mode_group = QGroupBox("整理范围")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup(self)
        
        self.primary_radio = QRadioButton("仅主显示器")
        self.primary_radio.setChecked(True)
        self.mode_group.addButton(self.primary_radio)
        mode_layout.addWidget(self.primary_radio)
        
        self.all_radio = QRadioButton("所有显示器")
        self.mode_group.addButton(self.all_radio)
        mode_layout.addWidget(self.all_radio)
        
        layout.addWidget(mode_group)
        
        # Monitor list (for future use)
        info_label = QLabel("提示: 多显示器时，每个显示器的图标会独立整理。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        layout.addStretch()
    
    def get_mode(self) -> str:
        """Get current monitor mode."""
        if self.primary_radio.isChecked():
            return "primary"
        return "all"
    
    def set_mode(self, mode: str):
        """Set monitor mode."""
        if mode == "primary":
            self.primary_radio.setChecked(True)
        else:
            self.all_radio.setChecked(True)


class HotkeyTab(QWidget):
    """Tab for hotkey settings."""
    
    hotkey_changed = pyqtSignal(str, bool)  # hotkey, enabled
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_hotkey = "ctrl+shift+o"
        self.is_recording = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Enable hotkey
        self.enable_cb = QCheckBox("启用全局快捷键")
        self.enable_cb.setChecked(True)
        self.enable_cb.toggled.connect(self._on_settings_changed)
        layout.addWidget(self.enable_cb)
        
        # Hotkey group
        hotkey_group = QGroupBox("一键整理快捷键")
        hotkey_layout = QHBoxLayout(hotkey_group)
        
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setReadOnly(True)
        self.hotkey_edit.setPlaceholderText("点击录制按钮设置快捷键")
        self.hotkey_edit.setText("Ctrl+Shift+O")
        hotkey_layout.addWidget(self.hotkey_edit)
        
        self.record_btn = QPushButton("录制")
        self.record_btn.clicked.connect(self._toggle_recording)
        hotkey_layout.addWidget(self.record_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self._reset_hotkey)
        hotkey_layout.addWidget(self.reset_btn)
        
        layout.addWidget(hotkey_group)
        
        # Info
        info_label = QLabel("提示: 按下 Ctrl+Shift+O 可快速整理桌面图标。\n录制时请按下想要的快捷键组合。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        # Autostart section
        autostart_group = QGroupBox("开机自启动")
        autostart_layout = QVBoxLayout(autostart_group)
        
        from core.autostart import is_autostart_enabled
        
        self.autostart_cb = QCheckBox("开机时自动启动 DesktopAutoSort")
        self.autostart_cb.setChecked(is_autostart_enabled())
        self.autostart_cb.toggled.connect(self._on_autostart_changed)
        autostart_layout.addWidget(self.autostart_cb)
        
        autostart_info = QLabel("启用后，程序会在 Windows 登录时自动启动并最小化到系统托盘。")
        autostart_info.setWordWrap(True)
        autostart_info.setStyleSheet("color: gray;")
        autostart_layout.addWidget(autostart_info)
        
        layout.addWidget(autostart_group)
        
        layout.addStretch()
    
    def _toggle_recording(self):
        """Toggle hotkey recording mode."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()
    
    def _start_recording(self):
        """Start recording hotkey."""
        self.is_recording = True
        self.record_btn.setText("停止")
        self.hotkey_edit.setText("按下快捷键...")
        self.hotkey_edit.setFocus()
        # Install event filter to capture key presses
        self.hotkey_edit.installEventFilter(self)
    
    def _stop_recording(self):
        """Stop recording hotkey."""
        self.is_recording = False
        self.record_btn.setText("录制")
        self.hotkey_edit.removeEventFilter(self)
        self.hotkey_edit.setText(self._format_hotkey(self.current_hotkey))
    
    def eventFilter(self, obj, event):
        """Capture key presses during recording."""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        
        if obj == self.hotkey_edit and event.type() == QEvent.Type.KeyPress:
            key_event = event
            key = key_event.key()
            modifiers = key_event.modifiers()
            
            # Ignore modifier-only keys
            from PyQt6.QtCore import Qt
            if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                return True
            
            # Build hotkey string
            parts = []
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                parts.append("ctrl")
            if modifiers & Qt.KeyboardModifier.AltModifier:
                parts.append("alt")
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                parts.append("shift")
            
            # Get key name
            key_text = QKeySequence(key).toString().lower()
            if key_text:
                parts.append(key_text)
            
            if len(parts) >= 2:  # Need at least one modifier + key
                self.current_hotkey = "+".join(parts)
                self._stop_recording()
                self._on_settings_changed()
            
            return True
        
        return super().eventFilter(obj, event)
    
    def _reset_hotkey(self):
        """Reset to default hotkey."""
        self.current_hotkey = "ctrl+shift+o"
        self.hotkey_edit.setText("Ctrl+Shift+O")
        self._on_settings_changed()
    
    def _format_hotkey(self, hotkey: str) -> str:
        """Format hotkey for display."""
        parts = hotkey.split("+")
        return "+".join(p.capitalize() for p in parts)
    
    def _on_settings_changed(self):
        """Emit signal when settings change."""
        self.hotkey_changed.emit(self.current_hotkey, self.enable_cb.isChecked())
    
    def get_hotkey(self) -> str:
        """Get current hotkey."""
        return self.current_hotkey
    
    def set_hotkey(self, hotkey: str):
        """Set hotkey."""
        self.current_hotkey = hotkey
        self.hotkey_edit.setText(self._format_hotkey(hotkey))
    
    def is_enabled(self) -> bool:
        """Check if hotkey is enabled."""
        return self.enable_cb.isChecked()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable hotkey."""
        self.enable_cb.setChecked(enabled)
    
    def _on_autostart_changed(self, enabled: bool):
        """Handle autostart checkbox change."""
        from core.autostart import set_autostart
        
        if set_autostart(enabled):
            status = "已启用" if enabled else "已禁用"
            print(f"Autostart {status}")
        else:
            # Failed, revert checkbox
            self.autostart_cb.blockSignals(True)
            self.autostart_cb.setChecked(not enabled)
            self.autostart_cb.blockSignals(False)
            QMessageBox.warning(self, "错误", "设置开机自启动失败")


class LayoutsTab(QWidget):
    """Tab for layout management."""
    
    layout_restored = pyqtSignal(str)  # layout name
    
    def __init__(self, layout_manager: LayoutManager, parent=None):
        super().__init__(parent)
        self.layout_manager = layout_manager
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("已保存的布局:"))
        
        self.layout_list = QListWidget()
        self.layout_list.itemDoubleClicked.connect(self._on_restore)
        layout.addWidget(self.layout_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("恢复选中布局")
        self.restore_btn.clicked.connect(self._on_restore)
        btn_layout.addWidget(self.restore_btn)
        
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.clicked.connect(self._on_rename)
        btn_layout.addWidget(self.rename_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh_list()
    
    def refresh_list(self):
        """Refresh the layout list."""
        self.layout_list.clear()
        
        layouts = self.layout_manager.get_user_layouts()
        for saved_layout in layouts:
            item = QListWidgetItem(saved_layout.name)
            item.setData(Qt.ItemDataRole.UserRole, saved_layout)
            self.layout_list.addItem(item)
        
        # Add last layout if exists
        last_layout = self.layout_manager.get_layout(LayoutManager.LAST_LAYOUT_NAME)
        if last_layout:
            item = QListWidgetItem("上次布局 (自动保存)")
            item.setData(Qt.ItemDataRole.UserRole, last_layout)
            item.setForeground(Qt.GlobalColor.gray)
            self.layout_list.insertItem(0, item)
    
    def _on_restore(self):
        """Restore selected layout."""
        item = self.layout_list.currentItem()
        if item:
            layout = item.data(Qt.ItemDataRole.UserRole)
            self.layout_restored.emit(layout.name)
    
    def _on_rename(self):
        """Rename selected layout."""
        item = self.layout_list.currentItem()
        if not item:
            return
        
        layout = item.data(Qt.ItemDataRole.UserRole)
        if layout.name.startswith("_"):
            QMessageBox.warning(self, "无法重命名", "自动保存的布局无法重命名。")
            return
        
        new_name, ok = QInputDialog.getText(
            self, "重命名布局", "新名称:", text=layout.name
        )
        if ok and new_name and new_name != layout.name:
            # Delete old, save with new name
            positions = layout.positions
            self.layout_manager.delete_layout(layout.name)
            
            # Create new layout with same positions
            from core.desktop import DesktopIcon
            fake_icons = [
                DesktopIcon(name=name, path="", x=pos[0], y=pos[1], 
                           is_folder=False, extension="")
                for name, pos in positions.items()
            ]
            self.layout_manager.save_layout(new_name, fake_icons)
            self.refresh_list()
    
    def _on_delete(self):
        """Delete selected layout."""
        item = self.layout_list.currentItem()
        if not item:
            return
        
        layout = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除布局 \"{layout.name}\" 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.layout_manager.delete_layout(layout.name)
            self.refresh_list()


class SettingsWindow(QDialog):
    """Main settings window."""
    
    settings_changed = pyqtSignal()
    layout_restored = pyqtSignal(str)
    organize_requested = pyqtSignal()  # New signal for organize button
    
    def __init__(self, classifier: Classifier, layout_manager: LayoutManager, 
                 parent=None):
        super().__init__(parent)
        self.classifier = classifier
        self.layout_manager = layout_manager
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("DesktopAutoSort - Settings")
        self.setMinimumSize(600, 450)
        
        # Set window icon
        import os
        try:
            # Check for icon.ico in current directory or resources
            icon_paths = ["icon.ico", "resources/icon.png", "resources/icon.ico"]
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            for path in icon_paths:
                full_path = os.path.join(base_dir, path)
                if os.path.exists(full_path):
                    self.setWindowIcon(QIcon(full_path))
                    break
        except Exception:
            pass
        
        # Enable minimize button (make it a regular window instead of dialog)
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowCloseButtonHint | 
            Qt.WindowType.WindowMinimizeButtonHint
        )
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Groups tab
        self.groups_tab = GroupsTab(self.classifier)
        self.groups_tab.groups_changed.connect(self.settings_changed.emit)
        self.tabs.addTab(self.groups_tab, "分组设置")
        
        # Arrange tab
        self.arrange_tab = ArrangeTab(self.layout_manager)
        self.tabs.addTab(self.arrange_tab, "排列设置")
        
        # Monitor tab
        self.monitor_tab = MonitorTab()
        self.tabs.addTab(self.monitor_tab, "显示器")
        
        # Layouts tab
        self.layouts_tab = LayoutsTab(self.layout_manager)
        self.layouts_tab.layout_restored.connect(self.layout_restored.emit)
        self.tabs.addTab(self.layouts_tab, "布局管理")
        
        # Settings tab (previously Hotkey tab)
        self.hotkey_tab = HotkeyTab()
        self.tabs.addTab(self.hotkey_tab, "设置")
        
        layout.addWidget(self.tabs)
        
        # Bottom buttons - only organize button
        btn_layout = QHBoxLayout()
        
        # Organize button on the left
        self.organize_btn = QPushButton("🔄 一键整理")
        self.organize_btn.setMinimumWidth(120)
        self.organize_btn.clicked.connect(self._on_organize_clicked)
        btn_layout.addWidget(self.organize_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
    
    def _on_organize_clicked(self):
        """Handle organize button click."""
        # Save settings first
        self.settings_changed.emit()
        # Then trigger organize
        self.organize_requested.emit()
    
    def get_monitor_mode(self) -> str:
        """Get the current monitor mode."""
        return self.monitor_tab.get_mode()
    
    def set_monitor_mode(self, mode: str):
        """Set the monitor mode."""
        self.monitor_tab.set_mode(mode)
    
    def refresh_layouts(self):
        """Refresh the layouts list."""
        self.layouts_tab.refresh_list()

