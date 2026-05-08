# -*- coding: utf-8 -*-
"""
AI Step Observer - 步骤执行结果验证器

每个步骤执行后，AI 截图分析当前页面状态，判断操作是否真正生效。
防止"假通过"：Playwright 未抛异常，但页面实际没有变化。

使用方式：
    observer = AIStepObserver(enabled=True)
    ok, reason = observer.verify(page, action="click", target="login.submit")
    if not ok:
        step_result.status = StepStatus.FAILED
        step_result.error_msg = f"AI验证失败: {reason}"
"""

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_OBSERVER_SYSTEM_PROMPT = """你是 Playwright 自动化测试验证专家。判断一个浏览器操作是否真正执行成功。

判断依据：
- click  : 页面是否有可见变化（按钮状态变化、弹窗出现、页面跳转、内容更新等）
- fill   : 输入框是否已填入内容
- navigate: URL 是否已到达目标页面
- assert : 预期文字是否出现在页面
- select : 下拉框是否已选中目标

只输出 JSON，格式：
{
  "ok": true,
  "confidence": 0.9,
  "reason": "按钮点击后页面已跳转至仪表盘，操作成功"
}

注意：如果无法确定，倾向于 ok=true（不误报）。置信度低于 0.65 时请如实填写低置信度。
"""


class AIStepObserver:
    """
    AI 步骤验证器

    在 TestEngine._execute_steps() 中，每步成功后调用 verify()，
    用 AI Vision 确认页面状态符合预期，防止假通过。

    默认关闭（ai_observe=False），开启后每步增加约 1~2 秒耗时，
    建议仅在核心用例或 debug 模式下开启。
    """

    # 不需要验证的动作（无状态变化或验证意义不大）
    _SKIP_ACTIONS = frozenset({
        "wait", "scroll", "hover", "screenshot",
        "clear_cookies", "refresh", "back", "forward",
        "execute_js", "upload",
    })
    # 置信度阈值，低于此值不判定失败
    _CONFIDENCE_THRESHOLD = 0.65

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._ai = self._load_ai() if enabled else None

    # ─── 对外接口 ────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self.enabled and self._ai is not None

    def verify(
        self,
        page,
        action: str,
        target: str = "",
        value: str = "",
        url_before: str = "",
    ) -> Tuple[bool, str]:
        """
        验证步骤是否真正执行成功。

        Args:
            page       : Playwright Page（操作执行完毕后的状态）
            action     : 执行的动作（click / fill / navigate 等）
            target     : 目标元素描述（locator key 或 selector）
            value      : 操作的值（如输入文字、目标 URL）
            url_before : 操作前的 URL，用于判断是否发生跳转

        Returns:
            (ok: bool, reason: str)
            ok=True  → 步骤有效
            ok=False → 步骤可能是假通过，附带原因
        """
        if not self.available:
            return True, ""

        if action.lower() in self._SKIP_ACTIONS:
            return True, ""

        screenshot_path = None
        try:
            screenshot_path = self._take_screenshot(page)
            if not screenshot_path:
                return True, "截图失败，跳过验证"

            result = self._ask_ai(
                action=action,
                target=target,
                value=value,
                screenshot_path=screenshot_path,
                url_before=url_before,
                url_after=page.url,
            )

            ok = result.get("ok", True)
            reason = result.get("reason", "")
            confidence = float(result.get("confidence", 1.0))

            # 置信度不足时不判定失败（避免误报）
            if confidence < self._CONFIDENCE_THRESHOLD:
                logger.debug(
                    f"[AIStepObserver] Low confidence ({confidence:.2f}) for "
                    f"{action}/{target}, skipping verdict"
                )
                return True, f"AI验证置信度低({confidence:.2f})，跳过"

            if not ok:
                logger.warning(
                    f"[AIStepObserver] Step may have failed: "
                    f"action={action}, target={target}, reason={reason}"
                )

            return ok, reason

        except Exception as e:
            logger.warning(f"[AIStepObserver] verify() error: {e}")
            return True, ""
        finally:
            try:
                if screenshot_path:
                    Path(screenshot_path).unlink(missing_ok=True)
            except Exception:
                pass

    # ─── 内部工具 ────────────────────────────────────────────────────

    def _load_ai(self):
        try:
            from app.services.ai_base import AiBaseService  # noqa: PLC0415
            return AiBaseService()
        except Exception as e:
            logger.warning(f"[AIStepObserver] AI service not available: {e}")
            return None

    def _take_screenshot(self, page) -> Optional[str]:
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            page.screenshot(path=tmp.name)
            return tmp.name
        except Exception as e:
            logger.warning(f"[AIStepObserver] Screenshot failed: {e}")
            return None

    def _ask_ai(
        self,
        action: str,
        target: str,
        value: str,
        screenshot_path: str,
        url_before: str,
        url_after: str,
    ) -> dict:
        action_desc = self._describe_action(action, target, value)

        url_info = ""
        if url_before and url_after:
            if url_before != url_after:
                url_info = f"\n页面已从 {url_before} 跳转至 {url_after}"
            else:
                url_info = f"\n页面 URL 未变化：{url_after}"

        prompt = (
            f"刚刚执行了一个浏览器操作：{action_desc}{url_info}\n\n"
            f"请根据当前页面截图，判断这个操作是否真正执行成功。\n"
            f"只输出 JSON，不要任何额外说明。"
        )

        try:
            text = self._ai.vision(image=screenshot_path, prompt=prompt)
            return self._parse_response(text)
        except Exception as e:
            logger.warning(f"[AIStepObserver] AI call failed: {e}")
            return {"ok": True, "confidence": 0.0, "reason": f"AI调用失败: {e}"}

    @staticmethod
    def _describe_action(action: str, target: str, value: str) -> str:
        """将操作翻译成人类可读的描述"""
        action_lower = action.lower()
        # 提取元素简短名称
        target_short = target.split(".")[-1].replace("_", " ") if "." in target else target

        if action_lower in ("click", "dblclick"):
            return f"点击了「{target_short}」"
        if action_lower in ("type", "fill", "input"):
            return f"在「{target_short}」中输入了「{value}」"
        if action_lower == "navigate":
            return f"导航到了「{value or target}」"
        if action_lower.startswith("assert"):
            return f"断言「{target_short}」包含「{value}」"
        if action_lower == "select":
            return f"在「{target_short}」下拉框中选择了「{value}」"
        if action_lower in ("check", "uncheck"):
            return f"{'勾选' if action_lower == 'check' else '取消勾选'}了「{target_short}」"
        return f"执行了 {action} 操作，目标：{target_short}"

    @staticmethod
    def _parse_response(text: str) -> dict:
        """解析 AI 返回的 JSON"""
        text = (text or "").strip()
        text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        ok_m = re.search(r'"ok"\s*:\s*(true|false)', text, re.IGNORECASE)
        reason_m = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
        conf_m = re.search(r'"confidence"\s*:\s*([\d.]+)', text)

        return {
            "ok":         ok_m.group(1).lower() == "true" if ok_m else True,
            "reason":     reason_m.group(1) if reason_m else "",
            "confidence": float(conf_m.group(1)) if conf_m else 0.5,
        }
