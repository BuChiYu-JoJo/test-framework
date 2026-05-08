# -*- coding: utf-8 -*-
"""
Project Schemas - 项目 API 的请求/响应模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = ""


class ProjectCreate(ProjectBase):
    env_config: Optional[dict] = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    env_config: Optional[dict] = None


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    env_config: dict = Field(default={})

    @field_validator('env_config', mode='before')
    def parse_env_config(cls, v):
        import json as _json
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return {}
        return v or {}

    class Config:
        from_attributes = True
