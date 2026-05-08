# -*- coding: utf-8 -*-
"""
Project Model - 项目模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base


class Project(Base):
    """测试项目"""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    env_config = Column(Text, default="{}")  # JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
