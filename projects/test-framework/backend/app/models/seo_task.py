# -*- coding: utf-8 -*-
"""
SEO Task Model - SEO 检测任务模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from app.core.database import Base


class SEOTask(Base):
    """SEO 检测任务"""

    __tablename__ = "seo_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    target_url = Column(String(1000), nullable=False)  # 入口 URL
    urls = Column(JSON, default=list)  # 要检测的 URL 列表
    config = Column(JSON, default=dict)  # 抓取深度、并发数、SPA 等待时间等
    status = Column(String(20), default="pending")  # pending / running / completed / failed
    score = Column(Float, default=0.0)  # 0-100 SEO 评分
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=datetime.now)