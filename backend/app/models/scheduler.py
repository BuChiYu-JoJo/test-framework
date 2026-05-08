# -*- coding: utf-8 -*-
"""
Scheduler Model - 定时任务模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.core.database import Base


class ScheduledJob(Base):
    """定时任务"""

    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="任务名称")
    cron_expr = Column(String(100), nullable=False, comment="Cron 表达式")
    # Cron 分量（方便前端展示和编辑）
    cron_second = Column(String(10), default="0", comment="秒")
    cron_minute = Column(String(10), default="*", comment="分")
    cron_hour = Column(String(10), default="*", comment="时")
    cron_day = Column(String(10), default="*", comment="日")
    cron_month = Column(String(10), default="*", comment="月")
    cron_weekday = Column(String(10), default="*", comment="周")

    case_id = Column(Integer, nullable=False, comment="关联用例ID")
    project_id = Column(Integer, nullable=False, comment="关联项目ID")
    env = Column(String(20), default="test", comment="执行环境")

    enabled = Column(Boolean, default=True, comment="是否启用")
    notify_on_complete = Column(Boolean, default=False, comment="执行完成是否通知")

    description = Column(Text, default="", comment="任务描述")

    # APScheduler 内部 Job ID（一个整数字符串）
    aps_job_id = Column(String(100), nullable=True, comment="APScheduler Job ID")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_run_at = Column(DateTime, nullable=True, comment="上次执行时间")
    next_run_time = Column(DateTime, nullable=True, comment="下次执行时间")
    run_count = Column(Integer, default=0, comment="累计执行次数")
