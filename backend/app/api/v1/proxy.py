# -*- coding: utf-8 -*-
"""
Proxy API - 代理管理 API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.proxy import Proxy, ProxyGroup, ProxyAlertRule
from app.schemas.proxy import (
    ProxyCreate, ProxyUpdate, ProxyResponse,
    ProxyGroupCreate, ProxyGroupResponse,
    ProxyAlertRuleCreate, ProxyAlertRuleResponse,
    ProxyStatsResponse, ProxyBatchAdd,
)
from app.services import proxy_service


router = APIRouter(prefix="/proxy", tags=["代理管理"])


# ─── 代理节点 ─────────────────────────────────────────────

@router.get("/list", response_model=List[ProxyResponse])
def list_proxies(
    group_id: Optional[int] = None,
    status: Optional[str] = None,
    protocol: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取代理列表"""
    q = db.query(Proxy)
    if group_id is not None:
        q = q.filter(Proxy.group_id == group_id)
    if status:
        q = q.filter(Proxy.status == status)
    if protocol:
        q = q.filter(Proxy.protocol == protocol)
    return q.order_by(Proxy.id.desc()).all()


@router.post("/add", response_model=dict)
def add_proxy(data: ProxyCreate, db: Session = Depends(get_db)):
    """添加单个代理"""
    proxy = Proxy(**data.model_dump())
    db.add(proxy)
    db.flush()
    db.commit()
    return {"id": proxy.id, "name": proxy.name}


@router.post("/batch", response_model=dict)
def batch_add_proxies(data: ProxyBatchAdd, db: Session = Depends(get_db)):
    """批量导入代理"""
    result = proxy_service.batch_import_proxies(db, data.proxies)
    return result


@router.put("/{proxy_id}", response_model=dict)
def update_proxy(proxy_id: int, data: ProxyUpdate, db: Session = Depends(get_db)):
    """更新代理信息"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(proxy, k, v)
    db.commit()
    return {"message": "updated"}


@router.delete("/{proxy_id}", response_model=dict)
def delete_proxy(proxy_id: int, db: Session = Depends(get_db)):
    """删除代理"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    db.delete(proxy)
    db.commit()
    return {"message": "deleted"}


@router.get("/{proxy_id}/stats")
def get_proxy_stats(proxy_id: int, db: Session = Depends(get_db)):
    """获取单个代理统计"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {
        "id": proxy.id,
        "name": proxy.name,
        "success_rate": proxy.success_rate,
        "avg_latency_ms": proxy.avg_latency_ms,
        "use_count": proxy.use_count,
        "check_count": proxy.check_count,
        "fail_count": proxy.fail_count,
        "last_check_at": proxy.last_check_at,
        "last_used_at": proxy.last_used_at,
        "status": proxy.status,
    }


@router.post("/{proxy_id}/test", response_model=dict)
def test_proxy(proxy_id: int, db: Session = Depends(get_db)):
    """手动触发单个代理健康检查"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    result = proxy_service._check_proxy_health(
        proxy.host, proxy.port, proxy.protocol, proxy.username, proxy.password
    )
    proxy.avg_latency_ms = result["latency_ms"]
    proxy.check_count += 1
    if not result["available"]:
        proxy.fail_count += 1
    proxy.success_rate = round(
        (proxy.check_count - proxy.fail_count) / max(proxy.check_count, 1) * 100, 1
    )
    proxy.last_check_at = __import__("datetime").datetime.now()
    proxy.status = "active" if result["available"] else "inactive"
    db.commit()

    return {"available": result["available"], "latency_ms": result["latency_ms"], "error": result["error"]}


@router.get("/available", response_model=Optional[ProxyResponse])
def get_available_proxy(
    group_id: Optional[int] = None,
    protocol: Optional[str] = None,
    strategy: str = "round_robin",
    db: Session = Depends(get_db),
):
    """按策略获取一个可用代理"""
    proxy = proxy_service.get_available_proxy(db, group_id, protocol, strategy)
    if not proxy:
        raise HTTPException(status_code=404, detail="No available proxy")
    return proxy


@router.post("/refresh", response_model=dict)
def refresh_all_proxies(db: Session = Depends(get_db)):
    """刷新所有代理健康状态"""
    proxy_service._check_all_proxies_async()
    return {"message": "health check started"}


@router.get("/stats", response_model=ProxyStatsResponse)
def get_proxy_stats_summary(db: Session = Depends(get_db)):
    """获取代理统计汇总"""
    proxies = db.query(Proxy).all()
    if not proxies:
        return ProxyStatsResponse(total=0, active=0, inactive=0, unknown=0, avg_success_rate=0, avg_latency_ms=0)
    total = len(proxies)
    active = sum(1 for p in proxies if p.status == "active")
    inactive = sum(1 for p in proxies if p.status == "inactive")
    unknown = sum(1 for p in proxies if p.status == "unknown")
    avg_rate = round(sum(p.success_rate for p in proxies) / total, 1)
    avg_lat = round(sum(p.avg_latency_ms for p in proxies if p.avg_latency_ms > 0) / max(sum(1 for p in proxies if p.avg_latency_ms > 0), 1), 1)
    return ProxyStatsResponse(
        total=total, active=active, inactive=inactive, unknown=unknown,
        avg_success_rate=avg_rate, avg_latency_ms=avg_lat
    )


# ─── 代理分组 ─────────────────────────────────────────────

@router.get("/groups", response_model=List[ProxyGroupResponse])
def list_groups(db: Session = Depends(get_db)):
    return db.query(ProxyGroup).order_by(ProxyGroup.id.desc()).all()


@router.post("/groups", response_model=dict)
def create_group(data: ProxyGroupCreate, db: Session = Depends(get_db)):
    group = ProxyGroup(**data.model_dump())
    db.add(group)
    db.commit()
    return {"id": group.id, "name": group.name}


@router.delete("/groups/{group_id}", response_model=dict)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(ProxyGroup).filter(ProxyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"message": "deleted"}


# ─── 告警规则 ─────────────────────────────────────────────

@router.get("/alert/rules", response_model=List[ProxyAlertRuleResponse])
def list_alert_rules(db: Session = Depends(get_db)):
    return db.query(ProxyAlertRule).order_by(ProxyAlertRule.id.desc()).all()


@router.post("/alert/rules", response_model=dict)
def create_alert_rule(data: ProxyAlertRuleCreate, db: Session = Depends(get_db)):
    rule = ProxyAlertRule(**data.model_dump())
    db.add(rule)
    db.flush()
    db.commit()
    return {"id": rule.id}


@router.delete("/alert/rules/{rule_id}", response_model=dict)
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(ProxyAlertRule).filter(ProxyAlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "deleted"}
