# 文档变更日志（Documentation Changelog）

所有重要的文档变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且此项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

## 2025-10-31

### 更新
- 同步文档至最新代码改动：
  - 主题切换统一（HTML `dark` + `theme-changing` 瞬时禁用过渡）。
  - Toast 视口调整到正中央并 0.5s 自动消失。
  - 前端样式改为主题令牌；聊天与卡片的暗色可读性更新。
  - 后端导出服务改为 Playwright 渲染 PNG 长图，修复 header 编码（latin-1）问题。
  - 空对话避免策略说明（仅在首条消息时创建）。
- 新增 `DAILY_SUMMARY_2025_10_31.md` 开发记录。

### 新增
- 导出文件名优化（主题+时间格式，ASCII + UTF-8 filename* 兼容）
- 时区支持完善（用户本地时间）
- 文件名安全性过滤
- 智能文件名生成逻辑

### 重要变更
- PDF 导出已下线，统一为图片导出。
- 部署与本地运行新增 Playwright 浏览器安装步骤：`python -m playwright install chromium`。

### 2025-10-29

#### 新增
- 批量OCR接口与结构化输出文档（己方/对方、气泡级分块）。
- 多图上传与段落筛选的交互规范（镜像排布、角色着色、勾选位置）。
- 后端阶段计时日志说明（编码/构包/发送/解析/总计）。

#### 改进
- 识别等待文案精简；成功不再弹toast。
- 批量识别默认限制4张以优化端到端时延。

#### 修复
- 兼容 `.env` OCR扩展字段，避免Pydantic校验错误。





