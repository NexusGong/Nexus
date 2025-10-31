import io
from typing import Optional
from datetime import datetime
from loguru import logger
from typing import Any
from app.models.analysis_card import AnalysisCard

# 全局缓存的 Playwright 实例与浏览器
_PW_INSTANCE = None
_BROWSER = None

async def startup_screenshot_service():
    """在应用启动时初始化浏览器，避免每次导出冷启动"""
    global _PW_INSTANCE, _BROWSER
    if _PW_INSTANCE is None or _BROWSER is None:
        from playwright.async_api import async_playwright
        _PW_INSTANCE = await async_playwright().start()
        _BROWSER = await _PW_INSTANCE.chromium.launch(headless=True, args=[
            "--disable-dev-shm-usage", "--disable-gpu", "--no-sandbox"
        ])
        logger.info("Playwright 浏览器已启动（全局复用）")

async def shutdown_screenshot_service():
    """在应用关闭时释放浏览器资源"""
    global _PW_INSTANCE, _BROWSER
    try:
        if _BROWSER is not None:
            await _BROWSER.close()
        if _PW_INSTANCE is not None:
            await _PW_INSTANCE.stop()
    finally:
        _BROWSER = None
        _PW_INSTANCE = None
        logger.info("Playwright 浏览器已关闭")


