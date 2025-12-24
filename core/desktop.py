"""
Desktop icon manager for Windows.
Uses Windows Shell API to control desktop icon positions.
"""

import os
import ctypes
from ctypes import wintypes
from typing import Dict, List, Tuple, Optional
import win32gui
import win32con
import win32api
import win32process
from dataclasses import dataclass


# ListView messages
LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMW = LVM_FIRST + 75
LVM_ARRANGE = LVM_FIRST + 22

# ListView item flags
LVIF_TEXT = 0x0001

# Memory allocation constants
MEM_COMMIT = 0x1000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

# Process access
PROCESS_ALL_ACCESS = 0x1F0FFF


@dataclass
class DesktopIcon:
    """Represents a desktop icon."""
    name: str
    path: str
    x: int
    y: int
    is_folder: bool
    extension: str
    is_system_icon: bool = False  # For Recycle Bin, This PC, etc.



@dataclass
class MonitorInfo:
    """Represents a monitor."""
    handle: int
    name: str
    x: int
    y: int
    width: int
    height: int
    work_area: Tuple[int, int, int, int]  # left, top, right, bottom
    is_primary: bool


class DesktopIconManager:
    """Manages desktop icons on Windows."""
    
    def __init__(self):
        self._desktop_hwnd = None
        self._shell_view_hwnd = None
        self._listview_hwnd = None
        self._init_desktop_handles()
    
    def _init_desktop_handles(self):
        """Initialize handles to the desktop ListView."""
        # Find Progman window
        progman = win32gui.FindWindow("Progman", "Program Manager")
        
        # Try to find SHELLDLL_DefView under Progman
        def_view = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
        
        if not def_view:
            # On some Windows versions, it's under a WorkerW window
            def enum_worker_callback(hwnd, results):
                if win32gui.GetClassName(hwnd) == "WorkerW":
                    child = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                    if child:
                        results.append(child)
                return True
            
            results = []
            win32gui.EnumWindows(enum_worker_callback, results)
            if results:
                def_view = results[0]
        
        if def_view:
            self._shell_view_hwnd = def_view
            # Find SysListView32 (the actual icon list)
            self._listview_hwnd = win32gui.FindWindowEx(def_view, 0, "SysListView32", None)
        
        if not self._listview_hwnd:
            raise RuntimeError("Could not find desktop ListView window")
    
    def get_icon_count(self) -> int:
        """Get the number of desktop icons."""
        return win32gui.SendMessage(self._listview_hwnd, LVM_GETITEMCOUNT, 0, 0)
    
    def _get_process_id(self) -> int:
        """Get the process ID of explorer.exe that owns the desktop."""
        _, pid = win32process.GetWindowThreadProcessId(self._listview_hwnd)
        return pid
    
    def get_desktop_icons(self) -> List[DesktopIcon]:
        """Get all desktop icons with their positions."""
        icons = []
        count = self.get_icon_count()
        
        if count == 0:
            return icons
        
        # Get process ID and open handle
        pid = self._get_process_id()
        process_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        
        if not process_handle:
            raise RuntimeError("Could not open explorer.exe process")
        
        try:
            # Allocate memory in explorer.exe for POINT structure
            point_size = ctypes.sizeof(wintypes.POINT)
            remote_point = ctypes.windll.kernel32.VirtualAllocEx(
                process_handle, None, point_size, MEM_COMMIT, PAGE_READWRITE
            )
            
            # Allocate memory for LVITEM structure and text buffer
            text_buffer_size = 520  # MAX_PATH * 2 for Unicode
            lvitem_size = 60  # Size of LVITEMW structure
            remote_lvitem = ctypes.windll.kernel32.VirtualAllocEx(
                process_handle, None, lvitem_size + text_buffer_size, MEM_COMMIT, PAGE_READWRITE
            )
            
            if not remote_point or not remote_lvitem:
                raise RuntimeError("Could not allocate memory in explorer.exe")
            
            try:
                desktop_paths = self._get_desktop_paths()
                
                for i in range(count):
                    # Get position
                    win32gui.SendMessage(
                        self._listview_hwnd, LVM_GETITEMPOSITION, i, remote_point
                    )
                    
                    # Read position back
                    local_point = wintypes.POINT()
                    bytes_read = ctypes.c_size_t()
                    ctypes.windll.kernel32.ReadProcessMemory(
                        process_handle, remote_point,
                        ctypes.byref(local_point), point_size,
                        ctypes.byref(bytes_read)
                    )
                    
                    # Get item text
                    name = self._get_item_text(process_handle, i, remote_lvitem, text_buffer_size)
                    
                    # Find actual file path
                    file_path, is_folder, extension = self._resolve_icon_path(name, desktop_paths)
                    
                    # Icons without a file path are system icons (Recycle Bin, This PC, etc.)
                    is_system = not file_path
                    
                    icons.append(DesktopIcon(
                        name=name,
                        path=file_path,
                        x=local_point.x,
                        y=local_point.y,
                        is_folder=is_folder,
                        extension=extension.lower() if extension else "",
                        is_system_icon=is_system
                    ))
            finally:
                # Free allocated memory
                if remote_point:
                    ctypes.windll.kernel32.VirtualFreeEx(process_handle, remote_point, 0, MEM_RELEASE)
                if remote_lvitem:
                    ctypes.windll.kernel32.VirtualFreeEx(process_handle, remote_lvitem, 0, MEM_RELEASE)
        finally:
            ctypes.windll.kernel32.CloseHandle(process_handle)
        
        return icons
    
    def _get_item_text(self, process_handle, index: int, remote_buffer, text_buffer_size: int) -> str:
        """Get the text of a ListView item."""
        # LVITEMW structure
        class LVITEMW(ctypes.Structure):
            _fields_ = [
                ("mask", wintypes.UINT),
                ("iItem", ctypes.c_int),
                ("iSubItem", ctypes.c_int),
                ("state", wintypes.UINT),
                ("stateMask", wintypes.UINT),
                ("pszText", ctypes.c_void_p),
                ("cchTextMax", ctypes.c_int),
                ("iImage", ctypes.c_int),
                ("lParam", ctypes.c_void_p),
                ("iIndent", ctypes.c_int),
                ("iGroupId", ctypes.c_int),
                ("cColumns", wintypes.UINT),
                ("puColumns", ctypes.c_void_p),
                ("piColFmt", ctypes.c_void_p),
                ("iGroup", ctypes.c_int),
            ]
        
        lvitem = LVITEMW()
        lvitem.mask = LVIF_TEXT
        lvitem.iItem = index
        lvitem.iSubItem = 0
        lvitem.cchTextMax = text_buffer_size // 2
        lvitem.pszText = remote_buffer + ctypes.sizeof(LVITEMW)
        
        # Write LVITEM to remote process
        bytes_written = ctypes.c_size_t()
        ctypes.windll.kernel32.WriteProcessMemory(
            process_handle, remote_buffer,
            ctypes.byref(lvitem), ctypes.sizeof(LVITEMW),
            ctypes.byref(bytes_written)
        )
        
        # Send message to get item text
        win32gui.SendMessage(self._listview_hwnd, LVM_GETITEMW, index, remote_buffer)
        
        # Read text back
        text_buffer = ctypes.create_unicode_buffer(text_buffer_size // 2)
        bytes_read = ctypes.c_size_t()
        ctypes.windll.kernel32.ReadProcessMemory(
            process_handle, remote_buffer + ctypes.sizeof(LVITEMW),
            text_buffer, text_buffer_size,
            ctypes.byref(bytes_read)
        )
        
        return text_buffer.value
    
    def _get_desktop_paths(self) -> List[str]:
        """Get user and public desktop paths."""
        paths = []
        
        # User desktop
        user_desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        if os.path.exists(user_desktop):
            paths.append(user_desktop)
        
        # Try alternate location
        user_desktop_alt = os.path.join(os.environ.get("USERPROFILE", ""), "桌面")
        if os.path.exists(user_desktop_alt) and user_desktop_alt not in paths:
            paths.append(user_desktop_alt)
        
        # Public desktop
        public_desktop = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
        if os.path.exists(public_desktop):
            paths.append(public_desktop)
        
        return paths
    
    def _resolve_icon_path(self, name: str, desktop_paths: List[str]) -> Tuple[str, bool, str]:
        """Resolve icon name to actual file path."""
        for desktop_path in desktop_paths:
            # Try exact match first
            full_path = os.path.join(desktop_path, name)
            if os.path.exists(full_path):
                is_folder = os.path.isdir(full_path)
                _, ext = os.path.splitext(name)
                return full_path, is_folder, ext
            
            # Try with common extensions
            for ext in [".lnk", ".url", ".exe"]:
                full_path = os.path.join(desktop_path, name + ext)
                if os.path.exists(full_path):
                    return full_path, False, ext
        
        return "", False, ""
    
    def set_icon_position(self, index: int, x: int, y: int):
        """Set the position of a desktop icon by index."""
        # Use LVM_SETITEMPOSITION32 for better compatibility
        # This requires a POINT structure in lParam
        
        # First try the simple approach with LVM_SETITEMPOSITION
        # Pack x and y into lParam (low word = x, high word = y)
        lparam = (y << 16) | (x & 0xFFFF)
        win32gui.SendMessage(self._listview_hwnd, LVM_SETITEMPOSITION, index, lparam)
    
    def set_icon_positions(self, positions: Dict[str, Tuple[int, int]]):
        """Set positions for multiple icons by name."""
        icons = self.get_desktop_icons()
        
        print(f"\nDEBUG set_icon_positions: {len(positions)} positions to apply, {len(icons)} icons on desktop")
        
        # First, check current positions
        print("Current icon positions BEFORE applying:")
        for i, icon in enumerate(icons):
            print(f"  #{i} '{icon.name}': ({icon.x}, {icon.y})")
        
        matched = 0
        unmatched = []
        
        for i, icon in enumerate(icons):
            if icon.name in positions:
                x, y = positions[icon.name]
                print(f"  Setting #{i} '{icon.name}' -> ({x}, {y})")
                self.set_icon_position(i, x, y)
                matched += 1
            else:
                unmatched.append(icon.name)
        
        if unmatched:
            print(f"  UNMATCHED icons ({len(unmatched)}): {unmatched}")
        print(f"  Applied {matched}/{len(positions)} positions")
        
        # Verify positions after setting
        print("\nVerifying positions AFTER applying:")
        icons_after = self.get_desktop_icons()
        mismatches = []
        for icon in icons_after:
            if icon.name in positions:
                expected_x, expected_y = positions[icon.name]
                if icon.x != expected_x or icon.y != expected_y:
                    mismatches.append(f"  '{icon.name}': expected ({expected_x}, {expected_y}), got ({icon.x}, {icon.y})")
        
        if mismatches:
            print("  WARNING: Positions NOT applied correctly!")
            for m in mismatches:
                print(m)
            print("\n  *** This usually means Windows Desktop has 'Auto arrange icons' or")
            print("  *** 'Align icons to grid' enabled. Right-click desktop -> View")
            print("  *** and uncheck these options! ***")
        else:
            print("  All positions applied correctly!")
    
    def get_monitors(self) -> List[MonitorInfo]:
        """Get information about all monitors."""
        monitors = []
        
        # EnumDisplayMonitors returns a list of tuples: (hMonitor, hdcMonitor, rect)
        monitor_list = win32api.EnumDisplayMonitors(None, None)
        
        for monitor_handle, hdc, rect in monitor_list:
            info = win32api.GetMonitorInfo(monitor_handle)
            monitor_rect = info["Monitor"]
            work_rect = info["Work"]
            
            monitors.append(MonitorInfo(
                handle=monitor_handle,
                name=info.get("Device", f"Monitor {len(monitors) + 1}"),
                x=monitor_rect[0],
                y=monitor_rect[1],
                width=monitor_rect[2] - monitor_rect[0],
                height=monitor_rect[3] - monitor_rect[1],
                work_area=tuple(work_rect),
                is_primary=(info.get("Flags", 0) & 1) == 1
            ))
        
        return monitors
    
    def get_primary_monitor(self) -> Optional[MonitorInfo]:
        """Get the primary monitor."""
        for monitor in self.get_monitors():
            if monitor.is_primary:
                return monitor
        return None
    
    def get_icon_spacing(self) -> Tuple[int, int]:
        """Get the horizontal and vertical spacing between icons.
        
        First tries to detect actual grid spacing from icon positions,
        falls back to system metrics if detection fails.
        """
        # Try to detect actual grid from current icon positions
        detected = self.detect_grid_spacing()
        if detected:
            return detected
        
        # Fall back to system metrics
        h_spacing = win32api.GetSystemMetrics(win32con.SM_CXICONSPACING)
        v_spacing = win32api.GetSystemMetrics(win32con.SM_CYICONSPACING)
        return h_spacing, v_spacing
    
    def detect_grid_spacing(self) -> Optional[Tuple[int, int]]:
        """Detect actual grid spacing from current icon positions.
        
        Windows desktop with "Align to grid" snaps icons to a grid.
        This method analyzes current positions to find that grid spacing.
        """
        icons = self.get_desktop_icons()
        if len(icons) < 2:
            return None
        
        # Collect all unique x and y coordinates
        x_positions = sorted(set(icon.x for icon in icons))
        y_positions = sorted(set(icon.y for icon in icons))
        
        # Calculate spacing between consecutive x positions
        h_spacings = []
        for i in range(1, len(x_positions)):
            diff = x_positions[i] - x_positions[i-1]
            if diff > 50:  # Minimum reasonable spacing
                h_spacings.append(diff)
        
        # Calculate spacing between consecutive y positions
        v_spacings = []
        for i in range(1, len(y_positions)):
            diff = y_positions[i] - y_positions[i-1]
            if diff > 50:  # Minimum reasonable spacing
                v_spacings.append(diff)
        
        # Use the most common spacing (mode) or minimum if available
        h_spacing = min(h_spacings) if h_spacings else None
        v_spacing = min(v_spacings) if v_spacings else None
        
        if h_spacing and v_spacing:
            print(f"DEBUG: Detected actual grid spacing: h={h_spacing}, v={v_spacing}")
            return (h_spacing, v_spacing)
        
        return None
    
    def get_grid_origin(self) -> Tuple[int, int]:
        """Get the origin point of the desktop grid."""
        icons = self.get_desktop_icons()
        if not icons:
            return (20, 2)  # Default origin
        
        # Find the minimum x and y (likely the grid origin)
        min_x = min(icon.x for icon in icons)
        min_y = min(icon.y for icon in icons)
        return (min_x, min_y)
    
    def snap_to_grid(self, x: int, y: int, h_spacing: int, v_spacing: int) -> Tuple[int, int]:
        """Snap a position to the nearest grid point."""
        origin_x, origin_y = self.get_grid_origin()
        
        # Calculate grid indices
        col = round((x - origin_x) / h_spacing)
        row = round((y - origin_y) / v_spacing)
        
        # Calculate snapped position
        snapped_x = origin_x + (col * h_spacing)
        snapped_y = origin_y + (row * v_spacing)
        
        return (snapped_x, snapped_y)
    
    def refresh_desktop(self):
        """Refresh the desktop to update icon display."""
        # Send WM_COMMAND to refresh
        win32gui.SendMessage(self._listview_hwnd, LVM_ARRANGE, 0, 0)

