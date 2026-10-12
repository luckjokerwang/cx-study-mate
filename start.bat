@echo off
chcp 65001 >nul
title 超星学习助手 (Chaoxing Study Mate)

echo ========================================================
echo  🎓 超星学习助手 (Chaoxing Study Mate) - 一键启动器
echo ========================================================
echo.

:: 1. 检查并自动安装 uv
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/3] 正在配置轻量免安装运行环境 (uv)...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
    echo [1/3] 运行环境已就绪。
)

:: 2. 启动脚本
echo [2/3] 正在启动主程序...
echo.
uv run main.py

echo.
echo 程序已退出。
pause
