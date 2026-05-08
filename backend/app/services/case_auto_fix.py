# -*- coding: utf-8 -*-
"""
Case Auto Fix Service - 执行失败后自动修复用例
检测失败步骤 → AI 分析截图生成真实 selector → 更新用例 → 重试
"""

import json
import logging
import time
import re
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from app.services.ai_base import AiBaseService, AIAPIError
from app.core.database import SessionLocal
from app.models.case import Case
from app.models.execution import Execution, ExecutionStep
from app.models.locator import Locator

logger = logging.getLogger(__name__)

AUTO_FIX_SYSTEM_PROMPT = """你是一个 Playwright 自动化测试专家。根据截图和步骤描述，分析页面找出目标元素的最佳 selector。

输入：
- 步骤描述：click [个人认证选项卡]
- 步骤 action：click
- 页面截图：用户当前看到的页面

输出（严格 JSON，不要任何其他内容）：
{
  "selector": "button:text('个人认证')",
  "selector_type": "text",
  "reason": "页面中个人认证Tab是按钮文字为'个人认证'的按钮",
  "alternative_selectors": ["[data-testid='personal-tab']", "button.primary"]
}

重要规则：
- 只输出 JSON，不要 markdown 包裹
- selector 必须是 Playwright 合法 CSS 或 text 选择器
- 优先使用 text 选择器（如 button:text()）或 aria 相关的选择器
- 如果元素不存在返回空 selector，让用户决定是否跳过
"""

AUTO_FIX_USER_PROMPT = """步骤：{step_description}
Action：{action}
截图文件：{screenshot_path}

请分析截图，找到对应元素的 selector，直接输出 JSON。"""


