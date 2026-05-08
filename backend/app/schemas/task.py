# -*- coding: utf-8 -*-
"""
Task Schemas - 统一任务 Pydantic 模型
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


class TaskCreate(BaseModel):
    task_type: str                          # ui/api/seo/performance/regression/ai_case
    project_id: int
    target_id: Optional[int] = None
    target_kind: Optional[str] = None      # case/batch/suite/url
    env: str = "test"
    trigger_type: str = "manual"
    triggered_by: Optional[str] = "system"
    options: Optional[Dict[str, Any]] = {}


class TaskResponse(BaseModel):
    id: int
    task_type: str
    project_id: int
    target_id: Optional[int]
    target_kind: Optional[str]
    env: str
    trigger_type: str
    triggered_by: Optional[str]
    status: str
    summary: Optional[Dict[str, Any]] = {}
    artifacts: Optional[Dict[str, Any]] = {}
    duration_ms: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_msg: Optional[str]
    created_at: datetime
    sse_url: Optional[str] = None

    @field_validator("summary", mode="before")
    @classmethod
    def parse_summary(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}

    @field_validator("artifacts", mode="before")
    @classmethod
    def parse_artifacts(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}

    model_config = {"from_attributes": True}


class TaskRunResponse(BaseModel):
    task_id: int
    status: str
    sse_url: str


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
