"""
Layout manager for desktop icons.
Handles icon position calculation and layout save/restore.
"""

import os
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .desktop import DesktopIcon, MonitorInfo


class SortOrder(Enum):
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    CREATED_ASC = "created_asc"
    CREATED_DESC = "created_desc"
    MODIFIED_ASC = "modified_asc"
    MODIFIED_DESC = "modified_desc"
    SIZE_ASC = "size_asc"
    SIZE_DESC = "size_desc"


class ArrangeDirection(Enum):
    VERTICAL = "vertical"  # Top to bottom, then next column
    HORIZONTAL = "horizontal"  # Left to right, then next row


@dataclass
class LayoutSettings:
    """Settings for icon layout."""
    direction: ArrangeDirection = ArrangeDirection.VERTICAL
    sort_order: SortOrder = SortOrder.NAME_ASC
    start_from_right: bool = False  # Global setting: start all groups from right side
    margin_left: int = 20
    margin_top: int = 20
    margin_right: int = 20
    margin_bottom: int = 20


@dataclass
class SavedLayout:
    """Represents a saved desktop layout."""
    name: str
    positions: Dict[str, Tuple[int, int]]  # icon name -> (x, y)
    created_at: str
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "positions": self.positions,
            "created_at": self.created_at
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "SavedLayout":
        return SavedLayout(
            name=data["name"],
            positions=data["positions"],
            created_at=data.get("created_at", "")
        )


