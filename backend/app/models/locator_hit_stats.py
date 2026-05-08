# -*- coding: utf-8 -*-
"""
LocatorHitStats Model - Locator 命中统计
记录每条策略的命中次数，用于健康度评分
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, Index
from app.core.database import Base


class LocatorHitStats(Base):
    """Locator 命中统计"""

    __tablename__ = "locator_hit_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    locator_key = Column(String(200), nullable=False)
    matched_type = Column(String(40), nullable=True)        # css/xpath/role/text/...
    matched_value = Column(Text, default="")
    matched_priority = Column(Integer, default=0)
    fallback_depth = Column(Integer, default=0)             # 0=首选命中, >0=fallback
    hit_count = Column(Integer, default=1)
    last_hit_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("project_id", "locator_key", "matched_type", "matched_value",
                         name="uq_locator_hit"),
        Index("idx_hit_project_key", "project_id", "locator_key"),
    )