def _escape_html(text: Optional[str]) -> str:
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_html(card: AnalysisCard, created_str: str) -> str:
    title = _escape_html(card.title)
    desc = "分析卡片详细信息"
    context_mode = _escape_html(card.context_mode or "general")
    export_count = str(card.export_count or 0)

    # 提取分析数据
    ad = card.analysis_data or {}
    intent_primary = _escape_html((ad.get("intent") or {}).get("primary") or "")
    intent_desc = _escape_html((ad.get("intent") or {}).get("description") or "")
    sentiment_overall = _escape_html((ad.get("sentiment") or {}).get("overall") or "")
    sentiment_desc = _escape_html((ad.get("sentiment") or {}).get("description") or "")
    tone_style = _escape_html((ad.get("tone") or {}).get("style") or "")
    tone_desc = _escape_html((ad.get("tone") or {}).get("description") or "")
    relationship_closeness = _escape_html((ad.get("relationship") or {}).get("closeness") or "")
    relationship_desc = _escape_html((ad.get("relationship") or {}).get("description") or "")

    # 标签/次要信息
    intent_secondary = (ad.get("intent") or {}).get("secondary") or []
    sentiment_emotions = (ad.get("sentiment") or {}).get("emotions") or []

    # 潜台词
    subtext = ad.get("subtext") or {}
    hidden_meanings = subtext.get("hidden_meanings") or []
    implications = subtext.get("implications") or []

    # 智能回复建议
    suggestions = (card.response_suggestions or []) if hasattr(card, 'response_suggestions') else []

    def render_suggestions(items: list) -> str:
        if not items:
            return ""
        blocks = []
        for s in items:
            try:
                s_title = _escape_html(str(s.get('title') or ''))
                s_type = _escape_html(str(s.get('type') or '通用'))
                s_desc = _escape_html(str(s.get('description') or ''))
                s_examples = s.get('examples') or []
                examples_html = "".join(
                    f'<div class="text-xs bg-muted/50 p-2 rounded">"{_escape_html(str(e))}"</div>' for e in s_examples
                )
                block = f'''
<div class="p-3 border rounded-md hover:bg-muted/30 transition-colors">
  <div class="flex items-start justify-between mb-2">
    <div>
      <div class="inline-flex items-center rounded-full border px-2.5 py-0.5 font-semibold text-foreground text-xs mb-1">{s_type}</div>
      <h4 class="text-sm font-medium">{s_title}</h4>
    </div>
  </div>
  <p class="text-xs text-muted-foreground mb-2">{s_desc}</p>
  <div class="space-y-1">{examples_html}</div>
</div>
'''
                blocks.append(block)
            except Exception:
                continue
        return "".join(blocks)

    def badge_list(items):
        return "".join(
            f'<div class="inline-flex items-center rounded-full border px-2.5 py-0.5 font-semibold text-xs text-foreground">{_escape_html(str(i))}</div>'
            for i in items
        )

    from string import Template
    tpl = Template("""
<!doctype html>
<html lang=zh-CN>
<head>
  <meta charset=utf-8 />
  <meta name=viewport content="width=device-width,initial-scale=1" />
  <style>
    html,body{background:#ffffff;margin:0;padding:0;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,"Helvetica Neue",Arial,"Noto Sans","Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol"}
    .max-w-4xl{max-width:56rem}
    .mx-auto{margin-left:auto;margin-right:auto}
    .p-6{padding:1.5rem}
    .grid{display:grid}
    .gap-4{gap:1rem}
    .border{border:1px solid #e2e8f0}
    .bg-white{background:#fff}
    .shadow-lg{box-shadow:0 10px 15px -3px rgb(0 0 0 / .1),0 4px 6px -4px rgb(0 0 0 / .1)}
    .rounded-lg{border-radius:.5rem}
    .flex{display:flex}
    .flex-col{flex-direction:column}
    .space-y-1\.5> * + *{margin-top:.375rem}
    .items-center{align-items:center}
    .items-start{align-items:flex-start}
    .justify-between{justify-content:space-between}
    .gap-2{gap:.5rem}
    .text-xl{font-size:1.25rem;line-height:1.75rem}
    .font-bold{font-weight:700}
    .text-sm{font-size:.875rem;line-height:1.25rem}
    .text-xs{font-size:.75rem;line-height:1rem}
    .text-slate-500{color:#64748b}
    .text-slate-600{color:#475569}
    .text-red-800{color:#991b1b}
    .bg-slate-100{background:#f1f5f9}
    .bg-red-100{background:#fee2e2}
    .border-red-200{border-color:#fecaca}
    .inline-flex{display:inline-flex}
    .rounded-full{border-radius:9999px}
    .px-2\.5{padding-left:.625rem;padding-right:.625rem}
    .py-0\.5{padding-top:.125rem;padding-bottom:.125rem}
    .mt-2{margin-top:.5rem}
    .mb-2{margin-bottom:.5rem}
    .rounded-md{border-radius:.375rem}
    .flex-wrap{flex-wrap:wrap}
    .space-y-2> * + *{margin-top:.5rem}
    .space-y-3> * + *{margin-top:.75rem}
    .h-5{height:1.25rem}.w-5{width:1.25rem}
    .h-4{height:1rem}.w-4{width:1rem}
    .p-3{padding:.75rem}
  </style>
  <title>$title</title>
 </head>
<body>
  <div id="capture" class="mx-auto max-w-4xl p-6">
    <div class="grid gap-4 border bg-white p-6 shadow-lg rounded-lg">
      <div class="flex flex-col space-y-1.5">
        <h2 class="tracking-tight text-xl font-bold flex items-center gap-2">📄 $title</h2>
        <p class="text-sm text-slate-500">$desc</p>
      </div>

      <div class="flex items-center gap-4 text-sm text-slate-500">
        <div class="flex items-center gap-1"><span>创建时间: $created_str</span></div>
        <div class="flex items-center gap-1"><span>导出次数: $export_count</span></div>
        <div class="inline-flex items-center rounded-full border px-2.5 py-0.5 font-semibold text-xs">$context_mode</div>
      </div>

      <div class="space-y-4">
        <div class="rounded-lg border bg-white shadow-sm">
          <div class="p-6 pb-3">
            <h3 class="font-semibold tracking-tight text-sm flex items-center gap-2">🧠 AI分析结果</h3>
          </div>
          <div class="p-6 pt-0 space-y-4">
            <div>
              <div class="flex items-center gap-2 mb-2"><span class="font-medium">意图分析</span><div class="inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold text-xs bg-slate-100 border">$intent_primary</div></div>
              <div class="mt-2 p-3 bg-slate-100 rounded-md">
                <p class="text-sm text-slate-600 mb-2">$intent_desc</p>
                <div class="flex flex-wrap gap-1">$intent_secondary_html</div>
              </div>
            </div>

            <div>
              <div class="flex items-center gap-2 mb-2"><span class="font-medium">情感分析</span><div class="inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold text-xs bg-red-100 text-red-800 border-red-200 border">$sentiment_overall</div></div>
              <div class="mt-2 p-3 bg-slate-100 rounded-md">
                <p class="text-sm text-slate-600 mb-2">$sentiment_desc</p>
                <div class="flex flex-wrap gap-1">$sentiment_emotions_html</div>
              </div>
            </div>

            <div>
              <div class="flex items-center gap-2 mb-2"><span class="font-medium">语气分析</span><div class="inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold text-xs border">$tone_style</div></div>
              <div class="mt-2 p-3 bg-slate-100 rounded-md">
                <p class="text-sm text-slate-600 mb-2">$tone_desc</p>
              </div>
            </div>

            <div>
              <div class="flex items-center gap-2 mb-2"><span class="font-medium">关系分析</span><div class="inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold text-xs border">$relationship_closeness</div></div>
              <div class="mt-2 p-3 bg-slate-100 rounded-md">
                <p class="text-sm text-slate-600 mb-2">$relationship_desc</p>
              </div>
            </div>

            <div>
              <div class="flex items-center gap-2 mb-2"><span class="font-medium">潜台词分析</span></div>
              <div class="mt-2 p-3 bg-slate-100 rounded-md space-y-2">
                <div>
                  <span class="text-xs font-medium">隐含含义:</span>
                  <div class="flex flex-wrap gap-1 mt-1">$hidden_meanings_html</div>
                </div>
                <div>
                  <span class="text-xs font-medium">潜在影响:</span>
                  <div class="flex flex-wrap gap-1 mt-1">$implications_html</div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <div class="rounded-lg border bg-white shadow-sm">
          <div class="p-6 pb-3">
            <h3 class="font-semibold tracking-tight text-sm flex items-center gap-2">💡 智能回复建议</h3>
            <p class="text-xs text-slate-500">基于分析结果生成的回复建议，点击复制使用</p>
          </div>
          <div class="p-6 pt-0">
            <div class="space-y-3">
              $suggestions_html
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
""")

    return tpl.substitute(
        title=title,
        desc=desc,
        created_str=created_str,
        export_count=export_count,
        context_mode=context_mode,
        intent_primary=intent_primary,
        intent_desc=intent_desc,
        sentiment_overall=sentiment_overall,
        sentiment_desc=sentiment_desc,
        tone_style=tone_style,
        tone_desc=tone_desc,
        relationship_closeness=relationship_closeness,
        relationship_desc=relationship_desc,
        intent_secondary_html=badge_list(intent_secondary),
        sentiment_emotions_html=badge_list(sentiment_emotions),
        hidden_meanings_html=badge_list(hidden_meanings),
        implications_html=badge_list(implications),
        suggestions_html=render_suggestions(suggestions),
    )


