# -*- coding: utf-8 -*-
"""
AI Explore API - 探索执行接口
POST /api/v1/explore/execute  → 后台执行，立即返回 task_id
GET  /api/v1/explore/tasks/{task_id} → 查询执行结果
"""

import logging
import asyncio
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai_explore_service import AIExploreService, ExploreResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/explore", tags=["explore"])

# 探索任务内存存储（生产环境应存数据库）
explore_tasks = {}


class ExploreExecuteRequest(BaseModel):
    steps: List[str] = Field(..., description="自然语言步骤列表")
    url: str = Field(..., description="起始 URL")
    case_name: str = Field(default="探索用例", description="用例名称")
    module: str = Field(default="explore", description="模块名称")
    priority: str = Field(default="P1", description="优先级")
    headless: bool = Field(default=True, description="是否无头执行")
    auth_token: Optional[str] = Field(default=None, description="可选的 Authorization token")


class ExploreTaskResponse(BaseModel):
    task_id: str
    status: str  # pending / running / completed / failed
    message: str


class ExploreExecuteResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/execute", response_model=ExploreExecuteResponse)
async def explore_execute(
    request: ExploreExecuteRequest,
    background_tasks: BackgroundTasks,
):
    """
    探索执行（后台模式）

    立即返回 task_id，探索任务在后台执行
    通过 GET /explore/tasks/{task_id} 查询结果
    """
    task_id = f"explore_{uuid.uuid4().hex[:12]}"

    explore_tasks[task_id] = {
        "status": "pending",
        "steps": request.steps,
        "url": request.url,
        "case_name": request.case_name,
        "module": request.module,
        "priority": request.priority,
        "headless": request.headless,
        "auth_token": request.auth_token,
        "result": None,
        "error": None,
    }

    # 后台执行，不阻塞请求
    background_tasks.add_task(
        _run_explore_task,
        task_id,
        request.steps,
        request.url,
        request.case_name,
        request.module,
        request.priority,
        request.headless,
        request.auth_token,
    )

    return ExploreExecuteResponse(
        task_id=task_id,
        status="pending",
        message=f"探索任务已创建，ID: {task_id}，通过 GET /explore/tasks/{task_id} 查询结果",
    )


def _run_explore_task(
    task_id: str,
    steps: List[str],
    url: str,
    case_name: str,
    module: str,
    priority: str,
    headless: bool,
    auth_token: str,
):
    """后台探索执行任务"""
    explore_tasks[task_id]["status"] = "running"

    service = AIExploreService()

    try:
        # execute() 在独立线程中运行，不阻塞事件循环
        result: ExploreResult = service.execute(
            steps=steps,
            start_url=url,
            project_id=1,
            case_name=case_name,
            module=module,
            priority=priority,
            headless=headless,
            auth_token=auth_token,
        )

        explore_tasks[task_id]["status"] = "completed"
        explore_tasks[task_id]["result"] = result.to_dict()

    except Exception as e:
        logger.error(f"[ExploreTask {task_id}] Failed: {e}")
        explore_tasks[task_id]["status"] = "failed"
        explore_tasks[task_id]["error"] = str(e)


class ExploreStepDTO(BaseModel):
    step_no: int
    action: str
    target: str
    value: str
    status: str
    error: Optional[str] = None
    screenshot: Optional[str] = None
    duration_ms: int


class ExploreResultResponse(BaseModel):
    task_id: str
    status: str
    total_steps: int
    passed_steps: int
    failed_steps: int
    duration_ms: int
    steps: List[ExploreStepDTO]
    yaml_case: str
    discovered_locators: List[dict]
    error: Optional[str] = None


