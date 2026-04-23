# -*- coding: utf-8 -*-
"""
SEO Schemas - SEO 检测 API 的请求/响应模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class SEOTaskCreate(BaseModel):
    """创建 SEO 任务"""
    name: str
    project_id: int
    target_url: str
    urls: Optional[List[str]] = []  # 指定检测的 URL 列表
    config: Optional[Dict[str, Any]] = {}  # 抓取深度、并发数、SPA 等待时间


class SEOTaskResponse(BaseModel):
    """SEO 任务列表响应"""
    id: int
    name: str
    project_id: int
    target_url: str
    status: str
    score: float
    critical_count: int
    warning_count: int
    info_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SEOTaskDetailResponse(SEOTaskResponse):
    """SEO 任务详情"""
    urls: List[str]
    config: Dict[str, Any]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class SEOIssueResponse(BaseModel):
    """SEO 问题响应"""
    id: int
    task_id: int
    url: str
    severity: str
    category: str
    rule_id: str
    description: str
    suggestion: Optional[str] = None
    screenshot: Optional[str] = None

    class Config:
        from_attributes = True


class SEOTaskCreateWithUrls(BaseModel):
    """批量 URL SEO 检测"""
    name: str
    project_id: int
    target_url: str  # 入口 URL（用于爬取）
    urls: List[str]  # 直接指定要检测的 URL
    config: Optional[Dict[str, Any]] = {
        "depth": 1,
        "concurrency": 3,
        "spa_wait": 3000,
    }


# ─── Performance Baseline ────────────────────────────────────────

class PerfBaselineCreate(BaseModel):
    """创建性能基线"""
    project_id: int
    name: str
    device: str = "desktop"
    network: str = "wifi"
    metrics: Dict[str, Any]  # 从已有任务复制或手动录入
    task_id: Optional[int] = None


class PerfBaselineResponse(BaseModel):
    """基线响应"""
    id: int
    project_id: int
    name: str
    device: str
    network: str
    metrics: Dict[str, Any]
    task_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PerfBaselineCompareResponse(BaseModel):
    """基线对比结果"""
    baseline_id: int
    current_metrics: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    degraded_items: List[Dict[str, Any]] = []
    improved_items: List[Dict[str, Any]] = []