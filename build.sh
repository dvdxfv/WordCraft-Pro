#!/bin/bash
# WordCraft Pro - macOS 打包脚本
# 用法: 双击运行 或 终端执行 ./build.sh

cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  WordCraft Pro macOS 打包工具"
echo "============================================================"
echo ""

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    echo "   方式1: brew install python3"
    echo "   方式2: https://www.python.org/downloads/"
    echo ""
    read -p "按回车退出..."
    exit 1
fi

# 执行打包
python3 build.py

echo ""
if [ $? -eq 0 ]; then
    echo "✅ 打包完成！"
    echo "📁 安装包位置: dist/WordCraft-Pro"
    echo ""
    echo "💡 提示: 可以将 dist/WordCraft-Pro 拖到「应用程序」文件夹"
else
    echo "❌ 打包失败"
fi
echo ""
read -p "按回车退出..."
