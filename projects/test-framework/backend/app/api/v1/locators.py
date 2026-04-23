# -*- coding: utf-8 -*-
"""
Locators API - 页面元素定位符管理 API
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.locator import Locator
from app.models.project import Project
from app.schemas.locator import LocatorCreate, LocatorUpdate, LocatorResponse


router = APIRouter(prefix="/locators", tags=["Locators"])


@router.get("", response_model=List[LocatorResponse])
def list_locators(
    project_id: int = Query(..., description="项目ID"),
    page_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取项目的定位符列表"""
    q = db.query(Locator).filter(Locator.project_id == project_id)
    if page_name:
        q = q.filter(Locator.page_name == page_name)
    return q.order_by(Locator.page_name, Locator.priority).all()


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
        selector=data.selector,
        selector_type=data.selector_type,
        priority=data.priority,
        description=data.description,
    )
    db.add(locator)
    db.commit()
    db.refresh(locator)
    return locator


@router.get("/init-sample/{project_id}")
def init_sample_data(project_id: int, db: Session = Depends(get_db)):
    """
    从项目本地的 locators.json 加载示例数据到数据库
    用于新项目首次初始化
    """
    import json
    from pathlib import Path
    from app.core.config import PROJECTS_DIR

    # 获取项目信息
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 读取 locators.json
    locators_file = PROJECTS_DIR / project.name / "locators.json"
    if not locators_file.exists():
        raise HTTPException(status_code=404, detail=f"未找到 locators.json，请确认项目目录存在：{locators_file}")

    with open(locators_file, encoding='utf-8') as f:
        data = json.load(f)

    pages = data.get("pages", {})
    imported = 0
    skipped = 0

    for page_name, page_data in pages.items():
        elements = page_data.get("elements", {})
        for elem_key, elem_data in elements.items():
            # 跳过系统页面标记
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
                selector=elem_data.get("selector", ""),
                selector_type=elem_data.get("type", "css"),
                priority=elem_data.get("priority", 1),
                description=elem_data.get("description", ""),
            )
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
    return locator


@router.put("/{locator_id}", response_model=LocatorResponse)
def update_locator(locator_id: int, data: LocatorUpdate, db: Session = Depends(get_db)):
    """更新定位符"""
    locator = db.query(Locator).filter(Locator.id == locator_id).first()
    if not locator:
        raise HTTPException(status_code=404, detail="定位符不存在")

    if data.selector is not None:
        locator.selector = data.selector
    if data.selector_type is not None:
        locator.selector_type = data.selector_type
    if data.priority is not None:
        locator.priority = data.priority
    if data.description is not None:
        locator.description = data.description
    if data.updated_by is not None:
        locator.updated_by = data.updated_by

    db.commit()
    db.refresh(locator)
    return locator


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
    （兼容原有文件格式，方便迁移）
    """
    locators = db.query(Locator).filter(Locator.project_id == project_id).all()

    pages = {}
    for loc in locators:
        if loc.page_name not in pages:
            pages[loc.page_name] = {"name": loc.page_name, "elements": {}}

        pages[loc.page_name]["elements"][loc.element_key] = {
            "selector": loc.selector,
            "type": loc.selector_type,
            "priority": loc.priority,
            "description": loc.description,
        }

    return {
        "version": "1.0.0",
        "project_id": project_id,
        "pages": pages,
    }


@router.post("/import/{project_id}")
def import_locators(project_id: int, data: dict, db: Session = Depends(get_db)):
    """
    从 locators.json 格式导入定位符到数据库
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

            if existing:
                # 更新已有
                existing.selector = elem_data.get("selector", "")
                existing.selector_type = elem_data.get("type", "css")
                existing.priority = elem_data.get("priority", 1)
                existing.description = elem_data.get("description", "")
            else:
                # 新建
                locator = Locator(
                    project_id=project_id,
                    page_name=page_name,
                    element_key=elem_key,
                    selector=elem_data.get("selector", ""),
                    selector_type=elem_data.get("type", "css"),
                    priority=elem_data.get("priority", 1),
                    description=elem_data.get("description", ""),
                )
                db.add(locator)
            imported += 1

    db.commit()
    return {"message": f"导入成功，共 {imported} 个定位符"}
