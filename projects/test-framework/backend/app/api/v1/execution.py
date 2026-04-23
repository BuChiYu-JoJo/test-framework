# -*- coding: utf-8 -*-
"""
Execution API - 执行触发与状态查询 API
"""

import json
import sys
import uuid
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.execution import Execution, ExecutionStep
from app.models.case import Case
from app.models.project import Project
from app.services.notify import notify_execution_complete
from app.services.events import event_bus
from app.schemas.execution import ExecutionCreate, ExecutionResponse, ExecutionDetailResponse


router = APIRouter(prefix="/executions", tags=["Execution"])


def _publish_step(execution_id: str, event: dict):
    """线程安全地发布步骤事件到 SSE 总线（直接发布，event_bus 内部 thread-safe）"""
    event_bus.publish(execution_id, event)


def run_test_case(execution_id: str, case_id: int, project_id: int, env: str, db_url: str):
    """
    在后台线程中执行测试用例
    
    注意：这里通过直接导入 engine 来执行。
    实际项目中可以改为向执行节点发请求（Redis Queue / RabbitMQ）。
    """
    # 延迟导入，避免顶层循环依赖
    import sys
    from pathlib import Path
    from app.core.database import SessionLocal
    from app.models.execution import Execution, ExecutionStep
    from app.models.case import Case

    db = SessionLocal()

    try:
        # 更新状态为 running
        exec_record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
        if not exec_record:
            return

        exec_record.status = "running"
        exec_record.started_at = datetime.now()
        db.commit()

        # 获取用例内容
        case_record = db.query(Case).filter(Case.id == case_id).first()
        if not case_record:
            exec_record.status = "failed"
            exec_record.error_msg = f"Case {case_id} not found"
            db.commit()
            return

        # 导入执行引擎（从项目目录）
        projects_dir = Path(settings.projects_dir)
        sys.path.insert(0, str(projects_dir.parent))

        # 用临时 YAML 文件执行（把用例 content 写进去）
        import tempfile
        case_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        case_file.write(case_record.content)
        case_file.close()

        try:
            from engine import TestEngine

            # 获取用例对应的项目配置
            case_record = db.query(Case).filter(Case.id == case_id).first()
            project = db.query(Project).filter(Project.id == case_record.project_id).first()
            project_name = project.name if project else "dataify"
            base_url = None
            if project and project.env_config:
                import json
                try:
                    ec = json.loads(project.env_config) if isinstance(project.env_config, str) else project.env_config
                    if isinstance(ec, dict) and ec.get("base_url"):
                        base_url = ec["base_url"]
                except Exception:
                    pass

            engine_kwargs = {
                "headless": settings.engine_headless,
                "execution_id": execution_id,
                "event_bus": event_bus,
            }
            if base_url:
                engine_kwargs["base_url"] = base_url

            engine = TestEngine(project_name, **engine_kwargs)
            result = engine.execute_case(engine.load_case(case_file.name), debug=True)

            # 生成 HTML 报告
            report_path = ""
            try:
                from engine import Reporter
                report_data = engine.get_report(result)
                reporter = Reporter(output_dir=settings.reports_dir)
                report_path = reporter.save_html(report_data, filename=f"report_{execution_id}.html")
            except Exception as report_err:
                import traceback
                print(f"报告生成失败: {report_err}\n{traceback.format_exc()}")

            # 保存步骤结果
            for step in result.steps:
                exec_step = ExecutionStep(
                    execution_id=exec_record.id,
                    step_no=step.step_no,
                    action=step.action,
                    target=step.target or "",
                    value=step.value or "",
                    status=step.status.value,
                    actual=str(step.actual) if step.actual else "",
                    error_msg=step.error_msg or "",
                    duration_ms=int(step.duration_ms),
                    screenshot=step.screenshot or "",
                )
                db.add(exec_step)
                db.flush()  # 确保 exec_step.id 可用

                # 发布步骤事件（供 SSE 订阅）
                _publish_step(execution_id, {
                    "type": "step",
                    "step_no": step.step_no,
                    "action": step.action,
                    "target": step.target or "",
                    "value": step.value or "",
                    "status": step.status.value,
                    "actual": str(step.actual) if step.actual else "",
                    "error_msg": step.error_msg or "",
                    "duration_ms": int(step.duration_ms),
                })

            # 更新执行结果
            exec_record.status = result.status.value  # passed / failed / error
            exec_record.result = result.status.value
            exec_record.duration_ms = result.duration_ms
            exec_record.error_msg = result.error_msg or ""
            exec_record.finished_at = datetime.now()
            exec_record.screenshots = json.dumps(result.screenshots)
            if report_path:
                exec_record.report_path = report_path
            db.commit()

            # 发布执行完成事件
            _publish_step(execution_id, {
                "type": "done",
                "status": result.status.value,
                "result": result.status.value,
                "duration_ms": result.duration_ms,
                "error_msg": result.error_msg or "",
            })

            # 发送执行完成通知
            try:
                case_name = case_record.name if case_record else str(case_id)
                report_url = f"/api/v1/reports/{execution_id}" if report_path else None
                notify_execution_complete(
                    execution_id=execution_id,
                    case_name=case_name,
                    result=result.status.value,
                    duration_ms=result.duration_ms,
                    error_msg=result.error_msg,
                    report_url=report_url,
                )
            except Exception as notify_err:
                import traceback
                print(f"通知发送失败: {notify_err}", flush=True); import traceback; traceback.print_exc()

        finally:
            Path(case_file.name).unlink()

    except Exception as e:
        import traceback
        exec_record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
        if exec_record:
            exec_record.status = "failed"
            exec_record.result = "error"
            exec_record.error_msg = f"{str(e)}\n{traceback.format_exc()}"
            exec_record.finished_at = datetime.now()
            db.commit()
            # 发送执行异常通知
            try:
                notify_execution_complete(
                    execution_id=execution_id,
                    case_name=str(case_id),
                    result="error",
                    duration_ms=0,
                    error_msg=str(e)[:200],
                )
            except Exception as notify_err:
                import traceback
                print(f"通知发送失败: {notify_err}", flush=True); import traceback; traceback.print_exc()
    finally:
        db.close()


