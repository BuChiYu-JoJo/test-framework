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
            return self._analyze_html_content(html_content, page_id)
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
        return age <= max_age_seconds

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
        state_path: Path,
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
                "base_url": base_url,
                "execution_id": f"ai_loc_{login_case.id}",
            }
            _eng_parent = Path(__file__).parent.parent.parent.parent
            if str(_eng_parent) not in sys.path:
                sys.path.insert(0, str(_eng_parent))
            from engine import TestEngine

            engine = TestEngine(project_name, **engine_kwargs)
            result = engine.execute_case_on_page(
                engine.load_case(case_file.name),
                page=page,
            )
            logger.info(f"[AILocator] login case finished with status: {result.status}")
            page.context.storage_state(path=str(state_path))
            return True
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
            structured = self._build_page_description(elements_info, url, intent)
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
            f"请分析以下页面结构，为每个可交互元素生成最优 CSS Selector。\n"
            f"页面标识：{page_id}\n"
            f"返回 JSON 对象，key 为 页面名.元素描述（英文小写下划线），"
            f"value 包含 type（固定css）、value（CSS选择器）、ai_confidence（0.0-1.0）。\n\n"
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
        }

    def _parse_locator_response(self, text: str) -> Dict[str, Any]:
        """解析 AI 返回文本，提取 locators JSON"""
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 markdown 代码块
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}\s*)```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 块
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

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
            logger.warning(
                f"[AILocator] salvaged {len(salvaged)} locator(s) from partial AI response"
            )
            return salvaged

        logger.warning(f"[AILocator] failed to parse: {text[:200]}")
        return {}

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


# ─── 新增：登录后获取目标页面 DOM ─────────────────────────────────

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
            # 3a. 优先复用缓存登录态
            if login_case and base_url and use_cached_state:
                logger.info(f"[AILocator] using cached auth state: {auth_state_path}")

            # 3b. 访问目标页面
            logger.info(f"[AILocator] 访问目标页面: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(1000)

            # 3c. 如缓存失效，则回退到重新登录
            if login_case and base_url and not self._looks_authenticated(page, target_url, login_case):
                logger.info("[AILocator] auth cache missing or expired, fallback to login case")
                self._build_login_state_cache(
                    auth_state_path,
                    page=page,
                    login_case=login_case,
                    project_name=project_name,
                    base_url=base_url,
                )
                page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(1000)

            # 3d. 如果有 intent，先处理切换
            if intent:
                self._navigate_to_intent(page, intent)
                logger.info(f"[AILocator] intent 处理完成: {page.url}")

            # 3e. 提取 DOM 元素
            elements_info = self._extract_interactive_elements(page)
            structured = self._build_page_description(elements_info, page.url, intent)

            # 3f. AI 分析
            try:
                result_data = self._analyze_html_content(structured, page_name)
            except Exception as e:
                raise RuntimeError(
                    f"AI analysis request failed after login/page fetch succeeded: {e}"
                ) from e
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
