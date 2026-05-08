# -*- coding: utf-8 -*-
"""
AI Locator Service - AI 自动生成页面元素定位符
Playwright 抓取页面结构 + MiniMax Text API 分析生成定位符
支持 AI 意图理解：用户描述目标（如"账密登录"），AI 自动找到切换按钮并执行
支持带登录态获取页面（复用项目登录用例）
"""

import json
import logging
import re
import sys
import tempfile
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.ai_base import AiBaseService

logger = logging.getLogger(__name__)


LOCATOR_SYSTEM_PROMPT = """你是专业的 Web 自动化测试工程师，负责为页面元素生成可复用、健壮的定位策略。

你的任务：
1. 分析页面结构文本中的可交互元素
2. 为每个元素输出 1 到 3 个候选定位策略
3. 优先使用更稳定的语义定位，其次再退回 CSS/XPath
4. 直接输出 JSON，不要解释

输出格式要求：
- 顶层 key 格式：页面名.元素描述（英文小写下划线）
- 每个元素 value 必须是对象，包含：
  - description
  - primary_type
  - strategies
- strategies 是数组，每项包含：
  - type: css / xpath / role / text / label / placeholder / testid
  - value: 字符串，或 role 类型对应的对象 {"role": "...", "name": "..."}
  - priority: 数字，越小越优先
  - confidence: 0.0-1.0
  - enabled: true

优先级建议：
- testid / role / label / placeholder 优先
- text 次之
- css / xpath 作为 fallback

如果无法提供多策略，至少返回 1 条 strategy。
只输出 JSON。"""

INTENT_SYSTEM_PROMPT = """你是一个网页自动化助手。用户想获取某个登录方式的元素定位符，但你需要先帮用户找到切换到目标登录方式的按钮，然后 AI 才能生成准确的 locators。

分析页面元素，找出切换到目标登录方式的按钮或 Tab。

输出格式（直接输出 JSON，不要解释）：
{
  "click_target": "按钮文字或描述",
  "reason": "为什么选这个按钮"
}

如果页面已经显示了目标登录方式（不需要切换），返回：
{
  "click_target": null,
  "reason": "页面已显示目标登录方式"
}"""


