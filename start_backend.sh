#!/bin/bash

# 聊天内容智能分析平台 - 后端启动脚本

echo "🚀 启动聊天内容智能分析平台后端服务..."

# 检查conda环境
if ! command -v conda &> /dev/null; then
    echo "❌ 未找到conda，请先安装Anaconda或Miniconda"
    exit 1
fi

# 激活conda环境（非交互式脚本需先加载conda.sh）
echo "📦 激活conda环境..."
USE_CONDA_RUN=0
CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$CONDA_BASE/etc/profile.d/conda.sh"
fi

if conda activate nexus-chat-analysis 2>/dev/null; then
    echo "✅ 已激活环境: $(conda info --envs | grep '\*' | tr -s ' ')"
else
    echo "⚠️  激活失败，改用 conda run 方式启动"
    USE_CONDA_RUN=1
fi

# 进入后端目录
cd backend

# 检查依赖是否安装
echo "🔍 检查Python依赖..."
if ! python -c "import fastapi" &> /dev/null; then
    echo "📥 安装Python依赖..."
    pip install -r requirements.txt
fi

# 如已有实例占用8000端口，先释放以避免重复启动导致地址占用
if lsof -ti tcp:8000 >/dev/null 2>&1; then
    echo "⚠️  检测到已有进程占用 8000 端口，正在释放..."
    PIDS=$(lsof -ti tcp:8000 | tr '\n' ' ')
    kill $PIDS 2>/dev/null || true
    sleep 1
    if lsof -ti tcp:8000 >/dev/null 2>&1; then
        echo "⛔ 强制结束残留进程..."
        lsof -ti tcp:8000 | xargs -I{} kill -9 {} 2>/dev/null || true
        sleep 0.5
    fi
fi

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到.env文件，请复制.env.example并配置API密钥"
    echo "cp .env.example .env"
    echo "然后编辑.env文件，填入你的API密钥"
    exit 1
fi

# 启动服务
echo "🌟 启动FastAPI服务..."
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务"
echo ""

if [ "$USE_CONDA_RUN" = "1" ]; then
    exec conda run -n nexus-chat-analysis python run.py
else
    exec python run.py
fi

