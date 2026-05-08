# -*- coding: utf-8 -*-
"""
AI Regression API - 智能回归选择接口
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai_regression import AIRegressionService

router = APIRouter(prefix="/ai/regression", tags=["AI Regression"])


class RegressionSelectRequest(BaseModel):
    changed_files: List[str] = Field(..., description="变更文件路径列表")
    project_id: int = Field(..., description="项目 ID")


class SelectedCase(BaseModel):
    id: int
    case_id: str
    name: str = ""
    module: str = ""
    priority: str = ""
    risk_score: float = Field(default=0.5, description="AI 评估的风险评分 0-1")


class RegressionSelectResponse(BaseModel):
    selected_cases: List[SelectedCase]
    reason: str = ""
    impact_modules: List[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"


@router.post("/select", response_model=RegressionSelectResponse)
def select_regression_cases(
    request: RegressionSelectRequest,
    db: Session = Depends(get_db),
):
    """
    智能回归选择
    
    输入变更文件列表 + 项目 ID，返回需要回归的用例列表及风险评分
    """
    if not request.changed_files:
        raise HTTPException(status_code=400, detail="changed_files cannot be empty")

    service = AIRegressionService()

    try:
        result = service.select_regression_cases(
            changed_files=request.changed_files,
            project_id=request.project_id,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI regression selection failed: {str(e)}")
