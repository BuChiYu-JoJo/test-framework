# -*- coding: utf-8 -*-
"""
Execution Model - 执行记录模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from app.core.database import Base


class Execution(Base):
    """执行记录"""

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(50), unique=True, nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    env = Column(String(20), default="test")
    status = Column(String(20), default="pending")  # pending/running/passed/failed/blocked/skipped
    result = Column(String(20), default="")  # passed/failed/error
    duration_ms = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, default="")
    report_path = Column(String(500), default="")  # HTML 报告路径
    screenshots = Column(Text, default="[]")  # JSON list
    created_at = Column(DateTime, default=datetime.now)


class ExecutionStep(Base):
    """执行步骤详情"""

    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    target = Column(String(200), default="")
    value = Column(Text, default="")
    status = Column(String(20), default="pending")
    actual = Column(Text, default="")
    error_msg = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    screenshot = Column(String(500), default="")