@router.post("", response_model=dict)
def create_execution(
    data: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    创建执行任务（异步执行）
    
    支持批量执行（多个 case_id），每个 case 生成一条 Execution 记录。
    """
    execution_ids = []

    for case_id in data.case_ids:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            continue  # 跳过不存在的用例

        exec_id = f"exec_{uuid.uuid4().hex[:12]}"
        execution = Execution(
            execution_id=exec_id,
            case_id=case_id,
            project_id=data.project_id,
            env=data.env,
            status="pending",
        )
        db.add(execution)
        db.flush()

        # 启动后台执行
        background_tasks.add_task(
            run_test_case,
            exec_id,
            case_id,
            data.project_id,
            data.env,
            settings.db_url,
        )

        execution_ids.append(exec_id)

    db.commit()
    return {"execution_ids": execution_ids, "count": len(execution_ids)}


@router.get("", response_model=List[ExecutionResponse])
def list_executions(
    case_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取执行记录列表
    
    status 筛选：
    - running: 只返回真正执行中的（finished_at 为空）
    - passed/failed/error: 查询 result 字段
    """
    q = db.query(Execution)
    if case_id:
        q = q.filter(Execution.case_id == case_id)
    if project_id:
        q = q.filter(Execution.project_id == project_id)
    if status:
        if status == "running":
            # 进行中：status=running 且未完成
            q = q.filter(Execution.status == "running", Execution.finished_at.is_(None))
        elif status in ("passed", "failed", "error"):
            # 已完成：按 result 字段筛选
            q = q.filter(Execution.result == status)
        else:
            q = q.filter(Execution.status == status)
    return q.order_by(Execution.id.desc()).limit(100).all()


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """获取执行详情（含步骤列表）"""
    record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.execution_id == record.id)
        .order_by(ExecutionStep.step_no)
        .all()
    )

    return ExecutionDetailResponse(
        id=record.id,
        execution_id=record.execution_id,
        case_id=record.case_id,
        project_id=record.project_id,
        env=record.env,
        status=record.status,
        result=record.result,
        duration_ms=record.duration_ms,
        error_msg=record.error_msg,
        started_at=record.started_at,
        finished_at=record.finished_at,
        report_path=record.report_path or "",
        screenshots=json.loads(record.screenshots or "[]"),
    )


@router.get("/{execution_id}/steps", response_model=List[dict])
def get_execution_steps(execution_id: str, db: Session = Depends(get_db)):
    """获取执行步骤列表"""
    record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.execution_id == record.id)
        .order_by(ExecutionStep.step_no)
        .all()
    )

    return [
        {
            "step_no": s.step_no,
            "action": s.action,
            "target": s.target,
            "value": s.value,
            "status": s.status,
            "actual": s.actual,
            "error_msg": s.error_msg,
            "duration_ms": s.duration_ms,
            "screenshot": s.screenshot,
        }
        for s in steps
    ]


