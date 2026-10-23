#!/usr/bin/env bash
set -e

# 0. 加载本地密钥（可选，.env.local 已被 .gitignore 忽略）
if [ -f ".env.local" ]; then
    set -a
    . ./.env.local
    set +a
fi

echo "========================================================"
echo " 🎓 超星学习助手 (Chaoxing Study Mate) - 一键启动器"
echo "========================================================"
echo ""

# 1. 国内网络加速检测
echo "[1/3] 正在检测网络环境并优化镜像源..."
USE_MIRROR=0
if ! curl -s --connect-timeout 2 -I https://github.com >/dev/null 2>&1; then
    echo "⚡ 检测到国内网络环境，自动启用清华大学开源镜像源加速..."
    USE_MIRROR=1
    export UV_INDEX_URL="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    export PIP_INDEX_URL="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
else
    echo "🌐 检测到海外网络，使用官方源加速..."
fi

# 2. 检查并安装 uv
if ! command -v uv &> /dev/null; then
    echo "正在自动安装极速运行时 uv..."
    if [ "$USE_MIRROR" -eq 1 ]; then
        curl -LsSf https://mirror.ghproxy.com/https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | sh || \
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi
echo "[2/3] 运行环境就绪。"

# 3. 启动主程序
echo "[3/3] 启动主程序..."
echo ""
uv run main.py "$@"
