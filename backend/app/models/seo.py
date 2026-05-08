# -*- coding: utf-8 -*-
"""
SEO Issue Model - SEO 检测问题记录模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from app.core.database import Base


class SEOIssue(Base):
    """SEO 问题记录"""

    __tablename__ = "seo_issues"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("seo_tasks.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    severity = Column(String(20), nullable=False)  # critical / warning / info
    category = Column(String(50), nullable=False)  # meta / content / link / technical
    rule_id = Column(String(50), nullable=False)   # 规则标识，如 "title_missing"
    description = Column(Text, nullable=False)     # 问题描述
    suggestion = Column(Text, nullable=True)       # 修复建议
    screenshot = Column(String(500), nullable=True)  # 截图路径
    created_at = Column(DateTime, default=datetime.now)