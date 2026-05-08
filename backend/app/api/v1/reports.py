# -*- coding: utf-8 -*-
"""
Reports API - 报告查询 API
"""

import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.execution import Execution


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/history")
def get_report_history(
    project_id: Optional[int] = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """获取历史报告摘要列表"""
    q = db.query(Execution).filter(Execution.status.in_(["passed", "failed"]))
    if project_id:
        q = q.filter(Execution.project_id == project_id)

    records = q.order_by(Execution.id.desc()).limit(limit).all()

    return [
        {
            "execution_id": r.execution_id,
            "case_id": r.case_id,
            "project_id": r.project_id,
            "env": r.env,
            "result": r.result,
            "duration_ms": r.duration_ms,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in records
    ]


@router.get("/{execution_id}")
def get_report(execution_id: str):
    """
    获取执行报告 HTML 文件
    """
    # 报告文件存放在项目 reports 目录
    reports_dir = Path(settings.reports_dir)
    report_file = reports_dir / f"report_{execution_id}.html"

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        str(report_file),
        media_type="text/html",
        filename=f"report_{execution_id}.html",
    )
