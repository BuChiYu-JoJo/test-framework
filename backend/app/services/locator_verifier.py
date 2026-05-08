# -*- coding: utf-8 -*-
"""
LocatorVerifier - Locator 命中数校验服务
用 Playwright 实时校验 selector 命中数，确保 AI 生成的策略准确
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    hit_count: int = 0
    sample_html: str = ""
    error: str = ""

    @property
    def verdict(self) -> str:
        if self.error:
            return "error"
        if self.hit_count == 1:
            return "verified"
        if self.hit_count == 0:
            return "miss"
        return "ambiguous"

    def to_dict(self) -> dict:
        return {
            "hit_count": self.hit_count,
            "verdict": self.verdict,
            "sample_html": self.sample_html[:200] if self.sample_html else "",
            "error": self.error,
        }


def verify_locator_on_page(
    page,
    selector: str,
    selector_type: str = "css",
) -> VerificationResult:
    """
    在已打开的 Playwright page 对象上直接校验 selector 命中数。
    适合 engine 内部调用（不需要额外开浏览器）。
    """
    try:
        if selector_type == "xpath":
            loc = page.locator(f"xpath={selector}")
        elif selector_type == "text":
            loc = page.get_by_text(selector, exact=False)
        elif selector_type == "role":
            loc = page.locator(f"[role='{selector}']")
        else:
            loc = page.locator(selector)

        count = loc.count()
        sample = ""
        if count >= 1:
            try:
                sample = loc.first.evaluate("el => el.outerHTML")[:300]
            except Exception:
                pass

        return VerificationResult(hit_count=count, sample_html=sample)
    except Exception as exc:
        return VerificationResult(hit_count=0, error=str(exc)[:200])


def verify_locator_strategy(
    page_url: str,
    selector: str,
    selector_type: str = "css",
    storage_state: Optional[dict] = None,
    timeout_ms: int = 8000,
) -> VerificationResult:
    """
    开一个新的 Playwright 实例，在真实页面校验 selector 命中数。
    适合 API 层独立调用（无 page 对象时使用）。
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx_kwargs = {}
            if storage_state:
                ctx_kwargs["storage_state"] = storage_state
            context = browser.new_context(**ctx_kwargs)
            page = context.new_page()
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)

            result = verify_locator_on_page(page, selector, selector_type)
            context.close()
            browser.close()
            return result
    except Exception as exc:
        logger.warning(f"[LocatorVerifier] verify failed for {selector}: {exc}")
        return VerificationResult(hit_count=0, error=str(exc)[:200])
