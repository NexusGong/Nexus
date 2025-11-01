"""
豆包OCR服务模块
负责图片文字识别和聊天内容提取
"""

import base64
from typing import Dict, Any, Optional
import os
from app.config import settings
from app.schemas.analysis import OCRResponse
import json as _json


class DoubaoOCRService:
    """豆包OCR服务类"""
    
    def __init__(self):
        """初始化OCR服务"""
        self.api_key = os.getenv("ARK_API_KEY") or settings.doubao_api_key
        self.api_url = settings.doubao_api_url
        self.model = settings.doubao_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def extract_text_from_images(
        self, 
        images_data: list[bytes], 
        image_formats: list[str] = None
    ) -> OCRResponse:
        """
        从多张图片中提取文字内容（批量处理）
        
        Args:
            images_data: 图片二进制数据列表
            image_formats: 图片格式列表 (png, jpg, jpeg, gif, webp)
            
        Returns:
            OCRResponse: OCR识别结果
            
        Raises:
            Exception: OCR识别失败时抛出异常
        """
        if not image_formats:
            image_formats = ["png"] * len(images_data)
        
        # 根据配置切换提供者
        provider = (settings.ocr_provider or "doubao").lower()
        if provider == "volc_ocr":
            return await self._extract_with_volc_ocr(images_data, image_formats)

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
            logger.info(f"[OCR][build] 构建content耗时: {(t_build1 - t_build0)*1000:.1f}ms; 图片数={len(images_data)}")
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
                        logger.warning(f"批量OCR 第{attempt}次请求失败: {type(e).__name__}: {e}")
                        # 4xx不重试，直接抛出
                        if isinstance(e, httpx.HTTPStatusError) and e.response is not None and e.response.status_code < 500:
                            raise
                        if attempt >= 3:
                            raise
                        import asyncio
                        await asyncio.sleep(0.6 * attempt)
                
                result = response.json()
                t_api1 = time.perf_counter()
                logger.info(f"[OCR][api] 请求+解析耗时: {(t_api1 - t_api0):.2f}s")
                
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
                
                logger.info(f"批量OCR识别成功，处理了 {len(images_data)} 张图片，文本长度: {len(text_content)}")
                
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
        从图片中提取文字内容
        
        Args:
            image_data: 图片二进制数据
            image_format: 图片格式 (png, jpg, jpeg, gif, webp)
            
        Returns:
            OCRResponse: OCR识别结果
            
        Raises:
            Exception: OCR识别失败时抛出异常
        """
        try:
            # 将图片转换为base64编码
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 构建请求数据
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请识别这张聊天截图中的所有文字内容，包括对话双方的发言。请按照以下格式返回：\n\n**对话内容：**\n[识别出的完整对话内容]\n\n**识别信息：**\n- 置信度：[0-1之间的数值]\n- 语言：中文/英文\n- 对话轮数：[数字]"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            # 发送请求到豆包API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 解析响应
                content = result["choices"][0]["message"]["content"]
                
                # 提取文本内容和元数据
                text_content, metadata = self._parse_ocr_response(content)
                
                logger.info(f"OCR识别成功，文本长度: {len(text_content)}")
                
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
                f"OCR API请求失败: status={status}, url={getattr(e.request, 'url', 'unknown')}, body={body}"
            )
            raise Exception(
                f"OCR识别服务暂时不可用: HTTP {status}"
            )
        except httpx.HTTPError as e:
            logger.error(f"OCR API请求失败(网络/超时): {e}")
            raise Exception("OCR识别服务网络异常，请稍后重试")
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            raise Exception(f"图片识别失败: {str(e)}")
    
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