class AILocatorService:

    def __init__(self, playwright_client=None):
        self.ai = AiBaseService()
        self.playwright = playwright_client
        self.auth_state_dir = Path(__file__).parent.parent.parent / ".auth_states"
        self.auth_state_dir.mkdir(parents=True, exist_ok=True)
        self._last_parse_diagnostics: Dict[str, Any] = {}

    def generate_from_url(
        self,
        url: str,
        page_name: str = "",
        viewport: dict = None,
        intent: str = "",
    ) -> Dict[str, Any]:
        """
        从 URL 生成 locators
        工作流程：
          - 无 intent：Playwright 打开页面 → 抓 DOM → AI 分析
          - 有 intent：Playwright 打开页面 → AI 找出切换按钮 → 点击 → 抓新 DOM → AI 分析
        """
        html_content = None

        if self.playwright:
            try:
                html_content = self._fetch_page_content(url, viewport, intent)
            except Exception as e:
                logger.warning(f"[AILocator] fetch page failed: {e}")
                html_content = None

        page_id = page_name or url
        if html_content:
            result = self._analyze_html_content(html_content, page_id)
            if self.playwright:
                result["validation_summary"] = self._validate_locators_for_url(
                    url=url,
                    viewport=viewport,
                    locators=result.get("locators", {}),
                    intent=intent,
                )
            return result
        else:
            return self._analyze_url_only(url, page_name or "")

    def enhance_locators(
        self,
        existing_locators: Dict[str, Any],
        url: str,
        page_name: str = "",
    ) -> Dict[str, Any]:
        """补全已有的 locators"""
        new_locators = self.generate_from_url(url, page_name)

        enhanced = dict(existing_locators)
        for key, loc in new_locators.get("locators", {}).items():
            if key not in enhanced:
                enhanced[key] = loc
            else:
                old_conf = enhanced[key].get("ai_confidence", 0)
                new_conf = loc.get("ai_confidence", 0)
                if new_conf > old_conf:
                    enhanced[key] = loc
                    logger.info(f"[AILocator] upgraded {key}: {old_conf} → {new_conf}")

        return enhanced

    def _get_auth_state_path(self, project_name: str, login_case_id: int, base_url: str) -> Path:
        cache_key = hashlib.md5(f"{project_name}:{login_case_id}:{base_url}".encode("utf-8")).hexdigest()[:12]
        return self.auth_state_dir / f"{project_name}_case{login_case_id}_{cache_key}.json"

    def _is_auth_state_fresh(self, state_path: Path, max_age_seconds: int = 1800) -> bool:
        if not state_path.exists():
            return False
        age = time.time() - state_path.stat().st_mtime
        if age > max_age_seconds:
            return False
        # A file with no cookies/origins is useless — treat it as stale
        try:
            with open(state_path, "r", encoding="utf-8") as _f:
                _state = json.load(_f)
            if not _state.get("cookies") and not _state.get("origins"):
                logger.warning(f"[AILocator] auth state has no cookies, ignoring cache: {state_path}")
                return False
        except Exception:
            return False
        return True

    def _looks_authenticated(self, page, target_url: str, login_case) -> bool:
        current_url = page.url or target_url
        login_name = (getattr(login_case, "name", "") or "").lower()
        if "/login" in current_url.lower() or "/signin" in current_url.lower():
            return False
        if "登录" in page.title():
            return False
        if "login" in login_name and current_url.rstrip("/") == target_url.rstrip("/"):
            return True
        return True

    def _build_login_state_cache(
        self,
        state_path,
        page,
        login_case,
        project_name: str,
        base_url: str,
    ) -> bool:
        logger.info("[AILocator] executing login case to refresh auth cache...")
        case_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        case_file.write(login_case.content)
        case_file.close()

        try:
            engine_kwargs = {
                "headless": True,
                "base_url": base_url or "",
                "execution_id": f"ai_loc_{login_case.id}",
            }
            _eng_parent = Path(__file__).parent.parent.parent.parent
            if str(_eng_parent) not in sys.path:
                sys.path.insert(0, str(_eng_parent))
            from engine import TestEngine

            engine = TestEngine(project_name, **engine_kwargs)
            case_data = engine.load_case(case_file.name)

            # Navigate to the login URL if the page is blank or not on the login page yet
            case_url = case_data.get("url") or ""
            current_url = page.url or ""
            if case_url and ("about:blank" in current_url or not current_url):
                logger.info(f"[AILocator] navigating to login URL before executing case: {case_url}")
                page.goto(case_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(500)

            result = engine.execute_case_on_page(case_data, page=page)
            logger.info(f"[AILocator] login case finished with status: {result.status}, error: {result.error_msg}")
            if state_path is not None:
                page.context.storage_state(path=str(state_path))
            return True
        except Exception as e:
            logger.error(f"[AILocator] _build_login_state_cache failed: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            try:
                Path(case_file.name).unlink(missing_ok=True)
            except Exception:
                pass

    # ─── 内部方法 ────────────────────────────────────────────────────

    def _fetch_page_content(self, url: str, viewport: dict = None, intent: str = "") -> str:
        """使用 Playwright 抓取页面 HTML 和可交互元素"""
        import logging
        logger = logging.getLogger(__name__)

        if not self.playwright:
            raise RuntimeError("Playwright client not available")

        pw = self.playwright
        if not pw._browser:
            pw.launch()

        viewport = viewport or pw.viewport
        ctx = pw._browser.new_context(viewport=viewport)
        page = ctx.new_page()

        try:
            logger.info(f"[AILocator] navigate to {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            logger.info(f"[AILocator] page loaded, url={page.url}, intent={intent}")
            page.wait_for_timeout(500)

            # 如果有目标意图，先让 AI 判断是否需要点击切换
            if intent:
                logger.info(f"[AILocator] processing intent: {intent}")
                self._navigate_to_intent(page, intent)
                logger.info(f"[AILocator] intent done, final url={page.url}")

            # 提取可交互元素信息
            elements_info = self._extract_interactive_elements(page)

            # 组合成结构化文本
            structured = self._build_page_description(elements_info, page.url or url, intent)
            return structured
        except Exception as e:
            logger.warning(f"[AILocator] fetch error: {e}, attempting fallback")
            # 尝试继续：获取当前页面的元素（即使不完整）
            try:
                elements_info = self._extract_interactive_elements(page)
                structured = self._build_page_description(elements_info, page.url or url, intent)
                return structured
            except Exception as fallback_err:
                logger.warning(f"[AILocator] fallback also failed: {fallback_err}")
                raise
        finally:
            page.close()
            ctx.close()

    def _navigate_to_intent(self, page, intent: str):
        """
        根据用户意图，AI 判断切换按钮并执行点击
        流程：提取页面元素 → 问 AI 该点击什么 → Playwright 执行
        """
        # 1. 提取当前页面可交互元素
        elements_info = self._extract_interactive_elements(page)
        page_desc = self._build_page_description(elements_info, page.url, intent)

        # 2. 让 AI 判断该点击哪个元素（限制 20 秒超时，防止挂起）
        intent_prompt = (
            f"用户目标：{intent}\n"
            f"分析以下页面元素，找出点击哪个按钮/Tab 可以切换到「{intent}」。"
            f"只需要告诉我该点击什么，不要生成 locators。\n\n{page_desc[:6000]}"
        )

        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(110)
        try:
            result_text = self.ai.generate(intent_prompt, system_prompt=INTENT_SYSTEM_PROMPT)
        except Exception as e:
            logger.warning(f"[AILocator] AI intent 分析超时或失败: {e}，跳过 intent 导航")
            socket.setdefaulttimeout(old_timeout)
            return
        finally:
            socket.setdefaulttimeout(old_timeout)

        # 3. 解析 AI 返回，找到 click_target
        click_target = self._parse_intent_response(result_text)

        if click_target:
            logger.info(f"[AILocator] AI 决定点击: {click_target}")
            self._click_element_by_text(page, click_target)
            # 等待切换完成
            page.wait_for_timeout(800)
        else:
            logger.info(f"[AILocator] AI 判断页面已显示目标，无需切换")

    def _parse_intent_response(self, text: str) -> Optional[str]:
        """从 AI 响应中提取要点击的元素描述"""
        text = text.strip()

        try:
            data = json.loads(text)
            return data.get("click_target")
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 click_target
        m = re.search(r'"click_target"\s*:\s*"?([^",}]+)"?', text)
        if m and m.group(1).strip().lower() not in ("null", "none", ""):
            return m.group(1).strip()

        return None

    def _click_element_by_text(self, page, text: str):
        """根据文字内容点击元素"""
        import logging
        logger = logging.getLogger(__name__)

        # 优先通过 Playwright 的 get_by_text 精确匹配
        try:
            page.get_by_text(text, exact=False).first.click(timeout=3000)
            logger.info(f"[AILocator] clicked via get_by_text: {text}")
            page.wait_for_timeout(500)
            return
        except Exception as e:
            logger.warning(f"[AILocator] get_by_text failed for '{text}': {e}")

        # Fallback：XPath 文本匹配
        xpath = f"//*[contains(text(),'{text}')]"
        try:
            elems = page.query_selector_all(f"xpath={xpath}")
            for el in elems:
                try:
                    if el.is_visible():
                        el.click(timeout=3000)
                        logger.info(f"[AILocator] clicked via xpath: {text}")
                        page.wait_for_timeout(500)
                        return
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[AILocator] xpath click failed for '{text}': {e}")

        # Fallback2：模糊 class / aria-label 匹配
        selectors = [
            f"[aria-label*='{text}']",
            f"[title*='{text}']",
            f"[data-testid*='{text}']",
        ]
        for sel in selectors:
            try:
                elems = page.query_selector_all(sel)
                for el in elems:
                    if el.is_visible():
                        el.click(timeout=3000)
                        logger.info(f"[AILocator] clicked via selector {sel}: {text}")
                        page.wait_for_timeout(500)
                        return
            except Exception:
                pass

        logger.warning(f"[AILocator] could not click '{text}' - element not found or not visible")

    def _extract_interactive_elements(self, page) -> list:
        """提取可交互元素"""
        selectors = [
            ("input:not([type='hidden'])", "input"),
            ("button", "button"),
            ("a", "link"),
            ("select", "select"),
            ("textarea", "textarea"),
            ("[role='button']", "role_button"),
            ("[role='link']", "role_link"),
            ("[role='textbox']", "role_textbox"),
            ("[role='checkbox']", "role_checkbox"),
            ("[role='radio']", "role_radio"),
            ("[role='tab']", "role_tab"),
            ("[contenteditable='true']", "editable"),
        ]

        results = []
        for css_sel, elem_type in selectors:
            try:
                elems = page.query_selector_all(css_sel)
                for idx, elem in enumerate(elems):
                    info = self._describe_element(elem, elem_type, idx)
                    if info:
                        results.append(info)
            except Exception:
                pass

        return results

    def _describe_element(self, elem, elem_type: str, idx: int) -> Optional[dict]:
        """提取单个元素的定位信息"""
        try:
            visible = elem.is_visible()
            if not visible:
                return None

            tag = elem.evaluate("el => el.tagName.toLowerCase()")
            elem_id = elem.get_attribute("id") or ""
            elem_class = " ".join(
                c for c in (elem.get_attribute("class") or "").split()
                if c and "ng-" not in c and "a-" not in c
            )[:80]
            elem_name = elem.get_attribute("name") or ""
            elem_type_attr = elem.get_attribute("type") or ""
            placeholder = elem.get_attribute("placeholder") or ""
            aria_label = elem.get_attribute("aria-label") or ""
            data_testid = elem.get_attribute("data-testid") or ""
            href = elem.get_attribute("href") or ""
            value = elem.get_attribute("value") or ""
            text = (elem.inner_text() or "").strip()[:60]
            role = elem.get_attribute("role") or ""
            tab_text = elem.get_attribute("aria-selected") or ""

            if not (elem_id or elem_class or elem_name or placeholder or text or href or aria_label):
                return None

            desc = ""
            if text:
                desc = text.replace("\n", " ").strip()
            elif placeholder:
                desc = placeholder
            elif aria_label:
                desc = aria_label
            elif elem_name:
                desc = elem_name

            return {
                "type": elem_type,
                "tag": tag,
                "id": elem_id,
                "class": elem_class,
                "name": elem_name,
                "input_type": elem_type_attr,
                "placeholder": placeholder,
                "aria_label": aria_label,
                "data_testid": data_testid,
                "href": href,
                "value": value,
                "text": text,
                "description": desc,
                "role": role,
                "aria_selected": tab_text,
            }
        except Exception:
            return None

    def _build_page_description(self, elements: list, url: str, intent: str = "") -> str:
        """把元素信息组合成 AI 可分析的文本"""
        lines = [
            f"页面URL: {url}",
            f"可交互元素数量: {len(elements)}",
        ]
        if intent:
            lines.append(f"用户目标: {intent}")

        lines.append("")
        lines.append("=== 可交互元素详情 ===")

        for i, el in enumerate(elements):
            lines.append(f"[{i+1}] {el['type']} | tag:{el['tag']} | text:{el['description'][:50]}")
            if el["id"]:
                lines.append(f"    id={el['id']}")
            if el["class"]:
                lines.append(f"    class={el['class'][:60]}")
            if el["name"]:
                lines.append(f"    name={el['name']}")
            if el["placeholder"]:
                lines.append(f"    placeholder={el['placeholder']}")
            if el["aria_label"]:
                lines.append(f"    aria-label={el['aria_label']}")
            if el["data_testid"]:
                lines.append(f"    data-testid={el['data_testid']}")
            if el["href"]:
                lines.append(f"    href={el['href'][:80]}")
            if el["input_type"]:
                lines.append(f"    input_type={el['input_type']}")
            if el["role"]:
                lines.append(f"    role={el['role']}")
            if el["aria_selected"]:
                lines.append(f"    aria-selected={el['aria_selected']}")

            # 推荐 selector 候选
            candidates = []
            if el["id"]:
                candidates.append(f"#{el['id']}")
            if el["data_testid"]:
                candidates.append(f"[data-testid='{el['data_testid']}']")
            if el["name"] and el["tag"] in ("input", "select", "textarea"):
                candidates.append(f"[name='{el['name']}']")
            if el["placeholder"]:
                candidates.append(f"[placeholder='{el['placeholder']}']")
            if el["aria_label"]:
                candidates.append(f"[aria-label='{el['aria_label']}']")
            if el["class"]:
                classes = el["class"].split()[:3]
                for c in classes:
                    if len(c) > 3:
                        candidates.append(f".{c}")
                        break
            if candidates:
                lines.append(f"    → {el['tag']}候选: {' | '.join(candidates[:2])}")

        return "\n".join(lines)

    def _analyze_html_content(self, html_text: str, page_id: str) -> Dict[str, Any]:
        """用 Text API 分析抓取到的页面结构"""
        prompt = (
            f"请分析以下页面结构，为每个可交互元素生成 1 到 3 个可复用定位策略。\n"
            f"页面标识：{page_id}\n"
            f"返回 JSON 对象，key 为 页面名.元素描述（英文小写下划线），"
            f"value 至少包含 description、primary_type、strategies。"
            f"strategies 中优先给出 testid、role、label、placeholder、text，再补 css/xpath。\n\n"
            f"页面结构：\n{html_text[:8000]}\n\n"
            f"直接输出 JSON，不要任何解释文字。"
        )

        result_text = self.ai.generate(
            prompt,
            system_prompt=LOCATOR_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        locators = self._normalize_locator_payload(self._parse_locator_response(result_text))

        return {
            "locators": locators,
            "page_identifier": page_id,
            "raw_ai_response": result_text,
            "parse_diagnostics": self._last_parse_diagnostics,
        }

    def _analyze_url_only(self, url: str, page_name: str) -> Dict[str, Any]:
        """无 Playwright 时（fallback）：基于 URL 推断"""
        prompt = (
            f"分析以下网页信息，页面名称：{page_name}，URL：{url}。\n"
            f"请生成该页面常见可交互元素的定位符，输出 JSON 格式。"
        )
        result_text = self.ai.generate(
            prompt,
            system_prompt=LOCATOR_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        locators = self._normalize_locator_payload(self._parse_locator_response(result_text))

        return {
            "locators": locators,
            "page_identifier": page_name or url,
            "raw_ai_response": result_text,
            "parse_diagnostics": self._last_parse_diagnostics,
        }

    def _parse_locator_response(self, text: str) -> Dict[str, Any]:
        """解析 AI 返回文本，提取 locators JSON"""
        text = text.strip()
        self._last_parse_diagnostics = {
            "status": "failed",
            "mode": "unknown",
            "message": "未识别到可解析的 locator JSON",
            "salvaged_count": 0,
        }

        try:
            parsed = json.loads(text)
            self._last_parse_diagnostics = {
                "status": "success",
                "mode": "raw_json",
                "message": "直接解析 AI 返回的 JSON 成功",
                "salvaged_count": len(parsed) if isinstance(parsed, dict) else 0,
            }
            return parsed
        except json.JSONDecodeError as exc:
            self._last_parse_diagnostics["message"] = f"原始 JSON 解析失败: {exc}"
            pass

        # 尝试提取 markdown 代码块
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}\s*)```", text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                self._last_parse_diagnostics = {
                    "status": "success",
                    "mode": "markdown_json_block",
                    "message": "从 Markdown JSON 代码块中解析成功",
                    "salvaged_count": len(parsed) if isinstance(parsed, dict) else 0,
                }
                return parsed
            except json.JSONDecodeError as exc:
                self._last_parse_diagnostics["message"] = f"Markdown JSON 代码块解析失败: {exc}"
                pass

        # 尝试提取 { ... } 块
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group())
                self._last_parse_diagnostics = {
                    "status": "success",
                    "mode": "brace_extract",
                    "message": "从文本中的 JSON 大括号片段解析成功",
                    "salvaged_count": len(parsed) if isinstance(parsed, dict) else 0,
                }
                return parsed
            except json.JSONDecodeError as exc:
                self._last_parse_diagnostics["message"] = f"大括号片段解析失败: {exc}"
                pass

        salvaged_entries = self._salvage_top_level_locator_entries(text)
        if salvaged_entries:
            self._last_parse_diagnostics = {
                "status": "partial",
                "mode": "top_level_entry_salvage",
                "message": "完整 JSON 解析失败，已提取出截断响应中的完整 locator 条目",
                "salvaged_count": len(salvaged_entries),
            }
            logger.warning(
                f"[AILocator] salvaged {len(salvaged_entries)} complete locator entrie(s) from truncated AI response"
            )
            return salvaged_entries

        salvaged = {}
        entry_pattern = re.compile(
            r'"([^"]+)"\s*:\s*\{\s*"type"\s*:\s*"([^"]+)"\s*,\s*"value"\s*:\s*"([^"]+)"\s*,\s*"ai_confidence"\s*:\s*([0-9.]+)',
            re.S,
        )
        for key, loc_type, value, confidence in entry_pattern.findall(text):
            try:
                salvaged[key] = {
                    "type": loc_type,
                    "value": value,
                    "ai_confidence": float(confidence),
                }
            except ValueError:
                continue

        if salvaged:
            self._last_parse_diagnostics = {
                "status": "partial",
                "mode": "regex_salvage",
                "message": "完整 JSON 解析失败，已从 AI 返回中抢救出部分 locator",
                "salvaged_count": len(salvaged),
            }
            logger.warning(
                f"[AILocator] salvaged {len(salvaged)} locator(s) from partial AI response"
            )
            return salvaged

        self._last_parse_diagnostics = {
            "status": "failed",
            "mode": "unparsed",
            "message": self._last_parse_diagnostics.get("message", "未识别到可解析的 locator JSON"),
            "salvaged_count": 0,
        }
        logger.warning(f"[AILocator] failed to parse: {text[:200]}")
        return {}

    def _salvage_top_level_locator_entries(self, text: str) -> Dict[str, Any]:
        """Extract complete top-level `"key": {...}` entries from a truncated JSON object."""
        salvaged: Dict[str, Any] = {}
        key_pattern = re.compile(r'"([^"]+)"\s*:\s*\{')
        search_pos = 0

        while True:
            match = key_pattern.search(text, search_pos)
            if not match:
                break

            key = match.group(1)
            object_start = match.end() - 1
            object_end = self._find_balanced_brace_end(text, object_start)
            if object_end is None:
                search_pos = match.end()
                continue

            raw_object = text[object_start:object_end + 1]
            try:
                salvaged[key] = json.loads(raw_object)
            except json.JSONDecodeError:
                search_pos = object_end + 1
                continue

            search_pos = object_end + 1

        return salvaged

    def _find_balanced_brace_end(self, text: str, start_index: int) -> Optional[int]:
        """Return the index of the matching `}` for the `{` at start_index."""
        if start_index < 0 or start_index >= len(text) or text[start_index] != "{":
            return None

        depth = 0
        in_string = False
        escaped = False

        for index in range(start_index, len(text)):
            char = text[index]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index

        return None

    def _normalize_locator_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AI output into the V1 multi-strategy locator structure."""
        normalized = {}

        for key, item in (payload or {}).items():
            if not isinstance(item, dict):
                continue

            description = item.get("description", "")
            primary_type = item.get("primary_type")
            strategies = item.get("strategies")

            if isinstance(strategies, list) and strategies:
                clean_strategies = []
                for idx, strategy in enumerate(strategies, start=1):
                    if not isinstance(strategy, dict):
                        continue
                    strategy_type = strategy.get("type")
                    strategy_value = strategy.get("value")
                    if not strategy_type or strategy_value in (None, ""):
                        continue
                    clean_strategies.append({
                        "type": strategy_type,
                        "value": strategy_value,
                        "priority": strategy.get("priority", idx),
                        "confidence": strategy.get("confidence", strategy.get("ai_confidence", 0.7)),
                        "enabled": strategy.get("enabled", True),
                    })
                if clean_strategies:
                    clean_strategies = sorted(clean_strategies, key=lambda x: x.get("priority", 999))
                    normalized[key] = {
                        "description": description,
                        "primary_type": primary_type or clean_strategies[0]["type"],
                        "strategies": clean_strategies,
                        # keep legacy fields for current UI compatibility
                        "type": clean_strategies[0]["type"],
                        "value": clean_strategies[0]["value"],
                        "ai_confidence": clean_strategies[0]["confidence"],
                    }
                    continue

            if item.get("type") and item.get("value") not in (None, ""):
                strategy = {
                    "type": item.get("type", "css"),
                    "value": item.get("value"),
                    "priority": item.get("priority", 1),
                    "confidence": item.get("confidence", item.get("ai_confidence", 0.7)),
                    "enabled": item.get("enabled", True),
                }
                normalized[key] = {
                    "description": description,
                    "primary_type": item.get("type", "css"),
                    "strategies": [strategy],
                    "type": strategy["type"],
                    "value": strategy["value"],
                    "ai_confidence": strategy["confidence"],
                }

        return normalized

    def _validate_locators_for_url(
        self,
        url: str,
        viewport: Optional[dict],
        locators: Dict[str, Any],
        intent: str = "",
    ) -> Dict[str, Any]:
        if not self.playwright or not locators:
            return {
                "total_elements": len(locators or {}),
                "validated_elements": 0,
                "validated_strategies": 0,
            }

        pw = self.playwright
        if not pw._browser:
            pw.launch()

        viewport = viewport or pw.viewport
        ctx = pw._browser.new_context(viewport=viewport)
        page = ctx.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(800)
            if intent:
                self._navigate_to_intent(page, intent)
                page.wait_for_timeout(500)
            return self._validate_locators_on_page(page, locators)
        finally:
            page.close()
            ctx.close()

    def _validate_locators_on_page(self, page, locators: Dict[str, Any]) -> Dict[str, Any]:
        total_elements = 0
        validated_elements = 0
        validated_strategies = 0

        for _, locator in (locators or {}).items():
            if not isinstance(locator, dict):
                continue

            total_elements += 1
            strategies = locator.get("strategies") or []
            validated_candidates = []

            for strategy in strategies:
                validation = self._validate_strategy(page, strategy)
                strategy.update(validation)
                if validation.get("validated"):
                    validated_candidates.append(strategy)
                    validated_strategies += 1

            if validated_candidates:
                validated_elements += 1

            ordered = sorted(
                strategies,
                key=lambda item: (
                    0 if item.get("validated") else 1,
                    0 if item.get("visible") else 1,
                    0 if item.get("match_count") == 1 else 1,
                    -(item.get("validation_score") or 0),
                    item.get("priority", 999),
                ),
            )
            if ordered:
                primary = ordered[0]
                locator["strategies"] = ordered
                locator["primary_type"] = primary.get("type") or locator.get("primary_type") or "css"
                locator["type"] = primary.get("type") or locator.get("type") or "css"
                locator["value"] = primary.get("value")
                locator["ai_confidence"] = primary.get("confidence", locator.get("ai_confidence", ""))
                locator["validated"] = bool(primary.get("validated"))
                locator["validated_strategy_count"] = len(validated_candidates)

        return {
            "total_elements": total_elements,
            "validated_elements": validated_elements,
            "validated_strategies": validated_strategies,
        }

    def _validate_strategy(self, page, strategy: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "validated": False,
            "match_count": 0,
            "visible": False,
            "validation_score": 0.0,
            "validation_error": "",
        }

        try:
            locator = self._build_locator_from_strategy(page, strategy)
            count = locator.count()
            visible = False
            if count > 0:
                try:
                    visible = locator.first.is_visible()
                except Exception:
                    visible = False

            score = self._safe_float(strategy.get("confidence"), default=0.6)
            if count == 1:
                score += 0.25
            elif count > 1:
                score += 0.05
            else:
                score -= 0.35
            if visible:
                score += 0.1

            result.update({
                "validated": count > 0,
                "match_count": count,
                "visible": visible,
                "validation_score": round(max(0.0, min(1.0, score)), 2),
            })
            strategy["confidence"] = result["validation_score"]
            return result
        except Exception as e:
            result["validation_error"] = str(e)
            return result

    def _build_locator_from_strategy(self, page, strategy: Dict[str, Any]):
        strategy_type = str(strategy.get("type") or "css").lower()
        value = strategy.get("value")

        if strategy_type == "css":
            return page.locator(str(value))
        if strategy_type == "xpath":
            expr = value if str(value).startswith("xpath=") else f"xpath={value}"
            return page.locator(expr)
        if strategy_type == "text":
            return page.get_by_text(str(value), exact=False)
        if strategy_type == "label":
            return page.get_by_label(str(value), exact=False)
        if strategy_type == "placeholder":
            return page.get_by_placeholder(str(value))
        if strategy_type == "testid":
            return page.get_by_test_id(str(value))
        if strategy_type == "aria-label":
            return page.locator(f'[aria-label="{str(value)}"]')
        if strategy_type == "href":
            href_value = str(value)
            return page.locator(f'[href="{href_value}"]')
        if strategy_type == "role":
            role_value = value if isinstance(value, dict) else {"role": str(value)}
            role = role_value.get("role", "button")
            options = {}
            if role_value.get("name"):
                options["name"] = role_value["name"]
                options["exact"] = False
            return page.get_by_role(role, **options)
        return page.locator(str(value))

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default


# ─── 新增：登录后获取目标页面 DOM ─────────────────────────────────

    def _looks_authenticated(self, page, target_url: str, login_case) -> bool:
        current_url = page.url or target_url
        if self._is_login_like_url(current_url):
            return False
        try:
            title = page.title() or ""
        except Exception:
            title = ""
        if self._is_login_like_title(title):
            return False
        return True

    def _is_login_like_url(self, url: str) -> bool:
        value = (url or "").lower()
        login_markers = (
            "/login",
            "/signin",
            "/sign-in",
            "/passport",
            "/auth/login",
        )
        return any(marker in value for marker in login_markers)

    def _is_login_like_title(self, title: str) -> bool:
        value = (title or "").strip().lower()
        if not value:
            return False
        login_markers = ("登录", "login", "sign in", "signin")
        return any(marker in value for marker in login_markers)

    def _wait_for_page_settle(self, page, timeout_ms: int = 15000) -> None:
        deadline = time.time() + max(timeout_ms, 1000) / 1000.0
        for state in ("domcontentloaded", "load", "networkidle"):
            remaining_ms = int((deadline - time.time()) * 1000)
            if remaining_ms <= 0:
                break
            try:
                page.wait_for_load_state(state, timeout=remaining_ms)
            except Exception:
                continue
        try:
            page.wait_for_timeout(800)
        except Exception:
            pass

    def _probe_authenticated_page(self, page, probe_url: str, login_case, timeout_ms: int = 20000) -> None:
        if not probe_url:
            return
        logger.info(f"[AILocator] probing authenticated page: {probe_url}")
        page.goto(probe_url, wait_until="domcontentloaded", timeout=120000)
        self._wait_for_page_settle(page, timeout_ms=timeout_ms)
        final_url = page.url or probe_url
        if not self._looks_authenticated(page, probe_url, login_case):
            raise RuntimeError(
                f"Authentication did not complete successfully. "
                f"After executing login case {getattr(login_case, 'id', '')}, "
                f"the browser landed on {final_url} instead of an authenticated page."
            )

    def _build_login_state_cache(
        self,
        state_path,
        page,
        login_case,
        project_name: str,
        base_url: str,
        probe_url: str = "",
    ) -> bool:
        logger.info("[AILocator] executing login case to refresh auth cache...")
        case_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        case_file.write(login_case.content)
        case_file.close()

        try:
            engine_kwargs = {
                "headless": True,
                "base_url": base_url or "",
                "execution_id": f"ai_loc_{login_case.id}",
            }
            _eng_parent = Path(__file__).parent.parent.parent.parent
            if str(_eng_parent) not in sys.path:
                sys.path.insert(0, str(_eng_parent))
            from engine import TestEngine

            engine = TestEngine(project_name, **engine_kwargs)
            case_data = engine.load_case(case_file.name)

            case_url = case_data.get("url") or ""
            current_url = page.url or ""
            if case_url and ("about:blank" in current_url or not current_url):
                logger.info(f"[AILocator] navigating to login URL before executing case: {case_url}")
                page.goto(case_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(500)

            result = engine.execute_case_on_page(case_data, page=page)
            logger.info(f"[AILocator] login case finished with status: {result.status}, error: {result.error_msg}")
            result_status = getattr(getattr(result, "status", None), "value", getattr(result, "status", None))
            if str(result_status).lower() == "failed":
                raise RuntimeError(
                    f"Login case {login_case.id} failed before authentication was established: "
                    f"{getattr(result, 'error_msg', '') or 'unknown error'}"
                )

            self._wait_for_page_settle(page, timeout_ms=15000)
            self._probe_authenticated_page(
                page,
                probe_url=probe_url or base_url or case_url,
                login_case=login_case,
                timeout_ms=20000,
            )

            if state_path is not None:
                page.context.storage_state(path=str(state_path))
            return True
        except Exception as e:
            logger.error(f"[AILocator] _build_login_state_cache failed: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            try:
                Path(case_file.name).unlink(missing_ok=True)
            except Exception:
                pass

    def generate_with_auth(
        self,
        target_url: str,
        page_name: str,
        login_case_id: int = None,
        project_id: int = None,
        viewport: dict = None,
        intent: str = "",
    ) -> Dict[str, Any]:
        """
        带登录态获取目标页面 locators

        流程：
          1. 执行 login_case_id 完成登录（复用项目已有的登录用例）
          2. 保持 Playwright browser context
          3. 访问 target_url
          4. 提取 DOM → AI 分析 → 输出 locator 候选

        Args:
            target_url: 目标页面 URL
            page_name: 页面名称前缀
            login_case_id: 登录用例 ID（项目内的登录用例）
            project_id: 项目 ID（用于读取项目 locators）
            viewport: 浏览器视口
            intent: 目标意图（如：点击订单详情）
        """
        import logging
        logger = logging.getLogger(__name__)

        from app.core.database import SessionLocal
        from app.models.case import Case
        from app.models.project import Project

        db = SessionLocal()
        try:
            # 1. 获取登录用例内容
            login_case = None
            if login_case_id:
                login_case = db.query(Case).filter(Case.id == login_case_id).first()

            # 2. 获取项目配置
            project = None
            if project_id:
                project = db.query(Project).filter(Project.id == project_id).first()

            project_name = project.name if project else "dataify"
            base_url = None
            if project and project.env_config:
                try:
                    ec = json.loads(project.env_config) if isinstance(project.env_config, str) else project.env_config
                    if isinstance(ec, dict) and ec.get("base_url"):
                        base_url = ec["base_url"]
                except Exception:
                    pass

            logger.info(f"[AILocator] login_case={login_case_id}, project={project_name}, base_url={base_url}")

        finally:
            db.close()

        auth_state_path = None
        if login_case and base_url:
            auth_state_path = self._get_auth_state_path(project_name, login_case.id, base_url)

        # 3. 使用 Playwright 完成登录并访问目标页面
        pw = self.playwright
        if not pw._browser:
            pw.launch()

        viewport = viewport or pw.viewport
        use_cached_state = bool(auth_state_path and self._is_auth_state_fresh(auth_state_path))
        ctx = pw._browser.new_context(
            viewport=viewport,
            storage_state=str(auth_state_path) if use_cached_state else None,
        )
        page = ctx.new_page()

        try:
            # 3a. 无缓存时先执行登录用例，再导航目标页面
            if login_case and not use_cached_state:
                logger.info("[AILocator] no cached auth state, executing login case first")
                self._build_login_state_cache(
                    auth_state_path,
                    page=page,
                    login_case=login_case,
                    project_name=project_name,
                    base_url=base_url,
                    probe_url=target_url,
                )
            elif login_case and use_cached_state:
                logger.info(f"[AILocator] using cached auth state: {auth_state_path}")

            # 3b. 导航到目标页面（登录后或带缓存态）
            logger.info(f"[AILocator] 访问目标页面: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
            self._wait_for_page_settle(page, timeout_ms=15000)

            # 3c. 缓存态失效时回退重新登录
            if login_case and use_cached_state and not self._looks_authenticated(page, target_url, login_case):
                logger.info("[AILocator] cached auth state expired, fallback to login case")
                self._build_login_state_cache(
                    auth_state_path,
                    page=page,
                    login_case=login_case,
                    project_name=project_name,
                    base_url=base_url,
                    probe_url=target_url,
                )
                page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                self._wait_for_page_settle(page, timeout_ms=15000)

            # 3d. Guard: if still on login page after all login attempts, fail fast
            if login_case:
                final_url = page.url or ""
                if not self._looks_authenticated(page, target_url, login_case):
                    raise RuntimeError(
                        f"Authentication failed: after running login case {login_case.id}, "
                        f"the browser is still on an unauthenticated page ({final_url})."
                    )

            # 3f. 如果有 intent，先处理切换
            if intent:
                self._navigate_to_intent(page, intent)
                logger.info(f"[AILocator] intent 处理完成: {page.url}")

            # 3g. 提取 DOM 元素
            elements_info = self._extract_interactive_elements(page)
            structured = self._build_page_description(elements_info, page.url, intent)

            # 3h. AI 分析
            try:
                result_data = self._analyze_html_content(structured, page_name)
            except Exception as e:
                raise RuntimeError(
                    f"AI analysis request failed after login/page fetch succeeded: {e}"
                ) from e
            result_data["validation_summary"] = self._validate_locators_on_page(
                page,
                result_data.get("locators", {}),
            )
            result_data["page_url"] = page.url
            result_data["login_used"] = bool(login_case)
            result_data["auth_cache_used"] = bool(use_cached_state)
            return result_data

        except Exception as e:
            logger.error(f"[AILocator] generate_with_auth failed: {e}")
            raise
        finally:
            page.close()
            ctx.close()
