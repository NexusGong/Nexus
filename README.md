# 聊天内容智能分析平台

一个基于AI的聊天内容多维度分析平台，支持图片OCR识别和智能回复建议生成。

## ✨ 功能特性

- 🔐 **用户认证**: 支持邮箱/手机号注册和登录（验证码验证）
- 📊 **使用限制**: 登录用户享有更多使用次数（OCR、会话、聊天分析）
- 👤 **用户资料**: 支持修改用户名和上传头像（支持图片压缩）
- 💾 **数据持久化**: 登录后对话和卡片自动保存，下次登录可见
- 🔒 **数据隔离**: 非登录用户和登录用户的数据完全隔离
- 📱 **多端支持**: 网页版 + PWA移动端 + iOS App
- 🖼️ **图片识别**: 支持聊天截图OCR识别（豆包OCR / 火山引擎OCR）
- 🔢 **多图OCR实时进度**: 在"识别中"卡片内以 x/N 与进度条实时显示（如 0/3 → 3/3），与实际处理保持同步
- ♻️ **稳定性增强**: 后端对多图序列化识别并内置指数退避重试；前端单图顺序调用与轻量重试，显著降低"单图成功、多图失败"问题
- 🧩 **对话结构准确**: 强化时间戳过滤与气泡合并收敛策略，避免将时间戳误判为己方、以及将多个对方气泡意外合并
- ➕ **预览页添加图片卡片**: 预览网格末尾提供与缩略图同尺寸的"添加图片"卡片（中间加号），不必重走上传流程；保留工具栏"上传图片"
- 🤖 **智能分析**: 多维度分析聊天内容（DeepSeek API）
- 💡 **回复建议**: 提供多种回复思路和示例
- 📊 **分析卡片**: 生成精美的分析结果卡片
- 📤 **导出功能**: 支持图片导出（后端 Playwright 渲染，智能文件名：主题+时间）
- 🎨 **现代UI**: 现代化聊天界面，暗色模式友好
- 💾 **一键保存**: 分析结果可直接保存为卡片
- 🗂️ **卡片管理**: 支持重命名、删除、搜索分析卡片
- 🕒 **时区支持**: 所有时间显示匹配用户本地时区
- 🎴 **卡片模式**: 像抽卡游戏一样，输入内容后生成精美的分析卡片，支持文本和图片识别，但不支持对话功能
- 💬 **自由交谈模式**: 与有趣的AI角色进行对话，每个角色都有独特的性格、语气和背景，支持多轮对话和上下文记忆，满意时可生成分析卡片

## 🛠️ 技术栈

- **框架**: FastAPI + SQLAlchemy + SQLite
- **AI服务**: 豆包OCR / 火山引擎OCR（图片识别）+ DeepSeek API（内容分析）
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

#### 卡片模式与自由交谈模式（2025-11-07）
- **卡片模式**：
  - 像抽卡游戏一样，输入内容后生成精美的分析卡片
  - 支持文本输入和图片识别（OCR）
  - 精美的抽卡动画和进度提示
  - 采用豆包UI风格设计
  - 卡片模式不会保存到最近对话中，只有点击"保存卡片"才会保存到分析卡片库
- **自由交谈模式**：
  - 预设了7个有趣的AI角色（小智、小暖、小机灵、诸葛亮、孙悟空、哆啦A梦、路飞）
  - 每个角色都有独特的性格、语气和说话风格
  - 支持多轮对话和上下文记忆
  - AI回复采用流式输出，实时显示生成内容
  - 支持Markdown格式显示
  - 在对话过程中可以随时切换不同的AI角色
  - 选择角色后会自动发送符合角色性格的欢迎消息
  - AI角色会引导用户生成分析卡片
- **模式选择**：
  - 在主页和新建对话界面都可以选择卡片模式或自由交谈模式
  - 未登录用户也可以使用这两种模式

#### 用户认证与使用限制系统（2025-11-07）
- **用户注册和登录**：支持邮箱/手机号注册和登录，6位验证码，5分钟有效期
- **使用次数限制**：
  - 非登录用户：极速OCR 5次/天，性能OCR 2次/天，会话5个，聊天分析10次/会话
  - 登录用户：极速OCR 10次/天，性能OCR 5次/天，聊天分析50次/会话