async def generate_card_image_with_playwright(card: AnalysisCard, created_str: str) -> bytes:
    """使用 Playwright 渲染HTML并截图为PNG"""
    html = _build_html(card, created_str)
    logger.info(f"开始生成卡片图片，card_id={card.id}, title={card.title[:50]}")
    
    try:
        from playwright.async_api import async_playwright
        # 全局复用浏览器实例，减少冷启动耗时
        global _PW_INSTANCE, _BROWSER
        if '_PW_INSTANCE' not in globals():
            _PW_INSTANCE = None  # type: ignore[var-annotated]
        if '_BROWSER' not in globals():
            _BROWSER = None  # type: ignore[var-annotated]

        if _PW_INSTANCE is None or _BROWSER is None:
            _PW_INSTANCE = await async_playwright().start()
            _BROWSER = await _PW_INSTANCE.chromium.launch(headless=True, args=[
                "--disable-dev-shm-usage", "--disable-gpu", "--no-sandbox"
            ])

        context = await _BROWSER.new_context(device_scale_factor=2)
        page = await context.new_page()
        await page.set_viewport_size({"width": 1024, "height": 800})
        
        # 不再依赖外部CDN，阻断图片/字体加载
        async def handle_route(route, request):
            rtype = request.resource_type
            if rtype in ("image", "font"):
                return await route.abort()
            return await route.continue_()
        await page.route("**/*", handle_route)
        
        await page.set_content(html, wait_until="domcontentloaded")
        await page.emulate_media(media="screen")
        
        # 等待元素
        await page.wait_for_selector('#capture', state='attached', timeout=2000)
        # 禁用动画/过渡以稳定与提速
        await page.add_style_tag(content="*{animation:none !important;transition:none !important}")
        
        # 等待字体
        try:
            await page.evaluate("document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()")
        except Exception:
            pass
        
        # 获取元素信息
        elem = await page.query_selector('#capture')
        if not elem:
            logger.error("未找到 #capture 元素")
            png = await page.screenshot(full_page=True)
        else:
            # 调试信息
            try:
                bbox = await elem.bounding_box()
                scroll_height = await page.evaluate("document.getElementById('capture').scrollHeight")
                inner_text = await page.evaluate("document.querySelector('#capture')?.innerText || ''")
                text_len = len(inner_text)
                logger.info(f"Playwright调试 - bbox: {bbox}, scrollHeight: {scroll_height}, innerText长度: {text_len}")
                
                if text_len == 0:
                    logger.error("警告：元素内容为空！HTML可能有问题")
                    # 尝试获取HTML内容
                    html_content = await page.evaluate("document.querySelector('#capture')?.innerHTML || ''")
                    logger.info(f"#capture innerHTML长度: {len(html_content)}")
            except Exception as e:
                logger.error(f"获取调试信息失败: {e}")
            
            # 根据内容高度调整视口
            try:
                scroll_height = await page.evaluate("document.getElementById('capture').scrollHeight")
                if scroll_height > 0:
                    height = max(int(scroll_height) + 100, 800)
                    await page.set_viewport_size({"width": 1024, "height": min(height, 10000)})
                    logger.info(f"调整视口高度为: {height}")
            except Exception:
                pass
            
            # 再次获取bbox
            bbox = await elem.bounding_box()
            if not bbox or bbox.get('height', 0) < 10 or bbox.get('width', 0) < 10:
                logger.warning(f"元素尺寸过小: {bbox}，使用整页截图")
                png = await page.screenshot(full_page=True, type='png')
            else:
                logger.info(f"截取元素，bbox: {bbox}")
                png = await elem.screenshot(type='png')
        
        await context.close()
        
        # 验证截图数据
        if not png:
            logger.error("截图数据为空！")
            raise Exception("截图返回空数据")

        logger.info(f"截图成功，数据大小: {len(png)} 字节")
        return png
        
    except Exception as e:
        logger.error(f"Playwright 截图失败: {e}", exc_info=True)
        raise


