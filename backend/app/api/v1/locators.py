# -*- coding: utf-8 -*-
"""
Locators API - 页面元素定位符管理 API
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.locator import Locator
from app.models.project import Project
from app.schemas.locator import LocatorCreate, LocatorUpdate, LocatorResponse


router = APIRouter(prefix="/locators", tags=["Locators"])


def _normalize_strategy(strategy: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    value = strategy.get("value", "")
    return {
        "type": strategy.get("type", "css") or "css",
        "value": value,
        "priority": strategy.get("priority", index + 1) or (index + 1),
        "confidence": strategy.get("confidence"),
        "enabled": strategy.get("enabled", True),
    }


def _load_strategies(locator: Locator) -> List[Dict[str, Any]]:
    raw = (locator.strategies_json or "").strip()
    if raw:
        try:
            strategies = json.loads(raw)
            if isinstance(strategies, list):
                normalized = [
                    _normalize_strategy(strategy, index)
                    for index, strategy in enumerate(strategies)
                    if isinstance(strategy, dict)
                ]
                if normalized:
                    return sorted(normalized, key=lambda item: item.get("priority", 999))
        except json.JSONDecodeError:
            pass

    return [{
        "type": locator.selector_type or "css",
        "value": locator.selector or "",
        "priority": locator.priority or 1,
        "confidence": locator.ai_confidence or None,
        "enabled": True,
    }]


def _extract_primary_fields(
    selector: str,
    selector_type: str,
    priority: int,
    strategies: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if strategies:
        primary = next((item for item in strategies if item.get("enabled", True)), strategies[0])
        primary_value = primary.get("value", "")
        return {
            "selector": primary_value if isinstance(primary_value, str) else json.dumps(primary_value, ensure_ascii=False),
            "selector_type": primary.get("type", selector_type or "css") or "css",
            "priority": primary.get("priority", priority or 1) or 1,
        }

    return {
        "selector": selector or "",
        "selector_type": selector_type or "css",
        "priority": priority or 1,
    }


def _serialize_locator(locator: Locator) -> Dict[str, Any]:
    strategies = _load_strategies(locator)
    primary_fields = _extract_primary_fields(
        locator.selector,
        locator.selector_type,
        locator.priority,
        strategies,
    )

    return {
        "id": locator.id,
        "project_id": locator.project_id,
        "page_name": locator.page_name,
        "element_key": locator.element_key,
        "selector": primary_fields["selector"],
        "selector_type": primary_fields["selector_type"],
        "priority": primary_fields["priority"],
        "description": locator.description or "",
        "primary_type": locator.primary_type or primary_fields["selector_type"],
        "strategies": strategies,
        "version": locator.version,
        "updated_by": locator.updated_by or "",
        "created_at": locator.created_at,
        "updated_at": locator.updated_at,
    }


def _apply_locator_payload(locator: Locator, payload: Dict[str, Any]):
    raw_strategies = payload.get("strategies") or []
    strategies = [
        _normalize_strategy(strategy, index)
        for index, strategy in enumerate(raw_strategies)
        if isinstance(strategy, dict)
    ]

    primary_fields = _extract_primary_fields(
        payload.get("selector", ""),
        payload.get("selector_type", "css"),
        payload.get("priority", 1),
        strategies,
    )

    locator.selector = primary_fields["selector"]
    locator.selector_type = primary_fields["selector_type"]
    locator.priority = primary_fields["priority"]
    locator.description = payload.get("description", locator.description or "")
    locator.primary_type = (
        payload.get("primary_type")
        or (strategies[0]["type"] if strategies else primary_fields["selector_type"])
        or "css"
    )
    locator.ai_confidence = "" if not strategies else str(strategies[0].get("confidence") or "")
    locator.version = "2.0.0" if strategies else locator.version or "1.0.0"
    locator.strategies_json = (
        json.dumps(strategies, ensure_ascii=False)
        if strategies
        else ""
    )


def _payload_from_element_data(elem_data: Dict[str, Any]) -> Dict[str, Any]:
    strategies = elem_data.get("strategies") or []
    if not isinstance(strategies, list):
        strategies = []

    return {
        "selector": elem_data.get("selector", ""),
        "selector_type": elem_data.get("type", "css"),
        "priority": elem_data.get("priority", 1),
        "description": elem_data.get("description", ""),
        "primary_type": elem_data.get("primary_type", ""),
        "strategies": strategies,
    }


@router.get("", response_model=List[LocatorResponse])
def list_locators(
    project_id: int = Query(..., description="项目ID"),
    page_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取项目的定位符列表"""
    query = db.query(Locator).filter(Locator.project_id == project_id)
    if page_name:
        query = query.filter(Locator.page_name == page_name)
    locators = query.order_by(Locator.page_name, Locator.priority).all()
    return [_serialize_locator(locator) for locator in locators]


@router.get("/pages/{project_id}")
def list_pages(project_id: int, db: Session = Depends(get_db)):
    """获取项目的页面列表（去重）"""
    rows = db.query(Locator.page_name).filter(
        Locator.project_id == project_id
    ).distinct().order_by(Locator.page_name).all()
    return [row[0] for row in rows]


@router.post("", response_model=LocatorResponse)
def create_locator(data: LocatorCreate, db: Session = Depends(get_db)):
    """创建定位符"""
    locator = Locator(
        project_id=data.project_id,
        page_name=data.page_name,
        element_key=data.element_key,
    )
    _apply_locator_payload(locator, data.model_dump())
    db.add(locator)
    db.commit()
    db.refresh(locator)
    return _serialize_locator(locator)


