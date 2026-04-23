# -*- coding: utf-8 -*-
"""
Cases API - 用例管理 API
"""

import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import PROJECTS_DIR
from app.models.case import Case
from app.models.project import Project
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse


router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("", response_model=List[CaseResponse])
def list_cases(
    project_id: Optional[int] = Query(None),
    module: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="搜索用例名称或用例ID"),
    db: Session = Depends(get_db),
):
    """获取用例列表（支持按项目/模块/优先级/关键词筛选）"""
    q = db.query(Case)
    if project_id:
        q = q.filter(Case.project_id == project_id)
    if module:
        q = q.filter(Case.module == module)
    if priority:
        q = q.filter(Case.priority == priority)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            (Case.name.ilike(kw)) | (Case.case_id.ilike(kw))
        )
    return q.order_by(Case.id.desc()).all()


@router.post("", response_model=CaseResponse)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    """创建用例"""
    # 检查项目是否存在
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查 case_id 是否重复
    existing = db.query(Case).filter(
        Case.project_id == data.project_id,
        Case.case_id == data.case_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="用例ID已存在")

    case = Case(
        name=data.name,
        case_id=data.case_id,
        project_id=data.project_id,
        module=data.module,
        priority=data.priority,
        tags=json.dumps(data.tags),
        content=data.content,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case




@router.get("/template/download")
def download_excel_template():
    """
    下载 Excel 用例模板
    """
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from app.core.config import PROJECTS_DIR

    template_path = PROJECTS_DIR / "dataify" / "cases" / "excel" / "用例模板_v1.0.xlsx"

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="模板文件不存在")

    return FileResponse(
        str(template_path),
        filename="用例模板_v1.0.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db)):
    """获取用例详情"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return case


@router.put("/{case_id}", response_model=CaseResponse)
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    """更新用例"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    if data.name is not None:
        case.name = data.name
    if data.module is not None:
        case.module = data.module
    if data.priority is not None:
        case.priority = data.priority
    if data.tags is not None:
        case.tags = json.dumps(data.tags)
    if data.content is not None:
        case.content = data.content

    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """删除用例"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    db.delete(case)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{case_id}/duplicate", response_model=CaseResponse)
def duplicate_case(case_id: int, db: Session = Depends(get_db)):
    """复制用例"""
    original = db.query(Case).filter(Case.id == case_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="用例不存在")

    # 生成新 case_id
    base = original.case_id
    counter = 1
    while db.query(Case).filter(Case.case_id == f"{base}_copy{counter}").first():
        counter += 1
    new_case_id = f"{base}_copy{counter}"

    new_case = Case(
        name=f"{original.name} (副本)",
        case_id=new_case_id,
        project_id=original.project_id,
        module=original.module,
        priority=original.priority,
        tags=original.tags,
        content=original.content,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case


@router.post("/import")
def import_cases(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    批量导入用例（Excel 文件）

    支持 .xlsx / .xls 文件
    - 相同用例ID的多行组成一个用例
    - 支持 [setup] / [teardown] 备注标记
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "engine"))
    from parser.excel_parser import ExcelParser

    if not file.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 格式")

    # 保存上传文件到临时目录
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parser = ExcelParser()
        cases_data = parser.parse(tmp_path)  # 返回 List[Dict]

        imported = 0
        updated = 0
        skipped = 0
        results = []

        for wb_data in cases_data:
            case_name = wb_data.get("name") or "未命名"
            case_id = wb_data.get("id") or f"AUTO_{imported + 1}"
            module = wb_data.get("module", "default")
            priority = wb_data.get("priority", "P2")

            # 构建 YAML content
            yaml_lines = [
                f"id: {case_id}",
                f"name: {case_name}",
                f"module: {module}",
                f"priority: {priority}",
                "steps:",
            ]
            for step in wb_data.get("steps", []):
                yaml_lines.append(f"  - no: {step.get('no', '')}")
                yaml_lines.append(f"    action: {step.get('action', '')}")
                if step.get("target"):
                    yaml_lines.append(f"    target: {step.get('target', '')}")
                if step.get("value"):
                    yaml_lines.append(f"    value: {step.get('value', '')}")
                if step.get("description"):
                    yaml_lines.append(f"    description: {step.get('description', '')}")

            yaml_content = "\n".join(yaml_lines)

            # 检查是否已存在同名 case_id
            existing = db.query(Case).filter(
                Case.project_id == project_id,
                Case.case_id == case_id,
            ).first()

            if existing:
                existing.name = case_name
                existing.content = yaml_content
                existing.module = module
                existing.priority = priority
                db.commit()
                updated += 1
                results.append(f"用例 {case_id} 已存在，已更新")
            else:
                new_case = Case(
                    name=case_name,
                    case_id=case_id,
                    project_id=project_id,
                    module=module,
                    priority=priority,
                    tags="[]",
                    content=yaml_content,
                )
                db.add(new_case)
                db.commit()
                imported += 1
                results.append(f"用例 {case_id} 导入成功")

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": imported + updated,
            "results": results,
        }

    finally:
        Path(tmp_path).unlink(missing_ok=True)



