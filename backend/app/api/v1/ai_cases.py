# -*- coding: utf-8 -*-
"""
AI Cases API - AI 辅助用例生成接口
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.services.ai_case_generator import AICaseGeneratorService

router = APIRouter(prefix="/ai/cases", tags=["AI Cases"])


class CaseGenerateRequest(BaseModel):
    description: str = Field(..., description="自然语言需求描述")
    module: str = Field(default="default", description="所属模块")
    priority: str = Field(default="P2", description="优先级 P0/P1/P2/P3")


class CaseResponse(BaseModel):
    yaml_content: str
    case_id: str
    raw_ai_response: str = ""


@router.post("/generate", response_model=CaseResponse)
def generate_case(request: CaseGenerateRequest):
    """
    根据自然语言描述生成测试用例 YAML
    
    输入：description（需求描述）、module（模块）、priority（优先级）
    输出：yaml_content（YAML 内容）、case_id
    """
    service = AICaseGeneratorService()

    try:
        result = service.generate_from_description(
            description=request.description,
            module=request.module,
            priority=request.priority,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI case generation failed: {str(e)}")


@router.post("/generate-with-screenshot", response_model=CaseResponse)
async def generate_case_with_screenshot(
    description: str = Form(...),
    module: str = Form("default"),
    priority: str = Form("P2"),
    screenshot: UploadFile = File(...),
):
    """
    根据描述 + 页面截图生成测试用例
    
    截图将作为 Vision API 的输入，帮助 AI 更准确地生成元素定位步骤
    """
    import tempfile
    from pathlib import Path

    service = AICaseGeneratorService()

    # 读取上传的截图
    contents = await screenshot.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Screenshot too large (max 10MB)")

    try:
        result = service.generate_from_description(
            description=description,
            module=module,
            priority=priority,
            screenshot=contents,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI case generation failed: {str(e)}")
