# -*- coding: utf-8 -*-
"""
Crawler Model - 爬虫巡检数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from app.core.database import Base


class CrawlerConfig(Base):
    """爬虫配置"""
    __tablename__ = "crawler_configs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    name = Column(String(200), nullable=False)
    script_path = Column(String(500), nullable=True)  # 脚本路径（本地）
    entry_url = Column(String(1000), nullable=True)  # 入口URL（远程）
    interval = Column(Integer, default=3600)  # 巡检间隔(秒)
    expected_count = Column(Integer, default=100)  # 预期抓取量
    completeness_schema = Column(JSON, default=dict)  # {"url": str, "title": str, "content": str}
    freshness_threshold = Column(Integer, default=86400)  # 新鲜度阈值(秒)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), default="unknown")  # passed / warning / failed / unknown
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CrawlerInspection(Base):
    """爬虫巡检记录"""
    __tablename__ = "crawler_inspections"

    id = Column(Integer, primary_key=True, index=True)
    crawler_id = Column(Integer, ForeignKey("crawler_configs.id"), nullable=False, index=True)
    status = Column(String(20), default="running")  # running / passed / warning / failed
    items_count = Column(Integer, default=0)  # 抓取数量
    error_count = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    completeness = Column(Float, default=0.0)  # 完整性 0-100
    anti_crawl_detected = Column(Boolean, default=False)
    error_msg = Column(Text, nullable=True)
    stdout_log = Column(Text, nullable=True)  # 标准输出
    stderr_log = Column(Text, nullable=True)  # 错误输出
    checked_at = Column(DateTime, default=datetime.now)
