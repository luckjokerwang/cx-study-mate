#!/usr/bin/env bash
set -e

echo "========================================================"
echo " 🎓 超星学习助手 (Chaoxing Study Mate) - 一键启动器"
echo "========================================================"
echo ""

# 1. 检查并自动安装 uv
if ! command -v uv &> /dev/null; then
    echo "[1/3] 正在配置轻量运行环境 (uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
else
    echo "[1/3] 运行环境已就绪。"
fi

# 2. 启动脚本
echo "[2/3] 正在启动主程序..."
echo ""
uv run main.py "$@"
