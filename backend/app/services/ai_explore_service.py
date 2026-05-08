# -*- coding: utf-8 -*-
"""
AI Explore Execution Service

以 DOM + 规则兜底为主，配合 LLM 生成候选定位方式，执行真实页面探索步骤。
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import List
from urllib.parse import urlparse

import yaml
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.services.ai_base import AIAPIError, AiBaseService

logger = logging.getLogger(__name__)


class ExploreStepResult:
    def __init__(self, step_no, action, selector, value, status, error=None, screenshot=None, duration_ms=0):
        self.step_no = step_no
        self.action = action
        self.selector = selector
        self.value = value
        self.status = status
        self.error = error
        self.screenshot = screenshot
        self.duration_ms = duration_ms

    def to_dict(self):
        return {
            "step_no": self.step_no,
            "action": self.action,
            "target": self.selector,
            "value": self.value,
            "status": self.status,
            "error": self.error,
            "screenshot": self.screenshot,
            "duration_ms": self.duration_ms,
        }


class ExploreResult:
    def __init__(self, status, total_steps, passed_steps, failed_steps, duration_ms, steps, yaml_case, discovered_locators=None):
        self.status = status
        self.total_steps = total_steps
        self.passed_steps = passed_steps
        self.failed_steps = failed_steps
        self.duration_ms = duration_ms
        self.steps = steps
        self.yaml_case = yaml_case
        self.discovered_locators = discovered_locators or []

    def to_dict(self):
        return {
            "status": self.status,
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "duration_ms": self.duration_ms,
            "steps": [s.to_dict() for s in self.steps],
            "yaml_case": self.yaml_case,
            "discovered_locators": self.discovered_locators,
        }


class AIExploreService:
    def __init__(self):
        self.ai = AiBaseService()

    def execute(self, steps, start_url, project_id, case_name="探索用例", module="explore",
                priority="P1", headless=True, auth_token=None, storage_state_path=None) -> ExploreResult:
        holder = {}

        def _run():
            try:
                holder["result"] = self._execute(
                    steps, start_url, project_id, case_name, module, priority, headless, auth_token, storage_state_path
                )
            except Exception as e:
                logger.error(f"[AIExplore] error: {e}")
                holder["error"] = str(e)

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join(timeout=600)
        if "error" in holder:
            raise Exception(holder["error"])
        if "result" not in holder:
            raise Exception("探索执行超时（10分钟）")
        return holder["result"]

    def _execute(self, steps, start_url, project_id, case_name, module, priority, headless, auth_token, storage_state_path=None) -> ExploreResult:
        start_time = time.time()
        results: List[ExploreStepResult] = []
        passed = 0
        failed = 0
        dom_cache = {"url": "", "dom": ""}
        planned_steps = self._plan_steps(steps)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={"Authorization": f"Bearer {auth_token}"} if auth_token else {},
                storage_state=storage_state_path if storage_state_path else None,
            )
            page = context.new_page()
            page.goto(start_url, wait_until="networkidle", timeout=60000)
            self._wait_for_interactive_content(page)
            current_url = page.url

            for index, step_desc in enumerate(steps, start=1):
                logger.info(f"[AIExplore] step {index}/{len(steps)}: {step_desc[:80]}")
                step_plan = planned_steps[index - 1] if index - 1 < len(planned_steps) else {"raw": step_desc}
                step_result = self._execute_step(page, index, step_desc, current_url, dom_cache, step_plan)
                results.append(step_result)
                if step_result.status == "passed":
                    passed += 1
                    logger.info(f"[AIExplore] step {index} PASSED ({step_result.duration_ms}ms)")
                else:
                    failed += 1
                    logger.warning(f"[AIExplore] step {index} FAILED: {step_result.error}")
                current_url = page.url

            browser.close()

        duration_ms = int((time.time() - start_time) * 1000)
        status = "passed" if failed == 0 else ("partial" if passed > 0 else "failed")
        yaml_case = self._make_yaml(case_name, module, priority, results, start_url)
        discovered_locators = self._build_discovered_locators(results, current_url, module)
        return ExploreResult(status, len(steps), passed, failed, duration_ms, results, yaml_case, discovered_locators)

    def _execute_step(self, page, step_no, step_desc, current_url, dom_cache, step_plan=None):
        started_at = time.time()
        screenshot = None
        action = selector = value = ""
        try:
            self._wait_for_interactive_content(page, timeout_ms=12000)
            if dom_cache.get("url") == page.url and dom_cache.get("dom"):
                dom = dom_cache["dom"]
            else:
                dom = self._get_dom(page)
                if not dom:
                    page.wait_for_timeout(1200)
                    dom = self._get_dom(page)
                dom_cache["url"] = page.url
                dom_cache["dom"] = dom or ""

            selector_info = self._llm_selector(
                step_desc=step_desc,
                dom=dom or "",
                url=current_url,
                screenshot=None,
                step_plan=step_plan or {},
            )
            action = selector_info.get("action", "click")
            selector = selector_info.get("selector", "")
            value = selector_info.get("value", "")
            if not selector:
                raise ValueError("LLM 未生成 selector")

            self._do_action_with_retry(page, action, selector, value)
            url_before = current_url
            time.sleep(0.3)
            if page.url != url_before:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    self._wait_for_interactive_content(page, timeout_ms=12000)
                except PlaywrightTimeout:
                    pass
                dom_cache["url"] = ""
                dom_cache["dom"] = ""
            time.sleep(0.3)
            return ExploreStepResult(
                step_no, action, selector, value, "passed", screenshot=screenshot,
                duration_ms=int((time.time() - started_at) * 1000)
            )
        except Exception as e:
            screenshot = f"backend/screenshots/explore_s{step_no}_{int(time.time() * 1000)}.png"
            try:
                page.screenshot(path=screenshot)
            except Exception:
                screenshot = None
            return ExploreStepResult(
                step_no, action, selector, value, "failed", error=str(e), screenshot=screenshot,
                duration_ms=int((time.time() - started_at) * 1000)
            )

    def _get_dom(self, page) -> str:
        try:
            js = """
            () => {
              const out = [];
              const selectors = 'button,a,input,select,textarea,label,span,div,li,h1,h2,h3,h4,p';
              document.querySelectorAll(selectors).forEach((el) => {
                const tag = el.tagName.toLowerCase();
                const text = (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60);
                const rect = el.getBoundingClientRect();
                const visible = rect.width > 0 && rect.height > 0;
                if (!visible && !text) return;
                const attrs = [];
                const id = el.getAttribute('id');
                const cls = el.getAttribute('class');
                const role = el.getAttribute('role');
                const href = el.getAttribute('href');
                const type = el.getAttribute('type');
                const placeholder = el.getAttribute('placeholder');
                const ariaLabel = el.getAttribute('aria-label');
                if (id) attrs.push(`id=${JSON.stringify(id)}`);
                if (cls) attrs.push(`cls=${JSON.stringify(cls.split(' ').slice(0, 4).join(' '))}`);
                if (role) attrs.push(`role=${JSON.stringify(role)}`);
                if (href) attrs.push(`href=${JSON.stringify(href.slice(0, 60))}`);
                if (type) attrs.push(`type=${JSON.stringify(type)}`);
                if (placeholder) attrs.push(`placeholder=${JSON.stringify(placeholder.slice(0, 30))}`);
                if (ariaLabel) attrs.push(`aria=${JSON.stringify(ariaLabel.slice(0, 30))}`);
                out.push(`${visible ? 'Y' : 'N'} ${tag}${attrs.length ? '[' + attrs.join(',') + ']' : ''} txt=${JSON.stringify(text)}`);
              });
              return out.slice(0, 120).join('\\n');
            }
            """
            return page.evaluate(js) or ""
        except Exception as e:
            logger.warning(f"[AIExplore] DOM failed: {e}")
            return ""

    def _wait_for_interactive_content(self, page, timeout_ms: int = 20000):
        """
        等待页面进入可交互状态。

        通用判断标准：
        - 无骨架屏/加载占位符
        - 有足够的文字内容（> 100 字符）
        - 有可交互元素（button / input / a）
        不再依赖任何业务关键词。
        """
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            try:
                state = page.evaluate(
                    """
                    () => {
                      const body = document.body;
                      const text = body
                        ? (body.innerText || body.textContent || '').replace(/\\s+/g, ' ').trim()
                        : '';
                      const skeletonCount = document.querySelectorAll(
                        '[class*="skeleton"],[class*="Skeleton"],[class*="shimmer"],[data-testid*="skeleton"],[class*="loading"]'
                      ).length;
                      const interactiveCount = document.querySelectorAll(
                        'button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[role="button"],[role="tab"]'
                      ).length;
                      return { textLength: text.length, skeletonCount, interactiveCount };
                    }
                    """
                )
                if (
                    state.get("textLength", 0) > 100
                    and state.get("skeletonCount", 0) == 0
                    and state.get("interactiveCount", 0) > 0
                ):
                    return
            except Exception:
                pass
            page.wait_for_timeout(800)

    def _llm_selector(self, step_desc, dom, url, screenshot=None, step_plan=None) -> dict:
        dom_text = (dom or "")[:4000]
        step_plan = step_plan or {}
        plan_hint = ""
        if step_plan:
            plan_hint = (
                f"\n步骤规划提示: action={step_plan.get('action_hint', '')}; "
                f"target={step_plan.get('target_hint', '')}; value={step_plan.get('value_hint', '')}\n"
            )

        for attempt in range(2):
            try:
                if screenshot:
                    prompt = (
                        f"你是 Playwright 自动化测试专家。\n"
                        f"用户步骤: {step_desc}\n当前页面: {url}\n页面元素信息:\n{dom_text}\n\n"
                        f"请输出严格 JSON: {{\"action\":\"click|fill|type|navigate|wait|assert_text\",\"selector\":\"...\",\"value\":\"...\"}}"
                    )
                    text = self.ai.vision(image=screenshot, prompt=prompt)
                else:
                    prompt = (
                        f"你是 Playwright 自动化测试专家。\n\n"
                        f"页面元素列表:\n{dom_text}\n\n"
                        f"用户步骤: {step_desc}\n当前页面: {url}\n{plan_hint}\n"
                        f"优先输出文本断言、button:has-text、input[type=...]、text=... 这种稳定定位。\n"
                        f"请输出严格 JSON: {{\"action\":\"click|fill|type|navigate|wait|assert_text\",\"selector\":\"...\",\"value\":\"...\"}}"
                    )
                    text = self.ai.generate(prompt=prompt, system_prompt="", max_tokens=512)
                result = self._parse(text)
                if result.get("selector"):
                    return result
            except AIAPIError as e:
                logger.error(f"[AIExplore] LLM error (attempt {attempt + 1}): {e}")

        logger.warning(f"[AIExplore] All LLM attempts failed, using fallback for step: {step_desc}")
        return self._fallback_selector(step_desc)

    def _plan_steps(self, steps: List[str]) -> List[dict]:
        """
        对步骤文本做轻量语义解析，生成 action_hint / value_hint 供 LLM 参考。
        只做通用动词识别，不再写死任何业务关键词（去认证/同意并继续 等已移除）。
        target_hint 由 LLM 根据 DOM 自行判断，无需预设。
        """
        planned = []
        for step in steps:
            raw = (step or "").strip()
            item = {"raw": raw, "action_hint": "", "target_hint": "", "value_hint": ""}

            # 通用动词识别（action_hint）
            if any(word in raw for word in ["输入", "填写", "键入", "fill", "type"]):
                item["action_hint"] = "fill"
            elif any(word in raw for word in ["确认", "校验", "验证", "assert", "check"]):
                item["action_hint"] = "assert_text"
            elif any(word in raw for word in ["点击", "click", "按下", "选择"]):
                item["action_hint"] = "click"
            elif any(word in raw for word in ["等待", "wait"]):
                item["action_hint"] = "wait"

            # 提取输入值（value_hint）— 通用：取动词后面的内容
            value_match = re.search(r"(?:输入|填写|键入|fill|type)\s+(.+)$", raw)
            if value_match:
                item["value_hint"] = value_match.group(1).strip()

            planned.append(item)
        return planned

    def _build_discovered_locators(self, step_results: List[ExploreStepResult], current_url: str, module: str) -> List[dict]:
        discovered = []
        seen = set()
        page_name = self._page_name_from_url(current_url, module)

        for step in step_results:
            if step.status != "passed" or not step.selector:
                continue
            if step.action == "assert_text":
                continue
            key = self._slugify_key(page_name, step.action, step.selector)
            if key in seen:
                continue
            seen.add(key)
            selector_type = self._infer_selector_type(step.selector)
            discovered.append({
                "page_name": page_name,
                "element_key": key.split(".", 1)[1] if "." in key else key,
                "full_key": key,
                "selector": step.selector,
                "selector_type": selector_type,
                "description": f"探索执行发现: {step.action}",
                "priority": 1,
                "strategies": [{
                    "type": selector_type,
                    "value": step.selector,
                    "priority": 1,
                    "confidence": 0.85,
                    "enabled": True,
                }],
            })

        return discovered

    def _page_name_from_url(self, current_url: str, module: str) -> str:
        path = urlparse(current_url or "").path.strip("/")
        if not path:
            return module or "explore"
        return re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_").lower() or (module or "explore")

    def _slugify_key(self, page_name: str, action: str, selector: str) -> str:
        selector_part = selector.replace("text=", "").replace("xpath=", "")
        selector_part = re.sub(r"[^a-zA-Z0-9]+", "_", selector_part).strip("_").lower()
        selector_part = selector_part[:40] or "target"
        return f"{page_name}.{action}_{selector_part}"

    def _infer_selector_type(self, selector: str) -> str:
        if selector.startswith("text="):
            return "text"
        if selector.startswith("role="):
            return "role"
        if selector.startswith("xpath=") or selector.startswith("//") or selector.startswith("(//"):
            return "xpath"
        return "css"

    def _fallback_selector(self, step_desc: str) -> dict:
        """
        LLM 两次调用均未返回有效 selector 时的通用语义兜底。
        不依赖任何业务关键词，通过动词语义生成候选 selector。
        """
        step = (step_desc or "").strip()

        # 断言类步骤 — 提取断言目标文本
        if any(word in step for word in ["确认", "校验", "验证", "assert", "check"]):
            cleaned = re.sub(
                r"^(确认|校验|验证|assert|check)[页面展示]?[：:]*\s*", "", step
            ).strip("，,。 ")
            return {"action": "assert_text", "selector": "body", "value": cleaned or step}

        # 点击类步骤 — 提取按钮/链接文字
        if any(word in step for word in ["点击", "click", "按下", "选择", "打开"]):
            text = re.sub(r"^(点击|click|按下|选择|打开)\s*", "", step).strip()
            text = re.sub(r"(按钮|链接|Tab|选项卡|菜单|图标)$", "", text).strip()
            if text:
                return {"action": "click", "selector": f"text={text}", "value": ""}

        # 输入类步骤 — 提取输入值及目标字段类型
        if any(word in step for word in ["输入", "填写", "fill", "type", "键入"]):
            value_match = re.search(r"(?:输入|填写|fill|type|键入)\s+(.+?)(?:\s|$)", step)
            value = value_match.group(1).strip() if value_match else ""
            if any(word in step for word in ["密码", "password", "passwd"]):
                return {"action": "fill", "selector": "input[type='password']:visible", "value": value}
            return {"action": "fill", "selector": "input:visible", "value": value}

        # 兜底：用步骤前 20 字作为 text 选择器
        return {"action": "click", "selector": f"text={step[:20]}", "value": ""}

    def _parse(self, text):
        text = re.sub(r"```[\s\S]*?```", "", (text or "")).strip()
        logger.warning(f"[AIExplore] _parse input: {text[:400]}")

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end + 1])
                return {
                    "action": data.get("action", "click"),
                    "selector": data.get("selector", ""),
                    "value": data.get("value", ""),
                }
            except Exception as e:
                logger.warning(f"[AIExplore] JSON parse failed: {e}")

        patterns = [
            (r'"action"\s*:\s*"([^"]*)"', "action"),
            (r'"action"\s*:\s*([a-z_]+)', "action"),
            (r'"selector"\s*:\s*"([^"]*)"', "selector"),
            (r'"value"\s*:\s*"([^"]*)"', "value"),
        ]
        result = {"action": "click", "selector": "", "value": ""}
        for pattern, key in patterns:
            matched = re.search(pattern, text)
            if matched:
                result[key] = matched.group(1)
        if not result["selector"]:
            logger.warning(f"[AIExplore] empty selector: {text[:500]}")
        return result

    def _do_action_with_retry(self, page, action, selector, value, max_retries=2):
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                if action == "click" and selector.startswith("text="):
                    if self._js_click_text(page, selector[5:].strip()):
                        return
                self._do_action(page, action, selector, value)
                return
            except PlaywrightTimeout:
                last_err = f"Timeout: selector '{selector}' not found or not clickable"
                if attempt < max_retries:
                    selector = self._fix_selector(page, selector, action)
                    logger.warning(f"[AIExplore] Retry {attempt + 1} with fixed selector: {selector}")
            except Exception as e:
                last_err = str(e)
                if attempt < max_retries:
                    selector = self._fix_selector(page, selector, action)
                    logger.warning(f"[AIExplore] Retry {attempt + 1}: {e} -> try: {selector}")
        raise Exception(last_err)

    def _fix_selector(self, page, selector, action) -> str:
        selector = (selector or "").strip()
        logger.warning(f"[AIExplore] _fix_selector: action={action} selector={selector}")

        if action in ("fill", "type"):
            try:
                if page.locator("input[type='password']").count() > 0:
                    return "input[type='password']"
            except Exception:
                pass
            try:
                if page.locator("input[type='text']").count() > 0:
                    return "input[type='text']"
            except Exception:
                pass

        if action == "click" and selector.startswith("text="):
            text = selector[5:].strip()
            for tag in ["button", "a", "div", "span"]:
                try:
                    count = page.locator(f"{tag}:has-text('{text}')").count()
                    if count > 0:
                        return f"{tag}:has-text('{text}')"
                except Exception:
                    pass
            return selector

        return selector

    def _do_action(self, page, action, selector, value):
        if action == "navigate":
            page.goto(value, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)
            return
        if action == "assert_text":
            expected_text = value or selector.replace("text=", "").strip()
            if not self._page_text_contains(page, expected_text):
                raise Exception(f"Expected page text not found: {expected_text}")
            return

        locator = self._make_locator(page, selector)
        if action in ("fill", "type"):
            locator.fill(value, timeout=15000)
        elif action == "click":
            locator.click(timeout=15000)
        elif action == "hover":
            locator.hover(timeout=15000)
        elif action == "select":
            locator.select_option(value, timeout=15000)
        elif action == "assert":
            locator.wait_for(state="visible", timeout=15000)
        elif action == "wait":
            locator.wait_for(state="visible", timeout=int(value) if value else 5000)

    def _make_locator(self, page, selector):
        selector = (selector or "").strip()
        if not selector:
            raise ValueError("Empty selector")
        if selector == "body":
            return page.locator("body").first
        if selector.startswith("text="):
            return page.locator(f"text={selector[5:]}").first
        if selector.startswith("role="):
            parts = re.split(r"\[name=", selector[5:])
            if len(parts) == 2:
                role = parts[0].strip()
                name = parts[1].rstrip("]").strip("'\"")
                return page.get_by_role(role, name=name)
            return page.get_by_role(selector[5:])
        if " + " in selector or " input" in selector:
            parts = re.split(r"\s*\+\s*|\s+input", selector)
            if parts:
                label_selector = parts[0].strip()
                label = page.locator(label_selector).first
                sibling_input = label.locator("xpath=following-sibling::input").first
                if sibling_input.count() > 0:
                    return sibling_input
        if selector.startswith("button:") and ":has-text(" in selector:
            match = re.search(r":has-text\(['\"](.+?)['\"]\)", selector)
            if match:
                return page.locator(f"button:has-text('{match.group(1)}')").first
        if ":has-text(" in selector:
            match = re.search(r"^(.+?):has-text\(['\"](.+?)['\"]\)", selector)
            if match:
                return page.locator(match.group(1)).filter(has_text=match.group(2)).first
        if any(selector.startswith(prefix) for prefix in ("(", "#", ".", "[", "*", "div", "span", "input", "button", "a", "label", "nav")):
            return page.locator(selector).first
        return page.get_by_text(selector, exact=False).first

    def _page_text_contains(self, page, text: str) -> bool:
        if not text:
            return True
        try:
            return bool(page.evaluate(
                """target => (document.body && (document.body.innerText || document.body.textContent || '')).includes(target)""",
                text,
            ))
        except Exception:
            return False

    def _js_click_text(self, page, text: str) -> bool:
        if not text:
            return False
        try:
            clicked = page.evaluate(
                """
                target => {
                  const normalize = value => (value || '').replace(/\\s+/g, ' ').trim();
                  const matches = value => normalize(value).includes(target);
                  const selectors = ['button', 'a', 'div', 'span', '[role=\"button\"]'];
                  for (const selector of selectors) {
                    for (const el of document.querySelectorAll(selector)) {
                      const content = normalize(el.innerText || el.textContent || '');
                      if (!content || !matches(content)) continue;
                      const rect = el.getBoundingClientRect();
                      if (!rect.width || !rect.height) continue;
                      el.scrollIntoView({block: 'center', inline: 'center'});
                      el.click();
                      return true;
                    }
                  }
                  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                  let node;
                  while ((node = walker.nextNode())) {
                    const content = normalize(node.textContent || '');
                    if (!content || !matches(content)) continue;
                    let element = node.parentElement;
                    while (element) {
                      const rect = element.getBoundingClientRect();
                      const role = element.getAttribute('role');
                      const clickable = ['BUTTON', 'A', 'DIV', 'SPAN'].includes(element.tagName) || role === 'button' || typeof element.onclick === 'function';
                      if (clickable && rect.width && rect.height) {
                        element.scrollIntoView({block: 'center', inline: 'center'});
                        element.click();
                        return true;
                      }
                      element = element.parentElement;
                    }
                  }
                  return false;
                }
                """,
                text,
            )
            if clicked:
                page.wait_for_timeout(1200)
            return bool(clicked)
        except Exception:
            return False

    def _make_yaml(self, case_name, module, priority, steps, start_url=""):
        yaml_steps = []
        for step in steps:
            item = {"action": step.action, "target": step.selector}
            if step.value:
                item["value"] = step.value
            yaml_steps.append(item)
        case_data = {
            "id": f"TC_EXPLORE_{int(time.time())}",
            "name": case_name,
            "module": module,
            "priority": priority,
            "url": start_url,
            "tags": ["explore", "ai-generated"],
            "source": "explore",
            "steps": yaml_steps,
            "expected": "探索执行全部步骤通过",
        }
        return yaml.dump(case_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
