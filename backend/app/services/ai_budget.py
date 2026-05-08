# -*- coding: utf-8 -*-
"""
AI Budget Service - AI 调用配额与流控
防止 AI 调用成本失控，提供配额计数与阻断机制
"""

import logging
import threading
from datetime import datetime, date
from typing import Dict

logger = logging.getLogger(__name__)


class AIBudgetService:
    """
    轻量级 AI 调用配额管理。

    配置项（可通过 settings 覆盖）：
      AI_HEAL_MAX_PER_CASE     单用例 Healer 触发上限（默认 5）
      AI_OBSERVE_SAMPLE_RATE   Step Observer 抽样率（默认 1.0）
      AI_CALL_TIMEOUT_MS       单次 AI 调用超时 ms（默认 15000）
      AI_DAILY_BUDGET_TOKENS   项目日级 token 配额（默认 5_000_000）
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._daily_usage: Dict[str, int] = {}   # key: "project_id:YYYY-MM-DD"
        self._case_heal_count: Dict[str, int] = {}  # key: "execution_id:locator_key"

    # ─── 配置读取 ─────────────────────────────────────────────────

    @property
    def heal_max_per_case(self) -> int:
        try:
            from app.core.config import settings
            return getattr(settings, "ai_heal_max_per_case", 5)
        except Exception:
            return 5

    @property
    def observe_sample_rate(self) -> float:
        try:
            from app.core.config import settings
            return float(getattr(settings, "ai_observe_sample_rate", 1.0))
        except Exception:
            return 1.0

    @property
    def call_timeout_ms(self) -> int:
        try:
            from app.core.config import settings
            return int(getattr(settings, "ai_call_timeout_ms", 15000))
        except Exception:
            return 15000

    @property
    def daily_budget_tokens(self) -> int:
        try:
            from app.core.config import settings
            return int(getattr(settings, "ai_daily_budget_tokens", 5_000_000))
        except Exception:
            return 5_000_000

    # ─── 公共接口 ─────────────────────────────────────────────────

    def can_heal(self, execution_id: str, locator_key: str) -> bool:
        """检查单用例 Healer 是否还有配额。"""
        with self._lock:
            k = f"{execution_id}:{locator_key}"
            count = self._case_heal_count.get(k, 0)
            return count < self.heal_max_per_case

    def record_heal(self, execution_id: str, locator_key: str):
        """记录一次 Healer 触发。"""
        with self._lock:
            k = f"{execution_id}:{locator_key}"
            self._case_heal_count[k] = self._case_heal_count.get(k, 0) + 1

    def should_observe(self, execution_id: str, step_no: int) -> bool:
        """根据抽样率决定是否对本步骤做 AI 观察。"""
        import random
        return random.random() < self.observe_sample_rate

    def can_call_ai(self, project_id: int, estimated_tokens: int = 1000) -> bool:
        """检查项目今日 token 配额是否充足。"""
        with self._lock:
            key = f"{project_id}:{date.today().isoformat()}"
            used = self._daily_usage.get(key, 0)
            return used + estimated_tokens <= self.daily_budget_tokens

    def record_tokens(self, project_id: int, tokens_used: int):
        """记录 AI 调用消耗的 token 数。"""
        with self._lock:
            key = f"{project_id}:{date.today().isoformat()}"
            self._daily_usage[key] = self._daily_usage.get(key, 0) + tokens_used

    def get_daily_usage(self, project_id: int) -> dict:
        today = date.today().isoformat()
        key = f"{project_id}:{today}"
        with self._lock:
            used = self._daily_usage.get(key, 0)
        return {
            "project_id": project_id,
            "date": today,
            "tokens_used": used,
            "tokens_budget": self.daily_budget_tokens,
            "remaining": max(0, self.daily_budget_tokens - used),
        }

    def reset_case(self, execution_id: str):
        """清除某次执行的自愈计数（每用例执行开始前调用）。"""
        with self._lock:
            keys = [k for k in self._case_heal_count if k.startswith(f"{execution_id}:")]
            for k in keys:
                del self._case_heal_count[k]


# 全局单例
ai_budget = AIBudgetService()
