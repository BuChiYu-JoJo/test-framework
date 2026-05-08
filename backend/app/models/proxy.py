# -*- coding: utf-8 -*-
"""
Proxy Model - 代理管理数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from app.core.database import Base


class ProxyGroup(Base):
    """代理分组"""
    __tablename__ = "proxy_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), default="")
    strategy = Column(String(20), default="round_robin")  # round_robin / random / failover
    created_at = Column(DateTime, default=datetime.now)


class Proxy(Base):
    """代理节点"""
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    protocol = Column(String(20), default="http")  # http / https / socks5
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)  # AES加密存储
    group_id = Column(Integer, ForeignKey("proxy_groups.id"), nullable=True)
    tags = Column(JSON, default=list)  # ["高匿", "美国"]
    avg_latency_ms = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)  # 可用率 0-100
    use_count = Column(Integer, default=0)
    check_count = Column(Integer, default=0)  # 总检查次数
    fail_count = Column(Integer, default=0)  # 失败次数
    last_check_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="unknown")  # active / inactive / unknown
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProxyAlertRule(Base):
    """代理告警规则"""
    __tablename__ = "proxy_alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    condition = Column(String(50), default="availability")  # availability / latency
    threshold = Column(Float, default=50.0)  # 阈值
    enabled = Column(Boolean, default=True)
    webhook_url = Column(String(500), nullable=True)
    notify_channels = Column(JSON, default=list)  # ["feishu", "dingtalk"]
    created_at = Column(DateTime, default=datetime.now)
