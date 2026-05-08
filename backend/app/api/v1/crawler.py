# -*- coding: utf-8 -*-
"""
Crawler API - 爬虫巡检 API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.crawler import CrawlerConfig, CrawlerInspection
from app.schemas.crawler import (
    CrawlerConfigCreate, CrawlerConfigUpdate, CrawlerConfigResponse,
    CrawlerInspectionResponse, CrawlerStatsResponse,
)
from app.services.crawler_service import run_crawler_inspection


router = APIRouter(prefix="/crawler", tags=["爬虫巡检"])


# ─── 爬虫配置 ─────────────────────────────────────────────

@router.get("/configs", response_model=List[CrawlerConfigResponse])
def list_configs(
    project_id: Optional[int] = None,
    status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = db.query(CrawlerConfig)
    if project_id is not None:
        q = q.filter(CrawlerConfig.project_id == project_id)
    if status:
        q = q.filter(CrawlerConfig.last_status == status)
    return q.order_by(CrawlerConfig.id.desc()).all()


@router.post("/configs", response_model=dict)
def create_config(data: CrawlerConfigCreate, db: Session = Depends(get_db)):
    cfg = CrawlerConfig(**data.model_dump())
    db.add(cfg)
    db.flush()
    db.commit()
    return {"id": cfg.id, "name": cfg.name}


@router.get("/configs/{cfg_id}", response_model=CrawlerConfigResponse)
def get_config(cfg_id: int, db: Session = Depends(get_db)):
    cfg = db.query(CrawlerConfig).filter(CrawlerConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return cfg


@router.put("/configs/{cfg_id}", response_model=dict)
def update_config(cfg_id: int, data: CrawlerConfigUpdate, db: Session = Depends(get_db)):
    cfg = db.query(CrawlerConfig).filter(CrawlerConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)
    db.commit()
    return {"message": "updated"}


@router.delete("/configs/{cfg_id}", response_model=dict)
def delete_config(cfg_id: int, db: Session = Depends(get_db)):
    cfg = db.query(CrawlerConfig).filter(CrawlerConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.query(CrawlerInspection).filter(CrawlerInspection.crawler_id == cfg_id).delete()
    db.delete(cfg)
    db.commit()
    return {"message": "deleted"}


# ─── 巡检记录 ─────────────────────────────────────────────

@router.get("/inspections", response_model=List[CrawlerInspectionResponse])
def list_inspections(
    crawler_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(CrawlerInspection)
    if crawler_id is not None:
        q = q.filter(CrawlerInspection.crawler_id == crawler_id)
    if status:
        q = q.filter(CrawlerInspection.status == status)
    return q.order_by(CrawlerInspection.id.desc()).limit(100).all()


@router.get("/inspections/{insp_id}", response_model=CrawlerInspectionResponse)
def get_inspection(insp_id: int, db: Session = Depends(get_db)):
    insp = db.query(CrawlerInspection).filter(CrawlerInspection.id == insp_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return insp


@router.post("/configs/{cfg_id}/run", response_model=dict)
def run_config_now(cfg_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    cfg = db.query(CrawlerConfig).filter(CrawlerConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    background_tasks.add_task(run_crawler_inspection, cfg_id, None)
    return {"message": f"crawler {cfg_id} inspection started"}


# ─── 统计 ─────────────────────────────────────────────

@router.get("/stats", response_model=CrawlerStatsResponse)
def get_crawler_stats(db: Session = Depends(get_db)):
    configs = db.query(CrawlerConfig).all()
    if not configs:
        return CrawlerStatsResponse(total=0, enabled=0, passed=0, warning=0, failed=0, unknown=0, avg_success_rate=0)

    total = len(configs)
    enabled = sum(1 for c in configs if c.enabled)
    passed = sum(1 for c in configs if c.last_status == "passed")
    warning = sum(1 for c in configs if c.last_status == "warning")
    failed = sum(1 for c in configs if c.last_status == "failed")
    unknown = sum(1 for c in configs if c.last_status in ("unknown", None))

    inspections = db.query(CrawlerInspection).order_by(CrawlerInspection.id.desc()).limit(total).all()
    if inspections:
        total_items = sum(i.items_count for i in inspections if i.items_count > 0)
        total_errors = sum(i.error_count for i in inspections)
        avg_rate = round(total_items / max(total_items + total_errors, 1) * 100, 1)
    else:
        avg_rate = 0.0

    return CrawlerStatsResponse(
        total=total, enabled=enabled, passed=passed, warning=warning,
        failed=failed, unknown=unknown, avg_success_rate=avg_rate,
    )
