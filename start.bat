@echo off
setlocal
title Chaoxing Study Mate Launcher

echo ========================================================
echo  Chaoxing Study Mate Launcher (Windows)
echo ========================================================
echo.

echo [1/3] Checking runtime environment...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing lightweight runtime via PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
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
