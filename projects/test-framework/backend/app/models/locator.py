# -*- coding: utf-8 -*-
"""
Locator Model - 页面元素定位符模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base


class Locator(Base):
    """页面元素定位符（存储在数据库，替代 locators.json）"""

    __tablename__ = "locators"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False, index=True)
    page_name = Column(String(100), nullable=False)  # 如 login / dashboard
    element_key = Column(String(100), nullable=False)  # 如 tab_password / submit
    selector = Column(Text, nullable=False)  # CSS/XPath selector
    selector_type = Column(String(20), default="css")  # css / xpath
    priority = Column(Integer, default=1)  # 1-4，越小越优先
    description = Column(String(500), default="")
    ai_confidence = Column(String(10), default="")  # AI 生成置信度，如 "0.95"
    version = Column(String(20), default="1.0.0")
    updated_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
