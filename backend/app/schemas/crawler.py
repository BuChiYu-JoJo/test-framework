# -*- coding: utf-8 -*-
"""
Crawler Schemas - 爬虫巡检模块 API 请求/响应模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class CrawlerConfigCreate(BaseModel):
    name: str
    project_id: Optional[int] = None
    script_path: Optional[str] = None
    entry_url: Optional[str] = None
    interval: int = 3600
    expected_count: int = 100
    completeness_schema: Dict[str, str] = {}
    freshness_threshold: int = 86400
    enabled: bool = True


class CrawlerConfigUpdate(BaseModel):
    name: Optional[str] = None
    script_path: Optional[str] = None
    entry_url: Optional[str] = None
    interval: Optional[int] = None
    expected_count: Optional[int] = None
    completeness_schema: Optional[Dict[str, str]] = None
    freshness_threshold: Optional[int] = None
    enabled: Optional[bool] = None


class CrawlerConfigResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    name: str
    script_path: Optional[str] = None
    entry_url: Optional[str] = None
    interval: int
    expected_count: int
    completeness_schema: Dict[str, Any]
    freshness_threshold: int
    enabled: bool
    last_run_at: Optional[datetime] = None
    last_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlerInspectionResponse(BaseModel):
    id: int
    crawler_id: int
    status: str
    items_count: int
    error_count: int
    duration_ms: int
    completeness: float
    anti_crawl_detected: bool
    error_msg: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


class CrawlerStatsResponse(BaseModel):
    total: int
    enabled: int
    passed: int
    warning: int
    failed: int
    unknown: int
    avg_success_rate: float