class CaseAutoFixService:
    """
    用例自动修复服务
    
    当执行失败时：
    1. 分析失败的 step（截图 + 步骤描述）
    2. AI 生成真实 selector
    3. 更新用例 content
    4. 返回修复结果供重试
    """

    def __init__(self):
        self.ai = AiBaseService()

    def fix_failed_step(
        self,
        execution_id: str,
        step_no: int,
    ) -> Dict[str, Any]:
        """
        修复单个失败步骤
        
        Args:
            execution_id: 执行记录 ID
            step_no: 失败步骤序号
        
        Returns:
            {
                "fixed": True/False,
                "old_target": "...",
                "new_selector": "...",
                "new_selector_type": "...",
                "reason": "...",
                "updated_case_id": ...,
                "error": "..."
            }
        """
        preview = self.preview_failed_step(execution_id, step_no)
        if not preview.get("proposed"):
            return {
                "fixed": False,
                "error": preview.get("error", "No fix proposal generated"),
                "old_target": preview.get("old_target", ""),
            }

        db = SessionLocal()
        try:
            case_record = db.query(Case).filter(Case.id == preview["case_id"]).first()
            if not case_record:
                return {"fixed": False, "error": "Case not found"}

            updated_case = self._update_case_content(
                case_record=case_record,
                old_target=preview["old_target"],
                new_selector=preview["new_selector"],
            )
            self._update_locator_library(
                project_id=case_record.project_id,
                old_target=preview["old_target"],
                new_selector=preview["new_selector"],
                new_selector_type=preview["new_selector_type"],
                reason=preview.get("reason", ""),
            )

            return {
                "fixed": True,
                "old_target": preview["old_target"],
                "new_selector": preview["new_selector"],
                "new_selector_type": preview["new_selector_type"],
                "reason": preview.get("reason", ""),
                "updated_case_id": case_record.id,
                "case_name": case_record.name,
            }

        except Exception as e:
            logger.error(f"[CaseAutoFix] Unexpected error: {e}")
            return {"fixed": False, "error": str(e)}
        finally:
            db.close()

    def _update_locator_library(
        self,
        project_id: int,
        old_target: str,
        new_selector: str,
        new_selector_type: str,
        reason: str = "",
    ) -> None:
        if "." not in old_target:
            return

        page_name, element_key = old_target.split(".", 1)
        db = SessionLocal()
        try:
            locator = db.query(Locator).filter(
                Locator.project_id == project_id,
                Locator.page_name == page_name,
                Locator.element_key == element_key,
            ).first()
            if not locator:
                return

            strategies = []
            if locator.strategies_json:
                try:
                    parsed = json.loads(locator.strategies_json)
                    if isinstance(parsed, list):
                        strategies = parsed
                except Exception:
                    strategies = []

            new_primary = {
                "type": new_selector_type or "css",
                "value": new_selector,
                "priority": 1,
                "confidence": 0.92,
                "enabled": True,
            }

            deduped = [new_primary]
            for strategy in strategies:
                if not isinstance(strategy, dict):
                    continue
                if strategy.get("value") == new_selector and strategy.get("type") == (new_selector_type or "css"):
                    continue
                cloned = dict(strategy)
                cloned["priority"] = max(int(cloned.get("priority", 1)), 2)
                deduped.append(cloned)

            locator.selector = new_selector
            locator.selector_type = new_selector_type or "css"
            locator.priority = 1
            locator.primary_type = new_selector_type or "css"
            locator.ai_confidence = "0.92"
            locator.strategies_json = json.dumps(deduped, ensure_ascii=False)
            locator.updated_by = f"auto-fix:{reason[:40]}" if reason else "auto-fix"
            locator.version = "2.0.0"
            db.commit()
        finally:
            db.close()

    def preview_failed_step(
        self,
        execution_id: str,
        step_no: int,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            exec_record = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()
            if not exec_record:
                return {"proposed": False, "error": f"Execution {execution_id} not found"}

            step_record = db.query(ExecutionStep).filter(
                ExecutionStep.execution_id == exec_record.id,
                ExecutionStep.step_no == step_no,
            ).first()
            if not step_record:
                return {"proposed": False, "error": f"Step {step_no} not found in execution"}

            case_record = db.query(Case).filter(
                Case.id == exec_record.case_id
            ).first()
            if not case_record:
                return {"proposed": False, "error": "Case not found"}

            screenshot = step_record.screenshot
            if not screenshot:
                return {"proposed": False, "error": "No screenshot for failed step"}

            fix_result = self._analyze_and_fix(
                step_description=step_record.action + " " + step_record.target,
                action=step_record.action,
                screenshot_path=screenshot,
            )
            if not fix_result.get("selector"):
                return {
                    "proposed": False,
                    "error": f"AI 无法生成 selector: {fix_result.get('reason', 'unknown')}",
                    "old_target": step_record.target,
                }

            return {
                "proposed": True,
                "execution_id": execution_id,
                "step_no": step_no,
                "case_id": case_record.id,
                "case_name": case_record.name,
                "old_target": step_record.target,
                "new_selector": fix_result["selector"],
                "new_selector_type": fix_result.get("selector_type", "css"),
                "reason": fix_result.get("reason", ""),
                "alternative_selectors": fix_result.get("alternative_selectors", []),
            }
        finally:
            db.close()

    def _analyze_and_fix(
        self,
        step_description: str,
        action: str,
        screenshot_path: str,
    ) -> Dict[str, Any]:
        """AI 分析截图并生成 selector"""
        # 截取步骤描述中的元素名称（如 "[个人认证选项卡]" → "个人认证选项卡"）
        element_name = self._extract_element_name(step_description)

        prompt = f"""步骤：{step_description}
Action：{action}
元素描述：{element_name}
截图文件：{screenshot_path}

请分析截图，找到「{element_name}」元素的最佳 Playwright selector，直接输出 JSON。"""

        try:
            result_text = self.ai.vision(
                image=screenshot_path,
                prompt=prompt,
            )
            return self._parse_fix_response(result_text)
        except AIAPIError as e:
            logger.error(f"[CaseAutoFix] AI API failed: {e}")
            return {"selector": "", "reason": f"AI API failed: {e}"}
        except Exception as e:
            logger.error(f"[CaseAutoFix] Analyze error: {e}")
            return {"selector": "", "reason": str(e)}

    def _extract_element_name(self, step_description: str) -> str:
        """从步骤描述中提取元素名称"""
        # 去掉 action 部分
        desc = step_description.lower()
        for a in ["click", "type", "assert", "navigate", "wait", "select", "hover", "check", "uncheck"]:
            if desc.startswith(a):
                desc = desc[len(a):].strip()
        # 去掉两边空白和常见符号
        desc = desc.strip().strip("[]\"'。，、,.。")
        return desc or step_description

    def _parse_fix_response(self, text: str) -> Dict[str, Any]:
        """解析 AI 返回的修复建议"""
        text = text.strip()

        # 尝试 JSON
        try:
            data = json.loads(text)
            if data.get("selector"):
                return data
        except json.JSONDecodeError:
            pass

        # 尝试从文本提取 selector
        selector_match = re.search(
            r'"selector"\s*:\s*"([^"]+)"',
            text
        )
        type_match = re.search(
            r'"selector_type"\s*:\s*"([^"]+)"',
            text
        )
        reason_match = re.search(
            r'"reason"\s*:\s*"([^"]+)"',
            text
        )
        alt_match = re.search(
            r'"alternative_selectors"\s*:\s*\[([^\]]+)\]',
            text
        )

        result = {
            "selector": selector_match.group(1) if selector_match else "",
            "selector_type": type_match.group(1) if type_match else "css",
            "reason": reason_match.group(1) if reason_match else "",
        }
        if alt_match:
            result["alternative_selectors"] = [
                s.strip().strip("'\"")
                for s in alt_match.group(1).split(",")
            ]

        return result

    def _update_case_content(
        self,
        case_record: Case,
        old_target: str,
        new_selector: str,
    ) -> Case:
        """更新用例 content 中的 target"""
        import yaml

        content = case_record.content
        # 替换 target 行的值（YAML 中 target: 后面跟的内容）
        # 匹配 target: old_target 或 target: "old_target" 等各种格式
        escaped_old = re.escape(old_target)

        # 替换 YAML 中的 target 行
        # 格式：target: [占位符] → target: 真实selector
        updated_lines = []
        for line in content.split("\n"):
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            if stripped.startswith("target:"):
                # 提取现有值
                rest = stripped[len("target:"):].strip()
                # 替换旧的 target
                if old_target in rest:
                    new_line = f"{indent}target: {new_selector}"
                    updated_lines.append(new_line)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        new_content = "\n".join(updated_lines)

        # 存入数据库
        db = SessionLocal()
        try:
            case_record.content = new_content
            db.commit()
            logger.info(f"[CaseAutoFix] Updated case {case_record.id}: {old_target} → {new_selector}")
            return case_record
        finally:
            db.close()
