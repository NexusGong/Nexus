import io
import logging
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from fastapi import HTTPException
from app.models.analysis_card import AnalysisCard

logger = logging.getLogger(__name__)

class CardService:
    """卡片服务类"""
    
    def __init__(self):
        """初始化卡片服务"""
        self.default_font_size = 14
        self.title_font_size = 24
        self.subtitle_font_size = 18
    
    async def generate_card_image(self, card: AnalysisCard, user_timezone: Optional[str] = None) -> bytes:
        """
        生成分析卡片图片 - 完全匹配前端Dialog详情页面
        
        Args:
            card: 分析卡片对象
            
        Returns:
            bytes: 图片二进制数据
        """
        try:
            # 动态计算所需高度
            total_height = self._calculate_required_height(card)
            
            # 创建画布 - 匹配前端Dialog max-w-4xl 宽度
            width, height = 1200, total_height  # max-w-4xl 对应约1200px
            image = Image.new('RGB', (width, height), color='#ffffff')
            draw = ImageDraw.Draw(image)
            
            # 加载字体
            fonts = self._load_fonts()
            
            # 绘制背景
            self._draw_background(draw, width, height)
            
            # 开始绘制内容 - 匹配Dialog布局
            y_position = 60
            
            # 绘制Dialog标题区域
            y_position = self._draw_dialog_header(draw, card, fonts, width, y_position)
            
            # 绘制基本信息区域 - 匹配前端flex布局
            y_position = self._draw_basic_info_row(draw, card, fonts, width, y_position)
            
            # 绘制分析结果 - 完全匹配AnalysisResultComponent
            y_position = self._draw_analysis_component(draw, card, fonts, width, y_position)
            
            # 转换为字节
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            logger.info(f"生成卡片图片成功: {card.id}, 尺寸: {width}x{height}")
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"生成卡片图片失败: {e}")
            raise HTTPException(status_code=500, detail=f"生成图片失败: {str(e)}")
    
    def _draw_dialog_header(self, draw, card: AnalysisCard, fonts, width: int, y: int) -> int:
        """绘制Dialog标题区域 - 匹配前端DialogHeader"""
        try:
            # Dialog标题 - 匹配前端 text-xl font-bold flex items-center gap-2
            title_text = f"📄 {card.title}"
            draw.text((60, y), title_text, fill='#0f172a', font=fonts['title'])
            
            # 绘制大脑图标
            self._draw_simple_icon(draw, 30, y + 5, 'brain', 20, '#64748b')
            
            # Dialog描述 - 匹配前端DialogDescription
            desc_y = y + 40
            draw.text((60, desc_y), "分析卡片详细信息", fill='#64748b', font=fonts['small'])
            
            return desc_y + 60
        except Exception as e:
            logger.error(f"绘制Dialog标题失败: {e}")
            return y + 100
    
    def _draw_basic_info_row(self, draw, card: AnalysisCard, fonts, width: int, y: int) -> int:
        """绘制基本信息行 - 完全匹配前端flex items-center gap-4布局"""
        try:
            # 基本信息容器 - 匹配前端flex items-center gap-4 text-sm text-muted-foreground
            info_x = 60
            info_y = y
            
            # 创建时间 - 匹配前端flex items-center gap-1
            if hasattr(card, 'created_at') and card.created_at:
                created_time = card.created_at.strftime("%m月%d日 %H:%M")
                # 绘制日历图标
                self._draw_simple_icon(draw, info_x - 20, info_y - 2, 'calendar', 16, '#64748b')
                draw.text((info_x, info_y), f"创建时间: {created_time}", fill='#64748b', font=fonts['small'])
                info_x += 250  # gap-4 对应约250px间距
            
            # 导出次数 - 匹配前端flex items-center gap-1
            export_count = card.export_count or 0
            # 绘制文件图标
            self._draw_simple_icon(draw, info_x - 20, info_y - 2, 'file', 16, '#64748b')
            draw.text((info_x, info_y), f"导出次数: {export_count}", fill='#64748b', font=fonts['small'])
            info_x += 200
            
            # 情景模式 - 匹配前端Badge variant="outline" text-xs
            if card.context_mode:
                self._draw_outline_badge(draw, info_x, info_y, card.context_mode, fonts['tiny'])
            
            return info_y + 40
        except Exception as e:
            logger.error(f"绘制基本信息行失败: {e}")
            return y + 80
    
    def _draw_analysis_component(self, draw, card: AnalysisCard, fonts, width: int, y: int) -> int:
        """绘制分析结果组件 - 完全匹配前端AnalysisResultComponent"""
        try:
            if not card.analysis_data:
                return y
            
            # 分析结果卡片 - 匹配前端Card组件
            card_height = self._calculate_analysis_card_height(card.analysis_data)
            self._draw_card_container(draw, 40, y - 20, width - 40, y + card_height, '#ffffff')
            
            # 卡片标题 - 匹配前端CardTitle text-sm flex items-center gap-2
            header_y = y + 20
            # 绘制大脑图标
            self._draw_simple_icon(draw, 60, header_y - 5, 'brain', 20, '#64748b')
            draw.text((90, header_y), "AI分析结果", fill='#0f172a', font=fonts['subtitle'])
            header_y += 50
            
            analysis_data = card.analysis_data
            current_y = header_y
            
            # 意图分析 - 匹配前端折叠按钮样式
            if 'intent' in analysis_data:
                current_y = self._draw_analysis_section(draw, "意图分析", analysis_data['intent'], 
                                                     fonts, width, current_y, '#3b82f6', 'key')
            
            # 情感分析
            if 'sentiment' in analysis_data:
                current_y = self._draw_analysis_section(draw, "情感分析", analysis_data['sentiment'], 
                                                     fonts, width, current_y, '#ef4444', 'heart')
            
            # 语气分析
            if 'tone' in analysis_data:
                current_y = self._draw_analysis_section(draw, "语气分析", analysis_data['tone'], 
                                                     fonts, width, current_y, '#8b5cf6', 'message')
            
            # 关系分析
            if 'relationship' in analysis_data:
                current_y = self._draw_analysis_section(draw, "关系分析", analysis_data['relationship'], 
                                                     fonts, width, current_y, '#f59e0b', 'users')
            
            # 潜台词分析
            if 'subtext' in analysis_data:
                current_y = self._draw_analysis_section(draw, "潜台词分析", analysis_data['subtext'], 
                                                     fonts, width, current_y, '#6b7280', 'eye')
            
            # 回复建议 - 匹配前端回复建议样式
            if card.response_suggestions and len(card.response_suggestions) > 0:
                current_y = self._draw_suggestions_card(draw, card, fonts, width, current_y)
            
            return y + card_height + 40
                
        except Exception as e:
            logger.error(f"绘制分析结果组件失败: {e}")
            return y + 200
    
    def _draw_outline_badge(self, draw, x: int, y: int, text: str, font):
        """绘制outline徽章 - 匹配前端Badge variant="outline" """
        try:
            # 获取文本尺寸
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 徽章背景
            padding = 6
            badge_width = text_width + padding * 2
            badge_height = text_height + padding
            
            # 绘制outline徽章 - 白色背景，灰色边框
            draw.rectangle([x, y, x + badge_width, y + badge_height], 
                          fill='#ffffff', outline='#e2e8f0', width=1)
            
            # 绘制徽章文字
            draw.text((x + padding, y + padding // 2), text, fill='#374151', font=font)
            
            return x + badge_width + 10
        except Exception as e:
            logger.error(f"绘制outline徽章失败: {e}")
            return x + 60
    
    def _draw_simple_icon(self, draw, x: int, y: int, icon_type: str, size: int = 16, color: str = '#64748b'):
        """绘制简单图标"""
        try:
            if icon_type == 'brain':
                # 大脑图标 - 简化为两个圆形
                draw.ellipse([x, y, x + size, y + size], outline=color, width=2)
                draw.ellipse([x + size//2, y, x + size + size//2, y + size], outline=color, width=2)
            elif icon_type == 'key':
                # 钥匙图标 - 简化为圆形和线条
                draw.ellipse([x + size//4, y + size//4, x + size*3//4, y + size*3//4], outline=color, width=2)
                draw.line([x + size*3//4, y + size//2, x + size, y + size//2], fill=color, width=2)
            elif icon_type == 'heart':
                # 心形图标 - 简化为两个圆形
                draw.ellipse([x + size//4, y + size//4, x + size*3//4, y + size*3//4], outline=color, width=2)
                draw.ellipse([x + size//2, y + size//4, x + size, y + size*3//4], outline=color, width=2)
            elif icon_type == 'message':
                # 消息图标 - 简化为矩形和三角形
                draw.rectangle([x, y + size//4, x + size, y + size*3//4], outline=color, width=2)
                draw.polygon([(x + size//4, y + size*3//4), (x + size*3//4, y + size*3//4), (x + size//2, y + size)], outline=color, width=2)
            elif icon_type == 'users':
                # 用户图标 - 简化为两个圆形
                draw.ellipse([x, y + size//4, x + size//2, y + size*3//4], outline=color, width=2)
                draw.ellipse([x + size//2, y + size//4, x + size, y + size*3//4], outline=color, width=2)
            elif icon_type == 'eye':
                # 眼睛图标 - 简化为椭圆
                draw.ellipse([x, y + size//4, x + size, y + size*3//4], outline=color, width=2)
                draw.ellipse([x + size//4, y + size//2, x + size*3//4, y + size//2], fill=color)
            elif icon_type == 'lightbulb':
                # 灯泡图标 - 简化为圆形和矩形
                draw.ellipse([x + size//4, y, x + size*3//4, y + size*3//4], outline=color, width=2)
                draw.rectangle([x + size//3, y + size*3//4, x + size*2//3, y + size], outline=color, width=2)
            elif icon_type == 'calendar':
                # 日历图标 - 简化为矩形和线条
                draw.rectangle([x, y + size//4, x + size, y + size], outline=color, width=2)
                draw.line([x, y + size//2, x + size, y + size//2], fill=color, width=2)
                draw.line([x + size//2, y + size//4, x + size//2, y + size//2], fill=color, width=2)
            elif icon_type == 'file':
                # 文件图标 - 简化为矩形和三角形
                draw.rectangle([x + size//4, y + size//4, x + size, y + size], outline=color, width=2)
                draw.polygon([(x, y), (x + size//4, y), (x + size//4, y + size//4)], outline=color, width=2)
            elif icon_type == 'copy':
                # 复制图标 - 简化为两个重叠的矩形
                draw.rectangle([x, y + size//4, x + size*3//4, y + size], outline=color, width=2)
                draw.rectangle([x + size//4, y, x + size, y + size*3//4], outline=color, width=2)
        except Exception as e:
            logger.error(f"绘制图标失败: {e}")
    
    def _draw_card_container(self, draw, x1: int, y1: int, x2: int, y2: int, fill: str = '#ffffff'):
        """绘制卡片容器 - 匹配前端Card组件"""
        try:
            # 绘制阴影
            shadow_offset = 2
            shadow_color = (0, 0, 0, 10)
            draw.rectangle([x1 + shadow_offset, y1 + shadow_offset, 
                           x2 + shadow_offset, y2 + shadow_offset], 
                          fill=shadow_color)
            
            # 绘制卡片主体
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline='#e2e8f0', width=1)
            
            # 绘制圆角效果（通过绘制小圆角）
            corner_radius = 8
            # 左上角
            draw.ellipse([x1, y1, x1 + corner_radius*2, y1 + corner_radius*2], fill=fill)
            # 右上角
            draw.ellipse([x2 - corner_radius*2, y1, x2, y1 + corner_radius*2], fill=fill)
            # 左下角
            draw.ellipse([x1, y2 - corner_radius*2, x1 + corner_radius*2, y2], fill=fill)
            # 右下角
            draw.ellipse([x2 - corner_radius*2, y2 - corner_radius*2, x2, y2], fill=fill)
            
        except Exception as e:
            logger.error(f"绘制卡片容器失败: {e}")
            # 降级到简单矩形
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline='#e2e8f0', width=1)
    
    def _draw_analysis_section(self, draw, title: str, data: dict, fonts, width: int, y: int, color: str, icon_type: str = None) -> int:
        """绘制分析项 - 完全匹配前端展开状态"""
        try:
            # 分析项标题行 - 匹配前端Button variant="ghost" flex items-center gap-2
            title_x = 60
            if icon_type:
                # 绘制图标
                self._draw_simple_icon(draw, title_x - 20, y + 5, icon_type, 16, '#64748b')
                title_x = 80
            draw.text((title_x, y + 10), title, fill='#0f172a', font=fonts['text'])
            
            # 主要信息徽章 - 匹配前端Badge样式
            badge_y = y + 10
            badge_x = 200
            
            if 'primary' in data:
                badge_x = self._draw_colored_badge(draw, badge_x, badge_y, data['primary'], color, fonts['tiny'])
            elif 'overall' in data:
                badge_x = self._draw_colored_badge(draw, badge_x, badge_y, data['overall'], color, fonts['tiny'])
            elif 'style' in data:
                badge_x = self._draw_colored_badge(draw, badge_x, badge_y, data['style'], color, fonts['tiny'])
            elif 'closeness' in data:
                badge_x = self._draw_colored_badge(draw, badge_x, badge_y, data['closeness'], color, fonts['tiny'])
            
            # 展开内容区域 - 匹配前端mt-2 p-3 bg-muted/30 rounded-md
            content_y = y + 50
            
            # 描述内容 - 完整显示，不折叠
            if data.get('description'):
                desc_lines = self._wrap_text(data['description'], width - 120, fonts['small'])
                for line in desc_lines:  # 显示所有行，不限制
                    draw.text((60, content_y), line, fill='#64748b', font=fonts['small'])
                    content_y += 25
                content_y += 10  # mb-2
            
            # 次要信息徽章 - 完整显示，不折叠
            badge_start_x = 60
            if 'secondary' in data and data['secondary']:
                for secondary_item in data['secondary']:  # 显示所有次要信息
                    badge_start_x = self._draw_secondary_badge(draw, badge_start_x, content_y, secondary_item, fonts['tiny'])
                    badge_start_x += 10  # gap-1
                content_y += 30
            elif 'emotions' in data and data['emotions']:
                for emotion in data['emotions']:  # 显示所有情感
                    badge_start_x = self._draw_secondary_badge(draw, badge_start_x, content_y, emotion, fonts['tiny'])
                    badge_start_x += 10  # gap-1
                content_y += 30
            
            # 置信度/强度信息 - 匹配前端text-xs text-muted-foreground
            if 'confidence' in data:
                confidence_percent = int(data['confidence'] * 100) if data['confidence'] else 0
                draw.text((60, content_y), f"置信度: {confidence_percent}%", fill='#64748b', font=fonts['tiny'])
                content_y += 20
            
            if 'intensity' in data:
                intensity_percent = int(data['intensity'] * 100) if data['intensity'] else 0
                draw.text((60, content_y), f"强度: {intensity_percent}%", fill='#64748b', font=fonts['tiny'])
                content_y += 20
            
            # 特殊处理：语气分析的额外信息
            if 'politeness' in data:
                politeness = data['politeness']
                draw.text((60, content_y), f"礼貌程度: {politeness}", fill='#64748b', font=fonts['tiny'])
                content_y += 20
            
            # 特殊处理：关系分析的额外信息
            if 'power_dynamic' in data:
                power = data['power_dynamic']
                draw.text((60, content_y), f"权力关系: {power}", fill='#64748b', font=fonts['tiny'])
                content_y += 20
            if 'trust_level' in data:
                trust = data['trust_level']
                draw.text((60, content_y), f"信任度: {trust}", fill='#64748b', font=fonts['tiny'])
                content_y += 20
            
            # 特殊处理：潜台词分析的复杂结构 - 完整显示，不折叠
            if 'subtext' in data:
                if 'hidden_meanings' in data:
                    draw.text((60, content_y), "隐含含义:", fill='#64748b', font=fonts['tiny'])
                    content_y += 20
                    for meaning in data['hidden_meanings']:  # 显示所有隐含含义
                        self._draw_secondary_badge(draw, 60, content_y, meaning, fonts['tiny'])
                        content_y += 25
                
                if 'implications' in data:
                    draw.text((60, content_y), "潜在影响:", fill='#64748b', font=fonts['tiny'])
                    content_y += 20
                    for impact in data['implications']:  # 显示所有潜在影响
                        self._draw_outline_badge(draw, 60, content_y, impact, fonts['tiny'])
                        content_y += 25
            
            return content_y + 20
        except Exception as e:
            logger.error(f"绘制分析项失败: {e}")
            return y + 140
    
    def _draw_colored_badge(self, draw, x: int, y: int, text: str, color: str, font):
        """绘制彩色徽章 - 匹配前端Badge样式"""
        try:
            # 获取文本尺寸
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 徽章背景
            padding = 8
            badge_width = text_width + padding * 2
            badge_height = text_height + padding
            
            # 绘制圆角徽章背景
            corner_radius = 12
            # 绘制主矩形
            draw.rectangle([x, y, x + badge_width, y + badge_height], 
                          fill=color, outline=color)
            
            # 绘制圆角效果
            draw.ellipse([x, y, x + corner_radius, y + corner_radius], fill=color)
            draw.ellipse([x + badge_width - corner_radius, y, x + badge_width, y + corner_radius], fill=color)
            draw.ellipse([x, y + badge_height - corner_radius, x + corner_radius, y + badge_height], fill=color)
            draw.ellipse([x + badge_width - corner_radius, y + badge_height - corner_radius, x + badge_width, y + badge_height], fill=color)
            
            # 绘制徽章文字
            draw.text((x + padding, y + padding // 2), text, fill='#ffffff', font=font)
            
            return x + badge_width + 10
        except Exception as e:
            logger.error(f"绘制彩色徽章失败: {e}")
            return x + 60
    
    def _draw_secondary_badge(self, draw, x: int, y: int, text: str, font):
        """绘制次要徽章 - 匹配前端Badge variant="secondary" """
        try:
            # 获取文本尺寸
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 徽章背景
            padding = 6
            badge_width = text_width + padding * 2
            badge_height = text_height + padding
            
            # 绘制圆角次要徽章 - 匹配前端bg-secondary text-secondary-foreground
            corner_radius = 10
            draw.rectangle([x, y, x + badge_width, y + badge_height], 
                          fill='#f1f5f9', outline='#e2e8f0', width=1)
            
            # 绘制圆角效果
            draw.ellipse([x, y, x + corner_radius, y + corner_radius], fill='#f1f5f9')
            draw.ellipse([x + badge_width - corner_radius, y, x + badge_width, y + corner_radius], fill='#f1f5f9')
            draw.ellipse([x, y + badge_height - corner_radius, x + corner_radius, y + badge_height], fill='#f1f5f9')
            draw.ellipse([x + badge_width - corner_radius, y + badge_height - corner_radius, x + badge_width, y + badge_height], fill='#f1f5f9')
            
            # 绘制徽章文字
            draw.text((x + padding, y + padding // 2), text, fill='#475569', font=font)
            
            return x + badge_width + 10
        except Exception as e:
            logger.error(f"绘制次要徽章失败: {e}")
            return x + 60
    
    def _draw_suggestions_card(self, draw, card: AnalysisCard, fonts, width: int, y: int) -> int:
        """绘制回复建议卡片 - 完全匹配前端回复建议样式"""
        try:
            if not card.response_suggestions or len(card.response_suggestions) == 0:
                return y
            
            # 回复建议卡片 - 匹配前端Card组件
            suggestions_height = len(card.response_suggestions) * 200 + 100
            self._draw_card_container(draw, 40, y - 20, width - 40, y + suggestions_height, '#ffffff')
            
            # 卡片标题 - 匹配前端CardTitle text-sm flex items-center gap-2
            header_y = y + 20
            # 绘制灯泡图标
            self._draw_simple_icon(draw, 60, header_y - 5, 'lightbulb', 20, '#64748b')
            draw.text((90, header_y), "智能回复建议", fill='#0f172a', font=fonts['subtitle'])
            header_y += 30
            
            # 卡片描述 - 匹配前端CardDescription text-xs text-muted-foreground
            draw.text((60, header_y), "基于分析结果生成的回复建议，点击复制使用", fill='#64748b', font=fonts['tiny'])
            header_y += 50
            
            current_y = header_y
            
            for i, suggestion in enumerate(card.response_suggestions):
                # 建议项容器 - 匹配前端p-3 border rounded-md hover:bg-muted/30
                suggestion_height = 180
                self._draw_suggestion_item(draw, 60, current_y - 10, width - 100, current_y + suggestion_height, '#ffffff')
                
                # 建议标题和类型徽章 - 匹配前端flex items-start justify-between mb-2
                suggestion_title = suggestion.get('title', f'建议 {i+1}')
                suggestion_type = suggestion.get('type', '通用')
                
                # 类型徽章 - 匹配前端Badge variant="outline" text-xs mb-1
                self._draw_outline_badge(draw, 70, current_y + 10, suggestion_type, fonts['tiny'])
                
                # 建议标题 - 匹配前端text-sm font-medium
                draw.text((70, current_y + 40), suggestion_title, fill='#0f172a', font=fonts['text'])
                
                # 复制按钮 - 匹配前端button copy图标
                copy_button_x = width - 120
                copy_button_y = current_y + 10
                self._draw_simple_icon(draw, copy_button_x, copy_button_y, 'copy', 16, '#64748b')
                # 绘制复制按钮边框
                draw.rectangle([copy_button_x - 2, copy_button_y - 2, copy_button_x + 18, copy_button_y + 18], 
                              outline='#e2e8f0', width=1)
                
                # 建议描述 - 完整显示，不折叠
                if suggestion.get('description'):
                    desc_lines = self._wrap_text(suggestion['description'], width - 140, fonts['tiny'])
                    for line in desc_lines:  # 显示所有行，不限制
                        draw.text((70, current_y + 70), line, fill='#64748b', font=fonts['tiny'])
                        current_y += 20
                    current_y += 10  # mb-2
                
                # 示例回复 - 完整显示，不折叠
                if suggestion.get('examples') and suggestion['examples']:
                    for j, example in enumerate(suggestion['examples']):  # 显示所有示例
                        # 匹配前端text-xs bg-muted/50 p-2 rounded
                        example_lines = self._wrap_text(f'"{example}"', width - 140, fonts['tiny'])
                        for line in example_lines:  # 每个示例显示所有行
                            draw.text((70, current_y + 10), line, fill='#374151', font=fonts['tiny'])
                            current_y += 20
                        current_y += 5  # space-y-1
                
                current_y += suggestion_height + 20
            
            return y + suggestions_height + 40
        except Exception as e:
            logger.error(f"绘制回复建议卡片失败: {e}")
            return y + 200
    
    def _draw_suggestion_item(self, draw, x1: int, y1: int, x2: int, y2: int, fill: str = '#ffffff'):
        """绘制建议项容器 - 匹配前端border rounded-md"""
        try:
            # 绘制圆角边框
            corner_radius = 6
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline='#e2e8f0', width=1)
            
            # 绘制圆角效果
            draw.ellipse([x1, y1, x1 + corner_radius, y1 + corner_radius], fill=fill)
            draw.ellipse([x2 - corner_radius, y1, x2, y1 + corner_radius], fill=fill)
            draw.ellipse([x1, y2 - corner_radius, x1 + corner_radius, y2], fill=fill)
            draw.ellipse([x2 - corner_radius, y2 - corner_radius, x2, y2], fill=fill)
        except Exception as e:
            logger.error(f"绘制建议项容器失败: {e}")
    
    def _calculate_analysis_card_height(self, analysis_data: dict) -> int:
        """计算分析结果卡片高度"""
        try:
            base_height = 100  # 标题和间距
            
            for key in ['intent', 'sentiment', 'tone', 'relationship', 'subtext']:
                if key in analysis_data:
                    base_height += 120  # 每个分析项120像素
            
            # 回复建议高度
            if 'response_suggestions' in analysis_data:
                suggestions_count = len(analysis_data['response_suggestions']) if analysis_data['response_suggestions'] else 0
                base_height += suggestions_count * 180 + 100
            
            return base_height
        except Exception as e:
            logger.error(f"计算分析卡片高度失败: {e}")
            return 200
    
    def _calculate_required_height(self, card: AnalysisCard) -> int:
        """计算所需图片高度"""
        try:
            base_height = 200  # 基础高度（标题、基本信息等）
            
            # 分析数据高度
            if card.analysis_data:
                analysis_height = self._calculate_analysis_card_height(card.analysis_data)
                base_height += analysis_height
            
            # 回复建议高度
            if card.response_suggestions:
                suggestions_height = len(card.response_suggestions) * 200 + 100
                base_height += suggestions_height
            
            return max(base_height, 800)  # 最小高度800px
        except Exception as e:
            logger.error(f"计算图片高度失败: {e}")
            return 1000
    
    def _load_fonts(self):
        """加载字体"""
        try:
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",  # macOS 中文字体
                "/System/Library/Fonts/STHeiti Light.ttc",  # macOS 中文字体
                "/System/Library/Fonts/Arial Unicode MS.ttf",  # macOS Unicode字体
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux 中文字体
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "arial.ttf",  # Windows
                "Arial.ttf"   # Windows
            ]
            
            fonts = {}
            font_sizes = {
                'title': 24,      # 标题字体
                'subtitle': 18,   # 副标题字体
                'text': 16,       # 正文字体
                'small': 14,      # 小字体
                'tiny': 12        # 超小字体
            }
            
            for font_path in font_paths:
                try:
                    fonts = {
                        'title': ImageFont.truetype(font_path, font_sizes['title']),
                        'subtitle': ImageFont.truetype(font_path, font_sizes['subtitle']),
                        'text': ImageFont.truetype(font_path, font_sizes['text']),
                        'small': ImageFont.truetype(font_path, font_sizes['small']),
                        'tiny': ImageFont.truetype(font_path, font_sizes['tiny'])
                    }
                    logger.info(f"成功加载字体: {font_path}")
                    break
                except:
                    continue
            
            if not fonts:
                logger.warning("无法加载系统字体，使用默认字体")
                fonts = {
                    'title': ImageFont.load_default(),
                    'subtitle': ImageFont.load_default(),
                    'text': ImageFont.load_default(),
                    'small': ImageFont.load_default(),
                    'tiny': ImageFont.load_default()
                }
            
            return fonts
        except Exception as e:
            logger.error(f"字体加载失败: {e}")
            return {
                'title': ImageFont.load_default(),
                'subtitle': ImageFont.load_default(),
                'text': ImageFont.load_default(),
                'small': ImageFont.load_default(),
                'tiny': ImageFont.load_default()
            }
    
    def _draw_background(self, draw, width: int, height: int):
        """绘制背景"""
        try:
            # 绘制白色背景
            draw.rectangle([0, 0, width, height], fill='#ffffff')
        except Exception as e:
            logger.error(f"绘制背景失败: {e}")
    
    def _wrap_text(self, text: str, max_width: int, font) -> list:
        """文本换行"""
        try:
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        except Exception as e:
            logger.error(f"文本换行失败: {e}")
            return [text]
    
    async def generate_card_pdf(self, card: AnalysisCard, user_timezone: Optional[str] = None) -> bytes:
        """
        生成分析卡片PDF
        
        Args:
            card: 分析卡片对象
            
        Returns:
            bytes: PDF二进制数据
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            # 自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                alignment=1  # 居中
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=10,
                textColor=colors.darkblue
            )
            
            content_style = ParagraphStyle(
                'CustomContent',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )
            
            story = []
            
            # 标题
            story.append(Paragraph(f"📄 {card.title}", title_style))
            story.append(Spacer(1, 20))
            
            # 基本信息
            story.append(Paragraph("📋 基本信息", subtitle_style))
            
            basic_info = []
            if hasattr(card, 'created_at') and card.created_at:
                created_time = card.created_at.strftime("%Y年%m月%d日 %H:%M")
                basic_info.append(['创建时间', created_time])
            
            export_count = card.export_count or 0
            basic_info.append(['导出次数', str(export_count)])
            
            if card.context_mode:
                basic_info.append(['情景模式', card.context_mode])
            
            if basic_info:
                basic_table = Table(basic_info, colWidths=[2*inch, 4*inch])
                basic_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(basic_table)
            story.append(Spacer(1, 20))
            
            # 分析结果
            if card.analysis_data:
                story.append(Paragraph("🧠 AI分析结果", subtitle_style))
                
                analysis_data = card.analysis_data
                
                # 创建分析结果表格
                analysis_table_data = []
                
                if 'intent' in analysis_data:
                    intent = analysis_data['intent']
                    analysis_table_data.append(['意图分析', intent.get('primary', '未知')])
                
                if 'sentiment' in analysis_data:
                    sentiment = analysis_data['sentiment']
                    analysis_table_data.append(['情感分析', sentiment.get('overall', '中性')])
                
                if 'tone' in analysis_data:
                    tone = analysis_data['tone']
                    analysis_table_data.append(['语气分析', tone.get('style', '一般')])
                
                if 'relationship' in analysis_data:
                    relationship = analysis_data['relationship']
                    analysis_table_data.append(['关系分析', relationship.get('closeness', '一般')])
                
                if analysis_table_data:
                    analysis_table = Table(analysis_table_data, colWidths=[2*inch, 4*inch])
                    analysis_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(analysis_table)
                    story.append(Spacer(1, 20))
            
            # 回复建议
            if card.response_suggestions and len(card.response_suggestions) > 0:
                story.append(Paragraph("💡 智能回复建议", subtitle_style))
                
                for i, suggestion in enumerate(card.response_suggestions[:3]):  # 最多显示3个建议
                    suggestion_title = suggestion.get('title', f'建议 {i+1}')
                    suggestion_type = suggestion.get('type', '通用')
                    
                    story.append(Paragraph(f"<b>{suggestion_type}: {suggestion_title}</b>", content_style))
                    
                    if suggestion.get('description'):
                        story.append(Paragraph(suggestion['description'], content_style))
                    
                    if suggestion.get('examples') and suggestion['examples']:
                        example = suggestion['examples'][0]
                        story.append(Paragraph(f'示例: "{example}"', content_style))
                    
                    story.append(Spacer(1, 10))
            
            # 构建PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info(f"生成卡片PDF成功: {card.id}")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"生成卡片PDF失败: {e}")
            raise HTTPException(status_code=500, detail=f"生成PDF失败: {str(e)}")

# 创建服务实例
card_service = CardService()