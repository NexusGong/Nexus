# 2025-11-07 每日总结

## 今日目标
- 实现用户注册和登录功能（邮箱/手机验证码）
- 实现使用次数限制系统（登录用户vs非登录用户）
- 实现用户资料管理（包括头像上传）
- 实现登录状态持久化
- 修复历史对话和卡片的关联问题
- 清理代码（删除日志和测试代码）

## 关键变更

### 用户认证系统
- **注册功能**：支持邮箱/手机号注册，6位验证码，5分钟有效期
- **登录功能**：支持邮箱/手机号登录，验证码验证
- **JWT认证**：使用JWT token进行身份验证，token存储在localStorage
- **登录状态持久化**：刷新页面后自动恢复登录状态
- **用户资料管理**：支持修改用户名和上传头像（支持图片压缩）

### 使用次数限制系统
- **非登录用户限制**：
  - 极速模式OCR：5次/天
  - 性能模式OCR：2次/天
  - 会话创建：5个
  - 聊天分析：10次/会话
- **登录用户限制**：
  - 极速模式OCR：10次/天
  - 性能模式OCR：5次/天
  - 聊天分析：50次/会话
- **统计方式**：
  - 非登录用户：按IP地址和session_token统计
  - 登录用户：按用户ID统计
- **实时更新**：使用统计在登录/注册后实时更新

### 数据隔离
- **会话Token**：非登录用户使用session_token标识会话
- **数据关联**：登录时自动将未登录时创建的对话和卡片关联到用户
- **权限控制**：用户只能看到自己创建的对话和卡片

### UI/UX优化
- **欢迎界面**：登录后显示个性化欢迎界面（类似豆包风格）
- **输入框优化**：欢迎界面输入框更大，按钮集成在输入框底部
- **用户菜单**：右上角头像下拉菜单，包含设置和退出选项
- **设置页面**：支持编辑个人资料、主题切换、语言设置
- **头像上传**：支持图片压缩，最大10MB，自动压缩到400x400

## 后端改动

### 新增模型
- **VerificationCode**：验证码表（邮箱/手机号、验证码、类型、过期时间）
- **UsageRecord**：使用记录表（用户ID/IP/session_token、功能、使用次数、日期）

### 新增服务
- **auth_service.py**：认证服务（验证码生成/发送/验证、用户注册/登录、JWT生成）
- **usage_limit_service.py**：使用限制服务（检查/记录OCR、会话、聊天分析使用次数）

### 新增API
- **auth.py**：认证相关API
  - `POST /auth/send-code`：发送验证码
  - `POST /auth/register`：用户注册
  - `POST /auth/login`：用户登录
  - `GET /auth/me`：获取当前用户信息
  - `GET /auth/usage-stats`：获取使用统计
  - `PUT /auth/profile`：更新用户资料

### 数据库迁移
- 添加 `users.phone`、`users.last_login_at`、`users.avatar_url` 字段
- 添加 `conversations.session_token`、`analysis_cards.session_token` 字段
- 创建 `verification_codes`、`usage_records` 表

### 配置更新
- **config.py**：新增使用限制配置、验证码配置、SMTP配置
  - 非登录用户限制：`guest_ocr_fast_limit`、`guest_ocr_quality_limit`、`guest_conversation_limit`、`guest_chat_analysis_limit`
  - 登录用户限制：`user_ocr_fast_limit`、`user_ocr_quality_limit`、`user_chat_analysis_limit`
  - 验证码配置：`verification_code_length`、`verification_code_expire_minutes`、`verification_code_resend_interval`

### API端点更新
- **chat.py**：集成使用限制检查
  - `POST /chat/conversations`：检查会话创建限制
  - `POST /chat/analyze`：检查聊天分析限制
  - `POST /chat/ocr/batch`：检查OCR使用限制
  - `GET /chat/conversations`：按用户ID或session_token过滤
- **cards.py**：按用户ID或session_token过滤卡片

## 前端改动

### 新增组件
- **LoginDialog.tsx**：登录对话框（联系方式、验证码输入、发送验证码按钮）
- **RegisterDialog.tsx**：注册对话框（联系方式、用户名、验证码输入）
- **UserMenu.tsx**：用户菜单（头像下拉菜单，包含设置和退出）
- **SettingsPage.tsx**：设置页面（个人资料、偏好设置、设备信息）
- **dropdown-menu.tsx**：下拉菜单组件（shadcn/ui风格）
- **tabs.tsx**：标签页组件（shadcn/ui风格）

### 新增Store
- **authStore.ts**：认证状态管理（用户信息、token、使用统计、session_token）

### 服务更新
- **api.ts**：
  - 新增 `authApi`：认证相关API调用
  - 请求拦截器：自动添加Authorization和X-Session-Token头
  - 响应拦截器：处理401错误，仅在获取用户信息失败时自动退出登录

### 组件更新
- **Header.tsx**：根据登录状态显示登录/注册按钮或用户菜单
- **ChatInterface.tsx**：
  - 登录后显示欢迎界面（个性化欢迎消息）
  - 欢迎界面输入框更大，按钮集成在底部
  - 发送消息后实时创建对话并更新侧边栏
- **Sidebar.tsx**：仅登录用户可见对话列表
- **CardsPage.tsx**：按用户ID或session_token过滤卡片
- **HomePage.tsx**：登录用户自动重定向到聊天页面
- **MultiImageUploader.tsx**：显示使用统计，登录状态变化时更新

### 路由更新
- **App.tsx**：新增 `/settings` 路由

## 数据清理
- 清除所有历史对话和卡片数据（user_id为NULL的记录）
- 删除测试和迁移脚本：
  - `clear_history_data.py`
  - `migrate_add_avatar.py`
  - `migrate_add_session_token.py`
  - `migrate_add_columns.py`
- 删除前端console.log和console.warn（保留console.error用于错误处理）

## 已知问题与后续计划
- 验证码发送功能目前为占位符，需要集成真实的邮件/短信服务
- 可以考虑添加"忘记密码"功能
- 可以考虑添加"记住我"功能（延长token有效期）
- 可以考虑添加"第三方登录"功能（微信、QQ等）

## 测试要点
- 注册流程：输入联系方式 → 发送验证码 → 输入用户名和验证码 → 注册成功
- 登录流程：输入联系方式 → 发送验证码 → 输入验证码 → 登录成功
- 使用限制：非登录用户和登录用户的使用次数限制是否正确
- 数据隔离：非登录用户只能看到自己的对话和卡片
- 登录关联：登录时自动关联未登录时创建的对话和卡片
- 状态持久化：刷新页面后登录状态是否保持
- 头像上传：图片压缩、大小限制、格式验证是否正常

## 技术亮点
- **JWT认证**：使用JWT token进行无状态认证
- **Session Token**：非登录用户使用session_token标识会话
- **使用限制**：统一配置，灵活可扩展
- **数据关联**：登录时自动关联历史数据
- **图片压缩**：客户端图片压缩，减少服务器压力
- **状态持久化**：使用Zustand persist中间件实现状态持久化