- **数据隔离**：非登录用户使用session_token标识会话，登录时自动关联历史数据
- **用户资料管理**：支持修改用户名和上传头像（支持图片压缩）
- **登录状态持久化**：刷新页面后自动恢复登录状态

#### 多图OCR与识别体验（2025-11-06）
- 前端：
  - 识别进度在处理中卡片内以“x/N + 进度条”实时展示，严格与单图顺序请求对齐
  - 预览网格新增“添加图片”卡片，点击复用统一隐藏文件输入；移除预览标题栏旧按钮；顶部工具栏“上传图片”保留
  - 移除冗余/噪声的控制台输出，仅保留必要关系信息
- 后端：
  - 将多图 OCR 从并发改为序列化调用，适配 OCR SDK 并提升稳定性
  - 为每张图引入最多 3 次指数退避 + 抖动重试，确保“单图成功、多图失败”问题显著缓解
  - 降噪日志：保留 info/warning/error，去除过度 debug

#### 导出长图（2025-10-31）

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

files: File[]  # 多张聊天截图，最多10张
provider: str  # 识别提供方，可选 'doubao' 或 'volc'
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

可选：
- `VOLC_ACCESS_KEY`、`VOLC_SECRET_KEY`、`VOLC_REGION`（直连火山引擎时使用）

### 识别体验优化
- **提供方选择**：支持豆包OCR与火山引擎OCR
- 多图顺序识别，实时进度（x/N + 进度条），失败轻量重试
- 前端等待界面为居中模态，成功不再弹toast
- 段落选择界面按己方/对方镜像排布，清晰展示对话结构
- 在图片预览时可直接选择识别提供方

## 🔧 配置说明

### API密钥配置
编辑 `backend/.env` 文件：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# 豆包/火山引擎配置（至少启用其一）
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL=doubao-seed-1-6-vision-250815

# 火山引擎（可选）
VOLC_ACCESS_KEY=your_volc_ak
VOLC_SECRET_KEY=your_volc_sk
VOLC_REGION=cn-north-1

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
- **OCR识别**: 自动识别聊天截图中的文字（豆包OCR / 火山引擎OCR）
- **提供方选择**: 预览阶段即可选择使用豆包或火山引擎
- **多图识别**: 顺序逐张识别，UI 实时展示 0/N → N/N 进度，失败自动重试
- **拖拽上传**: 支持拖拽上传图片
- **格式支持**: JPG、PNG、GIF、WebP
- **预览功能**: 实时预览上传的图片；预览网格末尾"添加图片"卡片便捷追加
- **结构化输出**: 识别发言人（己方/对方），并优化时间戳过滤与气泡合并，降低误判与过度合并

### 6. 卡片模式
- **游戏化体验**: 像抽卡游戏一样，输入内容后点击"开始抽卡"生成精美的分析卡片
- **精美动画**: 抽卡过程中有精美的动画效果，显示"正在识别"、"正在理解"、"正在生成"等动态提示
- **支持多种输入**: 支持文本输入和图片识别（OCR）
- **豆包UI风格**: 采用豆包UI风格设计，界面美观现代
- **卡片保存**: 生成后可以保存卡片到分析卡片库，或重新生成新卡片
- **不保存对话**: 卡片模式不会保存到最近对话中，只有点击"保存卡片"才会保存到分析卡片库

### 7. 自由交谈模式
- **AI角色系统**: 预设了7个有趣的AI角色，包括原创角色（小智、小暖、小机灵）和经典IP角色（诸葛亮、孙悟空、哆啦A梦、路飞）
- **角色个性化**: 每个角色都有独特的性格、语气、说话风格和背景故事
- **多轮对话**: 支持多轮对话，AI角色会记住整个对话上下文
- **流式输出**: AI回复采用流式输出，实时显示生成内容
- **Markdown支持**: AI回复支持Markdown格式，提供更好的阅读体验
- **角色切换**: 在对话过程中可以随时切换不同的AI角色
- **欢迎消息**: 选择角色后会自动发送符合角色性格的欢迎消息
- **生成卡片**: 在对话过程中，AI角色会引导用户生成分析卡片
- **对话管理**: 对话会自动保存到最近对话中，支持删除和管理

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
- **[📋 开发记录](docs/DAILY_SUMMARY_2025_11_07.md)** - 最新开发记录

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
