# -*- coding: utf-8 -*-
"""
Scheduler API - 定时任务 CRUD API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.scheduler import ScheduledJob
from app.schemas.scheduler import (
    SchedulerJobCreate,
    SchedulerJobUpdate,
    SchedulerJobResponse,
)
from app.services.scheduler import (
    add_job_to_aps,
    remove_job_from_aps,
    run_job_now,
)


router = APIRouter(prefix="/scheduler/jobs", tags=["Scheduler"])


def _build_cron_expr(second, minute, hour, day, month, weekday) -> str:
    """组合 cron 表达式字符串"""
    return f"{second} {minute} {hour} {day} {month} {weekday}"


@router.post("", response_model=SchedulerJobResponse)
def create_scheduled_job(data: SchedulerJobCreate, db: Session = Depends(get_db)):
    """创建定时任务"""
    job = ScheduledJob(
        name=data.name,
        cron_expr=data.cron_expr,
        cron_second=data.cron_second,
        cron_minute=data.cron_minute,
        cron_hour=data.cron_hour,
        cron_day=data.cron_day,
        cron_month=data.cron_month,
        cron_weekday=data.cron_weekday,
        case_id=data.case_id,
        project_id=data.project_id,
        env=data.env,
        enabled=data.enabled,
        notify_on_complete=data.notify_on_complete,
        description=data.description,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 同步到 APScheduler
    if job.enabled:
        try:
            add_job_to_aps(job)
        except Exception as e:
            # APScheduler 启动失败不影响数据库记录
            print(f"[Scheduler API] add_job_to_aps failed: {e}")

    return job


@router.get("", response_model=List[SchedulerJobResponse])
def list_scheduled_jobs(
    project_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """获取定时任务列表"""
    q = db.query(ScheduledJob)
    if project_id is not None:
        q = q.filter(ScheduledJob.project_id == project_id)
    if enabled is not None:
        q = q.filter(ScheduledJob.enabled == enabled)
    return q.order_by(ScheduledJob.id.desc()).all()


@router.get("/{job_id}", response_model=SchedulerJobResponse)
def get_scheduled_job(job_id: int, db: Session = Depends(get_db)):
    """获取单个定时任务"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return job


@router.put("/{job_id}", response_model=SchedulerJobResponse)
def update_scheduled_job(job_id: int, data: SchedulerJobUpdate, db: Session = Depends(get_db)):
    """更新定时任务"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(job, field, value)

    # 重新组合 cron_expr
    job.cron_expr = _build_cron_expr(
        job.cron_second, job.cron_minute, job.cron_hour,
        job.cron_day, job.cron_month, job.cron_weekday,
    )

    db.commit()
    db.refresh(job)

    # 同步到 APScheduler
    if job.enabled:
        try:
            add_job_to_aps(job)
        except Exception as e:
            print(f"[Scheduler API] add_job_to_aps failed: {e}")
    else:
        remove_job_from_aps(job.id)

    return job


@router.delete("/{job_id}")
def delete_scheduled_job(job_id: int, db: Session = Depends(get_db)):
    """删除定时任务"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    # 先从 APScheduler 移除
    try:
        remove_job_from_aps(job.id)
    except Exception:
        pass

    db.delete(job)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{job_id}/run")
def trigger_scheduled_job(job_id: int, db: Session = Depends(get_db)):
    """手动立即触发定时任务"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    try:
        run_job_now(job.id)
        return {"message": f"任务 '{job.name}' 已触发", "job_id": job.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")
