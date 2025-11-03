"""
OCR服务模块（火山引擎OCR + 豆包图片理解）
负责图片文字识别和聊天内容提取
"""

import base64
from typing import Dict, Any, Optional, List
import os
import re
import httpx
from loguru import logger
from app.config import settings
from app.schemas.analysis import OCRResponse
import json as _json
import hashlib
import time

# 火山引擎SDK
try:
    from volcengine.visual.VisualService import VisualService
    from volcengine.base.Service import Service
except ImportError:
    VisualService = None
    Service = None
    logger.warning("火山引擎SDK未安装，请运行: pip install volcengine")


class DoubaoOCRService:
    """OCR服务类（火山引擎OCR + 豆包图片理解）"""
    
    def __init__(self):
        """初始化OCR服务"""
        # 火山引擎OCR配置
        self.volc_access_key_id = settings.volc_access_key_id
        self.volc_secret_access_key = settings.volc_secret_access_key
        self.volc_region = settings.volc_region
        
        # 检查配置和环境
        has_visual_service = VisualService is not None
        has_access_key = bool(self.volc_access_key_id and self.volc_access_key_id.strip())
        has_secret_key = bool(self.volc_secret_access_key and self.volc_secret_access_key.strip())
        
        # 详细日志输出（但不输出完整的密钥值）
        access_key_preview = self.volc_access_key_id[:10] + "..." if has_access_key else "EMPTY"
        secret_key_preview = "***" if has_secret_key else "EMPTY"
        logger.info(f"[OCR][volc] 配置检查: VisualService={has_visual_service}, AccessKey={access_key_preview}, SecretKey={secret_key_preview}, Region={self.volc_region}, AccessKey长度={len(self.volc_access_key_id) if self.volc_access_key_id else 0}, SecretKey长度={len(self.volc_secret_access_key) if self.volc_secret_access_key else 0}")
        
        self.use_volc_ocr = has_access_key and has_secret_key and has_visual_service
        
        # 初始化火山引擎视觉服务
        self.volc_visual_service = None
        if self.use_volc_ocr and VisualService:
            try:
                self.volc_visual_service = VisualService()
                
                # 检查并调用配置方法
                if hasattr(self.volc_visual_service, 'set_ak'):
                    self.volc_visual_service.set_ak(self.volc_access_key_id)
                else:
                    # 如果set_ak不存在，尝试其他方法
                    logger.warning("[OCR][volc] VisualService没有set_ak方法，尝试其他配置方式")
                
                if hasattr(self.volc_visual_service, 'set_sk'):
                    self.volc_visual_service.set_sk(self.volc_secret_access_key)
                
                if hasattr(self.volc_visual_service, 'set_region'):
                    self.volc_visual_service.set_region(self.volc_region)
                
                logger.info("[OCR][volc] 火山引擎OCR服务初始化成功")
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                logger.error(f"[OCR][volc] 火山引擎OCR服务初始化失败: {e}")
                logger.error(f"[OCR][volc] 错误详情: {error_detail}")
                self.use_volc_ocr = False
        elif not has_visual_service:
            logger.warning("[OCR][volc] 火山引擎SDK未安装，请运行: pip install volcengine")
        elif not has_access_key or not has_secret_key:
            logger.warning(f"[OCR][volc] 火山引擎OCR未配置，请在.env文件中设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY")
        
        # 豆包API配置（用于结构化辅助或备用）
        self.api_key = os.getenv("ARK_API_KEY") or settings.doubao_api_key
        self.api_url = settings.doubao_api_url
        self.model = settings.doubao_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _volc_ocr_recognition_raw(self, image_data: bytes) -> Dict[str, Any]:
        """
        调用火山引擎OCR API进行识别（通用文字识别服务）
        使用官方SDK进行调用，无需手动签名
        
        返回火山引擎原始格式数据，不进行格式转换
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            Dict: 火山引擎OCR原始识别结果，包含line_texts, line_rects, line_probs等
        """
        try:
            if not self.use_volc_ocr or not self.volc_visual_service:
                raise Exception("未配置火山引擎OCR，请在.env文件中设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY")
            
            # 获取图片尺寸（用于坐标转换）
            image_width = 0
            image_height = 0
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(image_data))
                image_width, image_height = img.size
            except Exception:
                # 如果无法获取图片尺寸，使用默认值
                pass
            
            # 将图片转为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 准备请求参数（根据火山引擎API文档）
            params = {
                "image_base64": image_base64
            }
            
            # 使用SDK调用OCRNormal接口
            # OCRNormal接口：Action=OCRNormal, Version=2020-08-26
            # SDK可能是同步的，需要在线程池中运行
            import asyncio
            
            # 尝试使用SDK的不同方法
            # 方法1: 尝试使用request方法（如果有）
            # 方法2: 尝试使用ocr_normal或ocr_general方法
            loop = asyncio.get_event_loop()
            
            def call_ocr():
                # 首先尝试使用ocr_normal或ocr_general方法（推荐方式）
                if hasattr(self.volc_visual_service, 'ocr_normal'):
                    return self.volc_visual_service.ocr_normal(params)
                elif hasattr(self.volc_visual_service, 'ocr_general'):
                    return self.volc_visual_service.ocr_general(params)
                # 否则尝试使用request方法（需要正确的参数格式：action, version, data）
                elif hasattr(self.volc_visual_service, 'request'):
                    action = "OCRNormal"
                    version = "2020-08-26"
                    data = params  # data参数包含image_base64
                    # request方法格式：request(action, version, data)
                    return self.volc_visual_service.request(action, version, data)
                else:
                    raise Exception("火山引擎SDK未找到可用的OCR方法，请检查SDK版本")
            
            result = await loop.run_in_executor(None, call_ocr)
            
            # 检查错误（火山引擎SDK返回格式）
            if "ResponseMetadata" in result:
                response_metadata = result.get("ResponseMetadata", {})
                if response_metadata.get("Error"):
                    error_info = response_metadata["Error"]
                    error_msg = error_info.get("Message", "未知错误")
                    error_code = error_info.get("Code", "Unknown")
                    raise Exception(f"火山引擎OCR识别失败 [{error_code}]: {error_msg}")
            
            # 提取数据（火山引擎SDK返回格式：Result包含实际数据）
            if "Result" in result:
                # SDK返回格式：{"ResponseMetadata": {...}, "Result": {...}}
                volc_result = {
                    "code": 10000,
                    "data": result["Result"],
                    "message": "Success"
                }
            elif "data" in result and result.get("code") == 10000:
                # 兼容直接返回data的情况（原始API格式）
                volc_result = result
            else:
                # 其他情况，尝试将整个结果作为data
                volc_result = {
                    "code": 10000,
                    "data": result,
                    "message": "Success"
                }
            
            # 返回火山引擎原始格式，包含图片尺寸信息
            volc_result["_image_info"] = {
                "width": image_width,
                "height": image_height
            }
            return volc_result
                
        except Exception as e:
            logger.error(f"火山引擎OCR调用失败: {e}")
            raise Exception(f"火山引擎OCR识别失败: {str(e)}")
    
    async def _volc_ocr_recognition(self, image_data: bytes) -> Dict[str, Any]:
        """
        调用火山引擎OCR API进行识别（通用文字识别服务）
        使用官方SDK进行调用，无需手动签名
        
        保留此方法以兼容旧代码，内部调用_volc_ocr_recognition_raw
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            Dict: OCR识别结果（转换为百度OCR格式以便后续处理）
        """
        raw_result = await self._volc_ocr_recognition_raw(image_data)
        image_info = raw_result.pop("_image_info", {})
        return self._convert_volc_to_baidu_format(raw_result, image_info.get("width", 0), image_info.get("height", 0))
    
    def _convert_volc_to_baidu_format(self, volc_result: Dict[str, Any], image_width: int = 0, image_height: int = 0) -> Dict[str, Any]:
        """
        将火山引擎OCR结果转换为百度OCR格式，以便统一处理
        
        火山引擎OCR返回格式：
        {
            "code": 10000,
            "data": {
                "line_texts": ["文本1", "文本2", ...],
                "line_rects": [{"x": 1, "y": 2, "width": 100, "height": 20}, ...],
                "line_probs": [0.9, 0.95, ...],
                "chars": [[CharInfo, ...], ...],
                "polygons": [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ...]
            }
        }
        
        Args:
            volc_result: 火山引擎OCR返回的原始结果
            
        Returns:
            Dict: 转换为百度OCR格式的结果
        """
        data = volc_result.get("data", {})
        if not data:
            # 如果data为空，尝试直接使用result
            data = volc_result if isinstance(volc_result, dict) else {}
        
        line_texts = data.get("line_texts", [])
        line_rects = data.get("line_rects", [])
        line_probs = data.get("line_probs", [])
        chars = data.get("chars", [])
        polygons = data.get("polygons", [])
        
        # 转换为百度OCR格式：words_result数组
        words_result = []
        
        # 检测坐标类型：如果第一个rect的x/y是float且小于1或小于图片尺寸，可能是相对坐标（PDF）
        is_relative_coords = False
        if line_rects and len(line_rects) > 0:
            first_rect = line_rects[0]
            if isinstance(first_rect, dict):
                x_val = first_rect.get("x", 0)
                y_val = first_rect.get("y", 0)
                # 相对坐标判断：
                # 1. 如果x/y是float且在0-1之间，是百分比格式
                # 2. 如果x/y是float且小于1000，且图片尺寸已知，可能是相对坐标
                if isinstance(x_val, float) and isinstance(y_val, float):
                    if 0 <= x_val <= 1 and 0 <= y_val <= 1:
                        # 百分比格式（0-1）
                        is_relative_coords = True
                    elif image_width > 0 and image_height > 0:
                        # 如果坐标值远小于图片尺寸，可能是百分比（0-100）
                        if x_val < image_width * 0.1 and y_val < image_height * 0.1:
                            # 检查是否所有坐标都很小，可能是百分比格式
                            is_relative_coords = True
                        # 如果坐标是float但大于图片尺寸，可能是百分比（0-100）
                        elif x_val <= 100 and y_val <= 100:
                            is_relative_coords = True
        
        logger.debug(f"[OCR][volc][convert] 检测到坐标类型: {'相对坐标(PDF)' if is_relative_coords else '绝对坐标(图片)'}, 行数={len(line_texts)}, 图片尺寸=({image_width}x{image_height})")
        
        for i, text in enumerate(line_texts):
            if not text or not text.strip():
                continue
            
            # 获取位置信息
            rect = line_rects[i] if i < len(line_rects) else {}
            prob = line_probs[i] if i < len(line_probs) else 0.9
            
            if not isinstance(rect, dict):
                # 如果rect不是字典，尝试从polygons获取
                if i < len(polygons) and polygons[i]:
                    polygon = polygons[i]
                    if isinstance(polygon, list) and len(polygon) >= 4:
                        # 从多边形计算边界框
                        xs = [p[0] for p in polygon if len(p) >= 2]
                        ys = [p[1] for p in polygon if len(p) >= 2]
                        if xs and ys:
                            x = min(xs)
                            y = min(ys)
                            width = max(xs) - x
                            height = max(ys) - y
                        else:
                            continue
                    else:
                        continue
                else:
                    # 无法获取位置信息，跳过
                    logger.warning(f"[OCR][volc][convert] 行 {i} 缺少位置信息，跳过")
                    continue
            else:
                # 从rect获取坐标
                x = rect.get("x", 0)
                y = rect.get("y", 0)
                width = rect.get("width", 0)
                height = rect.get("height", 0)
            
            # 处理坐标类型
            if is_relative_coords:
                # 相对坐标（PDF格式），需要转换为绝对坐标
                # 根据实际图片尺寸转换
                if image_width > 0 and image_height > 0:
                    # 有图片尺寸，根据实际尺寸转换
                    if 0 <= x <= 1 and 0 <= y <= 1:
                        # 百分比格式（0-1），转换为像素
                        x = int(x * image_width)
                        y = int(y * image_height)
                        width = int(width * image_width) if isinstance(width, (int, float)) else int(width)
                        height = int(height * image_height) if isinstance(height, (int, float)) else int(height)
                    elif x <= 100 and y <= 100:
                        # 百分比格式（0-100），转换为像素
                        x = int((x / 100.0) * image_width)
                        y = int((y / 100.0) * image_height)
                        width = int((width / 100.0) * image_width) if isinstance(width, (int, float)) else int(width)
                        height = int((height / 100.0) * image_height) if isinstance(height, (int, float)) else int(height)
                    else:
                        # 其他情况，直接转换为int
                        x = int(x)
                        y = int(y)
                        width = int(width) if isinstance(width, (int, float)) else int(width)
                        height = int(height) if isinstance(height, (int, float)) else int(height)
                else:
                    # 没有图片尺寸，使用假设的尺寸（标准截图尺寸）
                    assumed_width = 1080  # 常见截图宽度
                    assumed_height = 1920  # 常见截图高度
                    if 0 <= x <= 1 and 0 <= y <= 1:
                        x = int(x * assumed_width)
                        y = int(y * assumed_height)
                        width = int(width * assumed_width) if isinstance(width, (int, float)) else int(width)
                        height = int(height * assumed_height) if isinstance(height, (int, float)) else int(height)
                    else:
                        # 直接转换为int
                        x = int(x)
                    y = int(y)
                    width = int(width) if isinstance(width, (int, float)) else 0
                    height = int(height) if isinstance(height, (int, float)) else 0
            else:
                # 绝对坐标（图片格式），直接转换为int
                x = int(x) if isinstance(x, (int, float)) else 0
                y = int(y) if isinstance(y, (int, float)) else 0
                width = int(width) if isinstance(width, (int, float)) else 0
                height = int(height) if isinstance(height, (int, float)) else 0
            
            # 验证坐标有效性
            if width <= 0 or height <= 0:
                logger.debug(f"[OCR][volc][convert] 行 {i} 坐标无效 (width={width}, height={height})，跳过")
                continue
            
            # 确保概率值是有效的
            if not isinstance(prob, (int, float)) or prob < 0 or prob > 1:
                # 如果概率不在0-1范围，可能是百分比形式（0-100），需要转换
                if isinstance(prob, (int, float)) and prob > 1:
                    prob = prob / 100.0 if prob <= 100 else 0.9
                else:
                    prob = 0.9
            
            # 百度OCR格式
            word_info = {
                "words": text.strip(),
                "location": {
                    "left": x,
                    "top": y,
                    "width": width,
                    "height": height
                },
                "probability": {
                    "variance": 0,
                    "average": prob,
                    "min": prob
                }
            }
            words_result.append(word_info)
        
        logger.info(f"[OCR][volc][convert] 转换完成: {len(words_result)} 个文字块，原始行数={len(line_texts)}")
        
        # 返回百度OCR格式的结果
        return {
            "words_result": words_result,
            "words_result_num": len(words_result),
            "language": "CHN_ENG"  # 默认中英文混合
        }
    
    async def extract_text_from_images(
        self, 
        images_data: list[bytes], 
        image_formats: list[str] = None,
        mode: str = "fast"
    ) -> OCRResponse:
        """
        从多张图片中提取文字内容（批量处理）
        
        Args:
            images_data: 图片二进制数据列表
            image_formats: 图片格式列表 (png, jpg, jpeg, gif, webp)
            mode: 识别模式，'fast'为极速模式（火山引擎OCR），'quality'为性能模式（豆包OCR）
            
        Returns:
            OCRResponse: OCR识别结果
            
        Raises:
            Exception: OCR识别失败时抛出异常
        """
        if not image_formats:
            image_formats = ["png"] * len(images_data)
        
        # 根据模式选择不同的识别方法
        if mode == "quality":
            return await self._extract_with_doubao_ocr(images_data, image_formats)
        else:
            # 默认与'fast'一致：使用火山引擎OCR
            return await self._extract_with_volc_ocr(images_data, image_formats)
    
    async def _extract_with_baidu_ocr(
        self,
        images_data: list[bytes],
        image_formats: list[str]
    ) -> OCRResponse:
        """
        使用百度OCR进行快速识别（极速模式）
        使用百度OCR快速识别，然后用本地算法判断发言人位置
        
        Args:
            images_data: 图片二进制数据列表
            image_formats: 图片格式列表
            
        Returns:
            OCRResponse: OCR识别结果
        """
        try:
            # 检查是否配置了百度OCR
            if not self.use_baidu_ocr:
                raise Exception("未配置百度OCR，请在.env文件中设置BAIDU_API_KEY和BAIDU_SECRET_KEY")
            
            t_ocr0 = time.perf_counter()
            
            # 步骤1: 使用百度OCR快速识别所有图片（并行处理，支持错误恢复）
            import asyncio
            ocr_tasks = [self._baidu_ocr_recognition(img_data) for img_data in images_data]
            # 使用return_exceptions=True，允许部分图片识别失败
            ocr_results = await asyncio.gather(*ocr_tasks, return_exceptions=True)
            
            t_ocr1 = time.perf_counter()
            logger.info(f"[OCR][baidu] 百度OCR识别耗时: {(t_ocr1 - t_ocr0):.2f}s; 图片数={len(images_data)}")
            
            # 步骤2: 整理OCR结果，提取所有文字块（跨图片，处理错误）
            t_process0 = time.perf_counter()
            all_blocks = []  # 所有文字块，包含位置信息
            failed_images = []  # 记录失败的图片索引
            
            for idx, ocr_result in enumerate(ocr_results):
                # 处理异常情况
                if isinstance(ocr_result, Exception):
                    logger.warning(f"[OCR][error] 图片 {idx + 1} OCR识别失败: {ocr_result}")
                    failed_images.append(idx + 1)
                    continue
                
                # 检查OCR结果格式
                if not isinstance(ocr_result, dict):
                    logger.warning(f"[OCR][error] 图片 {idx + 1} OCR结果格式异常: {type(ocr_result)}")
                    failed_images.append(idx + 1)
                    continue
                
                words_result = ocr_result.get("words_result", [])
                if not words_result:
                    logger.warning(f"[OCR][warn] 图片 {idx + 1} 未识别到文字")
                    continue
                
                # 提取每张图片的文字块
                image_blocks = []
                for word_info in words_result:
                    if not isinstance(word_info, dict):
                        continue
                    
                    words = word_info.get("words", "").strip()
                    if not words:
                        continue
                    
                    location = word_info.get("location", {})
                    if not isinstance(location, dict):
                        continue
                    
                    left = location.get("left", 0)
                    top = location.get("top", 0)
                    width = location.get("width", 0)
                    height = location.get("height", 0)
                    
                    # 验证位置信息有效性
                    if width <= 0 or height <= 0:
                        continue
                    
                    # 计算边界和中心点
                    right = left + width
                    bottom = top + height
                    center_x = left + width / 2
                    center_y = top + height / 2
                    
                    image_blocks.append({
                        "text": words,
                        "x": left,
                        "y": top,
                        "width": width,
                        "height": height,
                        "right": right,
                        "bottom": bottom,
                        "center_x": center_x,
                        "center_y": center_y,
                        "image_index": idx + 1
                    })
                
                all_blocks.extend(image_blocks)
                logger.debug(f"[OCR][process] 图片 {idx + 1} 提取了 {len(image_blocks)} 个文字块")
            
            logger.info(f"[OCR][process] 总共提取了 {len(all_blocks)} 个文字块，失败的图片: {failed_images}")
            
            if not all_blocks:
                # 如果没有文字块，返回空结果
                error_msg = f"所有图片OCR识别失败" if failed_images else "未识别到任何文字"
                return OCRResponse(
                    text="",
                    confidence=0.0,
                    language="mixed",
                    metadata={
                        "confidence": 0.0,
                        "language": "mixed",
                        "structured_messages": [],
                        "participants": [],
                        "ocr_method": "baidu_ocr",
                        "word_count": 0,
                        "failed_images": failed_images,
                        "error": error_msg
                    }
                )
            
            # 步骤3: 本地判断发言人位置并合并聊天块（每次都重新处理，不保留状态）
            messages, text_content = self._process_ocr_blocks(all_blocks)
            
            t_process1 = time.perf_counter()
            logger.info(f"[OCR][process] 本地处理耗时: {(t_process1 - t_process0)*1000:.1f}ms")
            
            # 提取participants
            participants = ["我", "对方"]
            
            # 检测语言类型（支持多语言）
            detected_languages = set()
            for msg in messages:
                text = msg.get("text", "")
                # 简单检测：包含中文字符
                if any('\u4e00' <= char <= '\u9fff' for char in text):
                    detected_languages.add("chinese")
                # 包含英文字符
                if any(char.isascii() and char.isalpha() for char in text):
                    detected_languages.add("english")
            
            language = "mixed" if len(detected_languages) > 1 else ("中文" if "chinese" in detected_languages else "英文")
            
            metadata = {
                "confidence": 0.9,
                "language": language,
                "structured_messages": messages,
                "participants": participants,
                "ocr_method": "baidu_ocr",
                "word_count": len(all_blocks),
                "failed_images": failed_images if failed_images else None
            }
            
            logger.info(f"批量OCR识别成功，处理了 {len(images_data)} 张图片，文本长度: {len(text_content)}，消息数: {len(messages)}，语言: {language}")
            
            return OCRResponse(
                text=text_content,
                confidence=metadata.get("confidence", 0.9),
                language=language,
                metadata=metadata
            )
                
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else 'unknown'
            body = None
            try:
                body = e.response.text if e.response is not None else None
            except Exception:
                body = None
            logger.error(
                f"批量OCR API请求失败: status={status}, url={getattr(e.request, 'url', 'unknown')}, body={body}"
            )
            raise Exception(
                f"OCR识别服务暂时不可用: HTTP {status}"
            )
        except httpx.HTTPError as e:
            logger.error(f"批量OCR API请求失败(网络/超时): {e}")
            raise Exception("OCR识别服务网络异常，请稍后重试")
        except Exception as e:
            logger.error(f"批量OCR识别失败: {e}")
            raise Exception(f"图片识别失败: {str(e)}")
    
    async def _extract_with_doubao_ocr(
        self,
        images_data: list[bytes],
        image_formats: list[str]
    ) -> OCRResponse:
        """
        使用豆包OCR进行识别（性能模式）
        使用豆包多模态模型进行高质量识别和结构化解析
        
        Args:
            images_data: 图片二进制数据列表
            image_formats: 图片格式列表
            
        Returns:
            OCRResponse: OCR识别结果
        """
        try:
            import time
            t_build0 = time.perf_counter()
            optimized_images: list[bytes] = []
            optimized_formats: list[str] = []
            # 服务器端轻量压缩，降低模型端耗时与带宽
            for raw, fmt in zip(images_data, image_formats):
                img_b, img_fmt, info = self._optimize_image_bytes(raw, fmt)
                optimized_images.append(img_b)
                optimized_formats.append(img_fmt)
            images_data = optimized_images
            image_formats = optimized_formats
            # 构建多图片的content数组
            content_parts = [
                {
                    "type": "text",
                    "text": (
                        "你将看到多张聊天截图，请进行OCR并理解排版位置来判断左右两侧发言人。"
                        "请严格返回JSON（不要包含多余文字），结构如下：\n"
                        "{\n"
                        "  \"participants\": [\"我\", \"对方\"],\n"
                        "  \"messages\": [\n"
                        "    {\"speaker_name\": \"我\", \"speaker_side\": \"right\", \"text\": \"内容\", \"block_index\": 1},\n"
                        "    {\"speaker_name\": \"对方\", \"speaker_side\": \"left\", \"text\": \"内容\", \"block_index\": 2}\n"
                        "  ]\n"
                        "}\n"
                        "要求：\n- 以气泡为单位进行分块，尽量合并同一气泡内的换行\n- right表示用户本人（右侧头像），left表示对方（左侧头像）\n- messages按时间顺序\n- block_index从1开始自增\n- 仅返回JSON\n"
                    )
                }
            ]
            
            # 添加所有图片（计时，必要时压缩以降低超时概率）
            for i, (image_data, image_format) in enumerate(zip(images_data, image_formats)):
                try:
                    from io import BytesIO
                    from PIL import Image  # 可选优化
                    img = Image.open(BytesIO(image_data)).convert("RGB")
                    max_side = 1600
                    w, h = img.size
                    if max(w, h) > max_side:
                        ratio = max_side / float(max(w, h))
                        img = img.resize((int(w*ratio), int(h*ratio)))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    image_data = buf.getvalue()
                except Exception:
                    pass
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{image_base64}"
                    }
                })
            
            t_build1 = time.perf_counter()
            logger.info(f"[OCR][doubao][build] 构建content耗时: {(t_build1 - t_build0)*1000:.1f}ms; 图片数={len(images_data)}")
            # 构建请求数据
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ],
                "max_tokens": 800,
                "temperature": 0,
                "top_p": 0,
                # 尽量让模型输出最小JSON以加速
                "response_format": {"type": "json_object"}
            }
            
            # 发送请求到豆包API（更长超时、http2、信任环境代理、带重试）
            t_api0 = time.perf_counter()
            timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=30.0)
            async with httpx.AsyncClient(timeout=timeout, http2=True, trust_env=True) as client:
                last_exc = None
                for attempt in range(1, 4):
                    try:
                        response = await client.post(
                            self.api_url,
                            headers=self.headers,
                            json=payload
                        )
                        # 对5xx进行重试
                        if response.status_code >= 500:
                            raise httpx.HTTPStatusError("server error", request=response.request, response=response)
                        response.raise_for_status()
                        break
                    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError, httpx.RemoteProtocolError, httpx.HTTPStatusError) as e:
                        last_exc = e
                        logger.warning(f"豆包OCR 第{attempt}次请求失败: {type(e).__name__}: {e}")
                        # 4xx不重试，直接抛出
                        if isinstance(e, httpx.HTTPStatusError) and e.response is not None and e.response.status_code < 500:
                            raise
                        if attempt >= 3:
                            raise
                        import asyncio
                        await asyncio.sleep(0.6 * attempt)
                
                result = response.json()
                t_api1 = time.perf_counter()
                logger.info(f"[OCR][doubao][api] 请求+解析耗时: {(t_api1 - t_api0):.2f}s")
                
                # 解析响应
                content = result["choices"][0]["message"]["content"]

                # 默认解析
                text_content, metadata = self._parse_ocr_response(content)

                # 尝试解析结构化JSON
                try:
                    import json
                    structured = json.loads(content)
                    if isinstance(structured, dict) and "messages" in structured:
                        metadata["structured_messages"] = structured.get("messages", [])
                        metadata["participants"] = structured.get("participants", [])
                        # 同时拼接整段文本供前端回显
                        joined = "\n\n".join([m.get("text", "").strip() for m in structured.get("messages", []) if m.get("text")])
                        if joined:
                            text_content = joined
                except Exception:
                    pass
                
                logger.info(f"豆包OCR识别成功，处理了 {len(images_data)} 张图片，文本长度: {len(text_content)}")
                
                return OCRResponse(
                    text=text_content,
                    confidence=metadata.get("confidence", 0.9),
                    language=metadata.get("language", "中文"),
                    metadata=metadata
                )
                
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else 'unknown'
            body = None
            try:
                body = e.response.text if e.response is not None else None
            except Exception:
                body = None
            logger.error(
                f"豆包OCR API请求失败: status={status}, url={getattr(e.request, 'url', 'unknown')}, body={body}"
            )
            raise Exception(
                f"OCR识别服务暂时不可用: HTTP {status}"
            )
        except httpx.HTTPError as e:
            logger.error(f"豆包OCR API请求失败(网络/超时): {e}")
            raise Exception("OCR识别服务网络异常，请稍后重试")
        except Exception as e:
            logger.error(f"豆包OCR识别失败: {e}")
            raise Exception(f"图片识别失败: {str(e)}")
    
    async def _extract_with_volc_ocr(
        self,
        images_data: list[bytes],
        image_formats: list[str]
    ) -> OCRResponse:
        """
        使用火山引擎OCR进行综合识别（综合模式）
        使用火山引擎OCR快速识别，然后用本地算法判断发言人位置
        
        Args:
            images_data: 图片二进制数据列表
            image_formats: 图片格式列表
            
        Returns:
            OCRResponse: OCR识别结果
        """
        try:
            # 检查是否配置了火山引擎OCR
            if not self.use_volc_ocr:
                raise Exception("未配置火山引擎OCR，请在.env文件中设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY")
            
            t_ocr0 = time.perf_counter()
            
            # 步骤1: 使用火山引擎OCR快速识别所有图片（并行处理，支持错误恢复）
            # 使用原始格式方法获取火山OCR数据
            import asyncio
            ocr_tasks = [self._volc_ocr_recognition_raw(img_data) for img_data in images_data]
            # 使用return_exceptions=True，允许部分图片识别失败
            ocr_results = await asyncio.gather(*ocr_tasks, return_exceptions=True)
            
            t_ocr1 = time.perf_counter()
            logger.info(f"[OCR][volc] 火山引擎OCR识别耗时: {(t_ocr1 - t_ocr0):.2f}s; 图片数={len(images_data)}")
            
            # 步骤2: 使用专门的火山OCR处理逻辑提取文字块
            t_process0 = time.perf_counter()
            all_blocks = []  # 所有文字块，包含位置信息
            failed_images = []  # 记录失败的图片索引
            
            for idx, ocr_result in enumerate(ocr_results):
                # 处理异常情况
                if isinstance(ocr_result, Exception):
                    logger.warning(f"[OCR][volc][error] 图片 {idx + 1} OCR识别失败: {ocr_result}")
                    failed_images.append(idx + 1)
                    continue
                
                # 检查OCR结果格式
                if not isinstance(ocr_result, dict):
                    logger.warning(f"[OCR][volc][error] 图片 {idx + 1} OCR结果格式异常: {type(ocr_result)}")
                    failed_images.append(idx + 1)
                    continue
                
                # 从火山OCR原始数据中提取文字块
                image_info = ocr_result.pop("_image_info", {})
                data = ocr_result.get("data", {})
                if not data:
                    logger.warning(f"[OCR][volc][warn] 图片 {idx + 1} OCR结果中data为空")
                    continue
                
                line_texts = data.get("line_texts", [])
                line_rects = data.get("line_rects", [])
                line_probs = data.get("line_probs", [])
                chars = data.get("chars", [])  # 2D Array of CharInfo，每行的所有字符信息
                polygons = data.get("polygons", [])
                
                if not line_texts:
                    logger.warning(f"[OCR][volc][warn] 图片 {idx + 1} 未识别到文字")
                    continue
                
                image_width = image_info.get("width", 0)
                image_height = image_info.get("height", 0)
                
                # 提取每张图片的文字块（尝试从chars拆分词级块，与百度OCR粒度一致）
                # 如果chars可用，使用chars拆分成词级块；否则使用行级块
                image_blocks = self._extract_volc_blocks(
                    line_texts, line_rects, line_probs, polygons, chars,
                    image_width, image_height, idx + 1
                )
                
                all_blocks.extend(image_blocks)
                logger.debug(f"[OCR][volc][process] 图片 {idx + 1} 提取了 {len(image_blocks)} 个文字块")
            
            logger.info(f"[OCR][volc][process] 总共提取了 {len(all_blocks)} 个文字块，失败的图片: {failed_images}")
            
            if not all_blocks:
                # 如果没有文字块，返回空结果
                error_msg = f"所有图片OCR识别失败" if failed_images else "未识别到任何文字"
                return OCRResponse(
                    text="",
                    confidence=0.0,
                    language="mixed",
                    metadata={
                        "confidence": 0.0,
                        "language": "mixed",
                        "structured_messages": [],
                        "participants": [],
                        "ocr_method": "volc_ocr",
                        "word_count": 0,
                        "failed_images": failed_images,
                        "error": error_msg
                    }
                )
            
            # 步骤3: 使用专门的火山OCR处理逻辑，按每张图片分别处理再合并，避免跨图片误合并
            messages: list[dict] = []
            combined_texts: list[str] = []

            # 按image_index分组
            blocks_by_image: dict[int, list[dict]] = {}
            for b in all_blocks:
                idx_key = int(b.get("image_index", 1))
                blocks_by_image.setdefault(idx_key, []).append(b)

            # 按图片顺序处理
            for img_idx in sorted(blocks_by_image.keys()):
                img_blocks = blocks_by_image[img_idx]
                # 使用火山OCR专用的行级块合并逻辑，避免大段公告被错误拆分
                img_messages, img_text = self._process_volc_ocr_blocks(img_blocks)

                # 重新编排每张图片内的block_index，再合并到总消息列表时继续递增
                for m in img_messages:
                    m["block_index"] = len(messages) + 1
                    messages.append(m)
                if img_text:
                    combined_texts.append(img_text)

            text_content = "\n\n".join(t for t in combined_texts if t)
            
            t_process1 = time.perf_counter()
            logger.info(f"[OCR][process] 本地处理耗时: {(t_process1 - t_process0)*1000:.1f}ms")
            
            # 提取participants
            participants = ["我", "对方"]
            
            # 检测语言类型（支持多语言）
            detected_languages = set()
            for msg in messages:
                text = msg.get("text", "")
                # 简单检测：包含中文字符
                if any('\u4e00' <= char <= '\u9fff' for char in text):
                    detected_languages.add("chinese")
                # 包含英文字符
                if any(char.isascii() and char.isalpha() for char in text):
                    detected_languages.add("english")
            
            language = "mixed" if len(detected_languages) > 1 else ("中文" if "chinese" in detected_languages else "英文")
            
            metadata = {
                "confidence": 0.9,
                "language": language,
                "structured_messages": messages,
                "participants": participants,
                "ocr_method": "volc_ocr",
                "word_count": len(all_blocks),
                "failed_images": failed_images if failed_images else None
            }
            
            logger.info(f"火山引擎OCR识别成功，处理了 {len(images_data)} 张图片，文本长度: {len(text_content)}，消息数: {len(messages)}，语言: {language}")
            
            return OCRResponse(
                text=text_content,
                confidence=metadata.get("confidence", 0.9),
                language=language,
                metadata=metadata
            )
                
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else 'unknown'
            body = None
            try:
                body = e.response.text if e.response is not None else None
            except Exception:
                body = None
            logger.error(
                f"火山引擎OCR API请求失败: status={status}, url={getattr(e.request, 'url', 'unknown')}, body={body}"
            )
            raise Exception(
                f"OCR识别服务暂时不可用: HTTP {status}"
            )
        except httpx.HTTPError as e:
            logger.error(f"火山引擎OCR API请求失败(网络/超时): {e}")
            raise Exception("OCR识别服务网络异常，请稍后重试")
        except Exception as e:
            logger.error(f"火山引擎OCR识别失败: {e}")
            raise Exception(f"图片识别失败: {str(e)}")
    
    def _extract_volc_blocks(
        self,
        line_texts: List[str],
        line_rects: List[Dict],
        line_probs: List[float],
        polygons: List[List],
        chars: List[List],
        image_width: int,
        image_height: int,
        image_index: int
    ) -> List[Dict]:
        """
        从火山OCR原始数据中提取文字块（行级块）
        
        使用行级块的优势：
        1. 更符合聊天气泡的自然结构（一个气泡通常是一行或几行）
        2. 块数量更少，合并逻辑更简单高效
        3. 避免了词级拆分可能带来的问题
        
        Args:
            line_texts: 文本行列表
            line_rects: 矩形框列表
            line_probs: 置信度列表
            polygons: 多边形列表
            chars: 2D数组，每行的所有字符信息（当前不使用）
            image_width: 图片宽度
            image_height: 图片高度
            image_index: 图片索引
            
        Returns:
            List[Dict]: 文字块列表（行级粒度）
        """
        blocks = []
        
        # 火山OCR返回的line_rects中的x, y, width, height都是整数类型，绝对坐标（输入图片文件时）
        # 无需进行坐标转换，直接使用
        
        # 使用行级块（不拆分），直接提取行级块
        for i, text in enumerate(line_texts):
            if not text or not text.strip():
                continue
            
            # 获取位置信息
            rect = line_rects[i] if i < len(line_rects) else {}
            prob = line_probs[i] if i < len(line_probs) else 0.9
            
            # 从rect获取坐标（火山OCR返回的是绝对坐标，整数类型，直接使用）
            if isinstance(rect, dict) and rect:
                x = int(rect.get("x", 0))
                y = int(rect.get("y", 0))
                width = int(rect.get("width", 0))
                height = int(rect.get("height", 0))
            elif i < len(polygons) and polygons[i] and isinstance(polygons[i], list):
                polygon = polygons[i]
                if len(polygon) >= 4:
                    xs = [p[0] for p in polygon if len(p) >= 2]
                    ys = [p[1] for p in polygon if len(p) >= 2]
                    if xs and ys:
                        x = min(xs)
                        y = min(ys)
                        width = max(xs) - x
                        height = max(ys) - y
                    else:
                        continue
                else:
                    continue
            else:
                continue
            
            # 验证坐标有效性
            if width <= 0 or height <= 0:
                continue
            
            # 计算边界和中心点
            right = x + width
            bottom = y + height
            center_x = x + width / 2
            center_y = y + height / 2
            
            blocks.append({
                "text": text.strip(),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "right": right,
                "bottom": bottom,
                "center_x": center_x,
                "center_y": center_y,
                "image_index": image_index,
                "confidence": prob
            })
        
        logger.debug(f"[OCR][volc][extract] 提取了 {len(blocks)} 个行级文字块")
        return blocks
    
    def _process_volc_ocr_blocks(self, blocks: list[dict]) -> tuple[list[dict], str]:
        """
        专门处理火山OCR的行级文字块，判断发言人位置并合并聊天气泡
        
        针对行级块的特点优化：
        1. 行级块更大（整行），块数量更少，处理更高效
        2. 主要依赖y距离和x对齐判断，x重叠判断不太准确（因为都是整行宽度）
        3. 阈值计算基于行级块的特性优化
        
        Args:
            blocks: OCR文字块列表（行级），每个块包含text, x, y, width, height等信息
            
        Returns:
            tuple: (结构化消息列表, 拼接的文本内容)
        """
        if not blocks:
            return [], ""
        
        # 0. 过滤噪声文本（只过滤居中的时间戳/日期）
        max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
        min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
        image_width = max_x - min_x
        
        filtered_blocks = []
        for block in blocks:
            text = block.get("text", "").strip()
            block_with_info = {
                **block,
                "image_width": image_width,
                "image_min_x": min_x
            }
            if not self._filter_noise_text(text, block_with_info):
                filtered_blocks.append(block)
            else:
                logger.debug(f"[OCR][volc][filter] 过滤噪声文本: '{text}'")
        
        if not filtered_blocks:
            return [], ""
        
        blocks = filtered_blocks
        logger.info(f"[OCR][volc][filter] 过滤后剩余 {len(blocks)} 个有效文字块")
        
        # 1. 按y坐标排序（从上到下）
        blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
        
        # 2. 计算图片宽度（用于分组）
        max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
        min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
        image_width = max_x - min_x
        
        # 3. 使用1D K-means(K=2)稳健分组左右两侧（行级块）
        center_x_list = [b.get("center_x", 0) for b in blocks]
        if not center_x_list:
            return [], ""
        
        def _kmeans_split_1d(points: list[float], min_x_val: float, width: float) -> tuple[float, list[int]]:
            if not points:
                return min_x_val + width / 2, []
            c1 = min_x_val + width * 0.25
            c2 = min_x_val + width * 0.75
            labels = [0] * len(points)
            for _ in range(10):
                changed = False
                for i, p in enumerate(points):
                    new_label = 0 if abs(p - c1) <= abs(p - c2) else 1
                    if labels[i] != new_label:
                        labels[i] = new_label
                        changed = True
                g1 = [p for p, l in zip(points, labels) if l == 0]
                g2 = [p for p, l in zip(points, labels) if l == 1]
                if g1:
                    c1 = sum(g1) / len(g1)
                if g2:
                    c2 = sum(g2) / len(g2)
                if not changed:
                    break
            if c1 > c2:
                c1, c2 = c2, c1
                labels = [1 - l for l in labels]
            threshold = (c1 + c2) / 2
            return threshold, labels

        x_threshold, labels = _kmeans_split_1d(center_x_list, min_x, image_width)
        
        # 4. 按x坐标分组：左侧=对方，右侧=我
        left_blocks = []
        right_blocks = []
        for block, label in zip(blocks, labels if labels else [0] * len(blocks)):
            if label == 0:
                left_blocks.append(block)
            else:
                right_blocks.append(block)
        
        # 如果分组结果不合理，使用图片中心回退
        if len(left_blocks) == 0 or len(right_blocks) == 0:
            x_threshold = min_x + image_width / 2
            left_blocks = [b for b in blocks if b.get("center_x", 0) < x_threshold]
            right_blocks = [b for b in blocks if b.get("center_x", 0) >= x_threshold]
            logger.warning(f"[OCR][volc][side] 分组异常，使用图片中心阈值: x={x_threshold:.1f}")
        
        logger.info(f"[OCR][volc][side] 左右分组: 左侧={len(left_blocks)}个块, 右侧={len(right_blocks)}个块, 阈值x={x_threshold:.1f}")
        
        # 5. 处理左右两组，分别合并气泡（使用专门的行级块合并逻辑）
        all_messages = []
        
        for blocks_group, side, speaker_name in [
            (left_blocks, "left", "对方"),
            (right_blocks, "right", "我")
        ]:
            if not blocks_group:
                continue
            
            # 按y坐标排序
            blocks_group = sorted(blocks_group, key=lambda b: (b.get("y", 0), b.get("x", 0)))
            
            # 使用专门的行级块合并逻辑
            bubbles = self._merge_volc_bubbles(blocks_group, speaker_name, side)
            
            # 转换为消息（保存y坐标用于排序）
            for bubble in bubbles:
                bubble_text = bubble["text"].strip()
                if not bubble_text:
                    continue
                
                bubble_y = bubble.get("top", 0) if bubble.get("blocks") else 0
                all_messages.append({
                    "speaker_name": speaker_name,
                    "speaker_side": side,
                    "text": bubble_text,
                    "block_index": len(all_messages) + 1,
                    "_sort_y": bubble_y
                })
        
        # 6. 按y坐标对所有消息排序
        all_messages.sort(key=lambda m: m.get("_sort_y", 0))
        
        for i, msg in enumerate(all_messages):
            msg["block_index"] = i + 1
            if "_sort_y" in msg:
                del msg["_sort_y"]
        
        # 7. 拼接文本内容
        text_content = "\n\n".join([m.get("text", "").strip() for m in all_messages if m.get("text")])
        
        logger.info(f"[OCR][volc][process] 处理完成: {len(blocks)}个块合并为{len(all_messages)}条消息")
        return all_messages, text_content
    
    def _merge_volc_bubbles(self, blocks: list[dict], speaker_name: str, side: str) -> list[dict]:
        """
        专门针对火山OCR行级块的合并策略（基于相对间隔比例）
        
        核心思路（用户提供）：
        1. 使用相对位置（相对于图片高度）而不是绝对像素
        2. 同一聊天气泡内各行的间隔比例（相对于图片高度）通常比不同聊天气泡之间的间隔比例小
        3. 分析间隔比例分布，找出分界点来区分同一气泡内换行 vs 不同气泡
        
        Args:
            blocks: 同一发言人的文字块列表（行级）
            speaker_name: 发言人名称
            side: 左右侧
            
        Returns:
            合并后的气泡列表
        """
        if not blocks:
            return []
        
        if len(blocks) == 1:
            # 只有一个块，直接返回
            return [{
                "text": blocks[0]["text"],
                "top": blocks[0]["y"],
                "bottom": blocks[0]["bottom"],
                "left": blocks[0]["x"],
                "right": blocks[0]["right"],
                "blocks": [blocks[0]],
                "anchor_left": blocks[0]["x"],
                "anchor_right": blocks[0]["right"],
                "anchor_width": max(1, blocks[0]["right"] - blocks[0]["x"])
            }]
        
        # 按y坐标排序
        blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
        
        # 计算图片高度（用于相对位置计算）
        all_bottoms = [b.get("bottom", 0) for b in blocks]
        all_tops = [b.get("y", 0) for b in blocks]
        image_height = max(all_bottoms) - min(all_tops) if all_bottoms and all_tops else 1
        image_height = max(image_height, 100)  # 确保至少100，避免除0
        
        # 计算平均行高（用于基准）
        avg_height = sum(b.get("height", 0) for b in blocks) / len(blocks) if blocks else 20
        
        # 代码特征判定（启发式）：符号密度/关键词/前导空格
        def _is_code_like(text: str) -> bool:
            if not text:
                return False
            s = text.strip()
            if not s:
                return False
            lower = s.lower()
            # 典型关键词
            keywords = [
                "def ", "class ", "function ", "var ", "let ", "const ",
                "if ", "for ", "while ", "return ", "import ", "from ",
                "public ", "private ", "protected ", "static ", "=>"
            ]
            if any(k in lower for k in keywords):
                return True
            # 代码围栏或缩进
            if s.startswith("```") or s.endswith("```"):
                return True
            if len(text) - len(text.lstrip(" \t")) >= 2:  # 明显缩进
                return True
            # 符号密度
            symbols = set("{}[]();,:=<>+-*/#`$\"'\\|&%._")
            symbol_cnt = sum(1 for ch in s if ch in symbols)
            digit_cnt = sum(1 for ch in s if ch.isdigit())
            ratio = symbol_cnt / max(1, len(s))
            digit_ratio = digit_cnt / max(1, len(s))
            if ratio >= 0.15 or digit_ratio >= 0.4:
                return True
            return False
        
        # 计算所有相邻块之间的y距离和相对比例
        y_gaps = []
        gap_ratios = []
        for i in range(len(blocks) - 1):
            prev_block = blocks[i]
            curr_block = blocks[i + 1]
            y_gap = curr_block["y"] - prev_block["bottom"]
            if y_gap >= 0:
                y_gaps.append(y_gap)
                gap_ratios.append((y_gap / image_height) if image_height > 0 else 0)

        # 自适应分位数阈值：小间隔=30%分位；大间隔=70%分位
        if gap_ratios:
            s = sorted(gap_ratios)
            def q(r: float) -> float:
                return s[min(len(s) - 1, max(0, int(len(s) * r)))]
            small = q(0.30)
            large = q(0.70)
            line_break_ratio_threshold = max(small * 1.3, (avg_height * 0.9) / image_height if image_height > 0 else small)
            message_gap_ratio_threshold = max(large * 0.9, line_break_ratio_threshold * 1.6)
            typical_small_ratio = small
        else:
            line_break_ratio_threshold = (avg_height * 1.3) / image_height if image_height > 0 else 0.02
            message_gap_ratio_threshold = line_break_ratio_threshold * 2.0
            typical_small_ratio = (avg_height * 1.0) / image_height if image_height > 0 else 0.015
        
        bubbles = []
        current_bubble = None
        
        for block in blocks:
            if current_bubble is None:
                # 创建第一个气泡
                current_bubble = {
                    "text": block["text"],
                    "top": block["y"],
                    "bottom": block["bottom"],
                    "left": block["x"],
                    "right": block["right"],
                    "blocks": [block],
                    "anchor_left": block["x"],
                    "anchor_right": block["right"],
                    "anchor_width": max(1, block["right"] - block["x"]),
                    "image_height": image_height,  # 保存图片高度用于后续计算
                    # 代码模式状态
                    "is_code": _is_code_like(block.get("text", "")),
                    "code_hits": 1 if _is_code_like(block.get("text", "")) else 0
                }
                bubbles.append(current_bubble)
            else:
                # 计算与前一个块的y距离（绝对像素）
                y_gap = block["y"] - current_bubble["bottom"]
                
                # 计算间隔比例（相对于图片高度）- 这是关键！
                gap_ratio = y_gap / image_height if image_height > 0 else 0
                
                # 计算x对齐（锚点锁定）
                if side == "left":
                    x_alignment_diff = abs(block["x"] - current_bubble.get("anchor_left", current_bubble["left"]))
                else:
                    x_alignment_diff = abs(block["right"] - current_bubble.get("anchor_right", current_bubble["right"]))
                anchor_width = max(1, current_bubble.get("anchor_width", (current_bubble["right"]-current_bubble["left"])))
                col_width = max(8, anchor_width)
                strict_anchor_tol = max(6, min(18, col_width * 0.18))
                x_alignment = x_alignment_diff <= strict_anchor_tol
                
                # 宽度/锚点相似度（用于识别整卡片/大公告）
                curr_width = max(1, current_bubble["right"] - current_bubble["left"])
                blk_width = max(1, block["right"] - block["x"])
                width_ratio = min(curr_width, blk_width) / max(curr_width, blk_width)

                # 大间隔硬切分：防止跨段误并（如跨越很远的两条消息）
                big_gap_cutoff = max(line_break_ratio_threshold * 3.5, (avg_height * 3.0) / image_height if image_height > 0 else 0.05)

                # 判断是否应该合并（基于间隔比例 + 代码块模式 + 宽度/锚点稳定）
                should_merge = False
                
                # 策略1: 间隔比例小于阈值且x对齐 -> 同一气泡内的换行
                if gap_ratio <= line_break_ratio_threshold and x_alignment:
                    should_merge = True
                # 策略2: 间隔比例非常小（小于小间隔比例的1.5倍），即使x不完全对齐也合并（避免过度分割）
                elif gap_ratio <= typical_small_ratio * 1.5:
                    should_merge = True
                # 策略3: 如果当前气泡已有多个块，且间隔比例在中等范围，且x对齐或宽度相近，可能是长气泡
                elif len(current_bubble.get("blocks", [])) >= 2:
                    # 计算当前气泡内部已有的间隔比例
                    bubble_blocks = current_bubble.get("blocks", [])
                    if len(bubble_blocks) >= 2:
                        bubble_internal_ratios = []
                        for j in range(len(bubble_blocks) - 1):
                            prev = bubble_blocks[j]
                            curr = bubble_blocks[j + 1]
                            internal_gap = curr["y"] - prev["bottom"]
                            internal_ratio = internal_gap / image_height if image_height > 0 else 0
                            bubble_internal_ratios.append(internal_ratio)
                        
                        if bubble_internal_ratios:
                            # 当前气泡内部的中位间隔比例
                            bubble_median_ratio = sorted(bubble_internal_ratios)[len(bubble_internal_ratios) // 2]
                            # 如果新行的间隔比例不超过气泡内部中位间隔比例的2.2倍，且x对齐或宽度相似度高，继续合并
                            if gap_ratio <= bubble_median_ratio * 2.2 and (x_alignment or width_ratio >= 0.75):
                                should_merge = True

                # 策略3b: 卡片/公告自然合并 —— 宽度相近且锚点稳定，允许到起新气泡阈值
                if not should_merge and width_ratio >= 0.8 and x_alignment and gap_ratio <= message_gap_ratio_threshold:
                    should_merge = True

                # 策略4: 代码块模式 — 只要锚点对齐就强合并（忽略y距离的远近）
                next_is_code = _is_code_like(block.get("text", ""))
                # 满足以下其一即可进入/维持代码模式：
                # - 当前已在代码模式
                # - 连续两行判断为代码
                # - 本行具备强代码信号（``` 或 明显缩进或关键词）
                in_code_mode = bool(current_bubble.get("is_code")) or (next_is_code and _is_code_like(current_bubble.get("blocks", [{}])[-1].get("text", "")))
                if in_code_mode and x_alignment:
                    should_merge = True
                
                # 最后保护：若间隔超过起新气泡阈值，则不合并（防跨段误并）
                if should_merge and gap_ratio >= message_gap_ratio_threshold:
                    should_merge = False

                if should_merge:
                    # 合并到当前气泡
                    current_bubble["text"] += "\n" + block["text"]
                    current_bubble["bottom"] = max(current_bubble["bottom"], block["bottom"])
                    current_bubble["left"] = min(current_bubble["left"], block["x"])
                    current_bubble["right"] = max(current_bubble["right"], block["right"])
                    current_bubble["blocks"].append(block)
                    # 更新代码模式状态
                    if next_is_code:
                        current_bubble["code_hits"] = current_bubble.get("code_hits", 0) + 1
                    # 若累计至少2次命中，则锁定为代码模式
                    if current_bubble.get("code_hits", 0) >= 2:
                        current_bubble["is_code"] = True
                else:
                    # 创建新气泡
                    current_bubble = {
                        "text": block["text"],
                        "top": block["y"],
                        "bottom": block["bottom"],
                        "left": block["x"],
                        "right": block["right"],
                        "blocks": [block],
                        "anchor_left": block["x"],
                        "anchor_right": block["right"],
                        "anchor_width": max(1, block["right"] - block["x"]),
                        "image_height": image_height,
                        "is_code": _is_code_like(block.get("text", "")),
                        "code_hits": 1 if _is_code_like(block.get("text", "")) else 0
                    }
                    bubbles.append(current_bubble)
        
        logger.info(f"[OCR][volc][merge] {side}侧合并完成: {len(blocks)}个行级块合并为{len(bubbles)}个气泡（使用间隔比例阈值: {line_break_ratio_threshold:.4f}）")
        return bubbles

    def _filter_noise_text(self, text: str, block: dict = None) -> bool:
        """
        判断文本是否是噪声（只过滤位于截图中间的时间戳/日期）
        
        策略：不过滤任何聊天内容，只过滤系统UI元素（居中的时间戳/日期）
        
        Args:
            text: 文本内容
            block: 文字块信息（包含位置信息），用于判断是否居中
            
        Returns:
            bool: True表示是噪声（居中的时间戳/日期），应该过滤掉
        """
        if not text or len(text.strip()) == 0:
            return True
        
        text = text.strip()
        
        # 只检查时间戳/日期格式（包括系统UI的日期时间戳）
        time_patterns = [
            r'^\d{1,2}:\d{2}$',  # 时间格式如 "10:49"、"15:03"
            r'^\d{1,2}:\d{2}:\d{2}$',  # 带秒的时间格式
            r'^\d{1,2}月\d{1,2}日$',  # 日期格式如 "11月2日"
            r'^\d{4}-\d{2}-\d{2}$',  # 日期格式如 "2025-11-02"
            r'^\d{4}/\d{1,2}/\d{1,2}$',  # 日期格式如 "2025/11/2"
            r'^\d{4}年\d{1,2}月\d{1,2}日$',  # 日期格式如 "2025年11月2日"
            r'^星期[一二三四五六日]$',  # 星期格式
            r'^[0-9]{1,2}:[0-9]{2}$',  # 另一种时间格式
            # 系统UI的日期时间戳格式（如"星期三14：01"、"星期四12：47"）
            r'^星期[一二三四五六日]\d{1,2}[：:]\d{2}$',  # "星期三14：01"、"星期四12：47"
            r'^星期[一二三四五六日]\s*\d{1,2}[：:]\d{2}$',  # 带空格："星期三 14：01"
            r'^星期[一二三四五六日](\d{1,2})?[：:](\d{2})?$',  # 更宽松的匹配
            # 其他常见的系统UI格式
            r'^\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}$',  # "11月2日 14:01"
            r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$',  # "2025-11-02 14:01"
        ]
        
        # 系统UI日期时间戳格式（明确是系统UI，直接过滤，不需要位置判断）
        system_ui_patterns = [
            r'^星期[一二三四五六日]\d{1,2}[：:]\d{2}$',  # "星期三14：01"、"星期四12：47"
            r'^星期[一二三四五六日]\s*\d{1,2}[：:]\d{2}$',  # 带空格："星期三 14：01"
            r'^星期[一二三四五六日]\d{1,2}[：:]\d{2}:\d{2}$',  # 带秒："星期三14：01：30"
        ]
        
        is_system_ui = any(re.match(pattern, text) for pattern in system_ui_patterns)
        if is_system_ui:
            # 系统UI日期时间戳，直接过滤（这是非聊天内容）
            logger.debug(f"[OCR][filter] 过滤系统UI日期时间戳: '{text}'")
            return True
        
        # 其他时间戳/日期格式
        time_patterns = [
            r'^\d{1,2}:\d{2}$',  # 时间格式如 "10:49"、"15:03"
            r'^\d{1,2}:\d{2}:\d{2}$',  # 带秒的时间格式
            r'^\d{1,2}月\d{1,2}日$',  # 日期格式如 "11月2日"
            r'^\d{4}-\d{2}-\d{2}$',  # 日期格式如 "2025-11-02"
            r'^\d{4}/\d{1,2}/\d{1,2}$',  # 日期格式如 "2025/11/2"
            r'^\d{4}年\d{1,2}月\d{1,2}日$',  # 日期格式如 "2025年11月2日"
            r'^星期[一二三四五六日]$',  # 星期格式
            r'^[0-9]{1,2}:[0-9]{2}$',  # 另一种时间格式
            # 其他常见的系统UI格式
            r'^\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}$',  # "11月2日 14:01"
            r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$',  # "2025-11-02 14:01"
        ]
        
        is_timestamp = any(re.match(pattern, text) for pattern in time_patterns)
        
        # 只有时间戳/日期格式才考虑过滤，其他所有内容都保留
        if not is_timestamp:
            return False
        
        # 对于其他时间戳/日期格式，需要判断是否应该过滤（基于位置）
        if block is not None:
            center_x = block.get("center_x", 0)
            image_min_x = block.get("image_min_x", 0)
            image_width = block.get("image_width", 0)
            
            if image_width > 0:
                # 计算图片中心的绝对位置
                image_center_absolute = image_min_x + image_width / 2
                # 判断是否在图片中心附近（中心±35%范围，确保能捕获截图中间的时间戳）
                center_range = image_width * 0.35
                
                # 计算距离中心的距离
                distance_from_center = abs(center_x - image_center_absolute)
                
                if distance_from_center <= center_range:
                    # 居中的时间戳/日期，过滤（这是系统UI元素）
                    logger.debug(f"[OCR][filter] 过滤居中的时间戳/日期: '{text}' (center_x={center_x:.1f}, image_center={image_center_absolute:.1f}, range={center_range:.1f}, distance={distance_from_center:.1f})")
                    return True
                else:
                    # 非居中的时间戳/日期，保留（可能是聊天消息的一部分）
                    logger.debug(f"[OCR][keep] 保留非居中的时间戳: '{text}' (center_x={center_x:.1f}, image_center={image_center_absolute:.1f}, distance={distance_from_center:.1f})")
                    return False
            else:
                # 无法判断位置，保守处理：不过滤
                return False
        else:
            # 没有位置信息，保守处理：不过滤
            return False
    
    def _process_ocr_blocks(self, blocks: list[dict]) -> tuple[list[dict], str]:
        """
        处理OCR文字块，判断发言人位置并合并聊天气泡
        
        策略：
        1. 过滤噪声文本
        2. 根据x坐标中心点分成左右两组（判断发言人）
        3. 对每组按y坐标排序
        4. 根据y距离和x重叠判断是否同一气泡
        5. 合并同一气泡内的文字块
        
        Args:
            blocks: OCR文字块列表，每个块包含text, x, y, width, height等信息
            
        Returns:
            tuple: (结构化消息列表, 拼接的文本内容)
        """
        if not blocks:
            return [], ""
        
        # 0. 过滤噪声文本（只过滤居中的时间戳/日期）
        max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
        min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
        image_width = max_x - min_x
        
        filtered_blocks = []
        for block in blocks:
            text = block.get("text", "").strip()
            # 传入图片宽度和最小x坐标，用于判断是否居中
            block_with_info = {
                **block,
                "image_width": image_width,
                "image_min_x": min_x
            }
            if not self._filter_noise_text(text, block_with_info):
                filtered_blocks.append(block)
            else:
                logger.debug(f"[OCR][filter] 过滤噪声文本: '{text}'")
        
        if not filtered_blocks:
            return [], ""
        
        blocks = filtered_blocks
        logger.info(f"[OCR][filter] 过滤后剩余 {len(blocks)} 个有效文字块")
        
        if not blocks:
            return [], ""
        
        # 1. 按y坐标排序（从上到下）
        blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
        
        # 2. 计算图片宽度
        max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
        min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
        image_width = max_x - min_x
        
        # 3. 使用1D K-means(K=2)稳健分组左右两侧
        def _kmeans_split_1d(points: list[float], min_x_val: float, width: float) -> tuple[float, list[int]]:
            if not points:
                return min_x_val + width / 2, []
            # 初始化两个中心：25% 和 75% 位置
            c1 = min_x_val + width * 0.25
            c2 = min_x_val + width * 0.75
            labels = [0] * len(points)
            for _ in range(10):
                # 赋值
                changed = False
                for i, p in enumerate(points):
                    new_label = 0 if abs(p - c1) <= abs(p - c2) else 1
                    if labels[i] != new_label:
                        labels[i] = new_label
                        changed = True
                # 重新计算中心
                g1 = [p for p, l in zip(points, labels) if l == 0]
                g2 = [p for p, l in zip(points, labels) if l == 1]
                if g1:
                    c1 = sum(g1) / len(g1)
                if g2:
                    c2 = sum(g2) / len(g2)
                if not changed:
                    break
            # 保证c1位于左侧
            if c1 > c2:
                c1, c2 = c2, c1
                labels = [1 - l for l in labels]
            # 阈值取两中心中点
            threshold = (c1 + c2) / 2
            return threshold, labels

        center_x_list = [b.get("center_x", 0) for b in blocks]
        x_threshold, labels = _kmeans_split_1d(center_x_list, min_x, image_width)
        
        # 4. 按x坐标分组：左侧=对方，右侧=我
        left_blocks = []  # 对方
        right_blocks = []  # 我
        for block, label in zip(blocks, labels if labels else [0] * len(blocks)):
            if label == 0:
                left_blocks.append(block)
            else:
                right_blocks.append(block)
        
        # 如果分组结果不合理（一侧数量为0），使用图片中心回退
        if len(left_blocks) == 0 or len(right_blocks) == 0:
            x_threshold = min_x + image_width / 2
            left_blocks = [b for b in blocks if b.get("center_x", 0) < x_threshold]
            right_blocks = [b for b in blocks if b.get("center_x", 0) >= x_threshold]
            logger.warning(f"[OCR][side] 分组异常，使用图片中心阈值: x={x_threshold:.1f}, 左侧={len(left_blocks)}个块, 右侧={len(right_blocks)}个块")
        
        logger.info(f"[OCR][side] 左右分组: 左侧={len(left_blocks)}个块, 右侧={len(right_blocks)}个块, 阈值x={x_threshold:.1f}, 图片宽度={image_width:.1f}")
        
        # 4. 处理左右两组，分别合并气泡
        all_messages = []
        
        for blocks_group, side, speaker_name in [
            (left_blocks, "left", "对方"),
            (right_blocks, "right", "我")
        ]:
            if not blocks_group:
                continue
            
            # 按y坐标排序
            blocks_group = sorted(blocks_group, key=lambda b: (b.get("y", 0), b.get("x", 0)))
            
            # 合并同一气泡内的文字块
            bubbles = self._merge_bubbles(blocks_group, speaker_name, side)
            
            # 转换为消息（保存y坐标用于排序）
            for bubble in bubbles:
                bubble_text = bubble["text"].strip()
                # 只过滤明显无意义的空消息
                if not bubble_text or len(bubble_text.strip()) == 0:
                    continue
                
                # 使用气泡的第一个块的y坐标
                bubble_y = bubble.get("top", 0) if bubble.get("blocks") else 0
                all_messages.append({
                    "speaker_name": speaker_name,
                    "speaker_side": side,
                    "text": bubble_text,
                    "block_index": len(all_messages) + 1,
                    "_sort_y": bubble_y  # 临时保存y坐标用于排序
                })
        
        # 5. 按y坐标对所有消息排序（确保对话顺序正确）
        # 消息已经在生成时保存了_sort_y字段
        all_messages.sort(key=lambda m: m.get("_sort_y", 0))
        
        # 重新分配block_index并删除临时字段
        for i, msg in enumerate(all_messages):
            msg["block_index"] = i + 1
            if "_sort_y" in msg:
                del msg["_sort_y"]
        
        # 6. 拼接文本内容
        text_content = "\n\n".join([m.get("text", "").strip() for m in all_messages if m.get("text")])
        
        return all_messages, text_content
    
    def _merge_bubbles(self, blocks: list[dict], speaker_name: str, side: str) -> list[dict]:
        """
        将同一发言人的文字块合并成气泡
        
        策略：
        - 先分析所有块之间的y距离分布，找出典型的消息间距
        - 同一消息内的换行：y距离小（1-1.5倍行高），x位置对齐
        - 不同消息气泡：y距离大（>2倍行高，通常是3-5倍行高），x位置可能有差异
        
        Args:
            blocks: 同一发言人的文字块列表
            speaker_name: 发言人名称
            side: 左右侧
            
        Returns:
            合并后的气泡列表
        """
        if not blocks:
            return []
        
        # 步骤1: 分析所有块之间的y距离分布，找出典型的消息间距阈值
        if len(blocks) > 1:
            # 计算所有相邻块之间的y距离
            y_gaps = []
            sorted_blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
            for i in range(len(sorted_blocks) - 1):
                prev_block = sorted_blocks[i]
                curr_block = sorted_blocks[i + 1]
                y_gap = curr_block["y"] - prev_block["bottom"]
                if y_gap > 0:  # 只考虑有距离的情况
                    y_gaps.append(y_gap)
            
            # 计算平均行高
            avg_height = sum(b.get("height", 0) for b in blocks) / len(blocks) if blocks else 20
            line_spacing = avg_height * 1.2  # 行间距约为行高的1.2倍
            
            # 分析y距离分布，区分同一消息内的换行 vs 不同消息的间距
            if y_gaps:
                y_gaps_sorted = sorted(y_gaps)
                # 同一消息内的换行距离通常在较小的y_gap范围内
                # 使用前50%的小距离作为参考，找出典型的换行距离
                median_gap_index = len(y_gaps_sorted) // 2
                typical_line_break = y_gaps_sorted[median_gap_index] if median_gap_index < len(y_gaps_sorted) else line_spacing
                
                # 典型的消息间距应该是换行距离的2-3倍
                # 使用75%分位数作为消息间距的参考
                message_gap_index = int(len(y_gaps_sorted) * 0.75)
                typical_message_gap = y_gaps_sorted[message_gap_index] if message_gap_index < len(y_gaps_sorted) else typical_line_break * 2.5
                
                # 设置阈值：如果在typical_line_break的2倍内，认为是同一消息的换行
                # 放宽阈值，避免错误分割
                line_break_threshold = max(typical_line_break * 2.0, line_spacing * 1.5)
                # 如果y距离大于typical_message_gap的0.8倍，很可能是不同消息
                message_gap_threshold = min(typical_message_gap * 0.8, line_spacing * 3.0)
            else:
                line_break_threshold = line_spacing * 1.5
                message_gap_threshold = line_spacing * 2.5
        else:
            line_break_threshold = 20
            message_gap_threshold = 40
        
        bubbles = []
        
        # 第一个块创建新气泡
        first_block = blocks[0]
        current_bubble = {
            "text": first_block["text"],
            "top": first_block["y"],
            "bottom": first_block["bottom"],
            "left": first_block["x"],
            "right": first_block["right"],
            "blocks": [first_block]
        }
        bubbles.append(current_bubble)
        
        # 处理后续块
        for block in blocks[1:]:
            # 计算与前一个块的y距离
            prev_block = current_bubble["blocks"][-1]
            y_gap = block["y"] - prev_block["bottom"]
            
            # 计算x重叠
            x_overlap = max(0, min(block["right"], prev_block["right"]) - max(block["x"], prev_block["x"]))
            min_width = min(block["width"], prev_block["width"])
            overlap_ratio = x_overlap / min_width if min_width > 0 else 0
            
            # 计算x中心距离
            block_center_x = block["center_x"]
            prev_center_x = prev_block["center_x"]
            x_distance = abs(block_center_x - prev_center_x)
            
            # 计算平均行高（用于判断换行的合理性）
            avg_height = (block["height"] + prev_block["height"]) / 2
            line_spacing = avg_height * 1.2  # 行间距约为行高的1.2倍
            
            # x位置相近的判断：重叠明显或中心距离小
            x_threshold = max(block["width"], prev_block["width"]) * 0.5  # x中心距离阈值
            x_similar = overlap_ratio > 0.25 or x_distance <= x_threshold
            
            # 判断是否同一气泡
            # 策略：优先考虑x位置，结合y距离进行综合判断
            # 关键洞察：同一消息内的换行，x位置通常对齐；不同消息，x位置可能有明显差异
            
            same_bubble = False
            
            # 如果x位置非常接近（重叠>35%或中心距离<40%宽度），即使y距离稍大也应该是同一消息
            x_very_similar = overlap_ratio > 0.35 or x_distance <= x_threshold * 0.6
            
            # 如果x位置明显不同（重叠<15%且中心距离>60%宽度），很可能是不同消息
            x_very_different = overlap_ratio < 0.15 and x_distance > x_threshold * 1.2
            
            # 判断逻辑（按优先级）
            if x_very_different and y_gap > line_spacing * 1.5:
                # x位置明显不同 + y距离较大 → 肯定是不同消息
                same_bubble = False
            elif x_very_similar:
                # x位置非常接近 → 很可能是同一消息的换行
                # 如果y距离不太大（<2.5倍行距），都认为是同一消息
                if y_gap <= line_spacing * 2.5:
                    same_bubble = True
                elif y_gap <= message_gap_threshold:
                    # y距离中等，但x位置很接近，也倾向于合并（可能是格式异常的长消息）
                    same_bubble = True
            elif y_gap <= line_break_threshold:
                # y距离很小 + x位置相近 → 同一消息的换行
                same_bubble = x_similar or overlap_ratio > 0.25
            elif y_gap <= line_spacing * 2.0 and x_similar:
                # y距离适中 + x位置相近 → 也可能是同一消息的换行
                same_bubble = overlap_ratio > 0.25
            elif y_gap <= message_gap_threshold:
                # y距离在中间范围，需要更严格的x位置条件
                # 只有在x重叠非常明显时才合并
                same_bubble = overlap_ratio > 0.45 and x_distance <= x_threshold * 0.6
            # else: y距离很大，肯定是不同消息，不合并
            
            if same_bubble:
                # 合并到当前气泡
                # 判断是否同一行（考虑行高和容差）
                line_height = max(block["height"], prev_block["height"])
                y_diff = abs(block["y"] - prev_block["y"])
                same_line = y_diff <= line_height * 0.8  # 同一行：y差异小于0.8倍行高
                
                # 判断x位置关系
                # 如果新块在右边，可能是同一行的继续；如果在下方，是下一行
                x_relative_pos = block["x"] - prev_block["x"]
                is_right_side = x_relative_pos > -block["width"] * 0.2  # 右侧：允许略微左移（20%）
                
                # 判断是否在下方（换行）
                is_below = block["y"] > prev_block["bottom"] + line_height * 0.3  # 换行：明显在下方
                
                if same_line and is_right_side and not is_below:
                    # 同一行右侧，用空格连接
                    current_bubble["text"] += " " + block["text"]
                else:
                    # 不同行或在左侧，用换行连接（同一消息内的换行）
                    current_bubble["text"] += "\n" + block["text"]
                
                # 更新气泡边界
                current_bubble["top"] = min(current_bubble["top"], block["y"])
                current_bubble["bottom"] = max(current_bubble["bottom"], block["bottom"])
                current_bubble["left"] = min(current_bubble["left"], block["x"])
                current_bubble["right"] = max(current_bubble["right"], block["right"])
                current_bubble["blocks"].append(block)
            else:
                # 创建新气泡
                current_bubble = {
                    "text": block["text"],
                    "top": block["y"],
                    "bottom": block["bottom"],
                    "left": block["x"],
                    "right": block["right"],
                    "blocks": [block]
                }
                bubbles.append(current_bubble)
        
        return bubbles

    def _rebuild_bubbles(self, blocks: list[dict]) -> tuple[list[dict], str]:
        """
        将OCR文字块按位置聚合成对话消息，推断左右角色。
        简化策略：
        - 先按y排序，再以x中值为阈值划分左右
        - 邻近行聚合为同一块
        """
        if not blocks:
            return [], ""
        # 排序
        blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
        xs = sorted([b.get("x", 0) + (b.get("w", 0) / 2) for b in blocks])
        mid = xs[len(xs)//2] if xs else 0

        messages: list[dict] = []
        current = None
        block_index = 1
        for b in blocks:
            cx = b.get("x", 0) + (b.get("w", 0) / 2)
            side = "right" if cx > mid else "left"
            text = (b.get("text") or "").strip()
            if not text:
                continue
            if current and abs(b.get("y", 0) - current.get("_last_y", 0)) < 24 and current.get("speaker_side") == side:
                current["text"] += ("\n" if not current["text"].endswith("\n") else "") + text
                current["_last_y"] = b.get("y", 0)
            else:
                if current:
                    del current["_last_y"]
                    messages.append(current)
                current = {
                    "speaker_name": "己方" if side == "right" else "对方",
                    "speaker_side": side,
                    "text": text,
                    "block_index": block_index,
                    "_last_y": b.get("y", 0)
                }
                block_index += 1
        if current:
            del current["_last_y"]
            messages.append(current)

        plain = "\n\n".join([m["text"] for m in messages])
        return messages, plain

    def _optimize_image_bytes(self, image_bytes: bytes, image_format: str) -> tuple[bytes, str, dict]:
        """
        将图片在服务端做轻量压缩、限制最长边，减少传给模型的数据量。
        目标：最长边<=1280，JPEG/WebP质量80。
        返回：优化后的字节、格式、信息。
        """
        try:
            from PIL import Image
            import io as _io
            with Image.open(_io.BytesIO(image_bytes)) as im:
                im = im.convert('RGB')
                w, h = im.size
                max_side = 1280
                if max(w, h) > max_side:
                    if w >= h:
                        new_w = max_side
                        new_h = int(h * max_side / w)
                    else:
                        new_h = max_side
                        new_w = int(w * max_side / h)
                    im = im.resize((new_w, new_h))
                    w, h = new_w, new_h
                out = _io.BytesIO()
                # 统一用JPEG以获得较好大小/质量比
                im.save(out, format='JPEG', quality=80, optimize=True)
                data = out.getvalue()
                return data, 'jpeg', {"orig_bytes": len(image_bytes), "opt_bytes": len(data), "size": [w, h]}
        except Exception:
            # 出错则原样返回
            return image_bytes, image_format, {"orig_bytes": len(image_bytes), "opt_bytes": len(image_bytes)}

    async def extract_text_from_image(
        self, 
        image_data: bytes, 
        image_format: str = "png"
    ) -> OCRResponse:
        """
        从单张图片中提取文字内容（统一使用火山引擎OCR）
        """
        return await self._extract_with_volc_ocr([image_data], [image_format])
    
    def _parse_ocr_response(self, content: str) -> tuple[str, Dict[str, Any]]:
        """
        解析OCR响应内容
        
        Args:
            content: OCR API返回的原始内容
            
        Returns:
            tuple: (提取的文本内容, 元数据字典)
        """
        try:
            # 提取对话内容部分
            if "**对话内容：**" in content:
                text_start = content.find("**对话内容：**") + len("**对话内容：**")
                text_end = content.find("**识别信息：**", text_start)
                if text_end == -1:
                    text_end = len(content)
                text_content = content[text_start:text_end].strip()
            else:
                # 如果没有找到特定格式，使用整个内容
                text_content = content.strip()
            
            # 提取元数据
            metadata = {
                "confidence": 0.9,
                "language": "中文",
                "dialogue_rounds": 1,
                "raw_response": content
            }
            
            # 尝试从响应中提取置信度
            if "置信度：" in content:
                try:
                    conf_start = content.find("置信度：") + len("置信度：")
                    conf_end = content.find("\n", conf_start)
                    if conf_end == -1:
                        conf_end = conf_start + 10
                    conf_text = content[conf_start:conf_end].strip()
                    metadata["confidence"] = float(conf_text)
                except:
                    pass
            
            # 尝试提取语言信息
            if "语言：" in content:
                try:
                    lang_start = content.find("语言：") + len("语言：")
                    lang_end = content.find("\n", lang_start)
                    if lang_end == -1:
                        lang_end = lang_start + 10
                    metadata["language"] = content[lang_start:lang_end].strip()
                except:
                    pass
            
            # 尝试提取对话轮数
            if "对话轮数：" in content:
                try:
                    rounds_start = content.find("对话轮数：") + len("对话轮数：")
                    rounds_end = content.find("\n", rounds_start)
                    if rounds_end == -1:
                        rounds_end = rounds_start + 5
                    rounds_text = content[rounds_start:rounds_end].strip()
                    metadata["dialogue_rounds"] = int(rounds_text)
                except:
                    pass
            
            return text_content, metadata
            
        except Exception as e:
            logger.warning(f"解析OCR响应失败，使用原始内容: {e}")
            return content.strip(), {"confidence": 0.8, "language": "中文"}
    
    async def extract_chat_content_from_image(
        self, 
        image_data: bytes, 
        image_format: str = "png"
    ) -> Dict[str, Any]:
        """
        从聊天截图中提取结构化的聊天内容
        
        Args:
            image_data: 图片二进制数据
            image_format: 图片格式
            
        Returns:
            Dict: 结构化的聊天内容
        """
        try:
            # 先进行OCR识别
            ocr_result = await self.extract_text_from_image(image_data, image_format)
            
            # 使用豆包API进一步解析聊天内容
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请分析以下聊天内容，将其解析为结构化的对话格式：

{ocr_result.text}

请按照以下JSON格式返回：
{{
    "participants": ["用户A", "用户B"],
    "messages": [
        {{
            "speaker": "用户A",
            "content": "消息内容",
            "timestamp": "时间戳（如果有）"
        }}
    ],
    "summary": "对话摘要",
    "context": "对话背景"
}}"""
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 尝试解析JSON响应
                import json
                try:
                    structured_content = json.loads(content)
                    return {
                        "raw_text": ocr_result.text,
                        "structured_content": structured_content,
                        "ocr_metadata": ocr_result.metadata
                    }
                except json.JSONDecodeError:
                    # 如果JSON解析失败，返回原始内容
                    return {
                        "raw_text": ocr_result.text,
                        "structured_content": {
                            "participants": ["用户A", "用户B"],
                            "messages": [{"speaker": "用户A", "content": ocr_result.text}],
                            "summary": "聊天内容识别",
                            "context": "图片识别"
                        },
                        "ocr_metadata": ocr_result.metadata
                    }
                    
        except Exception as e:
            logger.error(f"聊天内容解析失败: {e}")
            raise Exception(f"聊天内容解析失败: {str(e)}")


# 全局OCR服务实例
ocr_service = DoubaoOCRService()

