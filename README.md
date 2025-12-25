# DesktopAutoSort

Windows 桌面图标整理工具。根据文件类型自动分组和排列桌面图标。

## 功能特点

- **按类型分组**：自动识别快捷方式、文件夹、文档、图片、视频等
- **多种预设**：默认模式、按扩展名分类等
- **自定义分组**：可添加、编辑、删除分组和扩展名规则
- **灵活布局**：支持竖排/横排，可调整排序方式
- **保存布局**：保存当前图标位置，随时恢复
- **全局快捷键**：Ctrl+Shift+O 一键整理（可自定义）
- **系统托盘**：后台运行，点击图标打开设置

## 系统要求

- Windows 10/11
- Python 3.8+
- 必须关闭桌面"自动排列图标"功能

## 安装

### 从源码运行

```bash
git clone https://github.com/your-username/DesktopAutoSort.git
cd DesktopAutoSort
pip install -r requirements.txt
python main.py
```

### 打包为 EXE

```bash
python build.py
```

生成的可执行文件在 `dist/DesktopAutoSort.exe`

## 使用说明

1. 运行程序后会出现在系统托盘
2. 点击托盘图标打开设置窗口
3. 在"分组设置"中选择预设或自定义分组
4. 点击"一键整理"或按 Ctrl+Shift+O 整理桌面
5. 在"布局管理"中可保存和恢复图标位置

## 注意事项

- **必须关闭"自动排列图标"**：右键桌面 → 查看 → 取消勾选"自动排列图标"
- "将图标与网格对齐"可以保持开启
- 配置文件保存在程序目录的 `data/` 文件夹中

## 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件
