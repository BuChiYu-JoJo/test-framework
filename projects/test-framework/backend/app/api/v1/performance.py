# -*- coding: utf-8 -*-
"""
Performance API v2 - 多 URL 批量 + 基线对比 + 瀑布图
"""

import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.performance import PerformanceTask
from app.models.perf_baseline import PerfBaseline
from app.models.project import Project
from app.schemas.performance import (
    PerformanceTaskCreate,
    PerformanceTaskResponse,
    PerformanceTaskDetailResponse,
    WaterfallResponse,
)
from app.services.performance_service import run_performance_task


router = APIRouter(prefix="/performance/tasks", tags=["Performance"])


# ─── 原有 API（保留兼容）────────────────────────────────────────

@router.post("", response_model=dict)
def create_task(
    data: PerformanceTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")

    task = PerformanceTask(
        name=data.name,
        project_id=data.project_id,
        target_url=data.target_url,
        device=data.device,
        network=data.network,
        config=data.config or {},
        status="pending",
    )
    db.add(task)
    db.flush()
    task_id = task.id
    db.commit()

    background_tasks.add_task(run_performance_task, task_id, None)

    return {"id": task_id, "name": task.name, "status": task.status}


@router.get("", response_model=List[PerformanceTaskResponse])
def list_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(PerformanceTask)
    if project_id:
        q = q.filter(PerformanceTask.project_id == project_id)
    if status:
        q = q.filter(PerformanceTask.status == status)
    return q.order_by(PerformanceTask.id.desc()).limit(100).all()


@router.get("/{task_id}", response_model=PerformanceTaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return PerformanceTaskDetailResponse(
        id=task.id,
        name=task.name,
        project_id=task.project_id,
        target_url=task.target_url,
        device=task.device,
        network=task.network,
        status=task.status,
        score=task.score,
        config=task.config or {},
        metrics=task.metrics or {},
        resources=task.resources or {},
        har_file=task.har_file or "",
        error_msg=task.error_msg or "",
        created_at=task.created_at,
        finished_at=task.finished_at,
    )


@router.delete("/{task_id}", response_model=dict)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}


# ─── 新增：瀑布图数据 ────────────────────────────────────────────

@router.get("/{task_id}/waterfall", response_model=WaterfallResponse)
def get_waterfall(task_id: int, db: Session = Depends(get_db)):
    """获取资源瀑布图数据"""
    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，无法查看瀑布图")

    resources = task.resources or {}
    entries = resources.get("entries", [])

    # 按类型分类
    categories = {
        "js": [],
        "css": [],
        "img": [],
        "font": [],
        "xhr": [],
        "other": [],
    }

    for r in entries:
        url = r.get("name", "")
        resource_type = r.get("type", "other")
        size = r.get("size", 0)
        duration = r.get("duration", 0)
        start = r.get("startTime", 0)

        entry = {"url": url, "size": size, "duration": round(duration, 2), "start": round(start, 2)}

        if url.endswith(".js") or resource_type == "script":
            categories["js"].append({**entry, "mime": "application/javascript"})
        elif url.endswith(".css") or resource_type == "stylesheet":
            categories["css"].append({**entry, "mime": "text/css"})
        elif re.match(r"\.(png|jpg|jpeg|gif|svg|webp|ico)", url, re.I):
            categories["img"].append({**entry, "mime": "image/" + url.split(".")[-1]})
        elif re.match(r"\.(woff|woff2|ttf|otf|eot)", url, re.I):
            categories["font"].append({**entry, "mime": "font/" + url.split(".")[-1]})
        elif resource_type in ("xhr", "fetch", "websocket"):
            categories["xhr"].append({**entry, "mime": "application/xhr"})
        else:
            categories["other"].append({**entry, "mime": "application/octet-stream"})

    return WaterfallResponse(
        task_id=task_id,
        url=task.target_url,
        total_requests=len(entries),
        total_size=sum(r.get("size", 0) for r in entries),
        categories=categories,
    )


@router.get("/{task_id}/har")
def download_har(task_id: int, db: Session = Depends(get_db)):
    """下载 HAR 文件"""
    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if not task.har_file or not task.har_file.strip():
        raise HTTPException(status_code=404, detail="HAR 文件不存在")

    har_path = task.har_file
    if not har_path.startswith("/"):
        har_path = "/" + har_path

    import os
    if not os.path.exists(har_path):
        raise HTTPException(status_code=404, detail=f"HAR 文件未找到: {har_path}")

    return FileResponse(har_path, media_type="application/json", filename=f"task_{task_id}.har")


# ─── 新增：基线管理 ─────────────────────────────────────────────

@router.post("/baselines", response_model=dict)
def create_baseline(data: dict, db: Session = Depends(get_db)):
    """从已有任务创建基线"""
    task_id = data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required")

    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="只能对已完成的任务创建基线")

    baseline = PerfBaseline(
        project_id=task.project_id,
        name=data.get("name", f"Baseline from task {task_id}"),
        device=task.device,
        network=task.network,
        metrics=task.metrics or {},
        task_id=task_id,
    )
    db.add(baseline)
    db.flush()
    baseline_id = baseline.id
    db.commit()

    return {"id": baseline_id, "name": baseline.name, "created_at": baseline.created_at}


