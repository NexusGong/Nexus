#!/bin/bash

# 聊天内容智能分析平台 - 环境设置脚本

echo "🔧 设置聊天内容智能分析平台开发环境..."

# 检查conda
if ! command -v conda &> /dev/null; then
    echo "❌ 未找到conda，请先安装Anaconda或Miniconda"
    echo "下载地址: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 创建conda环境
echo "📦 创建conda环境..."
conda env create -f environment.yml

if [ $? -eq 0 ]; then
    echo "✅ conda环境创建成功"
else
    echo "❌ conda环境创建失败"
    exit 1
fi

# 激活环境
echo "🔄 激活conda环境..."
conda activate nexus-chat-analysis

# 进入后端目录并安装依赖
echo "📥 安装后端依赖..."
cd backend
pip install -r requirements.txt

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "📋 复制环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 backend/.env 文件，填入你的API密钥"
fi

# 返回根目录
cd ..

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "⚠️  未找到Node.js，请先安装Node.js"
    echo "推荐使用nvm安装: https://github.com/nvm-sh/nvm"
    echo "安装完成后运行: npm install"
else
    # 安装前端依赖
    echo "📥 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "🎉 环境设置完成！"
echo ""
echo "📝 下一步操作："
echo "1. 编辑 backend/.env 文件，配置API密钥"
echo "2. 启动后端服务: ./start_backend.sh"
echo "3. 启动前端服务: ./start_frontend.sh"
echo ""
echo "🔗 服务地址："
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"

