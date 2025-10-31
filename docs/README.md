# 📚 项目文档索引

## 📋 文档概览

本项目包含完整的文档体系，涵盖开发记录、部署指南、变更日志等各个方面。

### 2025-10-31 更新要点（与代码保持一致）

- 主题切换：在 HTML 根元素应用 `dark`，切换瞬间添加 `theme-changing` 禁用过渡，确保所有元素一致切换速度。
- Toast 视口：移动至右下角，避免居中遮挡。
- 前端样式：将 `bg-white / text-gray-* / border-gray-*` 等硬编码类统一替换为主题令牌（`bg-background/bg-card/bg-muted`、`text-foreground/text-muted-foreground`、`border/border-input`）。
- 聊天 UI：助手/分析气泡统一为 `bg-muted text-foreground border`，用户气泡保留品牌蓝。
- 卡片列表：卡片容器使用 `bg-card border`，强调区块使用 `bg-primary/5`，移除浅色渐变。
- 导出接口修复：后端导出服务函数签名新增可选 `user_timezone`，与路由调用一致，修复 500。
- 空对话避免：未输入内容时不创建对话，选择模式仅记忆为 `pendingContextMode`，首条消息发送时才创建。

## 📁 文档结构

### 📖 主要文档
- **[README.md](../README.md)** - 项目主要文档，包含功能介绍、快速开始、技术栈等
- **[DOCUMENTATION_CHANGELOG.md](./DOCUMENTATION_CHANGELOG.md)** - 文档变更日志，记录所有重要更新

### 🚀 部署相关
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 详细的部署指南，支持多种部署方式

### 📝 开发记录
- **[DAILY_SUMMARY_2024_10_24.md](./DAILY_SUMMARY_2024_10_24.md)** - 2024年10月24日开发记录
- **[DAILY_SUMMARY_2024_10_28.md](./DAILY_SUMMARY_2024_10_28.md)** - 2024年10月28日开发记录

## 🎯 快速导航

### 新用户入门
1. 阅读 [README.md](../README.md) 了解项目概况
2. 查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 进行环境配置
3. 运行 `./setup.sh` 一键设置环境

### 开发者参考
1. 查看 DOCUMENTATION_CHANGELOG.md 了解文档最新变更
2. 阅读开发记录了解功能实现细节（包括 2025-10-31 当日记录）
3. 参考部署指南进行生产环境配置

### 项目维护
1. 定期更新 DOCUMENTATION_CHANGELOG.md
2. 记录重要开发节点
3. 维护部署文档的准确性

## 📊 文档统计

- **总文档数**: 6个
- **总字数**: 约30,000字
- **覆盖内容**: 功能说明、技术实现、部署指南、开发记录
- **更新频率**: 每次重要更新都会更新相关文档

## 🔄 文档维护

### 更新原则
- 功能更新时同步更新README和变更日志
- 重要开发节点记录到开发记录
- 部署方式变更时更新部署指南
- 保持文档的准确性和时效性

### 维护责任
- 开发者负责更新技术文档
- 项目维护者负责更新变更日志
- 所有团队成员都有义务保持文档的准确性

## 📞 文档反馈

如果您发现文档中的问题或有改进建议，请：
1. 提交Issue反馈问题
2. 提交Pull Request改进文档
3. 联系项目维护者

---

**最后更新**: 2025年10月31日  
**维护者**: 项目开发团队  
**版本**: 1.0.1


