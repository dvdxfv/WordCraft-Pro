@echo off
chcp 65001 >nul 2>&1
title WordCraft Pro - Windows 打包
echo.
echo ============================================================
echo   WordCraft Pro Windows 打包工具
echo ============================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 执行打包
python build.py

if errorlevel 1 (
    echo.
    echo ❌ 打包失败
) else (
    echo.
    echo ✅ 打包完成！
    echo 📁 安装包位置: dist\WordCraft-Pro.exe
)
echo.
pause
