#!/bin/bash

# 聊天内容智能分析平台 - 前端启动脚本

echo "🚀 启动聊天内容智能分析平台前端服务..."

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未找到Node.js，请先安装Node.js"
    echo "推荐使用nvm安装: https://github.com/nvm-sh/nvm"
    exit 1
fi

# 检查npm
if ! command -v npm &> /dev/null; then
    echo "❌ 未找到npm，请先安装npm"
    exit 1
fi

# 进入前端目录
cd frontend

# 检查依赖是否安装
echo "🔍 检查前端依赖..."
if [ ! -d "node_modules" ]; then
    echo "📥 安装前端依赖..."
    npm install
fi

# 启动开发服务器
echo "🌟 启动前端开发服务器..."
echo "服务地址: http://localhost:5173 (已绑定 IPv4 0.0.0.0)"
echo "按 Ctrl+C 停止服务"
echo ""

npm run dev -- --host 0.0.0.0

