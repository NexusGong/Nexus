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
		]
		is_timestamp = any(re.match(pattern, text) for pattern in time_patterns)
		if not is_timestamp:
			return False
		if block is not None:
			center_x = block.get("center_x", 0)
			image_min_x = block.get("image_min_x", 0)
			image_width = block.get("image_width", 0)
			if image_width > 0:
				image_center_absolute = image_min_x + image_width / 2
				center_range = image_width * 0.4
				distance_from_center = abs(center_x - image_center_absolute)
				if distance_from_center <= center_range:
					logger.debug(f"[OCR][filter] 过滤居中的时间戳: '{text}'")
					return True
				logger.debug(f"[OCR][filter] 过滤非居中的时间戳: '{text}'")
				return True
			else:
				logger.debug(f"[OCR][filter] 过滤时间戳（无位置信息）: '{text}'")
				return True
		else:
			logger.debug(f"[OCR][filter] 过滤时间戳（无位置信息）: '{text}'")
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
			# 分批串行+可取消，避免不可中断的大量并行任务
			ocr_tasks = []
			for img in images_data:
				if OCRUtils.should_abort(cancel_event):
					raise asyncio.CancelledError()
				ocr_tasks.append(self._volc_ocr_recognition_raw(img))
			ocr_results = await asyncio.gather(*ocr_tasks, return_exceptions=True)
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
				if not line_texts:
					logger.warning(f"[OCR][volc][warn] 图片 {idx+1} 未识别到文字")
					continue
				# 无法可靠获取原图尺寸时，按行框绝对坐标处理即可
				image_blocks = self._extract_volc_blocks(
					line_texts, line_rects, line_probs, polygons, [], 0, 0, idx+1
				)
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
			messages, text_content = self._process_volc_ocr_blocks(all_blocks)
			participants = sorted({m.get("speaker_name") for m in messages if m.get("speaker_name")})
			language = "mixed"
			if all(c.isascii() or (not c.isalpha()) for c in text_content):
				language = "英文"
			elif any('\u4e00' <= ch <= '\u9fff' for ch in text_content):
				language = "中文"
			metadata = {
				"confidence": 0.9,
				"language": language,
				"structured_messages": messages,
				"participants": participants,
				"ocr_method": "volc_ocr",
				"word_count": len(all_blocks),
				"failed_images": failed_images if failed_images else None
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
		if not blocks:
			return [], ""
		max_x = max(b.get("right", 0) for b in blocks) if blocks else 0
		min_x = min(b.get("x", 0) for b in blocks) if blocks else 0
		image_width = max_x - min_x
		filtered_blocks = []
		for block in blocks:
			text = block.get("text", "").strip()
			block_with_info = {**block, "image_width": image_width, "image_min_x": min_x}
			if not OCRUtils.filter_noise_text(text, block_with_info):
				filtered_blocks.append(block)
		if not filtered_blocks:
			return [], ""
		blocks = sorted(filtered_blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
		max_x = max(b.get("right", 0) for b in blocks); min_x = min(b.get("x", 0) for b in blocks)
		max_y = max(b.get("bottom", 0) for b in blocks); min_y = min(b.get("y", 0) for b in blocks)
		image_height = max(100, (max_y - min_y) if max_y > min_y else 100)
		# 分组：基于右边缘到图片右边缘距离的K=2自适应
		right_edges = [b.get("right", 0) for b in blocks]
		image_right = max(right_edges) if right_edges else max_x
		distances = [image_right - b.get("right", 0) for b in blocks]
		sorted_distances = sorted(distances); n = len(sorted_distances)
		c1 = sorted_distances[n//4] if n >= 4 else sorted_distances[0]
		c2 = sorted_distances[n*3//4] if n >= 4 else (sorted_distances[-1] if n > 1 else sorted_distances[0])
		labels = [0]*n
		for _ in range(20):
			changed = False
			for i, d in enumerate(distances):
				new_l = 0 if abs(d-c1) <= abs(d-c2) else 1
				if labels[i] != new_l:
					labels[i] = new_l; changed = True
			g1 = [distances[i] for i in range(n) if labels[i]==0]
			g2 = [distances[i] for i in range(n) if labels[i]==1]
			new_c1 = (sum(g1)/len(g1)) if g1 else c1
			new_c2 = (sum(g2)/len(g2)) if g2 else c2
			if abs(new_c1-c1) < 0.1 and abs(new_c2-c2) < 0.1:
				c1, c2 = new_c1, new_c2; break
			c1, c2 = new_c1, new_c2
			if not changed: break
		if c1 > c2: c1, c2 = c2, c1; labels = [1-l for l in labels]
		split_threshold = (c1+c2)/2
		right_blocks = [b for b, l in zip(blocks, labels) if l==0]
		left_blocks = [b for b, l in zip(blocks, labels) if l==1]
		all_messages: list[dict] = []
		for blocks_group, side, speaker_name in [
			(left_blocks, "left", "对方"), (right_blocks, "right", "我")
		]:
			if not blocks_group: continue
			blocks_group = sorted(blocks_group, key=lambda b: (b.get("y", 0), b.get("x", 0)))
			bubbles = self._merge_volc_bubbles(blocks_group, speaker_name, side)
			for bubble in bubbles:
				bubble_text = (bubble.get("text") or "").strip()
				if not bubble_text: continue
				bubble_y = bubble.get("top", 0)
				if bubble.get("blocks"): bubble_y = bubble["blocks"][0].get("y", 0)
				all_messages.append({
					"speaker_name": speaker_name, "speaker_side": side, "text": bubble_text, "_sort_y": bubble_y
				})
		all_messages.sort(key=lambda m: m.get("_sort_y", 0))
		for i, msg in enumerate(all_messages):
			msg["block_index"] = i+1; msg.pop("_sort_y", None)
		text_content = "\n\n".join([m.get("text", "").strip() for m in all_messages if m.get("text")])
		return all_messages, text_content

	def _merge_volc_bubbles(self, blocks: list[dict], speaker_name: str, side: str) -> list[dict]:
		if not blocks:
			return []
		blocks = sorted(blocks, key=lambda b: (b.get("y", 0), b.get("x", 0)))
		for b in blocks:
			b.setdefault("right", b.get("x", 0) + b.get("width", 0))
			b.setdefault("bottom", b.get("y", 0) + b.get("height", 0))
		min_y = min((b.get("y", 0) for b in blocks), default=0)
		max_bottom = max((b.get("bottom", 0) for b in blocks), default=0)
		image_height = max(1.0, float(max_bottom - min_y))
		avg_height = max(10.0, float(sum(b.get("height", 0) for b in blocks) / max(1, len(blocks))))
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
				y_gaps.append(y_gap); gap_ratios.append(y_gap / image_height if image_height > 0 else 0)
		def _calc_thresholds(gap_ratios: list[float], y_gaps: list[float], avg_height: float, image_height: float) -> tuple[float, float, float]:
			if not gap_ratios:
				lr = (avg_height * 1.3) / image_height if image_height > 0 else 0.02
				mr = lr * 2.0; ts = (avg_height * 1.0) / image_height if image_height > 0 else 0.015
				return lr, mr, ts
			s = sorted(gap_ratios); n = len(s)
			q = lambda p: s[min(n-1, max(0, int(n*p)))]
			small = q(0.30); large = q(0.70)
			mean_gap_ratio = (sum(y_gaps)/len(y_gaps))/image_height if (y_gaps and image_height>0) else small
			line_break_ratio_threshold = max(max(small, q(0.25))*1.3, (avg_height*0.9)/image_height if image_height>0 else small, mean_gap_ratio*0.8)
			message_gap_ratio_threshold = max(max(large, q(0.75))*0.9, line_break_ratio_threshold*1.6, (avg_height*2.5)/image_height if image_height>0 else line_break_ratio_threshold*1.5)
			typical_small_ratio = max(q(0.10), q(0.25)*0.8)
			line_break_ratio_threshold = max(line_break_ratio_threshold, (avg_height*0.5)/image_height if image_height>0 else 0.01)
			message_gap_ratio_threshold = min(message_gap_ratio_threshold, 0.05)
			if line_break_ratio_threshold >= message_gap_ratio_threshold:
				message_gap_ratio_threshold = line_break_ratio_threshold*1.8
			return line_break_ratio_threshold, message_gap_ratio_threshold, typical_small_ratio
		line_break_ratio_threshold, message_gap_ratio_threshold, typical_small_ratio = _calc_thresholds(gap_ratios, y_gaps, avg_height, image_height)
		bubbles: list[dict] = []
		current_bubble: Optional[dict] = None
		for block in blocks:
			if current_bubble is None:
				current_bubble = {
					"text": block["text"], "top": block["y"], "bottom": block["bottom"], "left": block["x"], "right": block["right"],
					"blocks": [block], "anchor_left": block["x"], "anchor_right": block["right"], "anchor_width": max(1, block["right"]-block["x"]),
					"image_height": image_height, "is_code": _is_code_like(block.get("text", "")), "code_hits": 1 if _is_code_like(block.get("text", "")) else 0
				}
				bubbles.append(current_bubble)
			else:
				y_gap = block["y"] - current_bubble["bottom"]
				gap_ratio = y_gap / image_height if image_height>0 else 0
				if side == "left": x_alignment_diff = abs(block["x"] - current_bubble.get("anchor_left", current_bubble["left"]))
				else: x_alignment_diff = abs(block["right"] - current_bubble.get("anchor_right", current_bubble["right"]))
				anchor_width = max(1, current_bubble.get("anchor_width", (current_bubble["right"]-current_bubble["left"])));
				strict_anchor_tol = max(6, min(18, anchor_width * 0.18))
				x_alignment = x_alignment_diff <= strict_anchor_tol
				curr_width = max(1, current_bubble["right"]-current_bubble["left"]); blk_width = max(1, block["right"]-block["x"]) 
				width_ratio = min(curr_width, blk_width)/max(curr_width, blk_width)
				should_merge = False; in_code_mode = bool(current_bubble.get("is_code")); next_is_code = _is_code_like(block.get("text", ""))
				if gap_ratio <= line_break_ratio_threshold and x_alignment: should_merge = True
				elif gap_ratio <= typical_small_ratio * 1.5: should_merge = True
				elif len(current_bubble.get("blocks", [])) >= 2:
					bubble_blocks = current_bubble.get("blocks", [])
					bubble_internal_ratios = []
					for j in range(len(bubble_blocks)-1):
						prev = bubble_blocks[j]; curr = bubble_blocks[j+1]
						internal_gap = curr["y"] - prev["bottom"]
						bubble_internal_ratios.append(internal_gap / image_height if image_height>0 else 0)
					if bubble_internal_ratios:
						bubble_max_ratio = max(bubble_internal_ratios)
						if gap_ratio <= bubble_max_ratio*1.3 and (x_alignment or width_ratio>=0.75): should_merge = True
				if not should_merge and width_ratio>=0.8 and x_alignment and gap_ratio<=message_gap_ratio_threshold: should_merge = True
				if (in_code_mode or (next_is_code and _is_code_like(current_bubble.get("blocks", [{}])[-1].get("text", "")))) and x_alignment:
					should_merge = True; in_code_mode = True
				if should_merge and gap_ratio >= message_gap_ratio_threshold and not in_code_mode:
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
						"text": block["text"], "top": block["y"], "bottom": block["bottom"], "left": block["x"], "right": block["right"],
						"blocks": [block], "anchor_left": block["x"], "anchor_right": block["right"], "anchor_width": max(1, block["right"]-block["x"]),
						"image_height": image_height, "is_code": _is_code_like(block.get("text", "")), "code_hits": 1 if _is_code_like(block.get("text", "")) else 0
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

