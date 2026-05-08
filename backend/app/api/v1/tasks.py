# -*- coding: utf-8 -*-
"""
Tasks API - 统一任务调度入口
统一 UI / API / SEO / Performance / Regression / AI Case 任务
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskRunResponse
from app.services.task_dispatcher import task_dispatcher
from app.services.events import event_bus

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """创建任务（不立即执行）"""
    task_id = task_dispatcher.create({
        "task_type": data.task_type,
        "project_id": data.project_id,
        "target_id": data.target_id,
        "target_kind": data.target_kind,
        "env": data.env,
        "trigger_type": data.trigger_type,
        "triggered_by": data.triggered_by,
        "options": data.options or {},
    })
    task = db.query(Task).filter(Task.id == task_id).first()
    resp = TaskResponse.model_validate(task)
    resp.sse_url = f"/api/v1/tasks/{task_id}/events"
    return resp


@router.post("/run", response_model=TaskRunResponse)
def create_and_run_task(data: TaskCreate):
    """创建任务并立即执行（一步合并）"""
    result = task_dispatcher.create_and_run({
        "task_type": data.task_type,
        "project_id": data.project_id,
        "target_id": data.target_id,
        "target_kind": data.target_kind,
        "env": data.env,
        "trigger_type": data.trigger_type,
        "triggered_by": data.triggered_by,
        "options": data.options or {},
    })
    return TaskRunResponse(
        task_id=result["task_id"],
        status=result["status"],
        sse_url=result["sse_url"],
    )


@router.post("/{task_id}/run", response_model=TaskRunResponse)
def run_task(task_id: int, db: Session = Depends(get_db)):
    """执行已创建的任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        result = task_dispatcher.run(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TaskRunResponse(
        task_id=task_id,
        status=result["status"],
        sse_url=result["sse_url"],
    )


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    task_type: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询任务列表"""
    q = db.query(Task)
    if task_type:
        q = q.filter(Task.task_type == task_type)
    if project_id:
        q = q.filter(Task.project_id == project_id)
    if status:
        q = q.filter(Task.status == status)

    tasks = q.order_by(Task.id.desc()).offset((page - 1) * size).limit(size).all()
    result = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        resp.sse_url = f"/api/v1/tasks/{t.id}/events"
        result.append(resp)
    return result


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    resp = TaskResponse.model_validate(task)
    resp.sse_url = f"/api/v1/tasks/{task_id}/events"
    return resp


@router.get("/{task_id}/events")
def task_events(task_id: int):
    """SSE 实时日志流（复用 event_bus，以 task_id 为频道）"""
    import json as _json

    async def event_generator():
        import asyncio
        channel = str(task_id)
        queue = event_bus.subscribe(channel)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            event_bus.unsubscribe(channel, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{task_id}/report")
def get_task_report(task_id: int, db: Session = Depends(get_db)):
    """获取统一格式报告 JSON"""
    from app.services.report_renderer import render_unified_report
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "msg": "ok", "data": render_unified_report(task_id)}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """取消任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    ok = task_dispatcher.cancel(task_id)
    return {"code": 0, "msg": "ok" if ok else "无法取消（任务不在可取消状态）", "data": {"canceled": ok}}


@router.post("/{task_id}/rerun", response_model=TaskRunResponse)
def rerun_task(task_id: int, db: Session = Depends(get_db)):
    """基于原参数重新创建并执行任务"""
    import json
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = task_dispatcher.create_and_run({
        "task_type": task.task_type,
        "project_id": task.project_id,
        "target_id": task.target_id,
        "target_kind": task.target_kind,
        "env": task.env,
        "trigger_type": "manual",
        "triggered_by": "rerun",
        "options": json.loads(task.options_json or "{}"),
    })
    return TaskRunResponse(
        task_id=result["task_id"],
        status=result["status"],
        sse_url=result["sse_url"],
    )


@router.post("/{task_id}/heal-and-rerun", response_model=TaskRunResponse)
def heal_and_rerun(task_id: int, db: Session = Depends(get_db)):
    """AI 修复失败 Locator 后重跑任务"""
    import json
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    options = json.loads(task.options_json or "{}")
    options["ai_heal"] = True
    options["force_heal"] = True

    result = task_dispatcher.create_and_run({
        "task_type": task.task_type,
        "project_id": task.project_id,
        "target_id": task.target_id,
        "target_kind": task.target_kind,
        "env": task.env,
        "trigger_type": "manual",
        "triggered_by": "heal_and_rerun",
        "options": options,
    })
    return TaskRunResponse(
        task_id=result["task_id"],
        status=result["status"],
        sse_url=result["sse_url"],
    )
