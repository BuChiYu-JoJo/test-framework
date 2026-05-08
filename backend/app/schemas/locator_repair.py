# -*- coding: utf-8 -*-
"""
LocatorRepair Schemas - Locator 修复记录 Pydantic 模型
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


class RepairRecordCreate(BaseModel):
    project_id: int
    locator_key: str
    triggered_by: str = "ui_run"
    execution_id: Optional[str] = None
    old_strategies: Optional[List[Dict[str, Any]]] = []
    new_strategy: Optional[Dict[str, Any]] = {}
    hit_count: int = 0
    verdict: str = "miss"


class RepairRecordReview(BaseModel):
    review_user: Optional[str] = "admin"


class RepairRecordResponse(BaseModel):
    id: int
    project_id: int
    locator_key: str
    triggered_by: str
    execution_id: Optional[str]
    old_strategies: Optional[List[Dict[str, Any]]] = []
    new_strategy: Optional[Dict[str, Any]] = {}
    hit_count: int
    verdict: str
    review_status: str
    review_user: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    @field_validator("old_strategies", mode="before")
    @classmethod
    def parse_old(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    @field_validator("new_strategy", mode="before")
    @classmethod
    def parse_new(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v or {}

    model_config = {"from_attributes": True}
