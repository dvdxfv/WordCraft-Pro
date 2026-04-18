#!/usr/bin/env python3
"""
WordCraft Pro - 跨平台打包脚本
支持: Windows (.exe) / macOS (.app) / Linux
用法: python build.py
"""

import subprocess
import sys
import os
import platform

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
#  配置
# ============================================================
APP_NAME = "WordCraft-Pro"
APP_ID = "com.wordcraft.pro"
ENTRY = "app.py"
DEPS = ["pyinstaller>=6.0", "pywebview>=5.0", "python-docx>=0.8.11"]

# ============================================================
#  安装依赖
# ============================================================
print("=" * 50)
print(f"  WordCraft Pro 打包工具")
print(f"  平台: {platform.system()} ({platform.machine()})")
print(f"  Python: {sys.version.split()[0]}")
print("=" * 50)
print()

print("📦 安装打包依赖...")
pip_args = [sys.executable, "-m", "pip", "install"]
if platform.system() != "Windows":
    pip_args.append("--break-system-packages")
pip_args.extend(DEPS)
subprocess.check_call(pip_args)
print()

# ============================================================
#  构建 PyInstaller 命令
# ============================================================
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", APP_NAME,
    "--onefile",
    "--noconfirm",
    "--clean",
    # 隐藏导入
    "--hidden-import", "webview",
    "--hidden-import", "docx",
    "--hidden-import", "docx.opc",
    "--hidden-import", "docx.oxml",
    "--hidden-import", "docx.oxml.ns",
    "--collect-data", "webview",
    "--collect-data", "docx",
    # 资源文件
    "--add-data", "web:index.html",
]

# 平台特定参数
if platform.system() == "Windows":
    cmd.extend(["--windowed"])
    # Windows 图标（如果有）
    if os.path.exists("assets/icon.ico"):
        cmd.extend(["--icon", "assets/icon.ico"])
elif platform.system() == "Darwin":  # macOS
    cmd.extend([
        "--windowed",
        "--osx-bundle-identifier", APP_ID,
    ])
    if os.path.exists("assets/icon.icns"):
        cmd.extend(["--icon", "assets/icon.icns"])
else:  # Linux
    cmd.extend(["--windowed"])

cmd.append(ENTRY)

# ============================================================
#  执行打包
# ============================================================
print("🔨 开始打包...")
print(f"命令: {' '.join(cmd)}")
print()

result = subprocess.run(cmd)

if result.returncode == 0:
    print()
    print("=" * 50)
    print("✅ 打包成功！")
    print()

    dist_dir = "dist"
    if platform.system() == "Windows":
        exe = os.path.join(dist_dir, f"{APP_NAME}.exe")
    elif platform.system() == "Darwin":
        exe = os.path.join(dist_dir, APP_NAME)
    else:
        exe = os.path.join(dist_dir, APP_NAME)

    if os.path.exists(exe):
        size_mb = os.path.getsize(exe) / (1024 * 1024)
        print(f"  📁 输出: {exe}")
        print(f"  📦 大小: {size_mb:.1f} MB")
    print()
    print("  💡 使用方式: 双击运行即可")
    print("=" * 50)
else:
    print()
    print("❌ 打包失败，请检查上方错误信息")
    sys.exit(1)