@router.get("/{execution_id}/stream")
def stream_execution(execution_id: str, db: Session = Depends(get_db)):
    """
    SSE 实时推送执行进度
    前端通过 EventSource 订阅：new EventSource('/api/v1/executions/{id}/stream')
    """
    record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 执行已结束时，预先加载历史步骤（在 db session 关闭前）
    history_steps = []
    history_done = None
    if record.status not in ("pending", "running"):
        steps = db.query(ExecutionStep).filter(
            ExecutionStep.execution_id == record.id
        ).order_by(ExecutionStep.step_no).all()
        for s in steps:
            history_steps.append({'type': 'step', 'step_no': s.step_no, 'action': s.action, 'target': s.target or '', 'value': s.value or '', 'status': s.status, 'actual': s.actual or '', 'error_msg': s.error_msg or '', 'duration_ms': s.duration_ms})
        history_done = {'type': 'done', 'status': record.status, 'result': record.result or record.status, 'duration_ms': record.duration_ms or 0, 'error_msg': record.error_msg or ''}

    async def event_generator():
        queue = event_bus.subscribe(execution_id)
        try:
            yield f"event: connected\ndata: {json.dumps({'type': 'start', 'execution_id': execution_id})}\n\n"

            # 如果执行已结束，立即重放历史步骤
            if history_steps:
                for step_event in history_steps:
                    yield f"event: message\ndata: {json.dumps(step_event)}\n\n"
                yield f"event: message\ndata: {json.dumps(history_done)}\n\n"
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: message\ndata: {json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            event_bus.unsubscribe(execution_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{execution_id}/debug-stream")
def stream_debug(execution_id: str, db: Session = Depends(get_db)):
    """
    SSE 实时推送 debug 日志
    前端通过 EventSource 订阅：new EventSource('/api/v1/executions/{id}/debug-stream')
    """
    record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    async def event_generator():
        last_len = 0
        while True:
            logs = event_bus.get_debug_logs(execution_id)
            if len(logs) > last_len:
                for log in logs[last_len:]:
                    yield f"event: message\ndata: {json.dumps(log)}\n\n"
                last_len = len(logs)

            if record.status not in ("pending", "running"):
                yield f"event: message\ndata: {json.dumps({'type': 'done', 'status': record.status})}\n\n"
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{execution_id}/debug-logs")
def get_debug_logs(execution_id: str, db: Session = Depends(get_db)):
    """轮询获取 debug 日志"""
    record = db.query(Execution).filter(Execution.execution_id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    logs = event_bus.get_debug_logs(execution_id)
    return {"execution_id": execution_id, "status": record.status, "logs": logs}


@router.post("/validate")
def validate_cases(
    case_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """用例校验：跑前检查用例问题（locator 引用、变量定义、断言格式等）"""
    issues = []
    projects_dir = Path(settings.projects_dir)
    sys.path.insert(0, str(projects_dir.parent))

    for case_id in case_ids:
        case_record = db.query(Case).filter(Case.id == case_id).first()
        if not case_record:
            issues.append({
                "case_id": case_id,
                "case_name": f"Case {case_id}",
                "issues": [{"step_no": 0, "type": "not_found", "message": f"Case {case_id} not found", "severity": "error"}]
            })
            continue

        import yaml
        try:
            case_data = yaml.safe_load(case_record.content)
        except Exception as e:
            issues.append({
                "case_id": case_id,
                "case_name": case_record.name,
                "issues": [{"step_no": 0, "type": "parse_error", "message": f"YAML 解析失败: {e}", "severity": "error"}]
            })
            continue

        project = db.query(Project).filter(Project.id == case_record.project_id).first()
        project_name = project.name if project else "dataify"

        from engine import LocatorResolver, CaseValidator
        locators_path = projects_dir / project_name / "locators.json"
        locator_resolver = LocatorResolver(str(locators_path)) if locators_path.exists() else None

        validator = CaseValidator(locator_resolver)
        case_issues = validator.validate(case_data)

        issues.append({
            "case_id": case_id,
            "case_name": case_record.name,
            "issues": case_issues
        })

    return {"results": issues}
