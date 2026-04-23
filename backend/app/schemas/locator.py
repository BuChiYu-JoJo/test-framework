# -*- coding: utf-8 -*-
"""
Locator Schemas - 页面元素定位符 API 模型
"""

from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, Field


class LocatorStrategy(BaseModel):
    type: str = "css"
    value: Any = ""
    priority: int = 1
    confidence: Optional[Any] = None
    enabled: bool = True


class LocatorBase(BaseModel):
    page_name: str = Field(..., max_length=100)
    element_key: str = Field(..., max_length=100)
    selector: str = ""
    selector_type: str = "css"
    priority: int = 1
    description: str = ""
    primary_type: str = ""
    strategies: List[LocatorStrategy] = Field(default_factory=list)


class LocatorCreate(LocatorBase):
    project_id: int


class LocatorUpdate(BaseModel):
    selector: Optional[str] = None
    selector_type: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    primary_type: Optional[str] = None
    strategies: Optional[List[LocatorStrategy]] = None
    updated_by: Optional[str] = None


class LocatorResponse(LocatorBase):
    id: int
    project_id: int
    version: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
