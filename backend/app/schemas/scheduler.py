# -*- coding: utf-8 -*-
"""
Scheduler Schemas - 定时任务 API 的请求/响应模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SchedulerJobCreate(BaseModel):
    """创建定时任务"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    cron_expr: str = Field(..., description="完整 Cron 表达式（仅用于展示）")
    cron_second: str = Field(default="0", description="秒")
    cron_minute: str = Field(default="*", description="分")
    cron_hour: str = Field(default="*", description="时")
    cron_day: str = Field(default="*", description="日")
    cron_month: str = Field(default="*", description="月")
    cron_weekday: str = Field(default="*", description="周")
    case_id: int = Field(..., description="用例ID")
    project_id: int = Field(..., description="项目ID")
    env: str = Field(default="test", description="执行环境")
    enabled: bool = Field(default=True, description="是否启用")
    notify_on_complete: bool = Field(default=False, description="执行完成是否通知")
    description: str = Field(default="", description="任务描述")


class SchedulerJobUpdate(BaseModel):
    """更新定时任务"""
    name: Optional[str] = Field(None, max_length=200)
    cron_expr: Optional[str] = None
    cron_second: Optional[str] = None
    cron_minute: Optional[str] = None
    cron_hour: Optional[str] = None
    cron_day: Optional[str] = None
    cron_month: Optional[str] = None
    cron_weekday: Optional[str] = None
    case_id: Optional[int] = None
    project_id: Optional[int] = None
    env: Optional[str] = None
    enabled: Optional[bool] = None
    notify_on_complete: Optional[bool] = None
    description: Optional[str] = None


class SchedulerJobResponse(BaseModel):
    """定时任务响应"""
    id: int
    name: str
    cron_expr: str
    cron_second: str
    cron_minute: str
    cron_hour: str
    cron_day: str
    cron_month: str
    cron_weekday: str
    case_id: int
    project_id: int
    env: str
    enabled: bool
    notify_on_complete: bool
    description: str
    aps_job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    run_count: int = 0

    class Config:
        from_attributes = True
