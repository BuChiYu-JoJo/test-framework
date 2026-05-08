# -*- coding: utf-8 -*-
"""
PerformanceTask Model - 性能检测任务模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from app.core.database import Base


class PerformanceTask(Base):
    """性能检测任务"""

    __tablename__ = "performance_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    target_url = Column(String(1000), nullable=False)
    device = Column(String(20), default="desktop")  # mobile / desktop
    network = Column(String(20), default="wifi")  # 4g / wifi / slow2g
    config = Column(JSON, default=dict)  # throttling 配置
    status = Column(String(20), default="pending")  # pending / running / completed / failed
    score = Column(Float, default=0.0)  # 0-100
    metrics = Column(JSON, default=dict)  # {fcp, lcp, fid, cls, ttfb}
    resources = Column(JSON, default=dict)  # 资源瀑布图数据
    har_file = Column(String(500), default="")  # HAR 文件路径
    error_msg = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)