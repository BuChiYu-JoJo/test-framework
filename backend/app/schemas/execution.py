# -*- coding: utf-8 -*-
"""
Execution Schemas - 执行 API 的请求/响应模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ExecutionCreate(BaseModel):
    """创建执行任务"""
    case_ids: List[int]
    project_id: int
    env: str = "test"


class ExecutionResponse(BaseModel):
    """执行记录响应"""
    id: int
    execution_id: str
    case_id: int
    project_id: int
    env: str
    status: str
    result: str
    duration_ms: int
    error_msg: str
    started_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutionDetailResponse(ExecutionResponse):
    """执行详情（含步骤）"""
    report_path: str
    screenshots: List[str]


class StepResponse(BaseModel):
    """执行步骤响应"""
    step_no: int
    action: str
    target: str
    value: str
    status: str
    actual: str
    error_msg: str
    duration_ms: int
    screenshot: str

    class Config:
        from_attributes = True
