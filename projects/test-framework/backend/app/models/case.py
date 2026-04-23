# -*- coding: utf-8 -*-
"""
Case Model - 用例模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Case(Base):
    """测试用例"""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    case_id = Column(String(50), nullable=False, index=True)  # 外部ID，如 TC001
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    module = Column(String(100), default="default")
    priority = Column(String(10), default="P2")  # P0/P1/P2/P3
    tags = Column(Text, default="[]")  # JSON list
    content = Column(Text, nullable=False)  # YAML/JSON 内容
    version = Column(String(20), default="1.0.0")
    author = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
