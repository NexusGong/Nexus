# 卡片模式与自由交谈模式开发计划

## 📋 功能概述

在现有功能基础上，新增两个核心功能模式，让平台更有趣：

1. **卡片模式**：像抽卡游戏一样，读取用户记录后每次只生成一张卡片，不支持对话
2. **自由交谈模式**：可以选择不同的AI角色进行对话，每个角色有不同的语气和表述，支持多轮对话，满意时可生成结果卡片

## 🎯 核心设计理念

### 卡片模式
- **游戏化体验**：抽卡动画、卡片收集、稀有度系统
- **快速生成**：基于用户历史记录，一键生成分析卡片
- **视觉冲击**：精美的卡片设计，类似游戏卡牌

### 自由交谈模式
- **角色扮演**：每个AI角色有独特的性格、语气和背景
- **沉浸式对话**：多轮对话，角色会记住上下文
- **灵活生成**：用户满意时可随时生成分析卡片

## 🗄️ 数据库设计

### 1. AI角色表 (ai_characters)

```python
class AICharacter(Base):
    __tablename__ = "ai_characters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 角色名称
    avatar_url = Column(String(500), nullable=True)  # 头像URL
    description = Column(Text, nullable=True)  # 角色描述
    personality = Column(Text, nullable=False)  # 性格特点
    speaking_style = Column(Text, nullable=False)  # 说话风格
    background = Column(Text, nullable=True)  # 背景故事
    system_prompt = Column(Text, nullable=False)  # 系统提示词
    category = Column(String(50), nullable=False)  # 分类：original/classic/anime
    rarity = Column(String(20), default="common")  # 稀有度：common/rare/epic/legendary
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 2. 角色对话记录表 (character_conversations)

```python
class CharacterConversation(Base):
    __tablename__ = "character_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_token = Column(String(255), nullable=True, index=True)
    character_id = Column(Integer, ForeignKey("ai_characters.id"), nullable=False)
    title = Column(String(200), nullable=True)
    context_summary = Column(Text, nullable=True)  # 对话上下文摘要
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    character = relationship("AICharacter")
    messages = relationship("CharacterMessage", back_populates="conversation")
```

### 3. 角色消息表 (character_messages)

```python
class CharacterMessage(Base):
    __tablename__ = "character_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("character_conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user/assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("CharacterConversation", back_populates="messages")
```

## 🎨 AI角色设计

### 原创角色（适合中国用户）

1. **小智** - 智慧型助手
   - 性格：理性、专业、温和
   - 语气：正式但友好，善于分析
   - 背景：AI分析专家，擅长解读人际关系

2. **小暖** - 情感型助手
   - 性格：温暖、共情、细腻
   - 语气：温柔、体贴，善于情感共鸣
   - 背景：情感咨询师，擅长理解情感

3. **小机灵** - 幽默型助手
   - 性格：幽默、机智、轻松
   - 语气：轻松幽默，善于化解尴尬
   - 背景：社交达人，擅长活跃气氛

### 经典IP角色

1. **诸葛亮** - 智慧谋士
   - 性格：睿智、沉稳、深谋远虑
   - 语气：文雅、深刻，善于分析策略
   - 背景：三国时期的智慧化身

2. **孙悟空** - 直率英雄
   - 性格：直率、勇敢、正义
   - 语气：直接、豪爽，有时带点顽皮
   - 背景：齐天大圣，敢于直言

3. **哆啦A梦** - 贴心伙伴
   - 性格：善良、贴心、乐于助人
   - 语气：亲切、可爱，充满关怀
   - 背景：来自未来的机器猫

4. **路飞** - 热血少年
   - 性格：热血、乐观、坚持
   - 语气：充满激情，简单直接
   - 背景：海贼王，追求自由

## 🔌 API设计

### 1. 角色相关API

#### GET /api/characters
获取角色列表
```json
{
  "characters": [
    {
      "id": 1,
      "name": "小智",
      "avatar_url": "...",
      "description": "...",
      "personality": "...",
      "speaking_style": "...",
      "category": "original",
      "rarity": "common"
    }
  ]
}
```

#### GET /api/characters/{character_id}
获取角色详情

### 2. 卡片模式API

#### POST /api/cards/generate
基于用户记录生成卡片
```json
{
  "source": "history",  // history/random
  "user_history_id": 123  // 可选，指定历史记录
}
```

### 3. 自由交谈模式API

#### POST /api/character-chat/conversations
创建角色对话
```json
{
  "character_id": 1,
  "title": "与诸葛亮的对话"
}
```

#### POST /api/character-chat/messages
发送消息给角色
```json
{
  "conversation_id": 1,
  "message": "你好，我想咨询一个问题"
}
```

#### POST /api/character-chat/generate-card
从角色对话生成卡片
```json
{
  "conversation_id": 1,
  "title": "对话分析卡片"
}
```

## 🎨 前端设计

### 1. 主页模式切换

在 `HomePage.tsx` 中添加模式选择器：
- 卡片模式按钮（带抽卡图标）
- 自由交谈模式按钮（带对话图标）
- 保持原有的"开始分析"功能

### 2. 卡片模式页面 (CardModePage.tsx)

- **抽卡界面**：
  - 大按钮"抽取卡片"
  - 抽卡动画（卡片翻转、光效）
  - 卡片展示区域
  - 卡片收集列表

- **卡片展示**：
  - 精美的卡片设计
  - 显示分析结果
  - 保存/分享功能

### 3. 自由交谈模式页面 (ChatModePage.tsx)

- **角色选择界面**：
  - 角色卡片网格
  - 角色预览（头像、描述、性格）
  - 分类筛选（原创/经典）

- **对话界面**：
  - 角色头像和名称
  - 消息气泡（区分用户和角色）
  - 输入框
  - "生成卡片"按钮

## 🔧 实现步骤

### 阶段一：数据库和模型
1. ✅ 创建AI角色表模型
2. ✅ 创建角色对话和消息表模型
3. ✅ 数据库迁移

### 阶段二：后端API
1. ✅ 角色管理API
2. ✅ 卡片模式API
3. ✅ 自由交谈模式API
4. ✅ AI服务扩展（角色对话）

### 阶段三：前端页面
1. ✅ 主页模式切换
2. ✅ 卡片模式页面
3. ✅ 自由交谈模式页面
4. ✅ 路由配置

### 阶段四：AI角色实现
1. ✅ 设计角色prompt
2. ✅ 实现角色对话逻辑
3. ✅ 测试角色对话质量

### 阶段五：优化和测试
1. ✅ 抽卡动画优化
2. ✅ 卡片设计优化
3. ✅ 性能优化
4. ✅ 用户体验测试

## 📝 注意事项

1. **不影响现有功能**：所有新功能都是新增的，不修改现有代码逻辑
2. **数据隔离**：角色对话数据与普通对话数据分开存储
3. **使用限制**：卡片模式和自由交谈模式也需要遵循使用次数限制
4. **角色版权**：经典IP角色仅用于学习和研究，注意版权问题
5. **性能考虑**：角色对话需要维护上下文，注意token消耗

## 🎯 成功标准

1. ✅ 卡片模式可以流畅地生成和展示卡片
2. ✅ 自由交谈模式支持多轮对话，角色语气一致
3. ✅ 用户可以在主页轻松切换模式
4. ✅ 所有功能不影响现有系统
5. ✅ 用户体验流畅，界面美观

