# -*- coding: utf-8 -*-
"""
SEO API - SEO 检测任务 API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.seo_task import SEOTask
from app.models.seo import SEOIssue
from app.models.project import Project
from app.schemas.seo import (
    SEOTaskCreate,
    SEOTaskResponse,
    SEOTaskDetailResponse,
    SEOIssueResponse,
)
from app.services.seo_service import run_seo_task, check_seo


router = APIRouter(prefix="/seo/tasks", tags=["SEO"])


@router.post("", response_model=dict)
def create_task(
    data: SEOTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """创建 SEO 检测任务（异步执行）"""
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")

    task = SEOTask(
        name=data.name,
        project_id=data.project_id,
        target_url=data.target_url,
        urls=data.urls or [],
        config=data.config or {},
        status="pending",
    )
    db.add(task)
    db.flush()
    task_id = task.id
    db.commit()

    background_tasks.add_task(run_seo_task, task_id, None)

    return {"id": task_id, "name": task.name, "status": task.status}


@router.get("", response_model=List[SEOTaskResponse])
def list_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取 SEO 任务列表"""
    q = db.query(SEOTask)
    if project_id:
        q = q.filter(SEOTask.project_id == project_id)
    if status:
        q = q.filter(SEOTask.status == status)
    return q.order_by(SEOTask.id.desc()).limit(100).all()


@router.get("/{task_id}", response_model=SEOTaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return SEOTaskDetailResponse(
        id=task.id,
        name=task.name,
        project_id=task.project_id,
        target_url=task.target_url,
        urls=task.urls or [],
        config=task.config or {},
        status=task.status,
        score=task.score,
        critical_count=task.critical_count,
        warning_count=task.warning_count,
        info_count=task.info_count,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
    )


@router.get("/{task_id}/issues", response_model=List[SEOIssueResponse])
def get_task_issues(task_id: int, severity: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """获取任务的问题列表"""
    q = db.query(SEOIssue).filter(SEOIssue.task_id == task_id)
    if severity:
        q = q.filter(SEOIssue.severity == severity)
    return q.order_by(SEOIssue.id.desc()).all()


@router.get("/{task_id}/report")
def get_task_report(task_id: int, db: Session = Depends(get_db)):
    """生成 HTML 报告"""
    task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    issues = db.query(SEOIssue).filter(SEOIssue.task_id == task_id).all()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>SEO 检测报告 - {task.name}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
  .score {{ font-size: 48px; font-weight: bold; color: #4ade80; }}
  .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
  .summary .card {{ background: #f8fafc; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }}
  .critical {{ color: #ef4444; }} .warning {{ color: #f59e0b; }} .info {{ color: #3b82f6; }}
  .issue {{ background: white; border: 1px solid #e2e8f0; padding: 15px; margin: 10px 0; border-radius: 6px; }}
  .issue.severity-critical {{ border-left: 4px solid #ef4444; }}
  .issue.severity-warning {{ border-left: 4px solid #f59e0b; }}
  .issue.severity-info {{ border-left: 4px solid #3b82f6; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 12px; color: white; }}
  .badge.critical {{ background: #ef4444; }} .badge.warning {{ background: #f59e0b; }} .badge.info {{ background: #3b82f6; }}
</style>
</head>
<body>
<div class="header">
  <h1>🕷️ SEO 检测报告</h1>
  <p>任务: {task.name} | 目标: {task.target_url}</p>
  <div class="score">Score: {task.score}</div>
</div>
<div class="summary">
  <div class="card"><div class="critical" style="font-size:24px">{task.critical_count}</div><div>Critical</div></div>
  <div class="card"><div class="warning" style="font-size:24px">{task.warning_count}</div><div>Warning</div></div>
  <div class="card"><div class="info" style="font-size:24px">{task.info_count}</div><div>Info</div></div>
</div>
<h2>问题详情</h2>
"""
    for issue in issues:
        html += f"""
<div class="issue severity-{issue.severity}">
  <span class="badge {issue.severity}">{issue.severity.upper()}</span>
  <strong>[{issue.category}]</strong> {issue.description}
  <p><em>建议:</em> {issue.suggestion or '无'}</p>
  <small>URL: {issue.url} | Rule: {issue.rule_id}</small>
</div>
"""
    html += "</body></html>"

    return {"html": html, "json": {"score": task.score, "critical": task.critical_count, "warning": task.warning_count, "info": task.info_count, "issues_count": len(issues)}}


@router.post("/{task_id}/run")
def run_task_now(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """立即执行任务"""
    task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task.status = "pending"
    db.commit()
    background_tasks.add_task(run_seo_task, task_id, None)

    return {"message": f"Task {task_id} re-triggered", "status": "pending"}


@router.delete("/{task_id}", response_model=dict)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # 删除关联问题
    db.query(SEOIssue).filter(SEOIssue.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}