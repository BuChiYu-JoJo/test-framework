# -*- coding: utf-8 -*-
"""
AI Locator Healer - 实时元素定位自愈器

当 KeywordExecutor 中所有预定义策略都失败时，
AI 分析当前页面截图自动找到目标元素，返回新的 selector。
成功后可将结果写回 locators.json，实现持久化自愈。
"""

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_HEAL_PROMPT_SYSTEM = """你是 Playwright 自动化测试专家，擅长从页面截图和 DOM 结构中识别 UI 元素并生成精准的 selector。

只输出 JSON，不要 markdown 包裹，格式：
{
  "selector": "button:has-text('提交')",
  "selector_type": "text",
  "confidence": 0.9,
  "reason": "页面左下角有文字为'提交'的蓝色按钮"
}

selector 选择优先级（从高到低）：
1. :has-text() 或 text=       ← 最稳定，改版后依然可用
2. [aria-label='...']         ← 语义属性，稳定
3. [data-testid='...']        ← 测试专属，稳定
4. role 选择器                ← 语义化
5. CSS class / id             ← 最后手段，容易随版本变化

找不到目标元素时返回：{"selector": "", "reason": "元素不在当前视口"}
"""


class AILocatorHealer:
    """
    AI 元素定位自愈器

    工作流程：
      1. KeywordExecutor 的全部 selector 策略失败
      2. 调用 heal()：截图 + 提取可见 DOM 摘要
      3. AI Vision 分析，返回最佳 selector
      4. 在当前页面校验命中数（hit_count == 1 才视为 verified）
      5. KeywordExecutor 用新 selector 重试
      6. 成功后自动写回 locators.json（可关闭）
      7. 调用 repair_recorder 回调写入修复审计记录
    """

    def __init__(
        self,
        locators_json_path: str = None,
        auto_save: bool = True,
        repair_recorder=None,
    ):
        """
        Args:
            locators_json_path: locators.json 完整路径，用于将自愈结果持久化
            auto_save: 是否将修复的 selector 写回配置文件（默认 True）
            repair_recorder: 可选回调，签名 (target_key, old_strategies, new_strategy, verification, execution_id) -> None
        """
        self.locators_json_path = locators_json_path
        self.auto_save = auto_save
        self._ai = self._load_ai()
        self._repair_recorder = repair_recorder
        # 本次执行的自愈缓存，避免对同一个 key 重复调 AI
        self._healed_cache: Dict[str, str] = {}

    # ─── 对外接口 ────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """AI 服务是否可用"""
        return self._ai is not None

    def heal(
        self,
        page,
        target_key: str,
        description: str = "",
        execution_id: str = "",
    ) -> Optional[str]:
        """
        尝试用 AI 修复失败的 locator。

        Args:
            page         : Playwright Page 实例（用于截图和 DOM 提取）
            target_key   : locator key，如 "login.submit_btn"
            description  : 元素语义描述，如 "登录提交按钮"（优先使用）
            execution_id : 关联的执行 ID，用于修复审计记录

        Returns:
            新的 Playwright selector 字符串；找不到或命中数≠1 则返回 None
        """
        if not self.available:
            return None

        # 命中缓存直接返回
        if target_key in self._healed_cache:
            logger.info(f"[AILocatorHealer] Cache hit: {target_key} → {self._healed_cache[target_key]}")
            return self._healed_cache[target_key]

        screenshot_path = None
        try:
            screenshot_path = self._take_screenshot(page)
            if not screenshot_path:
                return None

            dom = self._get_dom(page)
            old_strategies = self._snapshot_strategies(target_key)
            result = self._ask_ai(target_key, description, screenshot_path, dom)
            new_selector = result.get("selector", "")

            if not new_selector:
                logger.warning(f"[AILocatorHealer] AI could not find element: {target_key}")
                self._call_recorder(
                    target_key, old_strategies, result, {"verdict": "miss", "hit_count": 0}, execution_id
                )
                return None

            # 在当前页面校验命中数
            verification = self._verify_in_page(page, new_selector, result.get("selector_type", "css"))
            verdict = verification.get("verdict", "error")

            logger.info(
                f"[AILocatorHealer] Healed {target_key} → {new_selector}"
                f" (confidence={result.get('confidence', '?')},"
                f" verdict={verdict},"
                f" reason={result.get('reason', '')})"
            )

            # 调用修复审计回调
            self._call_recorder(target_key, old_strategies, result, verification, execution_id)

            if verdict != "verified":
                logger.warning(
                    f"[AILocatorHealer] selector not verified (verdict={verdict}, "
                    f"hit_count={verification.get('hit_count')}), skipping persist"
                )
                return None

            # 写入缓存
            self._healed_cache[target_key] = new_selector

            # 持久化到 locators.json
            if self.auto_save and self.locators_json_path:
                self._persist(target_key, new_selector, result)

            return new_selector

        except Exception as e:
            logger.error(f"[AILocatorHealer] heal() error for {target_key}: {e}")
            return None
        finally:
            try:
                if screenshot_path:
                    Path(screenshot_path).unlink(missing_ok=True)
            except Exception:
                pass

    def reset_cache(self) -> None:
        """清空本次执行的自愈缓存（每个用例执行前调用）"""
        self._healed_cache.clear()

    # ─── 验证与回调工具 ──────────────────────────────────────────

    def _verify_in_page(self, page, selector: str, selector_type: str = "css") -> dict:
        """在当前页面校验 selector 命中数，返回 {verdict, hit_count, error}。"""
        try:
            if selector_type == "xpath":
                loc = page.locator(f"xpath={selector}")
            elif selector_type == "text":
                loc = page.get_by_text(selector, exact=False)
            else:
                loc = page.locator(selector)

            count = loc.count()
            if count == 1:
                verdict = "verified"
            elif count == 0:
                verdict = "miss"
            else:
                verdict = "ambiguous"

            return {"verdict": verdict, "hit_count": count, "error": ""}
        except Exception as exc:
            return {"verdict": "error", "hit_count": 0, "error": str(exc)[:200]}

    def _snapshot_strategies(self, target_key: str) -> list:
        """从 locators.json 读取当前 strategies 快照（修复前存档）。"""
        if not self.locators_json_path:
            return []
        path = Path(self.locators_json_path)
        if not path.exists() or "." not in target_key:
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            page_name, element_key = target_key.split(".", 1)
            elem = data.get("pages", {}).get(page_name, {}).get("elements", {}).get(element_key, {})
            return elem.get("strategies", [])
        except Exception:
            return []

    def _call_recorder(
        self,
        target_key: str,
        old_strategies: list,
        new_strategy: dict,
        verification: dict,
        execution_id: str,
    ):
        """调用外部 repair_recorder 回调（失败仅 warn，不阻塞主流程）。"""
        if not self._repair_recorder:
            return
        try:
            self._repair_recorder(
                target_key=target_key,
                old_strategies=old_strategies,
                new_strategy=new_strategy,
                verification=verification,
                execution_id=execution_id,
            )
        except Exception as exc:
            logger.warning(f"[AILocatorHealer] repair_recorder failed: {exc}")

    # ─── 内部工具 ────────────────────────────────────────────────────

    def _load_ai(self):
        """懒加载 AI 服务（engine 包不强依赖 backend，用 try/except 兜底）"""
        try:
            from app.services.ai_base import AiBaseService  # noqa: PLC0415
            return AiBaseService()
        except Exception as e:
            logger.warning(f"[AILocatorHealer] AI service not available: {e}")
            return None

    def _take_screenshot(self, page) -> Optional[str]:
        """截图保存到临时文件，返回路径"""
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            page.screenshot(path=tmp.name)
            return tmp.name
        except Exception as e:
            logger.warning(f"[AILocatorHealer] Screenshot failed: {e}")
            return None

    def _get_dom(self, page) -> str:
        """提取页面可见交互元素的 DOM 摘要（最多 80 个元素）"""
        try:
            js = """
            () => {
              const out = [];
              const tags = 'button,a,input,select,textarea,[role="button"],[role="tab"],[role="menuitem"],[role="option"]';
              document.querySelectorAll(tags).forEach(el => {
                const rect = el.getBoundingClientRect();
                if (!rect.width || !rect.height) return;
                const text = (el.innerText || el.value || el.getAttribute('placeholder') || '').trim().slice(0, 50);
                const attrs = [];
                if (el.id) attrs.push(`id="${el.id}"`);
                const cls = (el.className || '');
                const clsStr = typeof cls === 'string' ? cls.split(' ').slice(0,3).join(' ') : '';
                if (clsStr) attrs.push(`class="${clsStr}"`);
                const role = el.getAttribute('role');
                if (role) attrs.push(`role="${role}"`);
                const aria = el.getAttribute('aria-label');
                if (aria) attrs.push(`aria-label="${aria}"`);
                const testid = el.getAttribute('data-testid');
                if (testid) attrs.push(`data-testid="${testid}"`);
                out.push(`<${el.tagName.toLowerCase()} ${attrs.join(' ')}>${text}</${el.tagName.toLowerCase()}>`);
              });
              return out.slice(0, 80).join('\\n');
            }
            """
            return page.evaluate(js) or ""
        except Exception:
            return ""

    def _ask_ai(
        self,
        target_key: str,
        description: str,
        screenshot_path: str,
        dom: str,
    ) -> Dict[str, Any]:
        """调用 AI Vision 分析页面，返回修复结果"""
        element_hint = description or target_key.split(".")[-1].replace("_", " ")
        dom_text = dom[:2000] if dom else "（DOM 提取失败）"

        prompt = (
            f"页面元素定位失败，请帮我找到正确的 Playwright selector。\n\n"
            f"目标元素：「{element_hint}」（locator key: {target_key}）\n\n"
            f"当前页面可见元素摘要：\n{dom_text}\n\n"
            f"请根据截图和 DOM 摘要，找出「{element_hint}」对应元素的最佳 selector。\n"
            f"只输出 JSON，不要任何额外说明。"
        )

        try:
            text = self._ai.vision(image=screenshot_path, prompt=prompt)
            return self._parse_response(text)
        except Exception as e:
            logger.error(f"[AILocatorHealer] AI Vision call failed: {e}")
            return {"selector": "", "reason": str(e)}

    @staticmethod
    def _parse_response(text: str) -> Dict[str, Any]:
        """解析 AI 返回的 JSON"""
        text = (text or "").strip()
        # 去掉 markdown 代码块包裹
        text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 正则兜底提取
        def _extract(pattern):
            m = re.search(pattern, text)
            return m.group(1) if m else ""

        return {
            "selector":      _extract(r'"selector"\s*:\s*"([^"]*)"'),
            "selector_type": _extract(r'"selector_type"\s*:\s*"([^"]*)"') or "css",
            "reason":        _extract(r'"reason"\s*:\s*"([^"]*)"'),
            "confidence":    float(m.group(1)) if (m := re.search(r'"confidence"\s*:\s*([\d.]+)', text)) else 0.0,
        }

    def _persist(
        self,
        target_key: str,
        new_selector: str,
        result: Dict[str, Any],
    ) -> None:
        """将自愈结果写回 locators.json，作为 priority=0 的最高优先级策略"""
        path = Path(self.locators_json_path)
        if not path.exists():
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if "." not in target_key:
                return

            page_name, element_key = target_key.split(".", 1)
            pages = data.get("pages", {})
            if page_name not in pages or element_key not in pages[page_name].get("elements", {}):
                return

            elem = pages[page_name]["elements"][element_key]
            selector_type = result.get("selector_type", "css")

            healed_strategy = {
                "type":       selector_type,
                "value":      new_selector,
                "priority":   0,          # 最高优先级
                "enabled":    True,
                "confidence": result.get("confidence", 0.9),
                "source":     "ai_healed",
                "reason":     result.get("reason", ""),
            }

            strategies = elem.get("strategies", [])
            # 替换旧的自愈条目（避免堆积）
            strategies = [s for s in strategies if s.get("source") != "ai_healed"]
            strategies.insert(0, healed_strategy)
            elem["strategies"] = strategies

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"[AILocatorHealer] Persisted healed selector → {path}: {target_key}")

        except Exception as e:
            logger.warning(f"[AILocatorHealer] Failed to persist healed selector: {e}")
