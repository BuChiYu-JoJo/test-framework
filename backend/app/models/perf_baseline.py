# -*- coding: utf-8 -*-
"""
PerfBaseline Model - 性能基线模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, UniqueConstraint
from app.core.database import Base


class PerfBaseline(Base):
    """性能历史基线"""

    __tablename__ = "perf_baselines"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)  # 基线名称，如 "v1.0.0 baseline"
    device = Column(String(20), default="desktop")  # mobile / desktop
    network = Column(String(20), default="wifi")  # 4g / wifi / slow2g
    metrics = Column(JSON, default=dict)  # {fcp, lcp, fid, cls, ttfb, score}
    task_id = Column(Integer, nullable=True)  # 来源任务 ID
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('project_id', 'device', 'network', 'name', name='uq_baseline_name'),
    )