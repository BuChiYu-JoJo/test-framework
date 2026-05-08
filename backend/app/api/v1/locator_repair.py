# -*- coding: utf-8 -*-
"""
LocatorRepair API - Locator 修复记录管理
提供修复记录的查询、审核（接受/拒绝/回滚）接口
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.locator_repair_record import LocatorRepairRecord
from app.schemas.locator_repair import (
    RepairRecordCreate,
    RepairRecordReview,
    RepairRecordResponse,
)

router = APIRouter(prefix="/locator-repair", tags=["LocatorRepair"])


@router.get("/records", response_model=List[RepairRecordResponse])
def list_repair_records(
    project_id: Optional[int] = Query(None),
    locator_key: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取修复记录列表"""
    q = db.query(LocatorRepairRecord)
    if project_id:
        q = q.filter(LocatorRepairRecord.project_id == project_id)
    if locator_key:
        q = q.filter(LocatorRepairRecord.locator_key.ilike(f"%{locator_key}%"))
    if review_status:
        q = q.filter(LocatorRepairRecord.review_status == review_status)
    if verdict:
        q = q.filter(LocatorRepairRecord.verdict == verdict)

    records = q.order_by(LocatorRepairRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    return records


@router.post("/records", response_model=RepairRecordResponse)
def create_repair_record(data: RepairRecordCreate, db: Session = Depends(get_db)):
    """写入修复记录（由 engine 回调调用）"""
    record = LocatorRepairRecord(
        project_id=data.project_id,
        locator_key=data.locator_key,
        triggered_by=data.triggered_by,
        execution_id=data.execution_id,
        old_strategies=json.dumps(data.old_strategies or [], ensure_ascii=False),
        new_strategy=json.dumps(data.new_strategy or {}, ensure_ascii=False),
        hit_count=data.hit_count,
        verdict=data.verdict,
        review_status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/records/pending-count")
def pending_count(project_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """待审核修复记录数（用于前端头部徽标）"""
    q = db.query(LocatorRepairRecord).filter(
        LocatorRepairRecord.review_status == "pending"
    )
    if project_id:
        q = q.filter(LocatorRepairRecord.project_id == project_id)
    return {"code": 0, "data": {"count": q.count()}}


@router.post("/records/{record_id}/accept")
def accept_record(record_id: int, body: RepairRecordReview, db: Session = Depends(get_db)):
    """接受修复记录（策略写入 DB locators）"""
    record = _get_record(record_id, db)
    record.review_status = "accepted"
    record.review_user = body.review_user
    record.reviewed_at = datetime.now()
    db.commit()

    # 将新策略持久化到 locators 表
    _apply_strategy_to_db(record, db)
    return {"code": 0, "msg": "已接受"}


@router.post("/records/{record_id}/reject")
def reject_record(record_id: int, body: RepairRecordReview, db: Session = Depends(get_db)):
    """拒绝修复记录"""
    record = _get_record(record_id, db)
    record.review_status = "rejected"
    record.review_user = body.review_user
    record.reviewed_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已拒绝"}


@router.post("/records/{record_id}/rollback")
def rollback_record(record_id: int, body: RepairRecordReview, db: Session = Depends(get_db)):
    """回滚修复：将 locator 策略恢复到修复前的旧版本"""
    record = _get_record(record_id, db)

    old_strategies = _parse_json(record.old_strategies, [])
    if old_strategies:
        _restore_strategies_to_db(record, old_strategies, db)

    record.review_status = "rolled_back"
    record.review_user = body.review_user
    record.reviewed_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已回滚"}


# ─── 内部工具 ─────────────────────────────────────────────────────

def _get_record(record_id: int, db: Session) -> LocatorRepairRecord:
    record = db.query(LocatorRepairRecord).filter(
        LocatorRepairRecord.id == record_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="修复记录不存在")
    return record


def _parse_json(value: Optional[str], default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _apply_strategy_to_db(record: LocatorRepairRecord, db: Session):
    """将 AI 新策略以 priority=0 写入 locators 表的 strategies_json。"""
    from app.models.locator import Locator

    new_strategy = _parse_json(record.new_strategy, {})
    if not new_strategy.get("selector") and not new_strategy.get("value"):
        return

    _update_locator_strategies(record.project_id, record.locator_key, new_strategy, db)


def _restore_strategies_to_db(record: LocatorRepairRecord, old_strategies: list, db: Session):
    """回滚：用旧 strategies 覆盖 locators 表中对应条目。"""
    from app.models.locator import Locator

    if not record.locator_key or "." not in record.locator_key:
        return

    page_name, element_key = record.locator_key.split(".", 1)
    locator = db.query(Locator).filter(
        Locator.project_id == record.project_id,
        Locator.page_name == page_name,
        Locator.element_key == element_key,
    ).first()

    if locator:
        locator.strategies_json = json.dumps(old_strategies, ensure_ascii=False)
        db.commit()


def _update_locator_strategies(project_id: int, locator_key: str, new_strategy: dict, db: Session):
    """在 locators 表中，为 locator_key 插入新的自愈策略（priority=0）。"""
    from app.models.locator import Locator

    if "." not in locator_key:
        return

    page_name, element_key = locator_key.split(".", 1)
    locator = db.query(Locator).filter(
        Locator.project_id == project_id,
        Locator.page_name == page_name,
        Locator.element_key == element_key,
    ).first()

    if not locator:
        return

    strategies = _parse_json(locator.strategies_json, [])
    # 移除旧的 ai_healed 条目
    strategies = [s for s in strategies if s.get("source") != "ai_healed"]

    healed = {
        "type": new_strategy.get("selector_type") or new_strategy.get("type") or "css",
        "value": new_strategy.get("selector") or new_strategy.get("value") or "",
        "priority": 0,
        "enabled": True,
        "confidence": new_strategy.get("confidence", 0.9),
        "source": "ai_healed",
        "reason": new_strategy.get("reason", ""),
    }
    strategies.insert(0, healed)
    locator.strategies_json = json.dumps(strategies, ensure_ascii=False)
    locator.last_healed_at = datetime.now()
    db.commit()
