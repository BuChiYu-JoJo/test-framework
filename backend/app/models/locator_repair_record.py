# -*- coding: utf-8 -*-
"""
LocatorRepairRecord Model - Locator 修复审计记录
记录每次 AI Healer 触发的完整修复事件，支持人工审核与回滚
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.core.database import Base


class LocatorRepairRecord(Base):
    """Locator AI 修复审计记录"""

    __tablename__ = "locator_repair_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    locator_key = Column(String(200), nullable=False)       # 如 login.submit_btn
    triggered_by = Column(String(40), nullable=False)       # ui_run / locator_scan / manual
    execution_id = Column(String(64), nullable=True)        # 关联 task / execution
    old_strategies = Column(Text, default="[]")             # JSON：旧 strategies 数组
    new_strategy = Column(Text, default="{}")               # JSON：AI 给出的新策略
    hit_count = Column(Integer, default=0)                  # 校验时命中数
    verdict = Column(String(20), nullable=False, default="miss")  # verified/ambiguous/miss/error
    review_status = Column(String(20), default="pending")   # pending/accepted/rejected/rolled_back
    review_user = Column(String(80), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_repair_project_locator", "project_id", "locator_key"),
        Index("idx_repair_review_status", "review_status"),
    )
