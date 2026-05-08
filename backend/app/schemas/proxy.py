# -*- coding: utf-8 -*-
"""
Proxy Schemas - 代理模块 API 请求/响应模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ProxyGroupCreate(BaseModel):
    name: str
    description: str = ""
    strategy: str = "round_robin"


class ProxyGroupResponse(BaseModel):
    id: int
    name: str
    description: str
    strategy: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProxyCreate(BaseModel):
    name: str
    protocol: str = "http"
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    group_id: Optional[int] = None
    tags: List[str] = []


class ProxyUpdate(BaseModel):
    name: Optional[str] = None
    protocol: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    group_id: Optional[int] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


class ProxyResponse(BaseModel):
    id: int
    name: str
    protocol: str
    host: str
    port: int
    username: Optional[str] = None
    group_id: Optional[int] = None
    tags: List[str]
    avg_latency_ms: float
    success_rate: float
    use_count: int
    check_count: int
    last_check_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    status: str
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProxyBatchAdd(BaseModel):
    proxies: List[Dict[str, Any]]  # [{"protocol":"http","host":"1.2.3.4","port":8080}, ...]


class ProxyAlertRuleCreate(BaseModel):
    name: str
    condition: str = "availability"
    threshold: float = 50.0
    enabled: bool = True
    webhook_url: Optional[str] = None
    notify_channels: List[str] = []


class ProxyAlertRuleResponse(BaseModel):
    id: int
    name: str
    condition: str
    threshold: float
    enabled: bool
    webhook_url: Optional[str] = None
    notify_channels: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProxyStatsResponse(BaseModel):
    total: int
    active: int
    inactive: int
    unknown: int
    avg_success_rate: float
    avg_latency_ms: float
