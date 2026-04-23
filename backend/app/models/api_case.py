# -*- coding: utf-8 -*-
"""
API Case Model - 接口测试用例模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base


class APICase(Base):
    """接口测试用例"""

    __tablename__ = "api_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    module = Column(String(100), default="default")
    name = Column(String(200), nullable=False)
    method = Column(String(20), nullable=False)  # GET/POST/PUT/DELETE/PATCH
    url = Column(String(500), nullable=False)
    headers = Column(Text, default="{}")  # JSON
    params = Column(Text, default="{}")  # Query 参数
    body = Column(Text, default="{}")  # Body 参数
    body_type = Column(String(20), default="json")  # json / form / raw
    assertions = Column(Text, default="[]")  # JSON list [{type, expr, expected}]
    timeout = Column(Integer, default=30)  # 默认30秒
    tags = Column(Text, default="[]")  # JSON list
    created_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class APITestTask(Base):
    """接口测试执行任务"""

    __tablename__ = "api_test_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    case_ids = Column(Text, default="[]")  # JSON list [1,2,3]
    env = Column(String(20), default="dev")  # dev/staging/prod
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    total = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)