@router.get("/init-sample/{project_id}")
def init_sample_data(project_id: int, db: Session = Depends(get_db)):
    """
    从项目本地的 locators.json 加载示例数据到数据库
    用于新项目首次初始化
    """
    from app.core.config import PROJECTS_DIR

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    locators_file = PROJECTS_DIR / project.name / "locators.json"
    if not locators_file.exists():
        raise HTTPException(status_code=404, detail=f"未找到 locators.json，请确认项目目录存在：{locators_file}")

    with open(locators_file, encoding="utf-8") as file:
        data = json.load(file)

    pages = data.get("pages", {})
    imported = 0
    skipped = 0

    for page_name, page_data in pages.items():
        elements = page_data.get("elements", {})
        for elem_key, elem_data in elements.items():
            if elem_key == "__page__":
                continue

            existing = db.query(Locator).filter(
                Locator.project_id == project_id,
                Locator.page_name == page_name,
                Locator.element_key == elem_key,
            ).first()

            if existing:
                skipped += 1
                continue

            locator = Locator(
                project_id=project_id,
                page_name=page_name,
                element_key=elem_key,
            )
            _apply_locator_payload(locator, _payload_from_element_data(elem_data))
            db.add(locator)
            imported += 1

    db.commit()
    return {
        "imported": imported,
        "skipped": skipped,
        "pages": len(pages),
        "message": f"成功导入 {imported} 个元素（跳过 {skipped} 个已存在的）",
    }


@router.get("/{locator_id}", response_model=LocatorResponse)
def get_locator(locator_id: int, db: Session = Depends(get_db)):
    """获取定位符详情"""
    locator = db.query(Locator).filter(Locator.id == locator_id).first()
    if not locator:
        raise HTTPException(status_code=404, detail="定位符不存在")
    return _serialize_locator(locator)


@router.put("/{locator_id}", response_model=LocatorResponse)
def update_locator(locator_id: int, data: LocatorUpdate, db: Session = Depends(get_db)):
    """更新定位符"""
    locator = db.query(Locator).filter(Locator.id == locator_id).first()
    if not locator:
        raise HTTPException(status_code=404, detail="定位符不存在")

    payload = data.model_dump(exclude_unset=True)
    _apply_locator_payload(
        locator,
        {
            "selector": payload.get("selector", locator.selector),
            "selector_type": payload.get("selector_type", locator.selector_type),
            "priority": payload.get("priority", locator.priority),
            "description": payload.get("description", locator.description),
            "primary_type": payload.get("primary_type", locator.primary_type),
            "strategies": payload.get("strategies", _load_strategies(locator)),
        },
    )

    if data.updated_by is not None:
        locator.updated_by = data.updated_by

    db.commit()
    db.refresh(locator)
    return _serialize_locator(locator)


@router.delete("/{locator_id}")
def delete_locator(locator_id: int, db: Session = Depends(get_db)):
    """删除定位符"""
    locator = db.query(Locator).filter(Locator.id == locator_id).first()
    if not locator:
        raise HTTPException(status_code=404, detail="定位符不存在")
    db.delete(locator)
    db.commit()
    return {"message": "删除成功"}


@router.get("/export/{project_id}")
def export_locators(project_id: int, db: Session = Depends(get_db)):
    """
    导出项目的所有定位符为 locators.json 格式
    V1 导出保留旧字段，同时附带 strategies 以兼容新执行模型。
    """
    locators = db.query(Locator).filter(Locator.project_id == project_id).all()

    pages: Dict[str, Dict[str, Any]] = {}
    has_multi_strategy = False

    for loc in locators:
        serialized = _serialize_locator(loc)
        if loc.page_name not in pages:
            pages[loc.page_name] = {"name": loc.page_name, "elements": {}}

        strategies = serialized["strategies"]
        if len(strategies) > 1 or loc.strategies_json:
            has_multi_strategy = True

        pages[loc.page_name]["elements"][loc.element_key] = {
            "selector": serialized["selector"],
            "type": serialized["selector_type"],
            "priority": serialized["priority"],
            "description": serialized["description"],
            "primary_type": serialized["primary_type"],
            "strategies": strategies,
        }

    return {
        "version": "2.0.0" if has_multi_strategy else "1.0.0",
        "project_id": project_id,
        "pages": pages,
    }


@router.post("/import/{project_id}")
def import_locators(project_id: int, data: dict, db: Session = Depends(get_db)):
    """
    从 locators.json 格式导入定位符到数据库
    兼容旧格式 selector/type，也兼容新格式 strategies[]。
    """
    pages = data.get("pages", {})
    imported = 0

    for page_name, page_data in pages.items():
        elements = page_data.get("elements", {})
        for elem_key, elem_data in elements.items():
            existing = db.query(Locator).filter(
                Locator.project_id == project_id,
                Locator.page_name == page_name,
                Locator.element_key == elem_key,
            ).first()

            payload = _payload_from_element_data(elem_data)

            if existing:
                _apply_locator_payload(existing, payload)
            else:
                locator = Locator(
                    project_id=project_id,
                    page_name=page_name,
                    element_key=elem_key,
                )
                _apply_locator_payload(locator, payload)
                db.add(locator)
            imported += 1

    db.commit()
    return {"message": f"导入成功，共 {imported} 个定位符"}
