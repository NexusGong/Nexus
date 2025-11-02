# 2025-11-01 开发记录

## 今日完成

### OCR模式选择功能
- **双模式支持**：
  - 添加极速模式（百度OCR）和性能模式（豆包OCR）两种识别模式
  - 极速模式：识别速度快，等待时间短，适合快速预览
  - 性能模式：识别效果好，准确度高，等待时间较长
- **前端UI优化**：
  - 在图片预览界面添加模式选择卡片，支持用户自主选择
  - 模式选择卡片设计优化，选中状态更清晰（使用对勾图标和ring高亮）
  - 文本颜色对比度提高，确保清晰可读
  - "开始识别"按钮颜色根据选择的模式动态变化（蓝色/紫色）
- **后端API更新**：
  - 批量OCR接口添加 `mode` 参数（`fast`/`quality`）
  - 根据模式选择调用不同的OCR服务
  - 统一使用批量API，移除流式输出相关代码

### 简化OCR处理流程
- **移除流式输出**：
  - 移除了 `progressMessage`, `progressValue`, `elapsedTime` 状态
  - 移除了流式API调用 (`extractTextFromImagesStream`)
  - 简化了OCR处理逻辑，统一使用 `extractTextFromImages` API
- **简化UI**：
  - 移除了复杂的进度显示和流式更新UI
  - 简化了处理中的模态框，使用统一的动画提示
  - 简化了文本选择对话框的标题和描述

### UI细节优化
- **标签顺序调整**：
  - "已选择"标签显示在角色标签（"对方"/"己方"）左侧
  - 保持左右消息的镜像对齐效果
- **响应式布局优化**：
  - 文本选择对话框底部操作栏添加响应式布局
  - 小屏幕垂直排列，大屏幕水平排列
  - 使用 `order` 属性控制元素顺序

## 变更文件（关键）

### 前端
- `frontend/src/components/Chat/MultiImageUploader.tsx`：
  - 添加 `ocrMode` 状态管理（'fast' | 'quality'）
  - 添加模式选择UI组件（极速模式/性能模式卡片）
  - 移除流式输出相关代码和状态
  - 简化处理中的模态框
  - 简化文本选择对话框
  - 调整标签顺序和响应式布局

- `frontend/src/services/api.ts`：
  - `extractTextFromImages` 方法添加 `mode` 参数
  - 在 FormData 中传递 mode 参数

### 后端
- `backend/app/services/ocr_service.py`：
  - `extract_text_from_images` 方法添加 `mode` 参数
  - 添加 `_extract_with_baidu_ocr` 方法（极速模式）
  - 添加 `_extract_with_doubao_ocr` 方法（性能模式）
  - 根据模式选择调用不同的识别方法

- `backend/app/api/chat.py`：
  - 批量OCR接口添加 `mode` 参数（使用 `Form("fast")`）
  - 传递 mode 参数到 OCR 服务

## 验收建议
- 图片预览界面：应显示两种模式选择卡片，选中状态清晰可见
- 模式切换：选择不同模式后，"开始识别"按钮颜色应相应变化
- OCR识别：极速模式应使用百度OCR（需配置BAIDU_API_KEY），性能模式应使用豆包OCR
- 文本选择：标签顺序应为"已选择"在左，"对方"/"己方"在右
- 响应式布局：小屏幕底部操作栏应垂直排列，大屏幕水平排列

## 后续计划
- 优化OCR识别结果的准确性
- 添加识别模式的说明和提示
- 考虑添加识别历史的保存功能
- 优化性能模式的识别速度

