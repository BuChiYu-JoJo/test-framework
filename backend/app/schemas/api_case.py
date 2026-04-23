# -*- coding: utf-8 -*-
"""
API Case Schemas - 接口测试用例的请求/响应模型
"""

import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class AssertionItem(BaseModel):
    """断言项"""
    type: str = Field(..., description="断言类型：status_code/response_time/json_field")
    expr: str = Field("", description="表达式或字段路径")
    expected: str = Field(..., description="期望值")


class APICaseBase(BaseModel):
    name: str = Field(..., max_length=200)
    module: str = "default"
    method: str = Field(..., description="HTTP 方法：GET/POST/PUT/DELETE/PATCH")
    url: str = Field(..., max_length=500)
    headers: dict = {}
    params: dict = {}
    body: dict = {}
    body_type: str = "json"  # json / form / raw
    assertions: List[dict] = []
    timeout: int = 30
    tags: List[str] = []
    created_by: str = ""


class APICaseCreate(APICaseBase):
    project_id: int


class APICaseUpdate(BaseModel):
    name: Optional[str] = None
    module: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[dict] = None
    params: Optional[dict] = None
    body: Optional[dict] = None
    body_type: Optional[str] = None
    assertions: Optional[List[dict]] = None
    timeout: Optional[int] = None
    tags: Optional[List[str]] = None


class APICaseResponse(APICaseBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("headers", "params", "body", mode="before")
    @classmethod
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}

    @field_validator("assertions", "tags", mode="before")
    @classmethod
    def parse_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    model_config = {"from_attributes": True}


class APITestTaskBase(BaseModel):
    name: str = Field(..., max_length=200)
    case_ids: List[int] = []
    env: str = "dev"  # dev/staging/prod


class APITestTaskCreate(APITestTaskBase):
    project_id: int


class APITestTaskResponse(BaseModel):
    id: int
    name: str
    project_id: int
    case_ids: List[int] = []
    env: str
    status: str
    passed: int
    failed: int
    total: int
    duration_ms: int
    created_at: datetime
    finished_at: Optional[datetime] = None

    @field_validator("case_ids", mode="before")
    @classmethod
    def parse_case_ids(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    model_config = {"from_attributes": True}


class APITestLogResponse(BaseModel):
    """单条请求日志"""
    id: int
    case_id: int
    case_name: str
    method: str
    url: str
    headers: dict
    request_body: Optional[dict] = None
    response_status: int
    response_body: Optional[dict] = None
    response_time_ms: int
    assertions_passed: int
    assertions_failed: int
    assertion_details: List[dict] = []
    error_msg: Optional[str] = None
    executed_at: datetime