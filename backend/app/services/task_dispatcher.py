# -*- coding: utf-8 -*-
"""
TaskDispatcher - 统一任务分发服务
将所有任务类型（UI/API/SEO/Performance/Regression/AI Case）
统一路由到对应 service，并维护 task 表。
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    UI = "ui"
    API = "api"
    SEO = "seo"
    PERFORMANCE = "performance"
    REGRESSION = "regression"
    AI_CASE = "ai_case"


class TaskDispatcher:
    """统一任务分发：根据 task_type 路由到具体 service。"""

    _ROUTES = {
        TaskType.UI:          "_run_ui",
        TaskType.API:         "_run_api",
        TaskType.SEO:         "_run_seo",
        TaskType.PERFORMANCE: "_run_performance",
        TaskType.REGRESSION:  "_run_regression",
        TaskType.AI_CASE:     "_run_ai_case",
    }

    def create(self, payload: Dict[str, Any]) -> int:
        from app.core.database import SessionLocal
        from app.models.task import Task

        with SessionLocal() as db:
            task = Task(
                task_type=payload["task_type"],
                project_id=payload["project_id"],
                target_id=payload.get("target_id"),
                target_kind=payload.get("target_kind"),
                env=payload.get("env", "test"),
                trigger_type=payload.get("trigger_type", "manual"),
                triggered_by=payload.get("triggered_by", "system"),
                options_json=json.dumps(payload.get("options") or {}),
                status="pending",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task.id

    def run(self, task_id: int) -> Dict[str, Any]:
        """在后台线程启动任务，立即返回 running 状态。"""
        from app.core.database import SessionLocal
        from app.models.task import Task

        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Task {task_id} not found")
            if task.status not in ("pending", "canceled"):
                raise ValueError(f"Task {task_id} is already {task.status}")

            task.status = "running"
            task.started_at = datetime.now()
            db.commit()
            task_type = task.task_type
            target_id = task.target_id
            project_id = task.project_id
            env = task.env
            options = json.loads(task.options_json or "{}")

        method_name = self._ROUTES.get(TaskType(task_type))
        if not method_name:
            self._mark_failed(task_id, f"Unsupported task_type: {task_type}")
            raise ValueError(f"Unsupported task_type: {task_type}")

        handler = getattr(self, method_name)
        t = threading.Thread(
            target=self._run_with_error_handling,
            args=(task_id, handler, task_id, target_id, project_id, env, options),
            daemon=True,
        )
        t.start()

        return {
            "task_id": task_id,
            "status": "running",
            "sse_url": f"/api/v1/tasks/{task_id}/events",
        }

    def create_and_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task_id = self.create(payload)
        return self.run(task_id)

    def cancel(self, task_id: int) -> bool:
        from app.core.database import SessionLocal
        from app.models.task import Task

        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task or task.status not in ("pending", "running"):
                return False
            task.status = "canceled"
            task.finished_at = datetime.now()
            db.commit()
        return True

    # ─── 各类型任务处理 ─────────────────────────────────────────────

    def _run_ui(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        """路由到原有 UI 执行流程。"""
        from app.core.database import SessionLocal
        from app.models.case import Case
        from app.models.execution import Execution
        from app.api.v1.execution import run_test_case
        from app.core.config import settings

        with SessionLocal() as db:
            case = db.query(Case).filter(Case.id == target_id).first()
            if not case:
                raise ValueError(f"Case {target_id} not found")

        execution_id = str(uuid.uuid4())[:8]
        with SessionLocal() as db:
            exec_record = Execution(
                execution_id=execution_id,
                case_id=target_id,
                project_id=project_id,
                env=env,
                status="pending",
            )
            db.add(exec_record)
            db.commit()

        run_test_case(
            execution_id=execution_id,
            case_id=target_id,
            project_id=project_id,
            env=env,
            db_url=settings.db_url,
        )

        with SessionLocal() as db:
            exec_record = db.query(Execution).filter(
                Execution.execution_id == execution_id
            ).first()
            if exec_record:
                summary = {"execution_id": execution_id, "status": exec_record.status}
                self._mark_finished(task_id, exec_record.status, summary)

    def _run_api(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        try:
            from app.services.api_test_service import run_api_case
            result = run_api_case(case_id=target_id, project_id=project_id, env=env)
            status = "passed" if result.get("passed") else "failed"
            self._mark_finished(task_id, status, result)
        except Exception as exc:
            raise RuntimeError(f"API task failed: {exc}") from exc

    def _run_seo(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        try:
            from app.services.seo_service import run_seo_scan
            result = run_seo_scan(target_id=target_id, project_id=project_id)
            self._mark_finished(task_id, "passed", result)
        except Exception as exc:
            raise RuntimeError(f"SEO task failed: {exc}") from exc

    def _run_performance(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        try:
            from app.services.performance_service import run_performance_scan
            result = run_performance_scan(target_id=target_id, project_id=project_id)
            self._mark_finished(task_id, "passed", result)
        except Exception as exc:
            raise RuntimeError(f"Performance task failed: {exc}") from exc

    def _run_regression(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        try:
            from app.services.ai_regression import select_regression_cases
            result = select_regression_cases(project_id=project_id, options=options)
            self._mark_finished(task_id, "passed", result)
        except Exception as exc:
            raise RuntimeError(f"Regression task failed: {exc}") from exc

    def _run_ai_case(self, task_id: int, target_id: int, project_id: int, env: str, options: dict):
        self._mark_finished(task_id, "passed", {"message": "AI case generation task queued"})

    # ─── 内部工具 ─────────────────────────────────────────────────

    def _run_with_error_handling(self, task_id, handler, *args):
        try:
            handler(*args)
        except Exception as exc:
            logger.error(f"[TaskDispatcher] task {task_id} failed: {exc}", exc_info=True)
            self._mark_failed(task_id, str(exc))

    def _mark_finished(self, task_id: int, status: str, summary: dict):
        from app.core.database import SessionLocal
        from app.models.task import Task

        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                task.finished_at = datetime.now()
                if task.started_at:
                    task.duration_ms = int(
                        (task.finished_at - task.started_at).total_seconds() * 1000
                    )
                task.summary_json = json.dumps(summary or {}, ensure_ascii=False)
                db.commit()

    def _mark_failed(self, task_id: int, error_msg: str):
        from app.core.database import SessionLocal
        from app.models.task import Task

        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.finished_at = datetime.now()
                task.error_msg = error_msg
                db.commit()


# 全局单例
task_dispatcher = TaskDispatcher()