@router.get("/baselines", response_model=List[dict])
def list_baselines(
    project_id: Optional[int] = Query(None),
    device: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取基线列表"""
    q = db.query(PerfBaseline)
    if project_id:
        q = q.filter(PerfBaseline.project_id == project_id)
    if device:
        q = q.filter(PerfBaseline.device == device)
    return q.order_by(PerfBaseline.created_at.desc()).limit(50).all()


@router.get("/baselines/{baseline_id}", response_model=dict)
def get_baseline(baseline_id: int, db: Session = Depends(get_db)):
    """获取基线详情"""
    baseline = db.query(PerfBaseline).filter(PerfBaseline.id == baseline_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")
    return baseline


@router.post("/{task_id}/compare")
def compare_with_baseline(task_id: int, baseline_id: int, db: Session = Depends(get_db)):
    """对比任务指标与基线"""
    task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    baseline = db.query(PerfBaseline).filter(PerfBaseline.id == baseline_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")

    current_metrics = task.metrics or {}
    baseline_metrics = baseline.metrics or {}

    METRIC_THRESHOLDS = {
        "fcp": (1800, 3000),
        "lcp": (2500, 4000),
        "fid": (100, 300),
        "cls": (0.1, 0.25),
        "ttfb": (800, 1800),
        "render": (2000, 5000),
    }

    degraded_items = []
    improved_items = []

    for metric, (good_ms, poor_ms) in METRIC_THRESHOLDS.items():
        cur = current_metrics.get(metric, 0)
        base = baseline_metrics.get(metric, 0)
        if cur <= 0 or base <= 0:
            continue

        pct = ((cur - base) / base) * 100
        if pct > 10:  # 退化超过 10%
            degraded_items.append({
                "metric": metric,
                "baseline": round(base, 2),
                "current": round(cur, 2),
                "change_pct": round(pct, 1),
                "status": "退化",
            })
        elif pct < -10:  # 改善超过 10%
            improved_items.append({
                "metric": metric,
                "baseline": round(base, 2),
                "current": round(cur, 2),
                "change_pct": round(pct, 1),
                "status": "改善",
            })

    return {
        "task_id": task_id,
        "baseline_id": baseline_id,
        "baseline_name": baseline.name,
        "baseline_metrics": baseline_metrics,
        "current_metrics": current_metrics,
        "degraded_items": degraded_items,
        "improved_items": improved_items,
        "summary": f"degraded {len(degraded_items)}, improved {len(improved_items)}",
    }


import re