# -*- coding: utf-8 -*-
"""
AI Locators API - AI 生成定位符接口
"""

import sys
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case

# 确保 engine 目录在 path 中
_engine_path = Path(__file__).parent.parent.parent.parent.parent / "engine"
if str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))

from app.services.ai_locator import AILocatorService

router = APIRouter(prefix="/ai/locators", tags=["AI Locators"])


class LocatorGenerateRequest(BaseModel):
    url: str = Field(..., description="页面 URL")
    page_name: str = Field(default="", description="页面名称，用于 key 前缀")
    intent: str = Field(default="", description="目标意图，如：账密登录、验证码登录")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)


class LocatorEnhanceRequest(BaseModel):
    url: str = Field(..., description="页面 URL")
    page_name: str = Field(default="", description="页面名称")
    existing_locators: dict = Field(default={}, description="已有的 locators 字典")


class LocatorResponse(BaseModel):
    locators: dict
    page_identifier: str
    raw_ai_response: Optional[str] = None
    page_url: Optional[str] = None
    login_used: Optional[bool] = None
    auth_cache_used: Optional[bool] = None


def _build_playwright_client(viewport: dict):
    """创建 Playwright 客户端用于截图"""
    import sys
    from pathlib import Path
    # api/v1 → api → app → backend → test-framework/
    engine_path = Path(__file__).parent.parent.parent.parent.parent / "engine"
    if str(engine_path) not in sys.path:
        sys.path.insert(0, str(engine_path))
    from playwright_client import PlaywrightClient
    client = PlaywrightClient(
        base_url="http://example.com",
        headless=True,
        viewport=viewport,
        timeout=30000,
    )
    client.launch()
    return client


@router.post("/generate", response_model=LocatorResponse)
def generate_locators(request: LocatorGenerateRequest):
    """
    从 URL 生成 AI locators

    输入页面 URL，返回结构化的定位符 JSON
    """
    viewport = {"width": request.viewport_width, "height": request.viewport_height}
    playwright_client = _build_playwright_client(viewport)

    try:
        service = AILocatorService(playwright_client=playwright_client)
        result = service.generate_from_url(
            url=request.url,
            page_name=request.page_name,
            viewport=viewport,
            intent=request.intent,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI locator generation failed: {str(e)}")
    finally:
        playwright_client.close()


@router.post("/enhance", response_model=LocatorResponse)
def enhance_locators(request: LocatorEnhanceRequest):
    """
    补全已有 locators

    输入已有 locators + URL，AI 补全缺失的元素
    """
    viewport = {"width": 1920, "height": 1080}
    playwright_client = _build_playwright_client(viewport)

    try:
        service = AILocatorService(playwright_client=playwright_client)
        result = service.enhance_locators(
            existing_locators=request.existing_locators,
            url=request.url,
            page_name=request.page_name,
        )
        return {
            "locators": result,
            "page_identifier": request.page_name or request.url,
            "raw_ai_response": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI locator enhance failed: {str(e)}")
    finally:
        playwright_client.close()


# ─── 新增：带登录的 Locator 生成 ───────────────────────────────────────

class LocatorGenerateWithAuthRequest(BaseModel):
    target_url: str = Field(..., description="目标页面 URL（需登录后访问）")
    page_name: str = Field(default="", description="页面名称，用于 key 前缀")
    login_case_id: int = Field(default=None, description="登录用例 ID（将执行此用例完成登录）")
    project_id: int = Field(default=None, description="项目 ID（用于读取项目配置和 locators）")
    intent: str = Field(default="", description="目标意图，如：点击订单详情")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)


@router.post("/generate-with-auth", response_model=LocatorResponse)
def generate_locators_with_auth(request: LocatorGenerateWithAuthRequest):
    """
    带登录态生成 locators

    流程：
      1. 执行 login_case_id 完成登录（使用项目已有 locators）
      2. 保持登录态访问 target_url
      3. AI 分析页面结构，生成 locator 候选
    """
    viewport = {"width": request.viewport_width, "height": request.viewport_height}
    playwright_client = _build_playwright_client(viewport)

    try:
        service = AILocatorService(playwright_client=playwright_client)
        result = service.generate_with_auth(
            target_url=request.target_url,
            page_name=request.page_name,
            login_case_id=request.login_case_id,
            project_id=request.project_id,
            viewport=viewport,
            intent=request.intent,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI locator generate failed: {str(e)}")
    finally:
        playwright_client.close()


@router.get("/login-cases")
def list_login_cases(project_id: int, db: Session = Depends(get_db)):
    """
    获取项目下适合做登录的用例列表（供用户选择登录用例）
    """
    cases = db.query(Case).filter(
        Case.project_id == project_id,
        Case.name.like("%登录%"),
    ).limit(10).all()

    all_cases = db.query(Case).filter(
        Case.project_id == project_id,
    ).limit(20).all()

    return [
        {"id": c.id, "name": c.name, "module": c.module or ""}
        for c in (cases + all_cases)
    ]