class LayoutManager:
    """Manages icon layouts and positions."""
    
    # Special layout name for auto-save before organizing
    LAST_LAYOUT_NAME = "_上次布局"
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.layouts_file = os.path.join(config_dir, "layouts.json")
        self.settings = LayoutSettings()
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists."""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _sort_icons(self, icons_with_priority) -> List:
        """Sort icons according to current sort order.
        
        Args:
            icons_with_priority: List of (priority, icon) tuples
        
        Returns:
            List of DesktopIcon objects sorted by priority first, then by sort order
        """
        sort_order = self.settings.sort_order
        
        def get_sort_key(item):
            priority, icon = item
            
            # Secondary sort key based on sort order
            if sort_order in (SortOrder.NAME_ASC, SortOrder.NAME_DESC):
                secondary = icon.name.lower()
            elif not icon.path or not os.path.exists(icon.path):
                secondary = 0
            else:
                stat = os.stat(icon.path)
                if sort_order in (SortOrder.CREATED_ASC, SortOrder.CREATED_DESC):
                    secondary = stat.st_ctime
                elif sort_order in (SortOrder.MODIFIED_ASC, SortOrder.MODIFIED_DESC):
                    secondary = stat.st_mtime
                elif sort_order in (SortOrder.SIZE_ASC, SortOrder.SIZE_DESC):
                    secondary = stat.st_size if not icon.is_folder else 0
                else:
                    secondary = icon.name.lower()
            
            # Primary sort by priority (ascending), secondary by the selected order
            return (priority, secondary)
        
        reverse_secondary = sort_order.value.endswith("_desc")
        
        # Sort by priority ascending, then by secondary key
        sorted_items = sorted(icons_with_priority, key=get_sort_key, 
                              reverse=False)  # Priority always ascending
        
        # If secondary sort should be descending, we need special handling
        # Group by priority first, then sort each group
        if reverse_secondary:
            from itertools import groupby
            result = []
            for _, group in groupby(sorted_items, key=lambda x: x[0]):
                group_list = list(group)
                group_list.sort(key=lambda x: get_sort_key(x)[1], reverse=True)
                result.extend([item[1] for item in group_list])
            return result
        
        return [item[1] for item in sorted_items]
    
    
    def calculate_positions(
        self,
        classified_icons: Dict[str, List[DesktopIcon]],
        groups,  # List[IconGroup]
        monitor: MonitorInfo,
        icon_spacing: Tuple[int, int],
        grid_origin: Tuple[int, int] = None
    ) -> Dict[str, Tuple[int, int]]:
        """Calculate positions for all icons.
        
        Each group gets its own column(s) (Vertical) or row(s) (Horizontal), ensuring visual separation.
        
        Args:
            classified_icons: Dict mapping group name to list of icons
            groups: List of IconGroup objects with ordering info
            monitor: Monitor to arrange icons on
            icon_spacing: (horizontal, vertical) spacing between icons
            grid_origin: (x, y) origin point of the grid, detected from current icons
        
        Returns:
            Dict mapping icon name to (x, y) position
        """
        positions: Dict[str, Tuple[int, int]] = {}
        
        h_spacing, v_spacing = icon_spacing
        
        # Use grid origin if provided, otherwise use margins
        if grid_origin:
            origin_x, origin_y = grid_origin
        else:
            work_area = monitor.work_area
            origin_x = work_area[0] + self.settings.margin_left
            origin_y = work_area[1] + self.settings.margin_top
        
        # Calculate available area for max icons per column/row
        work_area = monitor.work_area
        bottom = work_area[3] - self.settings.margin_bottom
        right = work_area[2] - self.settings.margin_right
        
        # Get groups that have icons, in priority order
        active_groups = []
        for group in groups:
            if group.name in classified_icons and classified_icons[group.name]:
                active_groups.append((group, classified_icons[group.name]))
        
        if not active_groups:
            return positions
        
        # Merge groups with same merge_group value
        # Store (group_priority, icon) tuples so we can sort by priority first
        merged_groups = []  # List of (merge_group_id, list of (priority, icon) tuples)
        processed_merge_ids = set()
        
        for group, icons in active_groups:
            merge_id = group.merge_group
            
            if merge_id and merge_id not in processed_merge_ids:
                # Find all groups with this merge_id and combine their icons with priorities
                combined_icons = []
                for g, g_icons in active_groups:
                    if g.merge_group == merge_id:
                        for icon in g_icons:
                            combined_icons.append((g.priority, icon))
                merged_groups.append((merge_id, combined_icons))
                processed_merge_ids.add(merge_id)
            elif not merge_id:
                # No merge group, keep as individual (all same priority)
                icons_with_priority = [(group.priority, icon) for icon in icons]
                merged_groups.append((group.name, icons_with_priority))
        
        # Settings
        from_right = self.settings.start_from_right
        is_vertical = self.settings.direction == ArrangeDirection.VERTICAL
        
        # Calculate grid dimensions
        available_height = work_area[3] - work_area[1] - self.settings.margin_top - self.settings.margin_bottom
        available_width = work_area[2] - work_area[0] - self.settings.margin_left - self.settings.margin_right
        
        max_rows = max(1, available_height // v_spacing)
        max_cols = max(1, available_width // h_spacing)
        
        # Track occupied cells to avoid stacking
        occupied_cells = set()  # (col, row) tuples
        
        def get_next_free_cell(start_col, start_row, prefer_vertical=True):
            """Find next free cell starting from given position."""
            if prefer_vertical:
                # Try filling column first, then next column
                for col in range(start_col, max_cols):
                    row_start = start_row if col == start_col else 0
                    for row in range(row_start, max_rows):
                        if (col, row) not in occupied_cells:
                            return (col, row)
                # Wrap around to beginning
                for col in range(0, start_col):
                    for row in range(0, max_rows):
                        if (col, row) not in occupied_cells:
                            return (col, row)
            else:
                # Try filling row first, then next row
                for row in range(start_row, max_rows):
                    col_start = start_col if row == start_row else 0
                    for col in range(col_start, max_cols):
                        if (col, row) not in occupied_cells:
                            return (col, row)
                # Wrap around to beginning
                for row in range(0, start_row):
                    for col in range(0, max_cols):
                        if (col, row) not in occupied_cells:
                            return (col, row)
            return None  # No free cell found
        
        if is_vertical:
            # === VERTICAL LAYOUT (Columns) ===
            # Each group gets its own column(s), filling downward
            current_col = max_cols - 1 if from_right else 0
            
            group_list = list(reversed(merged_groups)) if from_right else list(merged_groups)
            
            for group_id, icons in group_list:
                sorted_icons = self._sort_icons(icons)
                group_start_col = current_col
                
                for i, icon in enumerate(sorted_icons):
                    # Preferred position within group's columns
                    col_offset = i // max_rows
                    row_idx = i % max_rows
                    
                    if from_right:
                        preferred_col = max(0, group_start_col - col_offset)
                    else:
                        preferred_col = min(max_cols - 1, group_start_col + col_offset)
                    
                    # Check if preferred position is free
                    if (preferred_col, row_idx) not in occupied_cells:
                        col, row = preferred_col, row_idx
                    else:
                        # Find next free cell
                        result = get_next_free_cell(preferred_col, row_idx, prefer_vertical=True)
                        if result:
                            col, row = result
                        else:
                            # Grid is full, skip this icon
                            continue
                    
                    x = origin_x + (col * h_spacing)
                    y = origin_y + (row * v_spacing)
                    positions[icon.name] = (x, y)
                    occupied_cells.add((col, row))
                
                # Move to next column(s) for next group
                cols_used = max(1, (len(sorted_icons) + max_rows - 1) // max_rows)
                if from_right:
                    current_col = max(0, current_col - cols_used)
                else:
                    current_col = min(max_cols - 1, current_col + cols_used)
                    
        else:
            # === HORIZONTAL LAYOUT (Rows) ===
            # Each group gets its own row(s), filling rightward
            current_row = 0
            
            for group_id, icons in merged_groups:
                sorted_icons = self._sort_icons(icons)
                group_start_row = current_row
                
                for i, icon in enumerate(sorted_icons):
                    # Preferred position within group's rows
                    row_offset = i // max_cols
                    col_idx = i % max_cols
                    
                    preferred_row = min(max_rows - 1, group_start_row + row_offset)
                    
                    if from_right:
                        preferred_col = max_cols - 1 - col_idx
                    else:
                        preferred_col = col_idx
                    
                    # Check if preferred position is free
                    if (preferred_col, preferred_row) not in occupied_cells:
                        col, row = preferred_col, preferred_row
                    else:
                        # Find next free cell
                        result = get_next_free_cell(preferred_col, preferred_row, prefer_vertical=False)
                        if result:
                            col, row = result
                        else:
                            # Grid is full, skip this icon
                            continue
                    
                    x = origin_x + (col * h_spacing)
                    y = origin_y + (row * v_spacing)
                    positions[icon.name] = (x, y)
                    occupied_cells.add((col, row))
                
                # Move to next row(s) for next group
                rows_used = max(1, (len(sorted_icons) + max_cols - 1) // max_cols)
                current_row = min(max_rows - 1, current_row + rows_used)
        
        return positions
    
    def _calculate_column_positions(
        self,
        icons: List[DesktopIcon],
        start_x: int,
        top: int,
        bottom: int,
        h_spacing: int,
        v_spacing: int,
        direction: ArrangeDirection,
        from_right: bool = False
    ) -> Tuple[Dict[str, Tuple[int, int]], int]:
        """Calculate positions for icons in columns/rows.
        
        DEPRECATED: This method is kept for compatibility but the new
        calculate_positions method handles everything directly.
        
        Returns:
            Tuple of (positions dict, next column x position)
        """
        positions = {}
        
        if direction == ArrangeDirection.VERTICAL:
            # Arrange top to bottom, then next column
            max_icons_per_col = max(1, (bottom - top) // v_spacing)
            
            col = 0
            row = 0
            for icon in icons:
                if row >= max_icons_per_col:
                    col += 1
                    row = 0
                
                if from_right:
                    x = start_x - (col * h_spacing)
                else:
                    x = start_x + (col * h_spacing)
                y = top + (row * v_spacing)
                
                positions[icon.name] = (x, y)
                row += 1
            
            # Calculate next x position - ensure at least 1 column of space
            total_cols = max(1, col + 1) if icons else 1
            if from_right:
                next_x = start_x - (total_cols * h_spacing)
            else:
                next_x = start_x + (total_cols * h_spacing)
        
        else:  # HORIZONTAL
            # Arrange left to right, then next row
            max_icons_per_row = 5  # Default, could be calculated from width
            
            row = 0
            col = 0
            for icon in icons:
                if col >= max_icons_per_row:
                    row += 1
                    col = 0
                
                if from_right:
                    x = start_x - (col * h_spacing)
                else:
                    x = start_x + (col * h_spacing)
                y = top + (row * v_spacing)
                
                positions[icon.name] = (x, y)
                col += 1
            
            # For horizontal, next group starts after max column width
            if from_right:
                next_x = start_x - (max_icons_per_row * h_spacing)
            else:
                next_x = start_x + (max_icons_per_row * h_spacing)
        
        return positions, next_x
    
    def save_layout(self, name: str, icons: List[DesktopIcon]) -> SavedLayout:
        """Save current icon positions as a named layout."""
        positions = {icon.name: (icon.x, icon.y) for icon in icons}
        
        layout = SavedLayout(
            name=name,
            positions=positions,
            created_at=datetime.now().isoformat()
        )
        
        # Load existing layouts
        layouts = self.load_all_layouts()
        
        # Replace if exists, otherwise append
        found = False
        for i, existing in enumerate(layouts):
            if existing.name == name:
                layouts[i] = layout
                found = True
                break
        
        if not found:
            layouts.append(layout)
        
        # Save to file
        self._save_layouts_to_file(layouts)
        
        return layout
    
    def load_all_layouts(self) -> List[SavedLayout]:
        """Load all saved layouts."""
        if not os.path.exists(self.layouts_file):
            return []
        
        try:
            with open(self.layouts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return [SavedLayout.from_dict(d) for d in data.get("layouts", [])]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def get_layout(self, name: str) -> Optional[SavedLayout]:
        """Get a layout by name."""
        for layout in self.load_all_layouts():
            if layout.name == name:
                return layout
        return None
    
    def delete_layout(self, name: str) -> bool:
        """Delete a layout by name."""
        layouts = self.load_all_layouts()
        new_layouts = [l for l in layouts if l.name != name]
        
        if len(new_layouts) < len(layouts):
            self._save_layouts_to_file(new_layouts)
            return True
        return False
    
    def _save_layouts_to_file(self, layouts: List[SavedLayout]):
        """Save layouts list to file."""
        data = {"layouts": [l.to_dict() for l in layouts]}
        with open(self.layouts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_layouts(self) -> List[SavedLayout]:
        """Get all user-created layouts (excluding auto-saved ones)."""
        return [l for l in self.load_all_layouts() 
                if not l.name.startswith("_")]
    
    def to_dict(self) -> Dict:
        """Convert settings to dictionary."""
        return {
            "direction": self.settings.direction.value,
            "sort_order": self.settings.sort_order.value,
            "start_from_right": self.settings.start_from_right,
            "margin_left": self.settings.margin_left,
            "margin_top": self.settings.margin_top,
            "margin_right": self.settings.margin_right,
            "margin_bottom": self.settings.margin_bottom
        }
    
    def from_dict(self, data: Dict):
        """Load settings from dictionary."""
        if "direction" in data:
            self.settings.direction = ArrangeDirection(data["direction"])
        if "sort_order" in data:
            self.settings.sort_order = SortOrder(data["sort_order"])
        if "start_from_right" in data:
            self.settings.start_from_right = data["start_from_right"]
        if "margin_left" in data:
            self.settings.margin_left = data["margin_left"]
        if "margin_top" in data:
            self.settings.margin_top = data["margin_top"]
        if "margin_right" in data:
            self.settings.margin_right = data["margin_right"]
        if "margin_bottom" in data:
            self.settings.margin_bottom = data["margin_bottom"]