@router.get("/tasks/{task_id}", response_model=ExploreResultResponse)
def explore_get_task(task_id: str):
    """查询探索任务结果"""
    task = explore_tasks.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    status = task["status"]

    if status == "pending":
        return ExploreResultResponse(
            task_id=task_id,
            status="pending",
            total_steps=len(task["steps"]),
            passed_steps=0,
            failed_steps=0,
            duration_ms=0,
            steps=[],
            yaml_case="",
            discovered_locators=[],
            error=None,
        )

    if status == "running":
        return ExploreResultResponse(
            task_id=task_id,
            status="running",
            total_steps=len(task["steps"]),
            passed_steps=0,
            failed_steps=0,
            duration_ms=0,
            steps=[],
            yaml_case="",
            discovered_locators=[],
            error=None,
        )

    if status == "failed":
        return ExploreResultResponse(
            task_id=task_id,
            status="failed",
            total_steps=len(task["steps"]),
            passed_steps=0,
            failed_steps=len(task["steps"]),
            duration_ms=0,
            steps=[],
            yaml_case="",
            discovered_locators=[],
            error=task.get("error", "Unknown error"),
        )

    # completed
    result = task["result"]
    steps_dtos = [ExploreStepDTO(**s) for s in result.get("steps", [])]

    return ExploreResultResponse(
        task_id=task_id,
        status=result.get("status", "completed"),
        total_steps=result.get("total_steps", 0),
        passed_steps=result.get("passed_steps", 0),
        failed_steps=result.get("failed_steps", 0),
        duration_ms=result.get("duration_ms", 0),
        steps=steps_dtos,
        yaml_case=result.get("yaml_case", ""),
        discovered_locators=result.get("discovered_locators", []),
        error=None,
    )


class ExploreSaveRequest(BaseModel):
    yaml_case: str = Field(..., description="YAML 用例内容")
    project_id: int = Field(..., description="项目 ID")
    case_name: str = Field(default="", description="用例名称")
    author: str = Field(default="AI", description="作者")
    discovered_locators: List[dict] = Field(default_factory=list, description="探索执行发现的定位器")
    save_discovered_locators: bool = Field(default=True, description="是否同时保存定位器")


@router.post("/save")
def explore_save(
    request: ExploreSaveRequest,
    db: Session = Depends(get_db),
):
    """将探索生成的 YAML 用例保存到用例库"""
    import yaml
    from app.models.case import Case
    from app.models.locator import Locator
    import json

    try:
        case_data = yaml.safe_load(request.yaml_case)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {e}")

    if not case_data:
        raise HTTPException(status_code=400, detail="YAML 解析结果为空")

    case_id = case_data.get("id", "TC_EXPLORE")
    name = request.case_name or case_data.get("name", "探索用例")

    case = Case(
        name=name,
        case_id=case_id,
        project_id=request.project_id,
        module=case_data.get("module", "explore"),
        priority=case_data.get("priority", "P2"),
        tags=json.dumps(case_data.get("tags", ["explore", "ai-generated"])),
        content=request.yaml_case,
        author=request.author,
        version="1.0.0",
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    saved_locators = 0
    if request.save_discovered_locators and request.discovered_locators:
        for locator_data in request.discovered_locators:
            page_name = locator_data.get("page_name") or case_data.get("module", "explore")
            element_key = locator_data.get("element_key")
            if not element_key:
                continue

            strategies = locator_data.get("strategies") or [{
                "type": locator_data.get("selector_type", "css"),
                "value": locator_data.get("selector", ""),
                "priority": 1,
                "confidence": 0.85,
                "enabled": True,
            }]
            primary = strategies[0]

            existing = db.query(Locator).filter(
                Locator.project_id == request.project_id,
                Locator.page_name == page_name,
                Locator.element_key == element_key,
            ).first()

            if existing:
                existing.selector = locator_data.get("selector", existing.selector)
                existing.selector_type = locator_data.get("selector_type", existing.selector_type)
                existing.priority = locator_data.get("priority", existing.priority or 1)
                existing.description = locator_data.get("description", existing.description or "")
                existing.primary_type = primary.get("type", existing.primary_type or "css")
                existing.ai_confidence = str(primary.get("confidence", 0.85))
                existing.strategies_json = json.dumps(strategies, ensure_ascii=False)
            else:
                db.add(Locator(
                    project_id=request.project_id,
                    page_name=page_name,
                    element_key=element_key,
                    selector=locator_data.get("selector", ""),
                    selector_type=locator_data.get("selector_type", "css"),
                    priority=locator_data.get("priority", 1),
                    description=locator_data.get("description", ""),
                    primary_type=primary.get("type", locator_data.get("selector_type", "css")),
                    ai_confidence=str(primary.get("confidence", 0.85)),
                    strategies_json=json.dumps(strategies, ensure_ascii=False),
                    version="2.0.0",
                    updated_by=request.author,
                ))
            saved_locators += 1

        db.commit()

    return {
        "id": case.id,
        "case_id": case.case_id,
        "name": case.name,
        "status": "saved",
        "saved_locators": saved_locators,
    }
