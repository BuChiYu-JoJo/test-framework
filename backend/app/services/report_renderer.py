# -*- coding: utf-8 -*-
"""
ReportRenderer - 统一报告渲染服务
将不同类型任务的原生结果转换为统一的报告结构
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def render_unified_report(task_id: int) -> Dict[str, Any]:
    """
    根据 task.summary_json / artifacts_json + 任务类型，输出统一报告结构。

    统一结构：
      task_id, task_type, status, summary,
      timeline, steps (ui), requests (api), issues (seo), metrics (perf),
      artifacts
    """
    from app.core.database import SessionLocal
    from app.models.task import Task

    with SessionLocal() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": f"Task {task_id} not found"}

        summary = _safe_json(task.summary_json)
        artifacts = _safe_json(task.artifacts_json)
        task_type = task.task_type
        project_id = task.project_id

    report: Dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "project_id": project_id,
        "status": task.status if hasattr(task, "status") else summary.get("status"),
        "summary": summary,
        "artifacts": artifacts,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "duration_ms": task.duration_ms,
        "error_msg": task.error_msg or "",
    }

    # 按任务类型追加专属字段
    if task_type == "ui":
        report.update(_render_ui_section(summary, artifacts))
    elif task_type == "api":
        report.update(_render_api_section(summary, artifacts))
    elif task_type == "seo":
        report.update(_render_seo_section(summary))
    elif task_type == "performance":
        report.update(_render_perf_section(summary))

    return report


def _render_ui_section(summary: dict, artifacts: dict) -> dict:
    """提取 UI 执行的步骤列表。"""
    steps = summary.get("steps") or []
    repair_records = summary.get("repair_records") or []
    return {
        "steps": steps,
        "repair_records": repair_records,
        "screenshots": artifacts.get("screenshots") or [],
        "html_report": artifacts.get("html") or "",
        "trace": artifacts.get("trace") or "",
    }


def _render_api_section(summary: dict, artifacts: dict) -> dict:
    return {
        "requests": summary.get("requests") or [],
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
    }


def _render_seo_section(summary: dict) -> dict:
    return {
        "issues": summary.get("issues") or [],
        "score": summary.get("score"),
        "url": summary.get("url") or "",
    }


def _render_perf_section(summary: dict) -> dict:
    return {
        "metrics": summary.get("metrics") or {},
        "lcp": summary.get("lcp"),
        "fid": summary.get("fid"),
        "cls": summary.get("cls"),
        "url": summary.get("url") or "",
    }


def _safe_json(value: Optional[str]) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def build_ui_summary(execution_id: str) -> Dict[str, Any]:
    """
    从 executions + execution_steps 表构建 UI 任务 summary_json。
    供 TaskDispatcher._run_ui() 调用。
    """
    from app.core.database import SessionLocal
    from app.models.execution import Execution, ExecutionStep

    with SessionLocal() as db:
        exec_record = db.query(Execution).filter(
            Execution.execution_id == execution_id
        ).first()
        if not exec_record:
            return {}

        steps = db.query(ExecutionStep).filter(
            ExecutionStep.execution_id == exec_record.id
        ).order_by(ExecutionStep.step_no).all()

        step_list = []
        for s in steps:
            step_list.append({
                "step_no": s.step_no,
                "action": s.action,
                "target": s.target,
                "value": s.value,
                "status": s.status,
                "actual": s.actual,
                "error_msg": s.error_msg,
                "duration_ms": s.duration_ms,
                "screenshot": s.screenshot,
                "matched_strategy_type": s.matched_strategy_type,
                "matched_strategy_value": s.matched_strategy_value,
            })

        passed = sum(1 for s in steps if s.status == "passed")
        failed = sum(1 for s in steps if s.status == "failed")

        return {
            "execution_id": execution_id,
            "status": exec_record.status,
            "total": len(steps),
            "passed": passed,
            "failed": failed,
            "duration_ms": exec_record.duration_ms,
            "report_path": exec_record.report_path,
            "steps": step_list,
        }
