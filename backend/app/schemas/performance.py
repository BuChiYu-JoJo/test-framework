# -*- coding: utf-8 -*-
"""
Performance Schemas - 性能检测 API 的请求/响应模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class PerformanceTaskCreate(BaseModel):
    """创建性能检测任务"""
    name: str
    project_id: int
    target_url: str
    device: str = "desktop"  # mobile / desktop
    network: str = "wifi"  # 4g / wifi / slow2g
    config: Optional[Dict[str, Any]] = {}


class PerformanceTaskResponse(BaseModel):
    """性能任务响应"""
    id: int
    name: str
    project_id: int
    target_url: str
    device: str
    network: str
    status: str
    score: float
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PerformanceTaskDetailResponse(PerformanceTaskResponse):
    """性能任务详情（含 metrics/resources）"""
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    resources: Dict[str, Any]
    har_file: str
    error_msg: str


class WaterfallEntry(BaseModel):
    """瀑布图资源条目"""
    url: str
    size: int
    duration: float
    start: float
    mime: Optional[str] = "application/octet-stream"


class WaterfallCategory(BaseModel):
    """按类型分类的资源"""
    js: List[WaterfallEntry] = []
    css: List[WaterfallEntry] = []
    img: List[WaterfallEntry] = []
    font: List[WaterfallEntry] = []
    xhr: List[WaterfallEntry] = []
    other: List[WaterfallEntry] = []


class WaterfallResponse(BaseModel):
    """瀑布图响应"""
    task_id: int
    url: str
    total_requests: int
    total_size: int
    categories: Dict[str, List[Dict]]  # {js: [], css: [], img: [], ...}