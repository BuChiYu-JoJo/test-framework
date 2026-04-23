# -*- coding: utf-8 -*-
"""
Playwright Client - 浏览器生命周期管理器
统一管理 Browser / Context / Page 的创建与销毁
支持多并发：每个用例独立 Context，互相隔离
"""

import time
import uuid
from typing import Optional, Dict, Any
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright


class PlaywrightClient:
    """
    Playwright 浏览器客户端
    
    职责：
    - Browser 启动 / 关闭
    - Context（上下文）创建 / 销毁
    - Page 管理
    - 截图 / 截图管理
    
    设计原则：
    - 每个用例分配独立 Context，用例间 cookie/storage 完全隔离
    - 外部获取 Page 对象后交给 KeywordExecutor 执行操作
    - 关闭时按 Page → Context → Browser 顺序清理
    """

    def __init__(
        self,
        base_url: str = "http://test-qzxbjwry.dataify-dev.com",
        headless: bool = True,
        viewport: dict = None,
        screenshot_dir: str = "screenshots",
        timeout: int = 30000,
    ):
        """
        初始化 Playwright 客户端
        
        Args:
            base_url: 默认 base URL（用于相对路径 navigate）
            headless: 是否无头模式
            viewport: 浏览器视口，默认 1920×1080
            screenshot_dir: 截图保存目录
            timeout: 默认超时时间（ms）
        """
        self.base_url = base_url
        self.headless = headless
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.screenshot_dir = screenshot_dir
        self.timeout = timeout

        # Playwright 核心对象（整个生命周期只需一个）
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        
        # 当前激活的 Context 和 Page
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Context 池（支持多并发用例）
        # { context_id: BrowserContext }
        self._contexts: Dict[str, BrowserContext] = {}

        # 确保截图目录存在
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────
    # 生命周期管理
    # ─────────────────────────────────────────────────────────────────

    def launch(self) -> "PlaywrightClient":
        """
        启动 Playwright 和 Browser
        
        Returns:
            self（支持链式调用）
        """
        if self._browser is not None:
            return self  # 已经启动

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        return self

    def close(self) -> None:
        """
        关闭所有资源：Browser → Playwright
        
        清理顺序：Page → Context → Browser → Playwright
        """
        # 关闭所有 Context
        for ctx in list(self._contexts.values()):
            try:
                ctx.close()
            except Exception:
                pass
        self._contexts.clear()

        # 关闭当前 Context
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None

        # 关闭 Browser
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        # 停止 Playwright
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def new_context(self, context_id: str = None, storage_state: str = None) -> BrowserContext:
        """
        创建新的 Browser Context
        
        每个用例应该使用独立 Context，做到完全的 cookie/storage 隔离。
        
        Args:
            context_id: 上下文 ID（默认自动生成 UUID）
            storage_state: 可选，加载已保存的登录状态（cookie 持久化）
            
        Returns:
            BrowserContext
        """
        if self._browser is None:
            self.launch()

        ctx_id = context_id or uuid.uuid4().hex[:8]
        
        ctx = self._browser.new_context(
            viewport=self.viewport,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            storage_state=storage_state,
        )
        
        self._contexts[ctx_id] = ctx
        self._context = ctx
        
        return ctx

    def new_page(self, context_id: str = None) -> Page:
        """
        在当前 Context 中创建新 Page
        
        Args:
            context_id: 指定 Context ID，默认使用最新创建的或主 Context
            
        Returns:
            Page
        """
        if self._context is None:
            self.new_context()

        page = self._context.new_page()
        self._page = page
        return page

    def switch_context(self, context_id: str) -> BrowserContext:
        """
        切换到指定的 Context（用于多并发场景）
        
        Args:
            context_id: Context ID
        """
        if context_id not in self._contexts:
            raise ValueError(f"Context not found: {context_id}")
        self._context = self._contexts[context_id]
        # 切换后默认取第一个 Page
        if self._context.pages:
            self._page = self._context.pages[0]
        return self._context

    def close_context(self, context_id: str = None) -> None:
        """
        关闭指定的 Context
        
        Args:
            context_id: Context ID，默认关闭当前 Context
        """
        ctx = self._contexts.pop(context_id or "default", None)
        if ctx is None:
            return
        try:
            ctx.close()
        except Exception:
            pass
        # 如果关闭的是当前 Context，清除引用
        if self._context is ctx:
            self._context = None
            self._page = None

    def __enter__(self) -> "PlaywrightClient":
        return self.launch()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ─────────────────────────────────────────────────────────────────
    # 页面操作（转发到 Page）
    # ─────────────────────────────────────────────────────────────────

    def navigate(self, url: str, page: Page = None, wait: str = "networkidle") -> None:
        """
        导航到指定 URL
        
        Args:
            url: 目标 URL（相对路径自动拼接 base_url）
            page: 目标 Page，默认使用当前 Page
            wait: 等待策略：networkidle / domcontentloaded / load
        """
        p = page or self._page
        if not p:
            raise ValueError("No page available, call new_page() first")

        if not url.startswith(("http://", "https://")):
            if url.startswith("/"):
                url = self.base_url.rstrip("/") + url
            else:
                from urllib.parse import urljoin
                url = urljoin(self.base_url, url)

        # SPA 必须 networkidle，否则 JS 还没执行完 DOM 是空的
        p.goto(url, wait_until=wait, timeout=self.timeout)
        
        # networkidle 后 DOM 可能还在渲染，额外等一下稳定
        if wait == "networkidle":
            p.wait_for_load_state("domcontentloaded")

    def screenshot(self, name: str = "screenshot", page: Page = None) -> str:
        """
        页面截图
        
        Args:
            name: 截图文件名（不含扩展名）
            page: 目标 Page，默认当前 Page
            
        Returns:
            保存的完整路径
        """
        p = page or self._page
        if not p:
            return ""

        filename = f"{name}_{int(time.time() * 1000)}.png"
        filepath = str(Path(self.screenshot_dir) / filename)
        p.screenshot(path=filepath, full_page=False)
        return filepath

    def close_page(self, page: Page = None) -> None:
        """关闭指定 Page"""
        p = page or self._page
        if p:
            try:
                p.close()
            except Exception:
                pass
            if p is self._page:
                self._page = None

    # ─────────────────────────────────────────────────────────────────
    # Cookie / Storage 管理
    # ─────────────────────────────────────────────────────────────────

    def save_storage_state(self, filepath: str = "storage_state.json", 
                          context_id: str = None) -> str:
        """
        保存当前 Context 的登录状态（cookie + localStorage）
        
        Args:
            filepath: 保存路径
            context_id: Context ID，默认当前 Context
            
        Returns:
            保存的完整路径
        """
        ctx = self._contexts.get(context_id) or self._context
        if not ctx:
            raise ValueError("No active context")
        
        ctx.storage_state(path=filepath)
        return filepath

    def load_storage_state(self, filepath: str) -> dict:
        """
        读取登录状态文件（不应用，仅读取）
        
        Args:
            filepath: 状态文件路径
            
        Returns:
            storage_state dict
        """
        from playwright.sync_api import FileType
        if not Path(filepath).exists():
            return {}
        with open(filepath, "r") as f:
            return json.load(f) if filepath.endswith(".json") else {}

    # ─────────────────────────────────────────────────────────────────
    # 便捷属性
    # ─────────────────────────────────────────────────────────────────

    @property
    def page(self) -> Optional[Page]:
        """获取当前激活的 Page"""
        return self._page

    @property
    def context(self) -> Optional[BrowserContext]:
        """获取当前激活的 Context"""
        return self._context

    @property
    def browser(self) -> Optional[Browser]:
        """获取 Browser 实例"""
        return self._browser

    @property
    def is_launched(self) -> bool:
        """是否已启动"""
        return self._browser is not None

    def is_page_alive(self, page: Page = None) -> bool:
        """检查 Page 是否仍然可用"""
        p = page or self._page
        if p is None:
            return False
        try:
            p.evaluate("1")  # 主动触发连接检查
            return True
        except Exception:
            return False


import json  # local import to avoid top-level dependency issue
