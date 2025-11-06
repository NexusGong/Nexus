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


class OCRUtils:
	"""通用OCR工具方法（无状态）。"""
	@staticmethod
	def filter_noise_text(text: str, block: dict = None) -> bool:
		if not text or len(text.strip()) == 0:
			return True
		text = text.strip()
		time_patterns = [
			r'^\d{1,2}:\d{2}$',
			r'^\d{1,2}:\d{2}:\d{2}$',
			r'^\d{1,2}[：:]\d{2}$',
			r'^\d{1,2}[：:]\d{2}[：:]\d{2}$',
			r'^\d{1,2}月\d{1,2}日$',
			r'^\d{4}-\d{2}-\d{2}$',
			r'^\d{4}/\d{1,2}/\d{1,2}$',
			r'^\d{4}年\d{1,2}月\d{1,2}日$',
			r'^星期[一二三四五六日]$',
			r'^星期[一二三四五六日]\s*\d{1,2}[：:]\d{2}$',
			r'^\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}$',
			r'^\s*\d{1,2}\s*[：:]\s*\d{2}\s*$',
			# 相对时间模式
			r'^(昨天|今天|前天)\s*\d{1,2}[：:]\d{2}$',  # 昨天18:03、今天10:30等
			r'^(昨天|今天|前天)\s*\d{1,2}:\d{2}$',  # 昨天18:03、今天10:30等
			r'^(昨天|今天|前天)[\s\S]*$',  # 以相对时间开头的文本
			# 更宽泛的时间模式
			r'^\d{1,2}:\d{2}[\s\S]*$',  # 以时间开头的文本
			r'^星期[一二三四五六日][\s\S]*$',  # 以星期开头的文本
			r'^\d{1,2}月\d{1,2}日[\s\S]*$',  # 以日期开头的文本
			r'^\d{4}年\d{1,2}月\d{1,2}日[\s\S]*$',  # 以完整日期开头的文本
		]
		is_timestamp = any(re.match(pattern, text) for pattern in time_patterns)
		if not is_timestamp:
			return False
		if block is not None:
			center_x = block.get("center_x", 0)
			y = block.get("y", 0)
			bottom = block.get("bottom", 0)
			image_min_x = block.get("image_min_x", 0)
			image_width = block.get("image_width", 0)
			image_min_y = block.get("image_min_y", 0)
			image_height = block.get("image_height", 0)
			
			if image_width > 0 and image_height > 0:
				# 检查X位置：时间戳通常在屏幕中央（聊天框外）
				image_center_absolute = image_min_x + image_width / 2
				center_range = image_width * 0.4
				distance_from_center = abs(center_x - image_center_absolute)
				is_centered_x = distance_from_center <= center_range
				
				# 检查Y位置：时间戳通常在屏幕顶部或底部（不在聊天框内）
				# 顶部区域：前15% 或 底部区域：后15%（放宽阈值）
				y_ratio = (y - image_min_y) / image_height if image_height > 0 else 0.5
				is_in_top_bottom = y_ratio < 0.15 or y_ratio > 0.85
				
				# 检查文本长度：时间戳通常很短（小于20个字符）
				is_short_text = len(text) <= 20
				
				# 如果时间戳在屏幕中央（X）或不在聊天区域（Y），且文本较短，则过滤
				# 更严格的过滤：只要满足以下任一条件就过滤：
				# 1. X居中且文本较短
				# 2. 在顶部/底部区域且文本较短
				# 3. X居中且在顶部/底部区域（无论文本长度）
				if (is_centered_x and is_short_text) or (is_in_top_bottom and is_short_text) or (is_centered_x and is_in_top_bottom):
					return True
				else:
					# 时间戳在聊天框内，保留
					return False
			else:
				return True
		else:
			return True

	@staticmethod
	def optimize_image_bytes(image_bytes: bytes, image_format: str) -> tuple[bytes, str, dict]:
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
				im.save(out, format='JPEG', quality=80, optimize=True)
				data = out.getvalue()
				return data, 'jpeg', {"orig_bytes": len(image_bytes), "opt_bytes": len(data), "size": [w, h]}
		except Exception:
			return image_bytes, image_format, {"orig_bytes": len(image_bytes), "opt_bytes": len(image_bytes)}

	@staticmethod
	def parse_ocr_response(content: str) -> tuple[str, Dict[str, Any]]:
		try:
			if "**对话内容：**" in content:
				text_start = content.find("**对话内容：**") + len("**对话内容：**")
				text_end = content.find("**识别信息：**", text_start)
				if text_end == -1:
					text_end = len(content)
				text_content = content[text_start:text_end].strip()
			else:
				text_content = content.strip()
			metadata = {
				"confidence": 0.9,
				"language": "中文",
				"dialogue_rounds": 1,
				"raw_response": content
			}
			return text_content, metadata
		except Exception as e:
			logger.warning(f"解析OCR响应失败，使用原始内容: {e}")
			return content.strip(), {"confidence": 0.8, "language": "中文"}
    
	@staticmethod
	def should_abort(cancel_event: Optional["asyncio.Event"]) -> bool:
		try:
			import asyncio  # 局部导入避免顶层依赖
			return bool(cancel_event and cancel_event.is_set())
		except Exception:
			return False


