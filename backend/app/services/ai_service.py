"""
DeepSeek AI服务模块
负责聊天内容的多维度分析和回复建议生成
"""

import httpx
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from app.config import settings
from app.schemas.analysis import AnalysisResult, ResponseSuggestion


class DeepSeekAIService:
    """DeepSeek AI服务类"""
    
    def __init__(self):
        """初始化AI服务"""
        self.api_key = settings.deepseek_api_key
        self.api_base = settings.deepseek_api_base
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_chat_content(
        self, 
        chat_content: str, 
        context_mode: Optional[str] = None,
        analysis_focus: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        分析聊天内容的多维度信息
        
        Args:
            chat_content: 聊天内容
            context_mode: 情景模式 (general/work/intimate/social)
            analysis_focus: 分析重点配置
            
        Returns:
            AnalysisResult: 分析结果
        """
        try:
            # 构建分析提示词
            prompt = self._build_analysis_prompt(chat_content, context_mode, analysis_focus)
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1500,  # 减少token数量，加快响应
                "temperature": 0.3
            }
            
            async with httpx.AsyncClient(timeout=90.0) as client:  # 增加超时时间
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析分析结果
                analysis_data = self._parse_analysis_response(content)
                
                logger.info(f"聊天内容分析完成")
                
                return AnalysisResult(**analysis_data)
                
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API请求失败: {e}")
            raise Exception(f"AI分析服务暂时不可用: {str(e)}")
        except Exception as e:
            logger.error(f"聊天内容分析失败: {e}")
            raise Exception(f"内容分析失败: {str(e)}")
    
    def _build_analysis_prompt(
        self, 
        chat_content: str, 
        context_mode: Optional[str] = None, 
        analysis_focus: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建分析提示词
        
        Args:
            chat_content: 聊天内容
            context_mode: 情景模式（可选）
            analysis_focus: 分析重点
            
        Returns:
            str: 构建的提示词
        """
        # 情景模式说明（如果提供了context_mode）
        context_desc = ""
        if context_mode:
            context_descriptions = {
                "general": "一般社交场景",
                "work": "职场工作场景",
                "intimate": "亲密关系场景",
                "social": "社交网络场景"
            }
            context_desc = f"场景：{context_descriptions.get(context_mode, '一般场景')}\n\n"
        
        prompt = f"""请对以下聊天内容进行多维度分析。{context_desc}

聊天内容：
{chat_content}

请按照以下JSON格式返回分析结果：
{{
    "intent": {{
        "primary": "主要意图",
        "secondary": ["次要意图1", "次要意图2"],
        "confidence": 0.9,
        "description": "意图分析说明"
    }},
    "sentiment": {{
        "overall": "positive/negative/neutral",
        "intensity": 0.8,
        "emotions": ["情绪1", "情绪2"],
        "description": "情感分析说明"
    }},
    "tone": {{
        "style": "正式/随意/幽默/严肃",
        "politeness": "礼貌/直接/委婉",
        "confidence": 0.9,
        "description": "语气分析说明"
    }},
    "relationship": {{
        "closeness": "亲密/熟悉/一般/陌生",
        "power_dynamic": "平等/上下级/主导/被动",
        "trust_level": "高/中/低",
        "description": "关系分析说明"
    }},
    "subtext": {{
        "hidden_meanings": ["潜台词1", "潜台词2"],
        "implications": ["暗示1", "暗示2"],
        "description": "潜台词分析说明"
    }},
    "key_points": [
        "关键信息点1",
        "关键信息点2",
        "关键信息点3"
    ],
    "context_analysis": {{
        "urgency": "紧急/重要/一般",
        "sensitivity": "敏感/一般/公开",
        "background": "背景信息分析",
        "description": "上下文分析说明"
    }}
}}

请确保返回有效的JSON格式。"""
        
        # 如果有分析重点，添加到提示词中
        if analysis_focus:
            focus_text = "分析重点：\n"
            for key, value in analysis_focus.items():
                focus_text += f"- {key}: {value}\n"
            prompt = focus_text + "\n" + prompt
        
        return prompt
    
    def _parse_analysis_response(self, content: str) -> Dict[str, Any]:
        """
        解析AI分析响应
        
        Args:
            content: AI返回的原始内容
            
        Returns:
            Dict: 解析后的分析数据
        """
        try:
            # 尝试直接解析JSON
            if content.strip().startswith('{'):
                return json.loads(content)
            
            # 如果内容不是纯JSON，尝试提取JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            
            # 如果无法解析JSON，返回默认结构
            logger.warning("无法解析AI分析响应为JSON，使用默认结构")
            return self._get_default_analysis_structure(content)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}，使用默认结构")
            return self._get_default_analysis_structure(content)
    
    def _get_default_analysis_structure(self, content: str) -> Dict[str, Any]:
        """
        获取默认的分析结构
        
        Args:
            content: 原始内容
            
        Returns:
            Dict: 默认分析结构
        """
        return {
            "intent": {
                "primary": "信息交流",
                "secondary": ["沟通"],
                "confidence": 0.7,
                "description": "基于内容的基本意图分析"
            },
            "sentiment": {
                "overall": "neutral",
                "intensity": 0.5,
                "emotions": ["平静"],
                "description": "情感状态分析"
            },
            "tone": {
                "style": "一般",
                "politeness": "礼貌",
                "confidence": 0.7,
                "description": "语气风格分析"
            },
            "relationship": {
                "closeness": "一般",
                "power_dynamic": "平等",
                "trust_level": "中",
                "description": "关系分析"
            },
            "subtext": {
                "hidden_meanings": [],
                "implications": [],
                "description": "潜台词分析"
            },
            "key_points": ["重要信息提取"],
            "context_analysis": {
                "urgency": "一般",
                "sensitivity": "一般",
                "background": "对话背景分析",
                "description": "上下文分析"
            }
        }
    
    async def generate_response_suggestions(
        self, 
        chat_content: str, 
        analysis_result: AnalysisResult,
        context_mode: Optional[str] = None
    ) -> List[ResponseSuggestion]:
        """
        生成回复建议
        
        Args:
            chat_content: 聊天内容
            analysis_result: 分析结果
            context_mode: 情景模式
            
        Returns:
            List[ResponseSuggestion]: 回复建议列表
        """
        try:
            prompt = self._build_suggestion_prompt(chat_content, analysis_result, context_mode)
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1200,  # 减少token数量
                "temperature": 0.7
            }
            
            async with httpx.AsyncClient(timeout=90.0) as client:  # 增加超时时间
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析回复建议
                suggestions = self._parse_suggestion_response(content)
                
                logger.info(f"回复建议生成完成，共{len(suggestions)}个建议")
                
                return suggestions
                
        except Exception as e:
            logger.error(f"回复建议生成失败: {e}")
            # 返回默认建议
            return self._get_default_suggestions()
    
    def _build_suggestion_prompt(
        self, 
        chat_content: str, 
        analysis_result: AnalysisResult,
        context_mode: Optional[str] = None
    ) -> str:
        """
        构建回复建议提示词
        
        Args:
            chat_content: 聊天内容
            analysis_result: 分析结果
            context_mode: 情景模式
            
        Returns:
            str: 构建的提示词
        """
        return f"""基于以下聊天内容和分析结果，请生成3-5个不同类型的回复建议。

聊天内容：
{chat_content}

分析结果：
- 意图：{analysis_result.intent.get('primary', '未知')}
- 情感：{analysis_result.sentiment.get('overall', '中性')}
- 语气：{analysis_result.tone.get('style', '一般')}
- 关系：{analysis_result.relationship.get('closeness', '一般')}
- 关键点：{', '.join(analysis_result.key_points[:3])}

请按照以下JSON格式返回回复建议：
[
    {{
        "type": "情感共鸣型",
        "title": "建议标题",
        "description": "建议说明",
        "examples": ["示例回复1", "示例回复2"]
    }},
    {{
        "type": "理性分析型",
        "title": "建议标题", 
        "description": "建议说明",
        "examples": ["示例回复1", "示例回复2"]
    }},
    {{
        "type": "幽默化解型",
        "title": "建议标题",
        "description": "建议说明", 
        "examples": ["示例回复1", "示例回复2"]
    }}
]

请确保返回有效的JSON格式，建议要实用且符合场景需求。"""
    
    def _parse_suggestion_response(self, content: str) -> List[ResponseSuggestion]:
        """
        解析回复建议响应
        
        Args:
            content: AI返回的原始内容
            
        Returns:
            List[ResponseSuggestion]: 解析后的建议列表
        """
        try:
            # 尝试解析JSON
            if content.strip().startswith('['):
                suggestions_data = json.loads(content)
            else:
                # 提取JSON部分
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx]
                    suggestions_data = json.loads(json_str)
                else:
                    raise ValueError("无法找到JSON数组")
            
            # 转换为ResponseSuggestion对象
            suggestions = []
            for item in suggestions_data:
                suggestion = ResponseSuggestion(
                    type=item.get("type", "通用型"),
                    title=item.get("title", "回复建议"),
                    description=item.get("description", "建议说明"),
                    examples=item.get("examples", ["示例回复"])
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.warning(f"解析回复建议失败: {e}，使用默认建议")
            return self._get_default_suggestions()
    
    def _get_default_suggestions(self) -> List[ResponseSuggestion]:
        """
        获取默认的回复建议
        
        Returns:
            List[ResponseSuggestion]: 默认建议列表
        """
        return [
            ResponseSuggestion(
                type="情感共鸣型",
                title="表达理解和共鸣",
                description="先表达对对方情感的理解，然后给出回应",
                examples=["我理解你的感受", "这确实不容易", "我也有过类似的经历"]
            ),
            ResponseSuggestion(
                type="理性分析型",
                title="客观分析问题",
                description="从理性角度分析问题，提供建设性意见",
                examples=["让我们分析一下这个问题", "从另一个角度看", "我建议我们可以"]
            ),
            ResponseSuggestion(
                type="幽默化解型",
                title="轻松幽默回应",
                description="用轻松幽默的方式回应，缓解紧张气氛",
                examples=["哈哈，这确实有点意思", "看来我们需要换个思路", "不如我们换个角度想想"]
            )
        ]


# 全局AI服务实例
ai_service = DeepSeekAIService()
