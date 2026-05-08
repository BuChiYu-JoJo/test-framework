# -*- coding: utf-8 -*-
"""
Task Model - 统一任务表
支持 UI / API / SEO / Performance / AI 任务的统一调度与查询
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.core.database import Base


class Task(Base):
    """执行任务统一表"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(20), nullable=False)       # ui/api/seo/performance/regression/ai_case
    project_id = Column(Integer, nullable=False, index=True)
    target_id = Column(Integer, nullable=True)           # case_id / api_case_id / seo_target_id
    target_kind = Column(String(20), nullable=True)      # case / batch / suite / url
    env = Column(String(20), default="test")
    trigger_type = Column(String(20), nullable=False, default="manual")  # manual/schedule/webhook/regression
    triggered_by = Column(String(80), default="system")
    status = Column(String(20), default="pending")       # pending/running/passed/failed/partial/canceled
    summary_json = Column(Text, default="{}")            # {total, passed, failed, warnings, ...}
    artifacts_json = Column(Text, default="{}")          # {html, json, trace, har, screenshots[]}
    options_json = Column(Text, default="{}")            # 任务专属配置
    duration_ms = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_task_project_status", "project_id", "status"),
        Index("idx_task_type_started", "task_type", "started_at"),
    )
