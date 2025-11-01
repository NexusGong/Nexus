# 聊天内容智能分析平台

一个基于AI的聊天内容多维度分析平台，支持图片OCR识别和智能回复建议生成。

## ✨ 功能特性

- 📱 **多端支持**: 网页版 + PWA移动端 + iOS App
- 🖼️ **图片识别**: 支持聊天截图OCR识别（豆包API）
- 🤖 **智能分析**: 多维度分析聊天内容（DeepSeek API）
- 💡 **回复建议**: 提供多种回复思路和示例
- 📊 **分析卡片**: 生成精美的分析结果卡片
- 📤 **导出功能**: 支持图片导出（后端Playwright渲染，智能文件名：主题+时间）
- 🎨 **现代UI**: ChatGPT风格的聊天界面
- 🔄 **实时分析**: 流式响应和实时分析结果
- 💾 **一键保存**: 分析结果可直接保存为卡片
- 🗂️ **卡片管理**: 支持重命名、删除、搜索分析卡片
- 🕒 **时区支持**: 所有时间显示匹配用户本地时区

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI + SQLAlchemy + SQLite
- **AI服务**: 豆包API（图片OCR）+ DeepSeek API（内容分析）
- **截图服务**: Playwright（后端渲染导出PNG图片，全局浏览器实例复用）
- **认证**: JWT Token
- **文档**: 自动生成API文档

### 前端
- **框架**: React 18 + TypeScript + Vite
- **UI**: Tailwind CSS + shadcn/ui
- **状态管理**: Zustand
- **PWA**: 支持离线访问和移动端安装

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Conda (推荐)
- Playwright 浏览器（首次使用需安装，详见下方说明）

### 一键设置
```bash
# 克隆项目
git clone <repository-url>
cd Nexus

# 运行设置脚本
./setup.sh
```

### 手动设置

#### 1. 创建Conda环境
```bash
conda env create -f environment.yml
conda activate nexus-chat-analysis
```

#### 2. 配置后端
```bash
cd backend
pip install -r requirements.txt
# 首次使用需安装 Playwright 浏览器
python -m playwright install chromium
cp .env.example .env
# 编辑 .env 文件，配置API密钥
```

#### 3. 配置前端
```bash
cd frontend
npm install
```

### 启动服务

#### 使用脚本启动（推荐）
```bash
# 启动后端
./start_backend.sh

# 启动前端（新终端）
./start_frontend.sh
```

#### 手动启动
```bash
# 后端（需要先激活conda环境）
conda activate nexus-chat-analysis
cd backend
bash start_backend.sh or python run.py

# 前端（新终端窗口）
cd frontend
bash start_frontend.sh or npm run dev


### 新增与重要变更

#### 导出长图（2025-10-31）
- **技术方案**: 后端使用 Playwright 渲染 HTML 生成高质量 PNG 图片
- **性能优化**: 全局浏览器实例复用，导出速度优化至 1-2 秒
- **版式一致**: 生成的图片版式与前端 Dialog 完全一致
- **文件名**: 智能文件名（主题+时间），支持中文，符合 RFC 5987 标准
- **安装要求**: 首次使用需安装 Playwright 浏览器：`python -m playwright install chromium`
- **已下线**: PDF 导出功能已移除

#### 新增API（2025-10-29）

#### 批量OCR识别
```http
POST /api/chat/ocr/batch
Content-Type: multipart/form-data

files: File[]  # 多张聊天截图，默认最多4张
```
响应：与单图OCR一致，`metadata` 中包含（若模型输出结构化成功）：
```json
{
  "metadata": {
    "participants": ["己方", "对方"],
    "structured_messages": [
      {"speaker_side":"right","speaker_name":"己方","text":"...","block_index":1},
      {"speaker_side":"left","speaker_name":"对方","text":"...","block_index":2}
    ]
  }
}
```

### 配置（.env）
必填：
- `DOUBAO_API_KEY` / `DOUBAO_API_URL`（如 `https://ark.cn-beijing.volces.com/api/v3/chat/completions`）
- `DOUBAO_MODEL`

可选（兼容）：
- `OCR_PROVIDER`、`VOLC_ACCESS_KEY`、`VOLC_SECRET_KEY`、`VOLC_REGION`

### 识别体验优化
- 多图批量识别，端到端目标5-10秒；后端输出阶段计时日志（编码/构包/发送/解析/总计）。
- 前端等待界面为居中模态，成功不再弹toast；段落选择界面按己方/对方镜像排布。

## 🔧 配置说明

### API密钥配置
编辑 `backend/.env` 文件：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# 豆包大模型配置
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL=doubao-seed-1-6-vision-250815

# JWT密钥（必需）
SECRET_KEY=your_secret_key_here
```

### Playwright 浏览器安装
首次使用图片导出功能前，需要安装 Playwright 浏览器：

```bash
# 激活conda环境
conda activate nexus-chat-analysis

