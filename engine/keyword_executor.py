# -*- coding: utf-8 -*-
"""
Keyword Executor - 关键字执行器
执行所有支持的关键字操作

设计原则：
- 只负责"对 Page 执行操作"，不管理浏览器生命周期
- 所有方法签名统一：def keyword(self, selector, value, page)
- Page 由调用方（TestEngine）通过 PlaywrightClient 获取并传入
"""

import time
from typing import Any, Dict
from playwright.sync_api import Page


class KeywordExecutor:
    """关键字执行器"""

    KEYWORDS = {
        # 页面导航
        'navigate': 'navigate', 'go': 'navigate', 'open': 'navigate',
        # 点击操作
        'click': 'click', 'dblclick': 'dblclick', 'rightclick': 'rightclick',
        'right_click': 'rightclick',
        # 输入操作
        'type': 'type', 'fill': 'type', 'input': 'type', 'clear': 'clear',
        # 选择操作
        'select': 'select', 'check': 'check', 'uncheck': 'uncheck',
        # 等待操作
        'wait': 'wait', 'wait_for': 'wait_for', 'wait_for_url': 'wait_for_url',
        'wait_for_element': 'wait_for_element',
        # 断言操作
        'assert_text': 'assert_text', 'assert_visible': 'assert_visible',
        'assert_hidden': 'assert_hidden', 'assert_count': 'assert_count',
        'assert_url': 'assert_url', 'assert_element_exists': 'assert_exists',
        # API操作
        'api_request': 'api_request', 'api_get': 'api_request', 'api_post': 'api_request',
        # 其他操作
        'screenshot': 'screenshot', 'refresh': 'refresh', 'back': 'back', 'forward': 'forward',
        'scroll': 'scroll', 'hover': 'hover', 'execute_js': 'execute_js',
        'upload': 'upload', 'clear_cookies': 'clear_cookies', 'clear_browser_cookies': 'clear_cookies',
    }

    def __init__(self, locator_resolver=None, base_url: str = None):
        self.locator_resolver = locator_resolver
        self.base_url = base_url or "http://test-qzxbjwry.dataify-dev.com"
        self.last_strategy_match = None

    def execute(self, action: str, target: str = "", value: Any = None,
                page: Page = None) -> Any:
        if page is None:
            raise ValueError("KeywordExecutor.execute() requires a page argument")
        self.last_strategy_match = None

        action_lower = action.lower().strip()

        if action_lower not in self.KEYWORDS:
            matched = next(
                (kw for kw in self.KEYWORDS if kw in action_lower or action_lower in kw), None)
            if matched:
                action_lower = self.KEYWORDS[matched]
            else:
                print(f"⚠️  Unknown action: {action}, skipping...")
                return None

        method_name = self.KEYWORDS[action_lower]
        if not hasattr(self, method_name):
            print(f"⚠️  No handler for action: {action}, skipping...")
            return None

        method = getattr(self, method_name)
        resolved_target = self._resolve(target) if target else ""

        value_based = {"wait", "wait_for_url", "navigate"}
        selector_based = {"refresh", "back", "forward", "clear_cookies"}

        if action_lower in value_based and value:
            return method(value, page)
        elif action_lower == "navigate":
            # navigate: URL is in target, resolved to selector (may be a URL or locator key)
            direct_target = target if isinstance(resolved_target, dict) else resolved_target
            return method(direct_target or target, page)
        elif action_lower == "screenshot":
            return method(value.get("path", "screenshot") if isinstance(value, dict) else (value or "screenshot"), page)
        elif action_lower in selector_based:
            return method(page)
        elif resolved_target:
            return method(resolved_target, value, page)
        else:
            return method(page)

    def _resolve(self, target: str):
        if not target:
            return ""
        if self.locator_resolver:
            strategies = self.locator_resolver.resolve_strategies(target)
            if strategies:
                return {"key": target, "strategies": strategies}
        return target

    def _build_locator_from_strategy(self, page: Page, strategy: Dict):
        strategy_type = (strategy.get("type") or "css").lower()
        value = strategy.get("value")

        if strategy_type == "css":
            return page.locator(value).first
        if strategy_type == "xpath":
            expr = value if str(value).startswith("xpath=") else f"xpath={value}"
            return page.locator(expr).first
        if strategy_type == "text":
            return page.get_by_text(str(value), exact=False).first
        if strategy_type == "label":
            return page.get_by_label(str(value), exact=False).first
        if strategy_type == "placeholder":
            return page.get_by_placeholder(str(value)).first
        if strategy_type == "testid":
            return page.get_by_test_id(str(value)).first
        if strategy_type == "role":
            role_value = value if isinstance(value, dict) else {"role": str(value)}
            role = role_value.get("role", "button")
            options = {}
            if role_value.get("name"):
                options["name"] = role_value["name"]
                options["exact"] = False
            return page.get_by_role(role, **options).first

        raise ValueError(f"Unsupported locator strategy type: {strategy_type}")

    def _build_locator_from_direct_target(self, page: Page, target: str):
        if not isinstance(target, str):
            raise ValueError(f"Unsupported target: {target}")
        if target.startswith("xpath=") or target.startswith("//") or target.startswith("(//"):
            expr = target if target.startswith("xpath=") else f"xpath={target}"
            return page.locator(expr).first
        return page.locator(target).first

    def _with_locator(self, target, page: Page, callback):
        last_error = None

        if isinstance(target, dict) and target.get("strategies"):
            for strategy in target["strategies"]:
                try:
                    locator = self._build_locator_from_strategy(page, strategy)
                    self.last_strategy_match = {
                        "key": target.get("key", ""),
                        "type": strategy.get("type", "css"),
                        "value": strategy.get("value"),
                        "priority": strategy.get("priority", 1),
                    }
                    return callback(locator)
                except Exception as e:
                    last_error = e
            if last_error:
                raise last_error
            raise ValueError(f"No enabled strategies found for {target.get('key')}")

        locator = self._build_locator_from_direct_target(page, target)
        self.last_strategy_match = {
            "key": target if isinstance(target, str) else "",
            "type": "direct",
            "value": target,
            "priority": 1,
        }
        return callback(locator)

    # ─── 页面导航 ────────────────────────────────────────────────────

    def navigate(self, url: str, page: Page) -> None:
        """导航到 URL
        
        SPA 必须：
        1. 先等待 networkidle（JS 下载完成）
        2. 再等待关键 DOM 元素出现（确保 JS 执行完成）
        3. 对于登录页，再等一下 tab 按钮出现，确保表单渲染完成
        """
        if not url.startswith(("http://", "https://")):
            if url.startswith("/"):
                url = self.base_url.rstrip("/") + url
            else:
                from urllib.parse import urljoin
                url = urljoin(self.base_url, url)

        page.goto(url, wait_until="networkidle", timeout=30000)

        # SPA: networkidle 后 DOM 可能还在渲染，额外等待关键元素
        try:
            page.wait_for_selector("input", timeout=8000, state="visible")
        except Exception:
            pass

        # 再等 800ms 让 Vue 完成最终渲染（特别是 tab 切换按钮）
        page.wait_for_timeout(800)

    # ─── 点击操作 ────────────────────────────────────────────────────

    def click(self, target, _, page: Page) -> None:
        """点击元素，支持多策略 fallback。"""
        return self._with_locator(target, page, lambda locator: locator.click(timeout=15000))

    def dblclick(self, target, _, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.dblclick(timeout=10000))

    def rightclick(self, target, _, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.click(button="right", timeout=10000))

    # ─── 输入操作 ────────────────────────────────────────────────────

    def type(self, target, text: str, page: Page) -> None:
        def _run(locator):
            locator.click(timeout=10000)
            page.wait_for_timeout(100)
            page.keyboard.type(str(text))
        return self._with_locator(target, page, _run)

    def clear(self, target, _, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.fill(""))

    # ─── 选择操作 ────────────────────────────────────────────────────

    def select(self, target, option: str, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.select_option(option))

    def check(self, target, _, page: Page) -> None:
        def _run(locator):
            try:
                if not locator.is_checked():
                    locator.check()
            except Exception:
                locator.click(timeout=10000)
        return self._with_locator(target, page, _run)

    def uncheck(self, target, _, page: Page) -> None:
        def _run(locator):
            try:
                if locator.is_checked():
                    locator.uncheck()
            except Exception:
                locator.click(timeout=10000)
        return self._with_locator(target, page, _run)

    # ─── 等待操作 ────────────────────────────────────────────────────

    def wait(self, seconds: float, page: Page) -> None:
        time.sleep(float(seconds))

    def wait_for(self, target, _, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.wait_for(state="visible", timeout=15000))

    def wait_for_url(self, pattern: str, page: Page) -> None:
        page.wait_for_url(pattern, timeout=30000, wait_until="commit")

    def wait_for_element(self, target, _, page: Page, timeout: int = 15000) -> None:
        return self._with_locator(target, page, lambda locator: locator.wait_for(state="visible", timeout=timeout))

    # ─── 断言操作 ────────────────────────────────────────────────────

    def assert_text(self, target, contains: str, page: Page) -> bool:
        def _run(locator):
            text = locator.text_content() or ""
            if contains not in text:
                raise AssertionError(f"Text '{text}' does not contain '{contains}'")
            return True
        return self._with_locator(target, page, _run)

    def assert_visible(self, target, _, page: Page) -> bool:
        def _run(locator):
            if not locator.is_visible():
                raise AssertionError(f"Element '{target}' is not visible")
            return True
        return self._with_locator(target, page, _run)

    def assert_hidden(self, target, _, page: Page) -> bool:
        def _run(locator):
            if locator.is_visible():
                raise AssertionError(f"Element '{target}' is visible (expected hidden)")
            return True
        return self._with_locator(target, page, _run)

    def assert_count(self, target, op_num: tuple, page: Page) -> bool:
        if isinstance(op_num, (list, tuple)) and len(op_num) == 2:
            op, num = op_num
        else:
            op, num = "==", int(op_num)
        def _run(locator):
            count = locator.count()
            ops = {">": count > num, "<": count < num, "==": count == num,
                   ">=": count >= num, "<=": count <= num}
            if not ops.get(op, False):
                raise AssertionError(f"Count {count} {op} {num} is false")
            return True
        return self._with_locator(target, page, _run)

    def assert_url(self, contains: str, _, page: Page) -> bool:
        if contains not in page.url:
            raise AssertionError(f"URL '{page.url}' does not contain '{contains}'")
        return True

    def assert_exists(self, target, _, page: Page) -> bool:
        def _run(locator):
            if locator.count() == 0:
                raise AssertionError(f"Element '{target}' does not exist in DOM")
            return True
        return self._with_locator(target, page, _run)

    # ─── 其他操作 ────────────────────────────────────────────────────

    def screenshot(self, name: str, page: Page) -> str:
        filename = f"{name}_{int(time.time() * 1000)}.png"
        filepath = f"screenshots/{filename}"
        page.screenshot(path=filepath, full_page=False)
        return filepath

    def refresh(self, page: Page) -> None:
        page.reload(wait_until="domcontentloaded")

    def back(self, page: Page) -> None:
        page.go_back(wait_until="domcontentloaded")

    def forward(self, page: Page) -> None:
        page.go_forward(wait_until="domcontentloaded")

    def scroll(self, direction: str, pixels: int, page: Page) -> None:
        if direction == "down":
            page.evaluate(f"window.scrollBy(0, {pixels})")
        elif direction == "up":
            page.evaluate(f"window.scrollBy(0, -{pixels})")

    def hover(self, target, _, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.hover())

    def execute_js(self, script: str, _, page: Page) -> Any:
        return page.evaluate(script)

    def upload(self, target, file_path: str, page: Page) -> None:
        return self._with_locator(target, page, lambda locator: locator.set_input_files(file_path))

    def clear_cookies(self, page: Page) -> None:
        """清除 cookies 和 Web Storage（localStorage/sessionStorage）

        SPA 登录态存在 localStorage，只清 cookie 不够。
        必须在 navigate 之前调用，否则旧的 session 会导致页面直接跳过后续页面。
        """
        page.context.clear_cookies()
        page.evaluate("""() => {
            try {
                localStorage.clear();
                sessionStorage.clear();
            } catch (e) {
                // 跨域访问 localStorage 时会抛异常，忽略
            }
        }""")

    # ─── API 操作 ────────────────────────────────────────────────────

    def api_request(self, url: str, method: str = "GET", data: dict = None,
                    headers: dict = None, page: Page = None) -> dict:
        """使用 Playwright APIRequestContext 发起 HTTP 请求"""
        ctx = page.context if page else None
        if ctx is None:
            raise ValueError("api_request requires a page with valid context")
        api_ctx = ctx.request
        method = method.upper()
        if method == "GET":
            resp = api_ctx.get(url, params=data)
        elif method == "POST":
            resp = api_ctx.post(url, json=data, headers=headers)
        elif method == "PUT":
            resp = api_ctx.put(url, json=data, headers=headers)
        elif method == "DELETE":
            resp = api_ctx.delete(url)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        return {"status": resp.status, "body": resp.json() if resp.ok else resp.text()}
