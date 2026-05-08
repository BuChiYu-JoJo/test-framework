# -*- coding: utf-8 -*-
"""
AI Case Orchestrator Service

将需求变更单先转换为草稿用例，再通过探索执行产出跑通后的正式用例。
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List

import yaml

from app.services.ai_explore_service import AIExploreService, ExploreResult
from app.services.auth_state_service import AuthStateService
from app.services.prd_parser import PRDParserService


class AICaseOrchestratorService:
    def __init__(self):
        self.prd_parser = PRDParserService()
        self.explore_service = AIExploreService()
        self.auth_state_service = AuthStateService()

    def build_drafts_from_prd(
        self,
        prd_content: str,
        product_name: str = "",
        max_cases: int = 5,
    ) -> List[Dict[str, Any]]:
        features = self.prd_parser.parse(prd_content, product_name=product_name)
        drafts: List[Dict[str, Any]] = []

        for index, feature in enumerate(features[:max_cases], start=1):
            module = self._normalize_module(feature.get("module") or f"module_{index}")
            name = feature.get("name") or f"增量用例_{index}"
            priority = feature.get("priority") or "P1"
            test_points = feature.get("test_points") or []
            ui_elements = feature.get("ui_elements") or []

            draft_steps = []
            for point_index, point in enumerate(test_points, start=1):
                point_text = point.get("point") or point.get("description") or f"步骤 {point_index}"
                draft_steps.append({
                    "step_no": point_index,
                    "intent": point_text,
                    "action_hint": point.get("action_type") or "",
                    "target_hint": self._guess_target_hint(point_text, ui_elements),
                    "expected_hint": point.get("expected") or "",
                })

            if not draft_steps:
                draft_steps = [{
                    "step_no": 1,
                    "intent": feature.get("description") or name,
                    "action_hint": "",
                    "target_hint": "",
                    "expected_hint": "",
                }]

            drafts.append({
                "draft_id": f"DRAFT_{int(time.time())}_{index}",
                "name": name,
                "module": module,
                "priority": priority,
                "description": feature.get("description") or "",
                "source_type": "prd_draft",
                "draft_steps": draft_steps,
            })

        return drafts

    def stabilize_draft(
        self,
        draft_case: Dict[str, Any],
        start_url: str,
        project_id: int,
        headless: bool = True,
        auth_token: str | None = None,
        login_case_id: int | None = None,
    ) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)

        steps = self._build_exploration_steps(draft_case)
        logger.info(f"[stabilize] draft_steps count={len(draft_case.get('draft_steps', []))}, "
                     f"exploration steps count={len(steps)}, steps={steps}")

        if not steps:
            raise ValueError(
                f"草稿用例没有可执行的步骤。draft_steps={draft_case.get('draft_steps', [])}"
            )

        case_name = draft_case.get("name") or "AI 稳定化用例"
        module = draft_case.get("module") or "default"
        priority = draft_case.get("priority") or "P1"
        storage_state_path = None

        if login_case_id:
            logger.info(f"[stabilize] 开始执行登录前置用例 login_case_id={login_case_id}")
            t0 = time.time()
            origin = self._origin_from_url(start_url)
            state_path = self.auth_state_service.ensure_auth_state(
                project_id=project_id,
                login_case_id=login_case_id,
                base_url=origin,
            )
            storage_state_path = str(state_path) if state_path else None
            logger.info(f"[stabilize] 登录前置完成，耗时 {time.time()-t0:.1f}s, "
                         f"state_path={storage_state_path}")

        logger.info(f"[stabilize] 开始探索执行，共 {len(steps)} 步，start_url={start_url}")
        explore_result: ExploreResult = self.explore_service.execute(
            steps=steps,
            start_url=start_url,
            project_id=project_id,
            case_name=case_name,
            module=module,
            priority=priority,
            headless=headless,
            auth_token=auth_token,
            storage_state_path=storage_state_path,
        )

        verified_yaml = self._build_verified_yaml(
            draft_case=draft_case,
            explore_result=explore_result,
            start_url=start_url,
        )

        return {
            "draft_case": draft_case,
            "status": explore_result.status,
            "total_steps": explore_result.total_steps,
            "passed_steps": explore_result.passed_steps,
            "failed_steps": explore_result.failed_steps,
            "duration_ms": explore_result.duration_ms,
            "steps": [step.to_dict() for step in explore_result.steps],
            "verified_yaml": verified_yaml,
            "discovered_locators": explore_result.discovered_locators,
            "auth_cache_used": bool(storage_state_path),
        }

    def _build_verified_yaml(
        self,
        draft_case: Dict[str, Any],
        explore_result: ExploreResult,
        start_url: str,
    ) -> str:
        case_name = draft_case.get("name") or "AI 稳定化用例"
        module = draft_case.get("module") or "default"
        priority = draft_case.get("priority") or "P1"

        yaml_steps = [{"action": "navigate", "value": start_url}]
        for step in explore_result.steps:
            if step.status != "passed":
                continue
            item = {
                "action": step.action,
                "target": self._selector_to_target_key(step.selector, module),
            }
            if step.value not in (None, ""):
                item["value"] = step.value
            item["selector"] = step.selector
            yaml_steps.append(item)

        expected = "AI 稳定化执行通过"
        if explore_result.status != "passed":
            expected = f"AI 稳定化执行结果: {explore_result.status}"

        payload = {
            "id": f"TC_STABLE_{int(time.time())}",
            "name": case_name,
            "module": module,
            "priority": priority,
            "source": "ai_stabilized",
            "tags": ["ai-stabilized", "incremental"],
            "draft_source": {
                "draft_id": draft_case.get("draft_id", ""),
                "description": draft_case.get("description", ""),
            },
            "steps": yaml_steps,
            "expected": expected,
        }
        return yaml.dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _draft_step_to_text(self, step: Dict[str, Any]) -> str:
        parts = [step.get("intent") or ""]
        if step.get("target_hint"):
            parts.append(f"目标: {step['target_hint']}")
        if step.get("expected_hint"):
            parts.append(f"预期: {step['expected_hint']}")
        return "，".join([part for part in parts if part])

    def _build_exploration_steps(self, draft_case: Dict[str, Any]) -> List[str]:
        """
        将草稿用例的 draft_steps 转换为探索执行步骤列表。

        原实现通过关键词匹配走固定预设路径（针对"实名认证"业务写死）。
        现改为直接使用草稿步骤的 intent 文本，不再依赖任何业务关键词，
        真正做到换任何项目/业务场景都能工作。
        """
        steps: List[str] = []
        for step in draft_case.get("draft_steps", []):
            text = self._draft_step_to_text(step)
            if text:
                steps.append(text)
        return self._dedupe_steps(steps)

    def _dedupe_steps(self, steps: List[str]) -> List[str]:
        deduped: List[str] = []
        for item in steps:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    def _normalize_module(self, module: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", module.strip()).strip("_").lower()
        return cleaned or "default"

    def _guess_target_hint(self, point_text: str, ui_elements: List[Dict[str, Any]]) -> str:
        for element in ui_elements:
            name = element.get("name") or ""
            if name and name in point_text:
                return name
        return ""

    def _selector_to_target_key(self, selector: str, module: str) -> str:
        cleaned = selector or "target"
        cleaned = cleaned.replace("text=", "").replace("xpath=", "")
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
        return f"{module}.{cleaned[:40] or 'target'}"

    def _origin_from_url(self, url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
