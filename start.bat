@echo off
setlocal
title Chaoxing Study Mate Launcher (Windows)

echo ========================================================
echo  Chaoxing Study Mate Launcher (Windows)
echo ========================================================
echo.

echo [1/3] Detecting network environment and configuring mirrors...
REM Configure Tsinghua open source mirror for ultra fast downloads in China
set "UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
set "PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/3] Installing lightweight runtime uv via PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { irm https://mirror.ghproxy.com/https://raw.githubusercontent.com/astral-sh/uv/main/install.ps1 | iex } catch { irm https://astral.sh/uv/install.ps1 | iex }"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
    echo [1/3] Runtime environment ready.
)

echo [2/3] Launching main application...
echo.
uv run main.py

if %errorlevel% neq 0 (
    echo.
    echo Application exited. Press any key to close...
    pause >nul
)