# 安装 Chromium 浏览器
python -m playwright install chromium
```

**注意**: 
- 浏览器安装只需执行一次
- 安装完成后，浏览器实例会在应用启动时自动初始化并全局复用
- 生产环境建议使用 `--no-sandbox` 参数（已在代码中配置）

### 服务地址
- 前端: http://localhost:5173
- 后端: http://localhost:8000
- API文档: http://localhost:8000/docs

## 📁 项目结构

```
Nexus/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── api/               # API路由
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic模式
│   │   ├── services/          # 业务逻辑
│   │   │   ├── ai_service.py       # AI分析服务
│   │   │   ├── ocr_service.py      # OCR识别服务
│   │   │   ├── card_service.py     # 卡片业务逻辑
│   │   │   └── screenshot_service.py # Playwright截图服务
│   │   ├── utils/             # 工具函数
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   └── main.py            # 应用入口
│   ├── requirements.txt       # Python依赖
│   └── run.py                 # 启动脚本
├── frontend/                   # React前端
│   ├── src/
│   │   ├── components/        # React组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API服务
│   │   ├── store/             # 状态管理
│   │   ├── hooks/             # 自定义钩子
│   │   └── lib/               # 工具函数
│   ├── package.json           # 前端依赖
│   └── vite.config.ts         # Vite配置
├── docs/                      # 项目文档
│   ├── DAILY_SUMMARY_2024_10_24.md  # 10月24日开发记录
│   ├── DAILY_SUMMARY_2024_10_28.md  # 10月28日开发记录
│   ├── DEPLOYMENT.md          # 部署指南
│   ├── DOCUMENTATION_CHANGELOG.md # 文档变更日志
│   └── DAILY_SUMMARY_2025_10_29.md # 2025-10-29开发记录
├── environment.yml             # Conda环境配置
├── setup.sh                   # 环境设置脚本
├── start_backend.sh           # 后端启动脚本
├── start_frontend.sh          # 前端启动脚本
├── docker-compose.yml         # Docker部署配置
├── Dockerfile                 # Docker镜像配置
└── README.md                  # 项目文档
```

## 🎯 核心功能

### 1. 聊天内容分析
- **意图识别**: 分析对话的主要意图和次要意图
- **情感分析**: 识别情感倾向和强度
- **语气分析**: 判断语气风格和礼貌程度
- **关系分析**: 推断对话双方的关系亲密度
- **潜台词挖掘**: 发现隐藏的含义和暗示
- **关键信息提取**: 提取重要信息点

### 2. 智能回复建议
- **情感共鸣型**: 表达理解和共鸣的回复
- **理性分析型**: 客观分析问题的回复
- **幽默化解型**: 轻松幽默的回复方式
- **专业得体型**: 正式专业的回复风格

### 3. 分析卡片系统
- **精美设计**: 现代化的卡片界面，完整展示分析结果和回复建议
- **图片导出**: 后端 Playwright 渲染生成高质量 PNG 图片（2倍设备像素比，支持长图）
- **性能优化**: 全局浏览器实例复用，导出速度快（1-2秒）
- **智能文件名**: 导出文件使用主题+时间格式命名，支持中文文件名
- **时区支持**: 文件名时间使用用户本地时区，格式为 RFC 5987 标准
- **导出统计**: 自动记录导出次数和最后导出时间
- **一键保存**: 分析结果可直接保存为卡片
- **卡片管理**: 支持重命名、删除、搜索等操作

### 4. 对话管理系统
- **最近对话**: 显示历史对话列表
- **对话管理**: 支持重命名、删除对话
- **智能摘要**: 显示对话消息数量和最后更新时间
- **即时更新**: 新对话立即显示在侧边栏

### 5. 图片识别功能
- **OCR识别**: 自动识别聊天截图中的文字
- **拖拽上传**: 支持拖拽上传图片
- **格式支持**: 支持JPG、PNG、GIF、WebP等格式
- **预览功能**: 实时预览上传的图片

## 🔄 开发工作流

### 后端开发
```bash
# 激活环境
conda activate nexus-chat-analysis

# 进入后端目录
cd backend

# 首次使用需安装 Playwright 浏览器
python -m playwright install chromium

# 启动开发服务器
python run.py
```

### 前端开发
```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev
```

### 数据库管理
```bash
# 创建数据库表
python -c "from app.database import create_tables; create_tables()"

# 重置数据库
python -c "from app.database import drop_tables, create_tables; drop_tables(); create_tables()"
```

## 📱 移动端支持

### PWA功能
- 支持离线访问
- 可安装到手机桌面
- 推送通知支持
- 响应式设计

### iOS App打包
使用Capacitor将PWA打包为iOS应用：
```bash
cd frontend
npm install @capacitor/core @capacitor/cli
npx cap init
npx cap add ios
npx cap run ios
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📚 项目文档

- **[📖 文档索引](docs/README.md)** - 完整的项目文档导航
- **[📝 文档变更日志](docs/DOCUMENTATION_CHANGELOG.md)** - 文档更新记录
- **[🚀 部署指南](docs/DEPLOYMENT.md)** - 详细的部署说明
- **[📋 开发记录](docs/DAILY_SUMMARY_2024_10_28.md)** - 最新开发记录

## 🧹 维护与清理

为保持仓库精简并避免将可生成文件提交到版本库，可使用脚本快速清理：

```bash
bash scripts/clean.sh
# 如需恢复前端依赖：
cd frontend && npm ci
```

已在 `.gitignore` 中忽略：构建产物、缓存、日志、编辑器文件、Python/Node 缓存等。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [React](https://reactjs.org/) - 用户界面库
- [Tailwind CSS](https://tailwindcss.com/) - 实用优先的CSS框架
- [豆包](https://www.volcengine.com/products/doubao) - AI图片识别服务
- [DeepSeek](https://www.deepseek.com/) - AI内容分析服务
