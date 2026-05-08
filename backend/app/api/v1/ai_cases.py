# -*- coding: utf-8 -*-
"""
AI Cases API - AI 辅助用例生成接口
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.ai_case_generator import AICaseGeneratorService
from app.services.ai_case_orchestrator import AICaseOrchestratorService
from app.core.database import get_db
from app.models.case import Case
from app.models.locator import Locator

router = APIRouter(prefix="/ai/cases", tags=["AI Cases"])
stabilize_tasks = {}


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


# ─── PRD → Cases 批量生成 ────────────────────────────────────────────────

from app.services.ai_case_from_prd import AICaseFromPRDService, CaseFromPRDError


class PRDGenerateRequest(BaseModel):
    prd_content: str = Field(..., description="PRD Markdown 内容")
    project_id: int = Field(..., description="项目 ID")
    product_name: str = Field(default="", description="产品名称")
    author: str = Field(default="AI", description="用例作者")


class PRDGenerateResponse(BaseModel):
    total: int
    success: int
    failed: int
    cases: List[dict]
    errors: List[dict]


class DraftStep(BaseModel):
    step_no: int
    intent: str
    action_hint: str = ""
    target_hint: str = ""
    expected_hint: str = ""


class DraftCaseDTO(BaseModel):
    draft_id: str
    name: str
    module: str
    priority: str
    description: str = ""
    source_type: str = "prd_draft"
    draft_steps: List[DraftStep]


class DraftFromPRDRequest(BaseModel):
    prd_content: str = Field(..., description="需求变更单 Markdown")
    product_name: str = ""
    max_cases: int = 5


class DraftFromPRDResponse(BaseModel):
    total: int
    drafts: List[DraftCaseDTO]


class StabilizeDraftRequest(BaseModel):
    draft_case: DraftCaseDTO
    start_url: str = Field(..., description="探索执行起始页面")
    project_id: int
    headless: bool = True
    auth_token: Optional[str] = None
    login_case_id: Optional[int] = None


class StabilizeDraftResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StabilizeDraftResultResponse(BaseModel):
    task_id: str
    status: str
    draft_case: Optional[dict] = None
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    duration_ms: int = 0
    steps: List[dict] = Field(default_factory=list)
    verified_yaml: str = ""
    discovered_locators: List[dict] = Field(default_factory=list)
    auth_cache_used: bool = False
    error: Optional[str] = None


class AcceptStabilizedCaseRequest(BaseModel):
    task_id: str
    project_id: int
    author: str = "AI"
    save_discovered_locators: bool = True


class AcceptStabilizedCaseResponse(BaseModel):
    status: str
    case_id: str
    case_db_id: int
    saved_locators: int = 0


@router.post("/generate-from-prd", response_model=PRDGenerateResponse)
def generate_cases_from_prd(request: PRDGenerateRequest):
    """
    从 PRD 文档批量生成测试用例
    
    输入：PRD Markdown 内容 + 项目 ID
    输出：批量生成的用例列表（已存入数据库）
    
    流程：PRD 解析 → 功能点拆分 → AI 生成用例 YAML → 存入 cases 表
    """
    service = AICaseFromPRDService()

    try:
        result = service.generate_from_prd(
            prd_content=request.prd_content,
            project_id=request.project_id,
            product_name=request.product_name,
            author=request.author,
        )
        return result
    except CaseFromPRDError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PRD → Cases 生成失败: {str(e)}")


@router.post("/draft-from-prd", response_model=DraftFromPRDResponse)
def draft_cases_from_prd(request: DraftFromPRDRequest):
    """先将需求变更单转换成草稿用例，不直接当最终执行用例。"""
    service = AICaseOrchestratorService()
    drafts = service.build_drafts_from_prd(
        prd_content=request.prd_content,
        product_name=request.product_name,
        max_cases=request.max_cases,
    )
    return DraftFromPRDResponse(total=len(drafts), drafts=drafts)


@router.post("/draft-from-prd-file", response_model=DraftFromPRDResponse)
async def draft_cases_from_prd_file(
    product_name: str = Form(""),
    max_cases: int = Form(5),
    prd_file: UploadFile = File(...),
):
    """从上传的 Markdown PRD 文件生成草稿用例。"""
    filename = (prd_file.filename or "").lower()
    if not filename:
        raise HTTPException(status_code=400, detail="未上传 PRD 文件")
    if not filename.endswith((".md", ".markdown", ".txt")):
        raise HTTPException(status_code=400, detail="仅支持 Markdown / TXT 文件")

    content = await prd_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="PRD 文件内容为空")
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PRD 文件过大（最大 2MB）")

    try:
        try:
            prd_content = content.decode("utf-8")
        except UnicodeDecodeError:
            prd_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="PRD 文件编码无法识别，请使用 UTF-8")

    service = AICaseOrchestratorService()
    drafts = service.build_drafts_from_prd(
        prd_content=prd_content,
        product_name=product_name,
        max_cases=max_cases,
    )
    return DraftFromPRDResponse(total=len(drafts), drafts=drafts)


@router.post("/stabilize", response_model=StabilizeDraftResponse)
def stabilize_draft_case(
    request: StabilizeDraftRequest,
    background_tasks: BackgroundTasks,
):
    task_id = f"stabilize_{uuid.uuid4().hex[:12]}"
    stabilize_tasks[task_id] = {
        "status": "pending",
        "result": None,
        "error": None,
    }

    background_tasks.add_task(_run_stabilize_task, task_id, request.model_dump())

    return StabilizeDraftResponse(
        task_id=task_id,
        status="pending",
        message="草稿稳定化任务已创建",
    )


@router.get("/stabilize/{task_id}", response_model=StabilizeDraftResultResponse)
def get_stabilize_task(task_id: str):
    task = stabilize_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="稳定化任务不存在")

    if task["status"] in ("pending", "running"):
        return StabilizeDraftResultResponse(task_id=task_id, status=task["status"])

    if task["status"] == "failed":
        return StabilizeDraftResultResponse(
            task_id=task_id,
            status="failed",
            error=task.get("error") or "未知错误",
        )

    result = task.get("result") or {}
    return StabilizeDraftResultResponse(
        task_id=task_id,
        status=result.get("status", "completed"),
        draft_case=result.get("draft_case"),
        total_steps=result.get("total_steps", 0),
        passed_steps=result.get("passed_steps", 0),
        failed_steps=result.get("failed_steps", 0),
        duration_ms=result.get("duration_ms", 0),
        steps=result.get("steps", []),
        verified_yaml=result.get("verified_yaml", ""),
        discovered_locators=result.get("discovered_locators", []),
        auth_cache_used=bool(result.get("auth_cache_used")),
        error=result.get("error"),
    )


@router.post("/stabilize/accept", response_model=AcceptStabilizedCaseResponse)
def accept_stabilized_case(
    request: AcceptStabilizedCaseRequest,
    db: Session = Depends(get_db),
):
    task = stabilize_tasks.get(request.task_id)
    if not task or task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="稳定化结果不可用")

    result = task.get("result") or {}
    verified_yaml = result.get("verified_yaml", "").strip()
    if not verified_yaml:
        raise HTTPException(status_code=400, detail="缺少已验证用例内容")

    import yaml
    import json

    try:
        case_data = yaml.safe_load(verified_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"已验证用例 YAML 解析失败: {e}")

    case = Case(
        name=case_data.get("name", "AI 稳定化用例"),
        case_id=case_data.get("id", f"TC_STABLE_{uuid.uuid4().hex[:8]}"),
        project_id=request.project_id,
        module=case_data.get("module", "default"),
        priority=case_data.get("priority", "P1"),
        tags=json.dumps(case_data.get("tags", ["ai-stabilized"])),
        content=verified_yaml,
        author=request.author,
        version="1.0.0",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    saved_locators = 0
    if request.save_discovered_locators:
        for locator_data in result.get("discovered_locators", []):
            element_key = locator_data.get("element_key")
            if not element_key:
                continue
            existing = db.query(Locator).filter(
                Locator.project_id == request.project_id,
                Locator.page_name == locator_data.get("page_name", "default"),
                Locator.element_key == element_key,
            ).first()
            strategies = locator_data.get("strategies") or []
            primary = strategies[0] if strategies else {}
            if existing:
                existing.selector = locator_data.get("selector", existing.selector)
                existing.selector_type = locator_data.get("selector_type", existing.selector_type)
                existing.priority = locator_data.get("priority", existing.priority or 1)
                existing.description = locator_data.get("description", existing.description or "")
                existing.primary_type = primary.get("type", existing.primary_type or "css")
                existing.ai_confidence = str(primary.get("confidence", 0.85))
                existing.strategies_json = json.dumps(strategies, ensure_ascii=False)
                existing.updated_by = request.author
            else:
                db.add(Locator(
                    project_id=request.project_id,
                    page_name=locator_data.get("page_name", "default"),
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

    return AcceptStabilizedCaseResponse(
        status="accepted",
        case_id=case.case_id,
        case_db_id=case.id,
        saved_locators=saved_locators,
    )


@router.post("/generate-from-prd-file", response_model=PRDGenerateResponse)
async def generate_cases_from_prd_file(
    project_id: int = Form(...),
    product_name: str = Form(""),
    author: str = Form("AI"),
    prd_file: UploadFile = File(...),
):
    """
    从上传的 Markdown PRD 文件批量生成增量测试用例

    支持 `.md` / `.markdown` / `text/plain`
    """
    filename = (prd_file.filename or "").lower()
    if not filename:
        raise HTTPException(status_code=400, detail="未上传 PRD 文件")

    if not filename.endswith((".md", ".markdown", ".txt")):
        raise HTTPException(status_code=400, detail="仅支持 Markdown / TXT 文件")

    content = await prd_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="PRD 文件内容为空")

    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PRD 文件过大（最大 2MB）")

    try:
        try:
            prd_content = content.decode("utf-8")
        except UnicodeDecodeError:
            prd_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="PRD 文件编码无法识别，请使用 UTF-8")

    service = AICaseFromPRDService()

    try:
        result = service.generate_from_prd(
            prd_content=prd_content,
            project_id=project_id,
            product_name=product_name,
            author=author,
        )
        return result
    except CaseFromPRDError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PRD 文件生成失败: {str(e)}")


def _run_stabilize_task(task_id: str, payload: dict):
    import traceback
    import logging
    import sys
    import asyncio
    logger = logging.getLogger(__name__)
    stabilize_tasks[task_id]["status"] = "running"

    # Windows 上 uvicorn 启动时设置了 WindowsSelectorEventLoopPolicy（不支持 subprocess）。
    # Playwright 启动浏览器需要 ProactorEventLoop。临时切换 policy，执行完后恢复。
    saved_policy = None
    if sys.platform == "win32":
        try:
            saved_policy = asyncio.get_event_loop_policy()
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception as e:
            logger.warning(f"set ProactorEventLoopPolicy failed: {e}")

    try:
        service = AICaseOrchestratorService()
        result = service.stabilize_draft(
            draft_case=payload["draft_case"],
            start_url=payload["start_url"],
            project_id=payload["project_id"],
            headless=payload.get("headless", True),
            auth_token=payload.get("auth_token"),
            login_case_id=payload.get("login_case_id"),
        )
        stabilize_tasks[task_id]["status"] = "completed"
        stabilize_tasks[task_id]["result"] = result
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"stabilize task {task_id} failed:\n{tb}")
        stabilize_tasks[task_id]["status"] = "failed"
        stabilize_tasks[task_id]["error"] = f"{str(e)}\n{tb}"
    finally:
        if saved_policy is not None:
            try:
                asyncio.set_event_loop_policy(saved_policy)
            except Exception:
                pass


# ─── PRD 工作台：返回草稿（不直接入库） ─────────────────────────────────────

class PRDWorkbenchRequest(BaseModel):
    project_id: int
    prd_text: Optional[str] = None
    product_name: str = ""
    options: dict = {}


class CaseDraftItem(BaseModel):
    draft_id: str
    title: str
    name: str = ""
    module: str
    priority: str
    case_id: str
    content: str          # YAML 内容
    description: str = ""
    automation: bool = True
    source_test_point: dict = {}
    draft_steps: List[dict] = Field(default_factory=list)


class PRDWorkbenchResponse(BaseModel):
    task_id: str
    project_id: int
    case_drafts: List[CaseDraftItem]
    total: int
    message: str = ""


@router.post("/from-prd", response_model=PRDWorkbenchResponse)
def generate_case_drafts_from_prd(request: PRDWorkbenchRequest):
    """
    PRD 工作台：解析 PRD 文本，返回用例草稿列表（不直接入库）。

    前端展示草稿后由用户确认，通过 POST /api/v1/cases/batch 批量入库。
    """
    prd_text = request.prd_text or ""
    if not prd_text.strip():
        raise HTTPException(status_code=400, detail="prd_text 不能为空")

    service = AICaseFromPRDService()
    try:
        yaml_cases = service._generate_yaml_from_prd(prd_text, request.product_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PRD 解析失败: {str(e)}")

    import time as _time
    drafts = []
    ts = int(_time.time())
    for idx, case_data in enumerate(yaml_cases):
        case_id_str = case_data.get("id") or f"PRD_{ts}_{idx+1:03d}"
        title = case_data.get("name") or case_id_str
        module = case_data.get("module") or "default"
        priority = case_data.get("priority") or "P2"
        description = case_data.get("description") or ""
        try:
            import yaml as _yaml
            content = _yaml.dump(case_data, allow_unicode=True, default_flow_style=False)
        except Exception:
            content = str(case_data)

        raw_steps = case_data.get("steps") or []
        draft_steps = []
        for s_idx, step in enumerate(raw_steps):
            if isinstance(step, dict):
                draft_steps.append({
                    "step_no": step.get("step_no", s_idx + 1),
                    "intent": step.get("intent") or step.get("action", "") + " " + step.get("target", ""),
                    "action_hint": step.get("action") or step.get("action_hint", ""),
                    "target_hint": step.get("target") or step.get("target_hint", ""),
                    "expected_hint": step.get("expected") or step.get("expected_hint", ""),
                })
            elif isinstance(step, str):
                draft_steps.append({
                    "step_no": s_idx + 1,
                    "intent": step,
                    "action_hint": "",
                    "target_hint": "",
                    "expected_hint": "",
                })

        drafts.append(CaseDraftItem(
            draft_id=f"draft_{ts}_{idx}",
            title=title,
            name=title,
            module=module,
            priority=priority,
            case_id=case_id_str,
            content=content,
            description=description,
            automation=True,
            source_test_point={"summary": title},
            draft_steps=draft_steps,
        ))

    return PRDWorkbenchResponse(
        task_id=f"prd_{ts}",
        project_id=request.project_id,
        case_drafts=drafts,
        total=len(drafts),
        message=f"已从 PRD 解析出 {len(drafts)} 条用例草稿，请确认后入库",
    )


@router.post("/from-prd-file", response_model=PRDWorkbenchResponse)
async def generate_case_drafts_from_prd_file(
    project_id: int = Form(...),
    product_name: str = Form(""),
    prd_file: UploadFile = File(...),
):
    """PRD 工作台：上传 PRD 文件（.md/.txt），返回用例草稿。"""
    content_bytes = await prd_file.read()
    if len(content_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PRD 文件过大（最大 2MB）")
    try:
        prd_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        prd_text = content_bytes.decode("utf-8-sig", errors="replace")

    return generate_case_drafts_from_prd(
        PRDWorkbenchRequest(
            project_id=project_id,
            prd_text=prd_text,
            product_name=product_name,
        )
    )