class VolcOCRService:
	"""火山引擎OCR服务（独立实现）。"""
	def __init__(self):
		self.volc_access_key_id = settings.volc_access_key_id
		self.volc_secret_access_key = settings.volc_secret_access_key
		self.volc_region = settings.volc_region
		has_visual_service = VisualService is not None
		has_access_key = bool(self.volc_access_key_id and self.volc_access_key_id.strip())
		has_secret_key = bool(self.volc_secret_access_key and self.volc_secret_access_key.strip())
		self.use_volc_ocr = has_access_key and has_secret_key and has_visual_service
		self.volc_visual_service = None
		if self.use_volc_ocr and VisualService:
			try:
				self.volc_visual_service = VisualService()
				if hasattr(self.volc_visual_service, 'set_ak'):
					self.volc_visual_service.set_ak(self.volc_access_key_id)
				if hasattr(self.volc_visual_service, 'set_sk'):
					self.volc_visual_service.set_sk(self.volc_secret_access_key)
				if hasattr(self.volc_visual_service, 'set_region'):
					self.volc_visual_service.set_region(self.volc_region)
			except Exception as e:
				logger.error(f"[OCR][volc] 初始化失败: {e}")
				self.use_volc_ocr = False

	async def extract_text_from_images(self, images_data: list[bytes], image_formats: list[str], cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		if not image_formats:
			image_formats = ["png"] * len(images_data)
		return await self._extract_with_volc_ocr(images_data, image_formats, cancel_event)

	async def extract_text_from_image(self, image_data: bytes, image_format: str = "png", cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		return await self._extract_with_volc_ocr([image_data], [image_format], cancel_event)

	async def _volc_ocr_recognition_raw(self, image_data: bytes) -> Dict[str, Any]:
		try:
			if not self.use_volc_ocr or not self.volc_visual_service:
				raise Exception("未配置火山引擎OCR，请在.env文件中设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY")
			image_base64 = base64.b64encode(image_data).decode('utf-8')
			params = {"image_base64": image_base64}
			import asyncio
			loop = asyncio.get_event_loop()
			def call_ocr():
				if hasattr(self.volc_visual_service, 'ocr_normal'):
					return self.volc_visual_service.ocr_normal(params)
				elif hasattr(self.volc_visual_service, 'ocr_general'):
					return self.volc_visual_service.ocr_general(params)
				elif hasattr(self.volc_visual_service, 'request'):
					return self.volc_visual_service.request("OCRNormal", "2020-08-26", params)
				else:
					raise Exception("火山引擎SDK未找到可用的OCR方法，请检查SDK版本")
			result = await loop.run_in_executor(None, call_ocr)
			if "ResponseMetadata" in result and result.get("ResponseMetadata", {}).get("Error"):
				error_info = result["ResponseMetadata"]["Error"]
				raise Exception(f"火山引擎OCR识别失败 [{error_info.get('Code','Unknown')}] : {error_info.get('Message','未知错误')}")
			if "Result" in result:
				volc_result = {"code": 10000, "data": result["Result"], "message": "Success"}
			elif "data" in result and result.get("code") == 10000:
				volc_result = result
			else:
				volc_result = {"code": 10000, "data": result, "message": "Success"}
			return volc_result
		except Exception as e:
			logger.error(f"火山引擎OCR调用失败: {e}")
			raise Exception(f"火山引擎OCR识别失败: {str(e)}")

	async def _extract_with_volc_ocr(self, images_data: list[bytes], image_formats: list[str], cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		try:
			if not self.use_volc_ocr:
				raise Exception("未配置火山引擎OCR，请在.env文件中设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY")
			import asyncio
			t_ocr0 = time.perf_counter()
			# 进度事件（供前端显示进度条）
			progress_events: list[dict] = []
			# 串行处理多张图片，避免并发调用导致的问题（火山引擎OCR SDK可能不支持并发）
			# 添加重试机制，确保所有图片都能识别
			ocr_results = []
			for idx, img in enumerate(images_data):
				if OCRUtils.should_abort(cancel_event):
					raise asyncio.CancelledError()
				# 记录开始事件
				progress_events.append({
					"type": "start",
					"image_index": idx + 1,
					"total": len(images_data),
					"progress": round((idx) / max(1, len(images_data)) * 100, 1)
				})
				
				# 重试机制：最多重试3次（指数退避+抖动）
				max_retries = 3
				result = None
				last_error = None
				
				for retry in range(max_retries + 1):
					try:
						if retry > 0:
							# 退避时间：0.4s, 0.8s, 1.2s，并加入±80ms抖动
							base = 0.4 * retry
							jitter = (retry * 37) % 80 / 1000.0
							await asyncio.sleep(base + jitter)
						
						result = await self._volc_ocr_recognition_raw(img)
						
						# 检查结果是否有效（有数据）
						data = result.get("data", {}) if isinstance(result, dict) else {}
						line_texts = data.get("line_texts", [])
						image_blocks_data = data.get("image_blocks", [])
						image_regions = data.get("image_regions", [])
						
						# 如果没有任何内容，记录详细信息并重试
						if not line_texts and not image_blocks_data and not image_regions:
							if retry < max_retries:
								logger.warning(f"[OCR][volc][warn] 图片 {idx+1} 返回空结果，准备重试。原始数据: {_json.dumps(data, ensure_ascii=False)[:200]}")
								last_error = Exception(f"图片 {idx+1} 返回空结果")
								progress_events.append({
									"type": "retry",
									"image_index": idx + 1,
									"retry": retry + 1
								})
								continue
							else:
								logger.error(f"[OCR][volc][error] 图片 {idx+1} 重试 {max_retries} 次后仍返回空结果。原始数据: {_json.dumps(data, ensure_ascii=False)[:500]}")
								last_error = Exception(f"图片 {idx+1} 重试后仍返回空结果")
								break
						
						# 成功获取到内容
						ocr_results.append(result)
						progress_events.append({
							"type": "done",
							"image_index": idx + 1,
							"progress": round((idx + 1) / max(1, len(images_data)) * 100, 1),
							"lines": len(line_texts),
							"image_blocks": len(image_blocks_data),
							"regions": len(image_regions)
						})
						break
						
					except Exception as e:
						last_error = e
						if retry < max_retries:
							logger.warning(f"[OCR][volc][error] 图片 {idx+1} OCR识别失败，准备重试: {e}")
							progress_events.append({
								"type": "retry",
								"image_index": idx + 1,
								"retry": retry + 1,
								"reason": str(e)[:120]
							})
							continue
						else:
							logger.error(f"[OCR][volc][error] 图片 {idx+1} OCR识别失败，已重试 {max_retries} 次: {e}")
							break
				
				# 如果所有重试都失败，添加错误到结果
				if result is None or last_error:
					ocr_results.append(last_error if last_error else Exception(f"图片 {idx+1} 识别失败"))
					progress_events.append({
						"type": "fail",
						"image_index": idx + 1,
						"progress": round((idx + 1) / max(1, len(images_data)) * 100, 1),
						"reason": str(last_error)[:200] if last_error else "unknown"
					})
			t_ocr1 = time.perf_counter()
			logger.info(f"[OCR][volc] 火山引擎OCR识别耗时: {(t_ocr1 - t_ocr0):.2f}s; 图片数={len(images_data)}")
			all_blocks: list[dict] = []
			failed_images: list[int] = []
			for idx, ocr_result in enumerate(ocr_results):
				if OCRUtils.should_abort(cancel_event):
					raise asyncio.CancelledError()
				if isinstance(ocr_result, Exception):
					logger.warning(f"[OCR][volc][error] 图片 {idx+1} OCR识别失败: {ocr_result}")
					failed_images.append(idx+1)
					continue
				data = ocr_result.get("data", {}) if isinstance(ocr_result, dict) else {}
				line_texts = data.get("line_texts", [])
				line_rects = data.get("line_rects", [])
				line_probs = data.get("line_probs", [])
				polygons = data.get("polygons", [])
				# 检查是否有图片块信息
				image_blocks_data = data.get("image_blocks", [])
				image_regions = data.get("image_regions", [])
				
				# 记录OCR返回的原始数据结构（用于调试，仅在错误时记录）
				if not line_texts and not image_blocks_data and not image_regions:
					# 检查是否有其他可能的文本字段
					for key in ["words", "text", "texts", "content", "lines"]:
						if key in data and data[key]:
							logger.warning(f"[OCR][volc] 图片 {idx+1} 发现未处理的文本字段 '{key}'")
				
				# 提取文本块
				text_blocks = []
				if line_texts:
					text_blocks = self._extract_volc_blocks(
						line_texts, line_rects, line_probs, polygons, [], 0, 0, idx+1
					)
				
				# 提取图片块
				image_blocks = []
				if image_blocks_data:
					for img_block in image_blocks_data:
						if isinstance(img_block, dict):
							x = int(img_block.get("x", 0))
							y = int(img_block.get("y", 0))
							width = int(img_block.get("width", 0))
							height = int(img_block.get("height", 0))
							if width > 0 and height > 0:
								image_blocks.append({
									"text": "[图片]",
									"x": x, "y": y, "width": width, "height": height,
									"right": x + width, "bottom": y + height,
									"center_x": x + width / 2, "center_y": y + height / 2,
									"image_index": idx + 1, "confidence": 0.9,
									"is_image": True
								})
				
				if image_regions:
					for img_region in image_regions:
						if isinstance(img_region, dict):
							x = int(img_region.get("x", 0))
							y = int(img_region.get("y", 0))
							width = int(img_region.get("width", 0))
							height = int(img_region.get("height", 0))
							if width > 0 and height > 0:
								image_blocks.append({
									"text": "[图片]",
									"x": x, "y": y, "width": width, "height": height,
									"right": x + width, "bottom": y + height,
									"center_x": x + width / 2, "center_y": y + height / 2,
									"image_index": idx + 1, "confidence": 0.9,
									"is_image": True
								})
				
				# 如果没有文本块也没有图片块，记录警告
				if not text_blocks and not image_blocks:
					logger.warning(f"[OCR][volc][warn] 图片 {idx+1} 未识别到文字或图片")
				
				all_blocks.extend(text_blocks)
				all_blocks.extend(image_blocks)
			logger.info(f"[OCR][volc][process] 总共提取了 {len(all_blocks)} 个文字块，失败的图片: {failed_images}")
			if not all_blocks:
				error_msg = f"所有图片OCR识别失败" if failed_images else "未识别到任何文字"
				return OCRResponse(text="", confidence=0.0, language="mixed", metadata={
					"confidence": 0.0,
					"language": "mixed",
					"structured_messages": [],
					"participants": [],
					"ocr_method": "volc_ocr",
					"word_count": 0,
					"failed_images": failed_images,
					"error": error_msg
				})
			if OCRUtils.should_abort(cancel_event):
				raise asyncio.CancelledError()
			
			# 按图片索引分组处理（多张图片需要分别处理，避免坐标混淆）
			all_messages: list[dict] = []
			all_text_content: list[str] = []
			
			# 按image_index分组，同时为所有图片创建空列表（确保所有图片都被处理）
			blocks_by_image: dict[int, list[dict]] = {}
			# 初始化所有图片的列表（确保所有图片都被处理，即使没有识别到内容）
			for img_idx in range(1, len(images_data) + 1):
				blocks_by_image[img_idx] = []
			
			# 将blocks分配到对应的图片
			for block in all_blocks:
				img_idx = block.get("image_index", 1)
				if img_idx not in blocks_by_image:
					blocks_by_image[img_idx] = []
				blocks_by_image[img_idx].append(block)
			
			# 按图片索引顺序处理每张图片（确保所有图片都被处理）
			for img_idx in sorted(blocks_by_image.keys()):
				if OCRUtils.should_abort(cancel_event):
					raise asyncio.CancelledError()
				image_blocks = blocks_by_image[img_idx]
				
				# 如果图片没有识别到任何内容，创建一个占位消息说明该图片没有识别到内容
				if not image_blocks:
					all_messages.append({
						"speaker_name": "系统",
						"speaker_side": "center",
						"text": f"[图片{img_idx}未识别到内容]",
						"_sort_y": 0,
						"image_index": img_idx,
						"is_placeholder": True
					})
					continue
				
				messages, text_content = self._process_volc_ocr_blocks(image_blocks)
				# 为每条消息添加图片索引
				for msg in messages:
					msg["image_index"] = img_idx
				all_messages.extend(messages)
				if text_content:
					all_text_content.append(text_content)
			
			# 按图片索引和Y坐标排序所有消息
			all_messages.sort(key=lambda m: (m.get("image_index", 0), m.get("_sort_y", 0)))
			
			# 合并文本内容
			text_content = "\n\n".join(all_text_content) if all_text_content else ""
			
			participants = sorted({m.get("speaker_name") for m in all_messages if m.get("speaker_name")})
			language = "mixed"
			if all(c.isascii() or (not c.isalpha()) for c in text_content):
				language = "英文"
			elif any('\u4e00' <= ch <= '\u9fff' for ch in text_content):
				language = "中文"
			metadata = {
				"confidence": 0.9,
				"language": language,
				"structured_messages": all_messages,
				"participants": participants,
				"ocr_method": "volc_ocr",
				"word_count": len(all_blocks),
				"failed_images": failed_images if failed_images else None,
				"progress": {
					"total_images": len(images_data),
					"events": progress_events
				}
			}
			return OCRResponse(text=text_content, confidence=0.9, language=language, metadata=metadata)
		except Exception as e:
			logger.error(f"火山引擎OCR识别失败: {e}")
			raise Exception(f"图片识别失败: {str(e)}")

	def _extract_volc_blocks(self, line_texts: List[str], line_rects: List[Dict], line_probs: List[float], polygons: List[List], chars: List[List], image_width: int, image_height: int, image_index: int) -> List[Dict]:
		blocks: list[dict] = []
		for i, text in enumerate(line_texts):
			if not text or not text.strip():
				continue
			rect = line_rects[i] if i < len(line_rects) else {}
			prob = line_probs[i] if i < len(line_probs) else 0.9
			if isinstance(rect, dict) and rect:
				x = int(rect.get("x", 0)); y = int(rect.get("y", 0)); width = int(rect.get("width", 0)); height = int(rect.get("height", 0))
			elif i < len(polygons) and polygons[i] and isinstance(polygons[i], list):
				polygon = polygons[i]
				if len(polygon) >= 4:
					xs = [p[0] for p in polygon if len(p) >= 2]
					ys = [p[1] for p in polygon if len(p) >= 2]
					if xs and ys:
						x = min(xs); y = min(ys); width = max(xs) - x; height = max(ys) - y
					else:
						continue
				else:
					continue
			else:
				continue
			if width <= 0 or height <= 0:
				continue
			right = x + width; bottom = y + height
			center_x = x + width / 2; center_y = y + height / 2
			blocks.append({
				"text": text.strip(), "x": x, "y": y, "width": width, "height": height,
				"right": right, "bottom": bottom, "center_x": center_x, "center_y": center_y,
				"image_index": image_index, "confidence": prob
			})
		return blocks

	def _process_volc_ocr_blocks(self, blocks: list[dict]) -> tuple[list[dict], str]:
		"""
		处理火山OCR识别的文字块，识别角色并组装成聊天消息。
		改进算法：
		1. 使用多种特征准确识别己方和对方
		2. 智能合并聊天气泡，处理长内容和多段内容
		3. 正确处理只有单方消息的情况
		"""
		if not blocks:
			return [], ""
		
		# 计算图片尺寸
		max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
		min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
		image_width = max_x - min_x
		
		# 计算图片高度（用于时间戳过滤）
		max_y_temp = max(b.get("bottom", 0) for b in blocks) if blocks else 0
		min_y_temp = min(b.get("y", 0) for b in blocks) if blocks else 0
		image_height_temp = max(100, (max_y_temp - min_y_temp) if max_y_temp > min_y_temp else 100)
		
		# 过滤噪声文本（时间戳等），但保留图片块
		# 先计算所有块的位置信息，用于时间戳过滤
		filtered_blocks = []
		for block in blocks:
			# 图片块直接保留，不过滤
			if block.get("is_image", False):
				filtered_blocks.append(block)
				continue
			text = block.get("text", "").strip()
			# 检查是否为时间戳（更严格的检查）
			block_with_info = {
				**block, 
				"image_width": image_width, 
				"image_min_x": min_x,
				"image_height": image_height_temp,
				"image_min_y": min_y_temp
			}
			# 如果检测到时间戳，直接过滤（无论位置）
			if OCRUtils.filter_noise_text(text, block_with_info):
				continue
			# 额外检查：如果文本是纯时间格式且很短（<=10字符），更严格地过滤
			if len(text) <= 10:
				time_patterns_strict = [
					r'^\d{1,2}:\d{2}$',
					r'^\d{1,2}:\d{2}:\d{2}$',
					r'^\d{1,2}[：:]\d{2}$',
					r'^\d{1,2}[：:]\d{2}[：:]\d{2}$',
				]
				is_time_format = any(re.match(pattern, text) for pattern in time_patterns_strict)
				if is_time_format:
					# 检查位置：如果中心位置在图片中间或右侧，很可能是聊天框外的时间戳
					center_x = block.get("center_x", 0)
					center_ratio = (center_x - min_x) / image_width if image_width > 0 else 0.5
					# 如果时间戳在中间区域（25%-75%），很可能是聊天框外的时间戳
					# 或者如果时间戳在右侧（>60%），也很可能是聊天框外的时间戳
					if 0.25 < center_ratio < 0.75 or center_ratio > 0.60:
						continue
			filtered_blocks.append(block)
		
		if not filtered_blocks:
			return [], ""
		
		# 按Y坐标排序
		blocks = sorted(filtered_blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
		
		# 计算图片高度
		max_x = max(b.get("right", 0) for b in blocks)
		min_x = min(b.get("x", 0) for b in blocks)
		max_y = max(b.get("bottom", 0) for b in blocks)
		min_y = min(b.get("y", 0) for b in blocks)
		image_height = max(100, (max_y - min_y) if max_y > min_y else 100)
		image_width = max_x - min_x
		
		# 改进的角色识别：使用多种特征
		left_blocks, right_blocks, has_both_sides = self._identify_speakers(blocks, image_width, image_height)
		
		# 组装所有消息
		all_messages: list[dict] = []
		
		# 处理左测（对方）消息
		if left_blocks:
			left_blocks = sorted(left_blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
			bubbles = self._merge_volc_bubbles(left_blocks, "对方", "left", image_width, image_height)
			for bubble in bubbles:
				bubble_text = (bubble.get("text") or "").strip()
				bubble_y = bubble.get("top", 0)
				if bubble.get("blocks"):
					bubble_y = bubble["blocks"][0].get("y", 0)
				# 检查是否为图片块
				is_image_bubble = any(b.get("is_image", False) for b in bubble.get("blocks", []))
				if not bubble_text and not is_image_bubble:
					continue
				all_messages.append({
					"speaker_name": "对方",
					"speaker_side": "left",
					"text": bubble_text if bubble_text else "[图片]",
					"_sort_y": bubble_y,
					"is_image": is_image_bubble
				})
		
		# 处理右侧（己方）消息
		if right_blocks:
			right_blocks = sorted(right_blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
			bubbles = self._merge_volc_bubbles(right_blocks, "我", "right", image_width, image_height)
			for bubble in bubbles:
				bubble_text = (bubble.get("text") or "").strip()
				bubble_y = bubble.get("top", 0)
				if bubble.get("blocks"):
					bubble_y = bubble["blocks"][0].get("y", 0)
				# 检查是否为图片块
				is_image_bubble = any(b.get("is_image", False) for b in bubble.get("blocks", []))
				if not bubble_text and not is_image_bubble:
					continue
				all_messages.append({
					"speaker_name": "己方",
					"speaker_side": "right",
					"text": bubble_text if bubble_text else "[图片]",
					"_sort_y": bubble_y,
					"is_image": is_image_bubble
				})
		
		# 按Y坐标排序所有消息
		all_messages.sort(key=lambda m: m.get("_sort_y", 0))
		
		# 添加索引
		for i, msg in enumerate(all_messages):
			msg["block_index"] = i + 1
			msg.pop("_sort_y", None)
		
		# 生成文本内容（多段文本之间不需要空行）
		text_content = "\n".join([m.get("text", "").strip() for m in all_messages if m.get("text")])
		
		return all_messages, text_content
	
	def _identify_speakers(self, blocks: list[dict], image_width: float, image_height: float) -> tuple[list[dict], list[dict], bool]:
		"""
		识别说话人角色（己方/对方）。
		使用多种特征进行准确识别：
		1. 位置特征：左对齐vs右对齐
		2. 中心位置分布
		3. 宽度特征
		4. 文本特征
		5. 适配非常规尺寸截图（宽屏等）
		
		返回: (left_blocks, right_blocks, has_both_sides)
		"""
		if not blocks:
			return [], [], False
		
		# 计算图片宽高比，用于调整阈值
		aspect_ratio = image_width / image_height if image_height > 0 else 1.0
		is_wide = aspect_ratio > 1.5  # 宽屏截图（宽高比大于1.5）
		is_portrait = aspect_ratio < 0.8  # 竖屏截图（宽高比小于0.8）
		
		# 计算文本块的实际分布范围（有效文本区域）
		min_x = min(b.get("x", 0) for b in blocks)
		max_x = max(b.get("right", 0) for b in blocks)
		text_range = max_x - min_x
		text_range_ratio = text_range / image_width if image_width > 0 else 1.0
		
		# 计算文本区域的中心位置（相对于图片）
		text_center_x = (min_x + max_x) / 2
		text_center_ratio = text_center_x / image_width if image_width > 0 else 0.5
		
		# 根据宽高比和文本分布动态调整阈值
		if is_wide:
			# 宽屏截图：使用更小的阈值，因为文本区域可能只占图片的一部分
			left_threshold = 0.35  # 从0.4调整为0.35
			right_threshold = 0.65  # 从0.6调整为0.65
			center_threshold_left = 0.30  # 明显偏左
			center_threshold_right = 0.70  # 明显偏右
			max_right_threshold = 0.60  # 从0.65调整为0.60
			min_left_threshold = 0.40  # 从0.35调整为0.40
			center_diff_threshold = 0.20  # 从0.25调整为0.20
		elif is_portrait:
			# 竖屏截图：使用标准阈值
			left_threshold = 0.4
			right_threshold = 0.6
			center_threshold_left = 0.35
			center_threshold_right = 0.65
			max_right_threshold = 0.65
			min_left_threshold = 0.35
			center_diff_threshold = 0.25
		else:
			# 标准截图：使用原始阈值
			left_threshold = 0.4
			right_threshold = 0.6
			center_threshold_left = 0.4
			center_threshold_right = 0.6
			max_right_threshold = 0.65
			min_left_threshold = 0.35
			center_diff_threshold = 0.25
		
		# 早期判断：检查左边缘和右边缘位置（最可靠的方法）
		# 对于完整的聊天块，左边缘位置是最可靠的指标
		all_left_positions = [b.get("x", 0) / image_width if image_width > 0 else 0.0 for b in blocks]
		all_right_positions = [min(b.get("right", 0) / image_width, 1.0) if image_width > 0 else 1.0 for b in blocks]  # 限制右边缘不超过1.0
		
		min_left_pos_all = min(all_left_positions) if all_left_positions else 0.5
		max_right_pos_all = max(all_right_positions) if all_right_positions else 0.5
		max_left_pos_all = max(all_left_positions) if all_left_positions else 0.5
		min_right_pos_all = min(all_right_positions) if all_right_positions else 0.5
		
		# 计算左边缘和右边缘的标准差（用于判断对齐一致性）
		left_std_all = self._calculate_std(all_left_positions) if len(all_left_positions) > 1 else 0.0
		right_std_all = self._calculate_std(all_right_positions) if len(all_right_positions) > 1 else 0.0
		
		
		# 计算整体范围：如果左边缘范围很大（>0.7），说明有左右两侧的消息，不是单方消息
		left_range = max_left_pos_all - min_left_pos_all
		right_range = max_right_pos_all - min_right_pos_all
		
		# 策略1（最高优先级）: 如果左边缘标准差很小（左对齐一致），且最小左边缘在左侧，且范围不太大，肯定是对方消息
		# 这是最可靠的判断方法，因为左对齐一致性是对方消息的最强信号
		left_std_threshold = 0.08  # 左对齐一致性阈值
		left_pos_threshold = 0.50  # 左边缘位置阈值（放宽，因为头像可能占据空间）
		left_range_threshold = 0.6  # 左边缘范围阈值（如果范围太大，说明有双方消息）
		
		if left_std_all < left_std_threshold and min_left_pos_all < left_pos_threshold and left_range < left_range_threshold:
			return blocks, [], False
		elif left_range >= left_range_threshold:
			pass  # 跳过早期单方检测
		
		# 策略2: 如果右边缘标准差很小（右对齐一致），且最小右边缘在右侧，肯定是己方消息
		right_std_threshold = 0.08
		right_pos_threshold = 0.50
		if right_std_all < right_std_threshold and min_right_pos_all > right_pos_threshold:
			return [], blocks, False
		
		# 策略3: 如果左边缘标准差小且左边缘整体在左侧，且范围不太大，肯定是对方消息
		if left_std_all < 0.12 and left_range < 0.6:  # 左对齐一致性较好且范围不太大
			# 计算左边缘的平均位置
			left_mean_all = sum(all_left_positions) / len(all_left_positions) if all_left_positions else 0.5
			if left_mean_all < 0.50:  # 平均左边缘在图片左侧
				return blocks, [], False
		
		# 策略4: 如果右边缘标准差小且右边缘整体在右侧，肯定是己方消息
		if right_std_all < 0.12:  # 右对齐一致性较好
			# 计算右边缘的平均位置
			right_mean_all = sum(all_right_positions) / len(all_right_positions) if all_right_positions else 0.5
			if right_mean_all > 0.50:  # 平均右边缘在图片右侧
				return [], blocks, False
		
		# 如果文本区域很窄（小于图片宽度的50%），可能是单方消息
		if text_range_ratio < 0.5:
			# 根据文本中心位置判断（对宽屏使用更严格的阈值）
			left_threshold_for_narrow = 0.35 if is_wide else 0.4
			right_threshold_for_narrow = 0.65 if is_wide else 0.6
			if text_center_ratio < left_threshold_for_narrow:
				return blocks, [], False
			elif text_center_ratio > right_threshold_for_narrow:
				return [], blocks, False
		
		# 提取特征（再次过滤时间戳，以防遗漏）
		features = []
		# 计算所有块的位置范围，用于时间戳过滤
		min_x_all = min(b.get("x", 0) for b in blocks) if blocks else 0
		max_x_all = max(b.get("right", 0) for b in blocks) if blocks else 0
		min_y_all = min(b.get("y", 0) for b in blocks) if blocks else 0
		max_y_all = max(b.get("bottom", 0) for b in blocks) if blocks else 0
		image_width_all = max_x_all - min_x_all
		image_height_all = max(max_y_all - min_y_all, 100)
		
		for block in blocks:
			# 再次检查是否为时间戳（更严格的检查）
			text = block.get("text", "").strip()
			# 检查是否为时间格式
			time_patterns_strict = [
				r'^\d{1,2}:\d{2}$',
				r'^\d{1,2}:\d{2}:\d{2}$',
				r'^\d{1,2}[：:]\d{2}$',
				r'^\d{1,2}[：:]\d{2}[：:]\d{2}$',
			]
			is_time_format = any(re.match(pattern, text) for pattern in time_patterns_strict)
			# 如果是时间格式且很短，直接过滤（无论位置）
			if is_time_format and len(text) <= 10:
				continue
			# 使用filter_noise_text检查
			if OCRUtils.filter_noise_text(text, {
				**block, 
				"image_width": image_width_all, 
				"image_min_x": min_x_all,
				"image_height": image_height_all,
				"image_min_y": min_y_all
			}):
				continue
			# 额外检查：如果时间戳在右侧（>60%），很可能是误判为己方的时间戳
			if is_time_format:
				center_x = block.get("center_x", 0)
				center_ratio = (center_x - min_x_all) / image_width_all if image_width_all > 0 else 0.5
				if center_ratio > 0.60:
					continue
			
			x = block.get("x", 0)
			right = block.get("right", 0)
			center_x = block.get("center_x", 0)
			width = block.get("width", 0)
			
			# 特征向量：
			# 1. 中心位置（归一化到0-1）
			center_pos = (center_x / image_width) if image_width > 0 else 0.5
			# 2. 距离右边缘的距离
			dist_from_right = image_width - right if image_width > 0 else 0
			# 3. 距离左边缘的距离
			dist_from_left = x
			# 4. 左边缘位置（归一化）
			left_pos = (x / image_width) if image_width > 0 else 0.0
			# 5. 右边缘位置（归一化）
			right_pos = (right / image_width) if image_width > 0 else 1.0
			
			features.append({
				"block": block,
				"center_pos": center_pos,
				"dist_from_right": dist_from_right,
				"dist_from_left": dist_from_left,
				"left_pos": left_pos,
				"right_pos": right_pos,
				"center_x": center_x,
				"x": x,
				"right": right
			})
		
		# 使用改进的聚类方法识别左右两侧
		center_positions = [f["center_pos"] for f in features]
		left_positions = [f["left_pos"] for f in features]
		right_positions = [f["right_pos"] for f in features]
		
		# 改进的单方消息检测：使用多个指标
		if len(center_positions) > 0:
			center_std = self._calculate_std(center_positions)
			center_mean = sum(center_positions) / len(center_positions)
			left_std = self._calculate_std(left_positions)
			right_std = self._calculate_std(right_positions)
			
			# 计算左边缘和右边缘的平均位置
			left_mean = sum(left_positions) / len(left_positions)
			right_mean = sum(right_positions) / len(right_positions)
			
			# 更严格的单方消息检测条件：
			# 1. 中心位置标准差小（位置集中）
			# 2. 左边缘标准差小（左对齐一致）
			# 3. 右边缘标准差小（右对齐一致）
			# 4. 或者整体位置明显偏左或偏右
			
			is_single_side = False
			single_side_side = None  # "left" 或 "right"
			
			# 优先检查左对齐（左边缘一致性是最可靠的指标）
			# 条件1: 左边缘标准差小，且大部分块都在左侧（优先级最高）
			min_left_pos = min(left_positions)
			max_right_pos = max(right_positions)
			
			# 首先检查左边缘位置（最可靠）
			# 对于宽屏截图，使用更宽松的阈值
			left_threshold_check = 0.35 if is_wide else 0.25
			right_threshold_check = 0.65 if is_wide else 0.75
			if min_left_pos < left_threshold_check:  # 左边缘在阈值以内，认为是对方
				if max_right_pos < right_threshold_check:  # 右边缘不超过阈值，确保不是居中
					is_single_side = True
					single_side_side = "left"
			
			# 如果左边缘标准差小，且大部分块都在左侧
			if not is_single_side and left_std < 0.12 and left_mean < left_threshold:  # 放宽左边缘标准差阈值
				# 检查是否所有块的右边缘都不超过阈值
				# 对于宽屏截图，如果左边缘靠近图片左侧，且右边缘不超过阈值，肯定是左对齐
				if is_wide:
					if min_left_pos < 0.20 and max_right_pos < max_right_threshold:
						is_single_side = True
						single_side_side = "left"
					elif max_right_pos < max_right_threshold:
						is_single_side = True
						single_side_side = "left"
				else:
					if max_right_pos < max_right_threshold:
						is_single_side = True
						single_side_side = "left"
			
			# 条件2: 检查右边缘位置（但需要确保不是左对齐的消息）
			# 只有在左对齐检查都失败的情况下，才检查右对齐
			if not is_single_side and right_std < 0.12 and right_mean > 0.50:  # 右对齐一致且平均位置在右侧
				if min_left_pos > 0.40:  # 左边缘超过40%，确保不是左对齐的消息
					is_single_side = True
					single_side_side = "right"
			
			# 条件3: 右边缘标准差小，且大部分块都在右侧
			if not is_single_side and right_std < 0.12 and right_mean > right_threshold:
				# 检查是否所有块的左边缘都不小于阈值
				# 对于宽屏截图，如果右边缘靠近图片右侧（大于0.85），且左边缘不小于阈值，肯定是右对齐
				if is_wide:
					if max_right_pos > 0.80 and min_left_pos > min_left_threshold:
						is_single_side = True
						single_side_side = "right"
					elif min_left_pos > min_left_threshold:
						is_single_side = True
						single_side_side = "right"
				else:
					if min_left_pos > min_left_threshold:
						is_single_side = True
						single_side_side = "right"
			
			# 条件4: 中心位置标准差小，且位置明显偏左或偏右（作为补充判断）
			if not is_single_side:
				std_threshold = 0.10 if is_wide else 0.12
				if center_std < std_threshold:
					if center_mean < center_threshold_left:  # 明显偏左
						is_single_side = True
						single_side_side = "left"
					elif center_mean > center_threshold_right:  # 明显偏右
						is_single_side = True
						single_side_side = "right"
			
			# 如果检测到单方消息，直接返回
			if is_single_side:
				if single_side_side == "left":
					return [f["block"] for f in features], [], False
				else:
					return [], [f["block"] for f in features], False
		
		# 方法2: 使用K-means聚类（改进版）
		# 使用右边缘距离和中心位置进行聚类
		right_distances = [f["dist_from_right"] for f in features]
		
		if len(right_distances) < 2:
			# 只有一个块，根据位置判断（考虑宽高比）
			f = features[0]
			# 优先检查左边缘位置（最可靠）
			if f["left_pos"] < 0.25:  # 左边缘在图片左侧25%以内，认为是对方
				if f["right_pos"] < 0.75:  # 右边缘不超过75%，确保不是居中
					return [f["block"]], [], False
			# 检查右边缘位置
			if f["right_pos"] > 0.75:  # 右边缘在图片右侧25%以内，认为是己方
				if f["left_pos"] > 0.25:  # 左边缘超过25%，确保不是居中
					return [], [f["block"]], False
			# 否则根据中心位置判断
			center_threshold = 0.40 if is_wide else 0.5  # 宽屏使用更小的阈值
			if f["center_pos"] < center_threshold:
				return [f["block"]], [], False
			else:
				return [], [f["block"]], False
		
		# K-means聚类（自适应）
		labels = self._kmeans_cluster_2d(right_distances, center_positions, max_iterations=30)
		
		# 分离两组
		group0 = [f["block"] for i, f in enumerate(features) if labels[i] == 0]
		group1 = [f["block"] for i, f in enumerate(features) if labels[i] == 1]
		
		# 判断哪组是左（对方），哪组是右（己方）
		# 计算每组的平均中心位置和位置范围
		group0_centers = [f["center_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group1_centers = [f["center_pos"] for i, f in enumerate(features) if labels[i] == 1]
		
		group0_lefts = [f["left_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group0_rights = [f["right_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group1_lefts = [f["left_pos"] for i, f in enumerate(features) if labels[i] == 1]
		group1_rights = [f["right_pos"] for i, f in enumerate(features) if labels[i] == 1]
		
		group0_mean_center = sum(group0_centers) / len(group0_centers) if group0_centers else 0.5
		group1_mean_center = sum(group1_centers) / len(group1_centers) if group1_centers else 0.5
		
		group0_max_right = max(group0_rights) if group0_rights else 0.5
		group1_max_right = max(group1_rights) if group1_rights else 0.5
		group0_min_left = min(group0_lefts) if group0_lefts else 0.5
		group1_min_left = min(group1_lefts) if group1_lefts else 0.5
		
		# 检查是否有块跨越中心线（可能是长消息被错误分类）
		# 对于长消息，如果左边缘在左侧但右边缘超过了中心线，应该根据左边缘判断
		image_center = 0.5
		for i, f in enumerate(features):
			left_pos = f["left_pos"]
			right_pos = f["right_pos"]
			# 如果块的左边缘在左侧（<0.4）但右边缘超过了中心线（>0.5），可能是对方的长消息
			if left_pos < 0.4 and right_pos > image_center:
				# 根据左边缘位置重新分类：如果左边缘明显在左侧，应该是对方
				if left_pos < 0.3:
					# 强制分类为左组（对方）
					if labels[i] == 1:
						labels[i] = 0
			# 如果块的右边缘在右侧（>0.6）但左边缘在中心线左侧（<0.5），可能是己方的长消息
			elif right_pos > 0.6 and left_pos < image_center:
				# 根据右边缘位置重新分类：如果右边缘明显在右侧，应该是己方
				if right_pos > 0.7:
					# 强制分类为右组（己方）
					if labels[i] == 0:
						labels[i] = 1
		
		# 重新分离两组（基于更新后的labels）
		group0 = [f["block"] for i, f in enumerate(features) if labels[i] == 0]
		group1 = [f["block"] for i, f in enumerate(features) if labels[i] == 1]
		
		# 重新计算（基于更新后的labels）
		group0_centers = [f["center_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group1_centers = [f["center_pos"] for i, f in enumerate(features) if labels[i] == 1]
		group0_lefts = [f["left_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group0_rights = [f["right_pos"] for i, f in enumerate(features) if labels[i] == 0]
		group1_lefts = [f["left_pos"] for i, f in enumerate(features) if labels[i] == 1]
		group1_rights = [f["right_pos"] for i, f in enumerate(features) if labels[i] == 1]
		group0_mean_center = sum(group0_centers) / len(group0_centers) if group0_centers else 0.5
		group1_mean_center = sum(group1_centers) / len(group1_centers) if group1_centers else 0.5
		group0_max_right = max(group0_rights) if group0_rights else 0.5
		group1_max_right = max(group1_rights) if group1_rights else 0.5
		group0_min_left = min(group0_lefts) if group0_lefts else 0.5
		group1_min_left = min(group1_lefts) if group1_lefts else 0.5
		
		# 中心位置较小的为左（对方），较大的为右（己方）
		if group0_mean_center < group1_mean_center:
			left_blocks = group0
			right_blocks = group1
			left_mean = group0_mean_center
			right_mean = group1_mean_center
			left_max_right = group0_max_right
			right_min_left = group1_min_left
		else:
			left_blocks = group1
			right_blocks = group0
			left_mean = group1_mean_center
			right_mean = group0_mean_center
			left_max_right = group1_max_right
			right_min_left = group0_min_left
		
		has_both_sides = len(left_blocks) > 0 and len(right_blocks) > 0
		
		# 更严格的单方消息验证：如果只有一方，但是聚类分成了两组，可能是误判
		if has_both_sides:
			# 条件1: 检查两组中心位置差异是否足够大
			center_diff = abs(left_mean - right_mean)
			
			# 条件2: 检查左组的最大右边缘是否明显小于右组的最小左边缘
			# 如果左组的最大右边缘和右组的最小左边缘重叠或接近，可能是单方
			overlap = left_max_right - right_min_left
			
			# 条件3: 检查是否有明显的左右分离
			# 对于宽屏截图，使用更小的分离阈值
			separation_threshold = 0.03 if is_wide else 0.05
			image_center = 0.5
			left_separated = left_max_right < image_center - separation_threshold  # 左组在中心左侧
			right_separated = right_min_left > image_center + separation_threshold  # 右组在中心右侧
			
			# 更严格的单方验证：检查左边缘对齐一致性
			# 如果左组的左边缘标准差很小，说明左对齐一致，应该是单方消息
			left_group_left_positions = [f["left_pos"] for i, f in enumerate(features) if labels[i] == (0 if group0_mean_center < group1_mean_center else 1)]
			left_group_right_positions = [f["right_pos"] for i, f in enumerate(features) if labels[i] == (0 if group0_mean_center < group1_mean_center else 1)]
			right_group_left_positions = [f["left_pos"] for i, f in enumerate(features) if labels[i] == (1 if group0_mean_center < group1_mean_center else 0)]
			right_group_right_positions = [f["right_pos"] for i, f in enumerate(features) if labels[i] == (1 if group0_mean_center < group1_mean_center else 0)]
			
			left_group_left_std = self._calculate_std(left_group_left_positions) if len(left_group_left_positions) > 1 else 0.0
			left_group_min_left = min(left_group_left_positions) if left_group_left_positions else 0.5
			left_group_max_right = max(left_group_right_positions) if left_group_right_positions else 0.5
			right_group_min_left = min(right_group_left_positions) if right_group_left_positions else 0.5
			right_group_max_right = max(right_group_right_positions) if right_group_right_positions else 0.5
			
			# 检查左组的分布范围：如果左组的右边缘范围很大（超过0.5），说明可能包含了双方消息
			left_group_range = left_group_max_right - left_group_min_left
			right_group_range = right_group_max_right - right_group_min_left
			
			# 检查两组之间的分离度：如果右组存在且明显分离，应该是双方消息
			groups_separation = right_group_min_left - left_group_max_right  # 右组左边缘 - 左组右边缘
			groups_overlap = left_group_max_right - right_group_min_left  # 如果 > 0，说明重叠
			
			# 检查右组是否合理：如果右组存在且范围合理，可能是双方消息
			right_group_valid = len(right_group_left_positions) > 0 and right_group_min_left > 0.5
			
			# 如果整体范围很大（>0.7），即使左组范围小，也可能是双方消息
			# 重新计算整体范围（可能有些块在早期检查中被过滤了）
			all_left_positions_all = [f["left_pos"] for f in features]
			all_right_positions_all = [f["right_pos"] for f in features]
			all_left_range = max(all_left_positions_all) - min(all_left_positions_all) if all_left_positions_all else 0.0
			all_right_range = max(all_right_positions_all) - min(all_right_positions_all) if all_right_positions_all else 0.0
			
			# 只有当左组左边缘对齐一致、范围小、不包含右边缘、且右组不存在或明显重叠时，才是单方消息
			if left_group_left_std < 0.08 and left_group_min_left < 0.35 and left_group_range < 0.6:
				# 如果右组存在且明显分离，应该是双方消息，不返回单方
				if right_group_valid and groups_separation > 0.1:
					pass  # 不返回，继续后续验证
				# 如果整体范围很大（>0.7），即使左组范围小，也可能是双方消息
				elif all_left_range > 0.7 or all_right_range > 0.7:
					pass  # 不返回，继续后续验证
				# 如果左组最大右边缘接近图片右侧（>0.7），可能是双方消息
				elif left_group_max_right > 0.7:
					pass  # 不返回，继续后续验证
				else:
					return [f["block"] for f in features], [], False
			else:
				pass  # 左组范围较大，继续验证
			
			# 如果中心位置差异太小，或者重叠太多，或者没有明显的左右分离，可能是单方
			# 但如果右组存在且分离明显，或者整体范围很大，应该是双方消息
			if center_diff < center_diff_threshold:  # 使用动态阈值
				# 如果之前检测到右组存在且分离明显，或整体范围很大，不判断为单方
				if right_group_valid and groups_separation > 0.1:
					pass  # 继续验证
				elif all_left_range > 0.7 or all_right_range > 0.7:
					pass  # 继续验证
				else:
					# 根据整体位置判断（考虑宽高比）
					overall_mean = (left_mean + right_mean) / 2
					center_threshold = 0.45 if is_wide else 0.5
					if overall_mean < center_threshold:
						return [f["block"] for f in features], [], False
					else:
						return [], [f["block"] for f in features], False
			
			# 对于宽屏截图，重叠检查更严格
			overlap_threshold = -0.05 if is_wide else -0.1
			if overlap > overlap_threshold:  # 如果重叠或接近
				# 如果之前检测到右组存在且分离明显，或整体范围很大，不判断为单方
				if right_group_valid and groups_separation > 0.1:
					pass  # 继续验证
				elif all_left_range > 0.7 or all_right_range > 0.7:
					pass  # 继续验证
				else:
					# 根据整体位置判断
					overall_mean = (left_mean + right_mean) / 2
					center_threshold = 0.45 if is_wide else 0.5
					if overall_mean < center_threshold:
						return [f["block"] for f in features], [], False
					else:
						return [], [f["block"] for f in features], False
			
			# 如果左组和右组都没有明显的分离，可能是单方
			# 但如果右组存在且分离明显，或者整体范围很大，应该是双方消息
			if not (left_separated and right_separated):
				# 如果之前检测到右组存在且分离明显，或整体范围很大，不判断为单方
				if right_group_valid and groups_separation > 0.1:
					pass  # 继续验证
				elif all_left_range > 0.7 or all_right_range > 0.7:
					pass  # 继续验证
				else:
					# 根据整体位置判断
					overall_mean = (left_mean + right_mean) / 2
					center_threshold = 0.45 if is_wide else 0.5
					if overall_mean < center_threshold:
						return [f["block"] for f in features], [], False
					else:
						return [], [f["block"] for f in features], False
		
		
		return left_blocks, right_blocks, has_both_sides
	
	def _calculate_std(self, values: list[float]) -> float:
		"""计算标准差"""
		if not values:
			return 0.0
		mean = sum(values) / len(values)
		variance = sum((x - mean) ** 2 for x in values) / len(values)
		return variance ** 0.5
	
	def _kmeans_cluster_2d(self, feature1: list[float], feature2: list[float], max_iterations: int = 30) -> list[int]:
		"""
		二维K-means聚类（K=2）
		"""
		if len(feature1) != len(feature2) or len(feature1) < 2:
			return [0] * len(feature1)
		
		# 初始化中心点
		n = len(feature1)
		c1 = (feature1[n//4] if n >= 4 else feature1[0], feature2[n//4] if n >= 4 else feature2[0])
		c2 = (feature1[n*3//4] if n >= 4 else (feature1[-1] if n > 1 else feature1[0]), 
		      feature2[n*3//4] if n >= 4 else (feature2[-1] if n > 1 else feature2[0]))
		
		labels = [0] * n
		
		for iteration in range(max_iterations):
			changed = False
			# 分配标签
			for i in range(n):
				dist1 = ((feature1[i] - c1[0])**2 + (feature2[i] - c1[1])**2) ** 0.5
				dist2 = ((feature1[i] - c2[0])**2 + (feature2[i] - c2[1])**2) ** 0.5
				new_label = 0 if dist1 <= dist2 else 1
				if labels[i] != new_label:
					labels[i] = new_label
					changed = True
			
			# 更新中心点
			group0_1 = [feature1[i] for i in range(n) if labels[i] == 0]
			group0_2 = [feature2[i] for i in range(n) if labels[i] == 0]
			group1_1 = [feature1[i] for i in range(n) if labels[i] == 1]
			group1_2 = [feature2[i] for i in range(n) if labels[i] == 1]
			
			new_c1 = (sum(group0_1)/len(group0_1) if group0_1 else c1[0],
			          sum(group0_2)/len(group0_2) if group0_2 else c1[1])
			new_c2 = (sum(group1_1)/len(group1_1) if group1_1 else c2[0],
			          sum(group1_2)/len(group1_2) if group1_2 else c2[1])
			
			# 检查收敛
			if abs(new_c1[0] - c1[0]) < 0.1 and abs(new_c1[1] - c1[1]) < 0.1 and \
			   abs(new_c2[0] - c2[0]) < 0.1 and abs(new_c2[1] - c2[1]) < 0.1:
				break
			
			c1, c2 = new_c1, new_c2
			
			if not changed:
				break
		
		return labels

	def _merge_volc_bubbles(self, blocks: list[dict], speaker_name: str, side: str, image_width: float, image_height: float) -> list[dict]:
		"""
		改进的聊天气泡合并算法。
		智能处理长内容和多段内容，正确组装聊天气泡。
		对于单方消息，更激进地合并。
		"""
		if not blocks:
			return []
		
		# 确保所有块都有必要的属性
		blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
		for b in blocks:
			b.setdefault("right", b.get("x", 0) + b.get("width", 0))
			b.setdefault("bottom", b.get("y", 0) + b.get("height", 0))
		
		# 检测是否为单方消息（所有块都在同一侧）
		# 如果左边缘标准差很小或右边缘标准差很小，可能是单方消息
		all_left_positions = [b.get("x", 0) / image_width if image_width > 0 else 0.0 for b in blocks]
		all_right_positions = [min(b.get("right", 0) / image_width, 1.0) if image_width > 0 else 1.0 for b in blocks]
		left_std_all = self._calculate_std(all_left_positions) if len(all_left_positions) > 1 else 0.0
		right_std_all = self._calculate_std(all_right_positions) if len(all_right_positions) > 1 else 0.0
		is_single_speaker = left_std_all < 0.10 or right_std_all < 0.10  # 单方消息的对齐一致性更好
		
		# 计算统计信息（用于阈值计算）
		min_y = min((b.get("y", 0) for b in blocks), default=0)
		max_bottom = max((b.get("bottom", 0) for b in blocks), default=0)
		actual_height = max(1.0, float(max_bottom - min_y))
		avg_height = max(10.0, float(sum(b.get("height", 0) for b in blocks) / max(1, len(blocks))))
		avg_width = max(1.0, float(sum(b.get("width", 0) for b in blocks) / max(1, len(blocks))))
		def _is_code_like(text: str) -> bool:
			if not text: return False
			s = text.strip(); lower = s.lower()
			if any(k in lower for k in ["def ", "class ", "function ", "var ", "let ", "const ", "return ", "import ", "from ", "=>"]): return True
			if s.startswith("```") or s.endswith("```"): return True
			if len(text) - len(text.lstrip(" \t")) >= 2: return True
			symbols = set("{}[]();,:=<>+-*/#`$\"'\\|&%._")
			ratio = sum(1 for ch in s if ch in symbols) / max(1, len(s))
			digit_ratio = sum(1 for ch in s if ch.isdigit()) / max(1, len(s))
			return ratio >= 0.15 or digit_ratio >= 0.4
		y_gaps = []
		gap_ratios = []
		for i in range(len(blocks)-1):
			prev_block = blocks[i]; curr_block = blocks[i+1]
			y_gap = curr_block["y"] - prev_block["bottom"]
			if y_gap >= 0:
				y_gaps.append(y_gap)
				gap_ratios.append(y_gap / actual_height if actual_height > 0 else 0)
		def _calc_thresholds_improved(gap_ratios: list[float], y_gaps: list[float], avg_height: float, actual_height: float) -> tuple[float, float, float]:
			"""
			改进的阈值计算：
			- line_break_threshold: 同一消息内的换行间距阈值
			- message_gap_threshold: 不同消息之间的间距阈值
			- small_gap_threshold: 很小的间距阈值（几乎肯定是同一消息）
			"""
			if not gap_ratios:
				# 默认值
				line_break = (avg_height * 1.5) / actual_height if actual_height > 0 else 0.02
				message_gap = line_break * 2.5
				small_gap = (avg_height * 0.8) / actual_height if actual_height > 0 else 0.01
				return line_break, message_gap, small_gap
			
			# 使用分位数方法
			sorted_gaps = sorted(gap_ratios)
			n = len(sorted_gaps)
			
			# 分位数函数
			def quantile(p: float) -> float:
				idx = min(n - 1, max(0, int(n * p)))
				return sorted_gaps[idx]
			
			# 小间距（25%分位数）
			small = quantile(0.25)
			# 中等间距（50%分位数）
			medium = quantile(0.50)
			# 大间距（75%分位数）
			large = quantile(0.75)
			
			# 计算平均间距
			mean_gap = sum(y_gaps) / len(y_gaps) if y_gaps else avg_height
			mean_gap_ratio = mean_gap / actual_height if actual_height > 0 else small
			
			# 行内换行阈值：基于小间距和平均间距（放宽，更倾向于合并）
			line_break_threshold = max(
				small * 2.2,  # 小间距的2.2倍（从1.8增加到2.2）
				medium * 1.5,  # 中等间距的1.5倍（从1.2增加到1.5）
				(avg_height * 1.5) / actual_height if actual_height > 0 else small,  # 基于平均高度（从1.2增加到1.5）
				mean_gap_ratio * 1.2  # 平均间距的1.2倍（从0.9增加到1.2）
			)
			
			# 消息间间距阈值：基于大间距（更严格，确保不同消息之间才分离）
			message_gap_threshold = max(
				large * 1.3,  # 大间距的1.3倍（从1.1增加到1.3）
				line_break_threshold * 2.5,  # 行内阈值的2.5倍（从2.0增加到2.5）
				(avg_height * 4.0) / actual_height if actual_height > 0 else line_break_threshold * 2.0,  # 基于平均高度（从3.0增加到4.0）
				mean_gap_ratio * 2.0  # 平均间距的2.0倍（从1.5增加到2.0）
			)
			
			# 小间距阈值：几乎肯定是同一消息（放宽）
			small_gap_threshold = min(
				small * 2.0,  # 小间距的2.0倍（从1.5增加到2.0）
				(avg_height * 0.8) / actual_height if actual_height > 0 else small * 1.0,  # 基于平均高度（从0.6增加到0.8）
				line_break_threshold * 0.8  # 行内阈值的80%（从60%增加到80%）
			)
			
			# 确保阈值顺序正确
			if line_break_threshold >= message_gap_threshold:
				message_gap_threshold = line_break_threshold * 2.8  # 从2.2增加到2.8
			
			# 放宽最大阈值限制（允许更大的合并阈值）
			message_gap_threshold = min(message_gap_threshold, 0.12)  # 从8%增加到12%
			line_break_threshold = min(line_break_threshold, 0.06)  # 从4%增加到6%
			
			return line_break_threshold, message_gap_threshold, small_gap_threshold
		
		line_break_threshold, message_gap_threshold, small_gap_threshold = _calc_thresholds_improved(
			gap_ratios, y_gaps, avg_height, actual_height
		)
		
		# 计算间距分布的统计信息，用于判断是否应该分开
		# 如果间距分布有明显的双峰（小间距和大间距），说明有多个消息
		if len(gap_ratios) >= 3:
			sorted_gaps = sorted(gap_ratios)
			# 计算间距的分布：如果有很多大间距，说明有多个消息
			large_gaps_count = sum(1 for g in gap_ratios if g > message_gap_threshold * 0.7)
			medium_gaps_count = sum(1 for g in gap_ratios if message_gap_threshold * 0.4 < g <= message_gap_threshold * 0.7)
			# 如果大间距数量较多，说明有多个消息，不应该过度合并
			has_multiple_messages = large_gaps_count >= 2 or (large_gaps_count >= 1 and medium_gaps_count >= 2)
		else:
			has_multiple_messages = False
		
		bubbles: list[dict] = []
		current_bubble: Optional[dict] = None
		for block in blocks:
			# 图片块应该独立成段，不合并
			is_image_block = block.get("is_image", False)
			if is_image_block:
				# 如果有当前气泡，先保存
				if current_bubble:
					bubbles.append(current_bubble)
				# 创建新的图片气泡
				current_bubble = {
					"text": "[图片]",
					"top": block["y"],
					"bottom": block["bottom"],
					"left": block["x"],
					"right": block["right"],
					"blocks": [block],
					"anchor_left": block["x"],
					"anchor_right": block["right"],
					"anchor_width": max(1, block["right"] - block["x"]),
					"image_height": actual_height,
					"is_code": False,
					"code_hits": 0
				}
				bubbles.append(current_bubble)
				current_bubble = None
				continue
			
			if current_bubble is None:
				current_bubble = {
					"text": block.get("text", ""),
					"top": block["y"],
					"bottom": block["bottom"],
					"left": block["x"],
					"right": block["right"],
					"blocks": [block],
					"anchor_left": block["x"],
					"anchor_right": block["right"],
					"anchor_width": max(1, block["right"] - block["x"]),
					"image_height": actual_height,
					"is_code": _is_code_like(block.get("text", "")),
					"code_hits": 1 if _is_code_like(block.get("text", "")) else 0
				}
				bubbles.append(current_bubble)
			else:
				# 判断是否应该合并到当前气泡
				y_gap = block["y"] - current_bubble["bottom"]
				gap_ratio = y_gap / actual_height if actual_height > 0 else 0
				
				# 计算水平对齐差异
				if side == "left":
					# 左侧消息：检查左对齐
					x_alignment_diff = abs(block["x"] - current_bubble.get("anchor_left", current_bubble["left"]))
					anchor_x = current_bubble.get("anchor_left", current_bubble["left"])
				else:
					# 右侧消息：检查右对齐
					x_alignment_diff = abs(block["right"] - current_bubble.get("anchor_right", current_bubble["right"]))
					anchor_x = current_bubble.get("anchor_right", current_bubble["right"])
				
				# 对齐容差（基于锚点宽度，放宽以提高合并率）
				anchor_width = max(1, current_bubble.get("anchor_width", (current_bubble["right"] - current_bubble["left"])))
				# 对于单方消息，使用更宽松的对齐容差
				if is_single_speaker:
					# 单方消息：容差更大，因为所有行都应该对齐
					alignment_tolerance = max(12, min(40, anchor_width * 0.30))  # 更宽松的容差
				else:
					# 多方消息：使用标准容差
					alignment_tolerance = max(8, min(30, anchor_width * 0.22))
				x_alignment = x_alignment_diff <= alignment_tolerance
				
				# 计算宽度相似度
				curr_width = max(1, current_bubble["right"] - current_bubble["left"])
				blk_width = max(1, block["right"] - block["x"])
				width_ratio = min(curr_width, blk_width) / max(curr_width, blk_width)
				
				# 判断是否为代码
				in_code_mode = bool(current_bubble.get("is_code"))
				next_is_code = _is_code_like(block.get("text", ""))
				
				# 检测可能的空白区域（表情包位置）
				# 如果两个块之间有较大的空白区域，可能是表情包
				# 计算空白区域的大小
				prev_block = current_bubble.get("blocks", [])[-1] if current_bubble.get("blocks") else None
				has_emoji_gap = False
				emoji_gap_size = 0
				if prev_block:
					# 计算垂直和水平间距
					y_gap = block["y"] - prev_block.get("bottom", 0)
					x_overlap = min(block["right"], prev_block.get("right", 0)) - max(block["x"], prev_block.get("x", 0))
					# 如果垂直间距在合理范围内（可能是表情包导致的换行）
					if y_gap > 0:
						gap_ratio_v = y_gap / actual_height if actual_height > 0 else 0
						# 如果间距在表情包范围内（1%-15%），可能是表情包
						if 0.01 < gap_ratio_v < 0.15:
							# 检查水平位置：如果两个块水平位置相近，可能是表情包
							prev_center_x = (prev_block.get("x", 0) + prev_block.get("right", 0)) / 2
							curr_center_x = (block["x"] + block["right"]) / 2
							center_diff = abs(curr_center_x - prev_center_x) / image_width if image_width > 0 else 0
							# 如果中心位置相近（<30%），可能是表情包导致的换行
							if center_diff < 0.30:
								has_emoji_gap = True
								emoji_gap_size = gap_ratio_v
				
				# 合并决策（多条件判断，更激进地合并）
				should_merge = False
				force_reject = False  # 强制拒绝标记（多消息模式下使用）
				
				# 对于单方消息，优先基于间距判断，对齐要求放宽
				# 但需要注意：即使是单方消息，多个气泡之间也应该分开
				if is_single_speaker:
					# 如果检测到多个消息，更严格地判断是否合并
					if has_multiple_messages:
						# 多消息模式：更严格，避免过度合并
						# 条件1: 很小的间距（几乎肯定是同一消息）
						if gap_ratio <= small_gap_threshold:
							should_merge = True
						# 条件2: 行内间距 + 对齐
						if not should_merge and gap_ratio <= line_break_threshold and x_alignment:
							should_merge = True
						# 条件3: 如果对齐且间距很小，才合并
						if not should_merge and x_alignment and gap_ratio <= message_gap_threshold * 0.5:
							should_merge = True
						# 条件4: 如果间距很小且宽度相似且对齐，才合并
						if not should_merge and x_alignment and gap_ratio <= line_break_threshold * 0.7 and width_ratio >= 0.70:
							should_merge = True
						# 条件5: 如果间距超过行内阈值，即使对齐也不合并（多消息模式）
						if should_merge and gap_ratio > line_break_threshold * 1.0:
							should_merge = False
							force_reject = True  # 强制拒绝，后续条件不能覆盖
					else:
						# 单消息模式：更激进地合并
						# 条件1: 很小的间距（几乎肯定是同一消息，即使对齐稍差）
						if gap_ratio <= small_gap_threshold * 1.2:  # 从1.5收紧到1.2，避免过度合并
							should_merge = True
						# 条件2: 行内间距（即使对齐稍差也合并，但要更严格）
						if gap_ratio <= line_break_threshold * 1.0:  # 从1.2收紧到1.0，避免过度合并
							should_merge = True
						# 条件3: 如果对齐且间距不太大，就合并
						if not should_merge and x_alignment and gap_ratio <= message_gap_threshold * 0.7:  # 从0.9收紧到0.7
							should_merge = True
						# 条件4: 如果间距很小且宽度相似，即使对齐稍差也合并
						if not should_merge and gap_ratio <= line_break_threshold * 0.8 and width_ratio >= 0.65:  # 从0.60提高到0.65
							should_merge = True
						# 条件5: 如果间距非常小，即使不对齐也合并（单方消息的特殊处理，但要更严格）
						if not should_merge and gap_ratio <= small_gap_threshold * 1.5:  # 从2.0收紧到1.5，避免过度合并
							should_merge = True
				else:
					# 多方消息策略：使用标准条件
					# 条件1: 很小的间距 + 对齐 = 几乎肯定是同一消息
					if gap_ratio <= small_gap_threshold and x_alignment:
						should_merge = True
					
					# 条件2: 行内间距 + 对齐 = 同一消息的换行
					if gap_ratio <= line_break_threshold and x_alignment:
						should_merge = True
				
				# 条件3: 如果当前气泡已经有多个块，参考气泡内部间距（更激进地合并）
				if not should_merge and len(current_bubble.get("blocks", [])) >= 2:
					bubble_blocks = current_bubble.get("blocks", [])
					bubble_internal_gaps = []
					for j in range(len(bubble_blocks) - 1):
						prev = bubble_blocks[j]
						curr = bubble_blocks[j + 1]
						internal_gap = curr["y"] - prev["bottom"]
						bubble_internal_gaps.append(internal_gap / actual_height if actual_height > 0 else 0)
					
					if bubble_internal_gaps:
						max_internal_gap = max(bubble_internal_gaps)
						mean_internal_gap = sum(bubble_internal_gaps) / len(bubble_internal_gaps)
						
						# 检查当前间距是否明显大于气泡内部间距（可能是不同消息）
						# 如果当前间距明显大于最大内部间距（>1.5倍），可能是不同消息，不合并
						if gap_ratio > max_internal_gap * 1.5:
							# 对于多方消息，更严格：如果间距明显大于内部间距，且不在很小范围内，可能是不同消息
							if not is_single_speaker and gap_ratio > message_gap_threshold * 0.7:  # 从0.8收紧到0.7
								should_merge = False
							# 即使单方消息，如果间距明显大于内部间距且超过阈值，也可能是不同消息
							# 收紧阈值，避免多个对方消息被合并
							elif is_single_speaker:
								# 如果检测到多个消息，更严格
								if has_multiple_messages:
									# 多消息模式：更严格，如果间距大于内部间距的1.5倍或超过行内阈值，就分开
									if gap_ratio > max_internal_gap * 1.5 or gap_ratio > line_break_threshold * 1.0:
										should_merge = False
										force_reject = True  # 强制拒绝，后续条件不能覆盖
								else:
									# 单消息模式：使用原有逻辑
									if gap_ratio > max_internal_gap * 1.8 and gap_ratio > message_gap_threshold * 0.6:
										should_merge = False
									# 对于单方消息，如果间距明显超过行内阈值，可能是不同消息
									elif gap_ratio > line_break_threshold * 1.2:
										should_merge = False
							else:
								# 对于单方消息，放宽对齐要求
								if is_single_speaker:
									# 如果当前间距与气泡内部最大间距相似，就合并（不要求对齐）
									if gap_ratio <= max_internal_gap * 2.5:  # 更宽松
										should_merge = True
									# 或者与平均间距相似
									elif gap_ratio <= mean_internal_gap * 3.0:  # 更宽松
										should_merge = True
								else:
									# 如果当前间距与气泡内部最大间距相似，且对齐或宽度相似（放宽条件）
									if gap_ratio <= max_internal_gap * 2.0 and (x_alignment or width_ratio >= 0.65):
										should_merge = True
									# 或者与平均间距相似（放宽条件）
									elif gap_ratio <= mean_internal_gap * 2.5 and (x_alignment or width_ratio >= 0.65):
										should_merge = True
						else:
							# 当前间距与气泡内部间距相似，可以合并
							# 对于单方消息，放宽对齐要求
							if is_single_speaker:
								# 如果当前间距与气泡内部最大间距相似，就合并（不要求对齐）
								if gap_ratio <= max_internal_gap * 2.5:  # 更宽松
									should_merge = True
								# 或者与平均间距相似
								elif gap_ratio <= mean_internal_gap * 3.0:  # 更宽松
									should_merge = True
							else:
								# 如果当前间距与气泡内部最大间距相似，且对齐或宽度相似（放宽条件）
								if gap_ratio <= max_internal_gap * 2.0 and (x_alignment or width_ratio >= 0.65):
									should_merge = True
								# 或者与平均间距相似（放宽条件）
								elif gap_ratio <= mean_internal_gap * 2.5 and (x_alignment or width_ratio >= 0.65):
									should_merge = True
				
				# 条件4: 宽度相似 + 对齐 + 间距不太大 = 可能是同一消息（放宽条件）
				# 但对于多方消息，如果间距已经接近消息间阈值，即使对齐也应该分开
				if not should_merge and width_ratio >= 0.65 and x_alignment:
					if is_single_speaker:
						# 单方消息：更宽松
						if gap_ratio <= message_gap_threshold:
							should_merge = True
					else:
						# 多方消息：更严格，如果间距接近消息间阈值，需要宽度相似度更高
						if gap_ratio <= message_gap_threshold * 0.8:  # 更严格的阈值
							should_merge = True
						elif gap_ratio <= message_gap_threshold and width_ratio >= 0.75:  # 间距较大时需要更高的宽度相似度
							should_merge = True
				
				# 条件5（新增）: 如果对齐且间距不太大，即使宽度不太相似也合并（适合长消息）
				# 但对于多方消息，更严格
				if not should_merge and x_alignment:
					if is_single_speaker:
						# 单方消息：更宽松
						if gap_ratio <= message_gap_threshold * 0.8:
							should_merge = True
					else:
						# 多方消息：更严格
						if gap_ratio <= message_gap_threshold * 0.6:  # 更严格的阈值
							should_merge = True
				
				# 条件6: 如果对齐且宽度相似度较高，即使间距稍大也合并（适合长消息）
				# 但对于多方消息，需要更高的宽度相似度
				if not should_merge and x_alignment and width_ratio >= (0.70 if is_single_speaker else 0.75):
					if is_single_speaker:
						# 单方消息：更宽松
						if gap_ratio <= message_gap_threshold * 1.2:
							should_merge = True
					else:
						# 多方消息：更严格
						if gap_ratio <= message_gap_threshold * 1.0:  # 更严格的阈值
							should_merge = True
				
				# 条件9（单方消息专用）: 如果间距很小，即使不对齐也合并（单方消息的特殊处理）
				# 但如果已经被强制拒绝，不执行
				if not should_merge and not force_reject and is_single_speaker and gap_ratio <= line_break_threshold:
					should_merge = True
				
				# 条件10（新增）: 如果检测到可能的表情包位置，更宽松地合并
				# 表情包虽然OCR识别不到，但会导致文本分成多行，应该合并
				# 但在多消息模式下，需要更严格，避免过度合并
				# 如果已经被强制拒绝（多消息模式下间距过大），不执行表情包合并
				if not should_merge and not force_reject and has_emoji_gap:
					# 如果间距在表情包范围内（1%-15%），且水平位置相近，合并
					# 但在多消息模式下，如果间距明显大于气泡内部间距，不应该合并
					if is_single_speaker and has_multiple_messages:
						# 多消息模式：只有在间距很小且与气泡内部间距相似时才合并
						if emoji_gap_size < 0.08 and len(current_bubble.get("blocks", [])) >= 2:
							bubble_blocks = current_bubble.get("blocks", [])
							bubble_internal_gaps = []
							for j in range(len(bubble_blocks) - 1):
								prev = bubble_blocks[j]
								curr = bubble_blocks[j + 1]
								internal_gap = curr["y"] - prev["bottom"]
								bubble_internal_gaps.append(internal_gap / actual_height if actual_height > 0 else 0)
							if bubble_internal_gaps:
								max_internal_gap = max(bubble_internal_gaps)
								# 只有在表情包间距与气泡内部间距相似时才合并
								if emoji_gap_size <= max_internal_gap * 2.0:
									should_merge = True
					elif emoji_gap_size < 0.06:
						# 非常小的间距，可能是表情包
						should_merge = True
					else:
						# 单消息模式：正常合并
						if emoji_gap_size < 0.15:
							should_merge = True
				
				# 条件7: 代码模式（代码块通常需要合并）
				if (in_code_mode or next_is_code) and x_alignment:
					# 代码块内，只要间距不太大就合并
					if gap_ratio <= message_gap_threshold * 1.2:
						should_merge = True
						in_code_mode = True
				
				# 条件8: 如果间距非常大，即使其他条件满足也不合并（除非是代码）
				# 放宽阈值，只有在间距非常大时才拒绝合并
				if should_merge and gap_ratio >= message_gap_threshold * 1.8 and not in_code_mode:  # 从1.5增加到1.8，更宽松
					should_merge = False
				
				# 如果已经被强制拒绝，确保不合并
				if force_reject:
					should_merge = False
				
				if should_merge:
					current_bubble["text"] += "\n" + block["text"]
					current_bubble["bottom"] = max(current_bubble["bottom"], block["bottom"])
					current_bubble["left"] = min(current_bubble["left"], block["x"])
					current_bubble["right"] = max(current_bubble["right"], block["right"])
					current_bubble["blocks"].append(block)
					if next_is_code: current_bubble["code_hits"] = current_bubble.get("code_hits", 0)+1
					if current_bubble.get("code_hits", 0) >= 2: current_bubble["is_code"] = True
				else:
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
						"image_height": actual_height,
						"is_code": _is_code_like(block.get("text", "")),
						"code_hits": 1 if _is_code_like(block.get("text", "")) else 0
					}
					bubbles.append(current_bubble)
		
		
		return bubbles


class DoubaoOCRService:
	"""豆包OCR服务（独立实现）。"""
	def __init__(self):
		self.api_key = os.getenv("ARK_API_KEY") or settings.doubao_api_key
		self.api_url = settings.doubao_api_url
		self.model = settings.doubao_model
		self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

	async def extract_text_from_images(self, images_data: list[bytes], image_formats: list[str], cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		if not image_formats:
			image_formats = ["png"] * len(images_data)
		return await self._extract_with_doubao_ocr(images_data, image_formats, cancel_event)

	async def extract_text_from_image(self, image_data: bytes, image_format: str = "png", cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		return await self._extract_with_doubao_ocr([image_data], [image_format], cancel_event)

	async def _extract_with_doubao_ocr(self, images_data: list[bytes], image_formats: list[str], cancel_event: Optional["asyncio.Event"] = None) -> OCRResponse:
		try:
			import time as _t
			t_build0 = _t.perf_counter()
			optimized_images: list[bytes] = []
			optimized_formats: list[str] = []
			for raw, fmt in zip(images_data, image_formats):
				if OCRUtils.should_abort(cancel_event):
					import asyncio as _a
					raise _a.CancelledError()
				img_b, img_fmt, _ = OCRUtils.optimize_image_bytes(raw, fmt)
				optimized_images.append(img_b)
				optimized_formats.append(img_fmt)
			images_data = optimized_images; image_formats = optimized_formats
			content_parts = [{"type": "text", "text": (
				"你将看到多张聊天截图，请进行OCR并理解排版位置来判断左右两侧发言人。"
				"请严格返回JSON（不要包含多余文字），结构如下：\n{\n  \"participants\": [\"我\", \"对方\"],\n  \"messages\": [\n    {\"speaker_name\": \"我\", \"speaker_side\": \"right\", \"text\": \"内容\", \"block_index\": 1},\n    {\"speaker_name\": \"对方\", \"speaker_side\": \"left\", \"text\": \"内容\", \"block_index\": 2}\n  ]\n}" )}]
			for image_data, image_format in zip(images_data, image_formats):
				if OCRUtils.should_abort(cancel_event):
					import asyncio as _a
					raise _a.CancelledError()
				try:
					from io import BytesIO
					from PIL import Image
					img = Image.open(BytesIO(image_data)).convert("RGB")
					max_side = 1600; w, h = img.size
					if max(w, h) > max_side:
						ratio = max_side / float(max(w, h))
						img = img.resize((int(w*ratio), int(h*ratio)))
					buf = BytesIO(); img.save(buf, format="JPEG", quality=85, optimize=True)
					image_data = buf.getvalue()
				except Exception:
					pass
				image_base64 = base64.b64encode(image_data).decode('utf-8')
				content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{image_base64}"}})
			payload = {"model": self.model, "messages": [{"role": "user", "content": content_parts}], "max_tokens": 800, "temperature": 0, "top_p": 0, "response_format": {"type": "json_object"}}
			_timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=30.0)
			async with httpx.AsyncClient(timeout=_timeout, http2=True, trust_env=True) as client:
				for attempt in range(1, 4):
					if OCRUtils.should_abort(cancel_event):
						import asyncio as _a
						raise _a.CancelledError()
					try:
						response = await client.post(self.api_url, headers=self.headers, json=payload)
						if response.status_code >= 500:
							raise httpx.HTTPStatusError("server error", request=response.request, response=response)
						response.raise_for_status(); break
					except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError, httpx.RemoteProtocolError, httpx.HTTPStatusError) as e:
						if isinstance(e, httpx.HTTPStatusError) and e.response is not None and e.response.status_code < 500:
							raise
						if attempt >= 3: raise
						import asyncio as _a; await _a.sleep(0.6 * attempt)
				result = response.json()
				content = result["choices"][0]["message"]["content"]
				if OCRUtils.should_abort(cancel_event):
					import asyncio as _a
					raise _a.CancelledError()
				text_content, metadata = OCRUtils.parse_ocr_response(content)
				try:
					import json
					structured = json.loads(content)
					if isinstance(structured, dict) and "messages" in structured:
						metadata["structured_messages"] = structured.get("messages", [])
						metadata["participants"] = structured.get("participants", [])
						joined = "\n\n".join([m.get("text", "").strip() for m in structured.get("messages", []) if m.get("text")])
						if joined: text_content = joined
				except Exception:
					pass
				return OCRResponse(text=text_content, confidence=metadata.get("confidence", 0.9), language=metadata.get("language", "中文"), metadata=metadata)
		except Exception as e:
			logger.error(f"豆包OCR识别失败: {e}")
			raise Exception(f"图片识别失败: {str(e)}")


# 导出两个独立服务实例
volc_ocr_service = VolcOCRService()
doubao_ocr_service = DoubaoOCRService()

