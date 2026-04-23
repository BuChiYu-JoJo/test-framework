# -*- coding: utf-8 -*-
"""
Case Schemas - 用例 API 的请求/响应模型
"""

import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CaseBase(BaseModel):
    name: str = Field(..., max_length=200)
    case_id: str = Field(..., max_length=50)  # 外部ID，如 TC001
    module: str = "default"
    priority: str = "P2"
    tags: List[str] = []


class CaseCreate(CaseBase):
    project_id: int
    content: str = Field(..., description="YAML/JSON 格式的用例内容")


class CaseUpdate(BaseModel):
    name: Optional[str] = None
    module: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    content: Optional[str] = None


class CaseResponse(CaseBase):
    id: int
    project_id: int
    content: str
    version: str
    author: str
    created_at: datetime
    updated_at: datetime

    # tags 存在数据库是 JSON 字符串，这里反序列化为 List
    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    model_config = {"from_attributes": True}
