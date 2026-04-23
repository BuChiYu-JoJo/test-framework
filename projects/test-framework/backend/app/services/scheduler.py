# -*- coding: utf-8 -*-
"""
Scheduler Service - APScheduler 定时任务管理服务
"""

import threading
import traceback
from datetime import datetime
from typing import Optional, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.scheduler import ScheduledJob


# ─── APScheduler 单例（进程内全局）───────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = threading.Lock()


def _get_scheduler() -> BackgroundScheduler:
    """获取或创建 APScheduler 单例"""
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                # 使用与主程序相同的 SQLite 数据库作为 job store
                jobstores = {
                    "default": SQLAlchemyJobStore(url=settings.db_url.replace("sqlite:///", "sqlite:///"))
                }
                _scheduler = BackgroundScheduler(jobstores=jobstores)
    return _scheduler


def _build_cron_trigger(second: str, minute: str, hour: str,
                          day: str, month: str, weekday: str) -> CronTrigger:
    """从分量构建 CronTrigger"""
    return CronTrigger(
        second=second,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=weekday,
    )


def _run_scheduled_job(job_id: str):
    """
    APScheduler 触发执行的回调函数（在新线程中运行）
    
    注意：这里直接调用已有的执行逻辑，避免循环导入。
    """
    db = SessionLocal()
    try:
        job: ScheduledJob = db.query(ScheduledJob).filter(ScheduledJob.id == int(job_id)).first()
        if not job:
            print(f"[Scheduler] Job {job_id} not found in DB, skip.", flush=True)
            return

        # 更新 last_run_at
        job.last_run_at = datetime.now()
        job.run_count = (job.run_count or 0) + 1
        db.commit()

        print(f"[Scheduler] Triggering job '{job.name}' (id={job.id})", flush=True)

        # 触发执行（复用现有的异步执行逻辑）
        _trigger_execution(job.id, job.case_id, job.project_id, job.env, job.notify_on_complete)

    except Exception as e:
        print(f"[Scheduler] Job {job_id} execution error: {e}\n{traceback.format_exc()}", flush=True)
    finally:
        db.close()


def _trigger_execution(job_record_id: int, case_id: int, project_id: int, env: str, notify: bool):
    """
    触发测试执行（在新线程中执行，避免阻塞 APScheduler）
    
    实际项目中可改为向执行节点发请求（Celery / RabbitMQ）。
    """
    def _do():
        try:
            from app.core.database import SessionLocal
            from app.models.execution import Execution
            from app.api.v1.execution import run_test_case
            import uuid

            db = SessionLocal()
            try:
                exec_id = f"sched_{uuid.uuid4().hex[:12]}"
                execution = Execution(
                    execution_id=exec_id,
                    case_id=case_id,
                    project_id=project_id,
                    env=env,
                    status="pending",
                )
                db.add(execution)
                db.commit()

                # 在当前线程池中运行（避免创建新的嵌套事件循环）
                run_test_case(
                    execution_id=exec_id,
                    case_id=case_id,
                    project_id=project_id,
                    env=env,
                    db_url=settings.db_url,
                )
            finally:
                db.close()
        except Exception as e:
            print(f"[_trigger_execution] error: {e}\n{traceback.format_exc()}", flush=True)

    # 启动新线程执行（FastAPI 的 run_test_case 依赖 asyncio，需在独立线程运行）
    t = threading.Thread(target=_do, daemon=True)
    t.start()


# ─── 公开 API ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """启动调度器（在应用 startup 时调用）"""
    sched = _get_scheduler()
    if not sched.running:
        sched.start()
        print("[Scheduler] APScheduler started.", flush=True)

        # 将数据库中 enabled=True 的任务同步到 APScheduler
        _sync_jobs_from_db()


def stop_scheduler():
    """停止调度器（在应用 shutdown 时调用）"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[Scheduler] APScheduler stopped.", flush=True)


def add_job_to_aps(db_job: ScheduledJob):
    """将数据库记录添加为 APScheduler Job"""
    sched = _get_scheduler()
    job_id = str(db_job.id)

    # 移除旧的（如果存在）
    if sched.get_job(job_id):
        sched.remove_job(job_id)

    trigger = _build_cron_trigger(
        second=db_job.cron_second,
        minute=db_job.cron_minute,
        hour=db_job.cron_hour,
        day=db_job.cron_day,
        month=db_job.cron_month,
        weekday=db_job.cron_weekday,
    )

    sched.add_job(
        func=_run_scheduled_job,
        trigger=trigger,
        args=[job_id],
        id=job_id,
        name=db_job.name,
        replace_existing=True,
        misfire_grace_time=60,  # 允许最多 60s 的错过调度宽限
    )

    print(f"[Scheduler] Job '{db_job.name}' added to APScheduler (id={db_job.id})", flush=True)


def remove_job_from_aps(job_id: int):
    """从 APScheduler 移除 Job"""
    sched = _get_scheduler()
    job = sched.get_job(str(job_id))
    if job:
        sched.remove_job(str(job_id))
        print(f"[Scheduler] Job {job_id} removed from APScheduler.", flush=True)


def _sync_jobs_from_db():
    """应用启动时，将 DB 中 enabled=True 的任务同步到 APScheduler"""
    db = SessionLocal()
    try:
        jobs = db.query(ScheduledJob).filter(ScheduledJob.enabled == True).all()
        for job in jobs:
            try:
                add_job_to_aps(job)
            except Exception as e:
                print(f"[Scheduler] Failed to sync job {job.id}: {e}", flush=True)
    finally:
        db.close()


def run_job_now(job_id: int):
    """手动立即触发一个定时任务"""
    job: ScheduledJob = SessionLocal().query(ScheduledJob).filter(
        ScheduledJob.id == job_id
    ).first()
    if not job:
        raise ValueError(f"ScheduledJob {job_id} not found")

    _run_scheduled_job(str(job_id))
