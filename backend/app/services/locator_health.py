# -*- coding: utf-8 -*-
"""
LocatorHealth - Locator 健康度评分服务
基于命中统计计算每个 locator 的健康颜色（红/黄/绿）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 颜色阈值
RED_FALLBACK_RATE = 0.3     # fallback 率 >= 30% → 红
YELLOW_FALLBACK_RATE = 0.1  # 10% <= fallback 率 < 30% → 黄


def calculate_health_color(
    all_hits: int,
    fallback_hits: int,
    last_24h_hits: int,
    has_history: bool = True,
) -> str:
    """
    计算 locator 健康颜色。

    红：fallback_rate >= 0.3 或（24h 命中 0 且历史曾被命中）
    黄：0.1 <= fallback_rate < 0.3
    绿：fallback_rate < 0.1
    """
    if all_hits == 0:
        return "grey"

    fallback_rate = fallback_hits / all_hits

    if fallback_rate >= RED_FALLBACK_RATE:
        return "red"
    if last_24h_hits == 0 and has_history:
        return "red"
    if fallback_rate >= YELLOW_FALLBACK_RATE:
        return "yellow"
    return "green"


def compute_project_locator_health(project_id: int) -> Dict[str, dict]:
    """
    计算项目下所有 locator 最近 7 天的健康度。
    返回 {locator_key: {color, fallback_rate, total_hits, last_24h_hits}}
    """
    from app.core.database import SessionLocal
    from app.models.locator_hit_stats import LocatorHitStats

    seven_days_ago = datetime.now() - timedelta(days=7)
    one_day_ago = datetime.now() - timedelta(hours=24)

    with SessionLocal() as db:
        stats = (
            db.query(LocatorHitStats)
            .filter(
                LocatorHitStats.project_id == project_id,
                LocatorHitStats.last_hit_at >= seven_days_ago,
            )
            .all()
        )

    result = {}
    for row in stats:
        key = row.locator_key
        if key not in result:
            result[key] = {
                "total_hits": 0,
                "fallback_hits": 0,
                "last_24h_hits": 0,
            }
        result[key]["total_hits"] += row.hit_count
        if row.fallback_depth > 0:
            result[key]["fallback_hits"] += row.hit_count
        if row.last_hit_at >= one_day_ago:
            result[key]["last_24h_hits"] += row.hit_count

    for key, data in result.items():
        data["fallback_rate"] = round(
            data["fallback_hits"] / data["total_hits"], 3
        ) if data["total_hits"] > 0 else 0
        data["color"] = calculate_health_color(
            all_hits=data["total_hits"],
            fallback_hits=data["fallback_hits"],
            last_24h_hits=data["last_24h_hits"],
            has_history=data["total_hits"] > 0,
        )

    return result


def update_locator_health_colors(project_id: int) -> int:
    """
    批量更新 locators 表的 health_color 字段。
    返回更新行数。
    """
    from app.core.database import SessionLocal
    from app.models.locator import Locator

    health_map = compute_project_locator_health(project_id)
    if not health_map:
        return 0

    updated = 0
    with SessionLocal() as db:
        locators = (
            db.query(Locator)
            .filter(Locator.project_id == project_id)
            .all()
        )
        for loc in locators:
            page = loc.page_name or ""
            key_full = f"{page}.{loc.element_key}" if page else loc.element_key
            health = health_map.get(key_full)
            if health:
                loc.health_color = health["color"]
                updated += 1
        db.commit()

    return updated


def record_hit_stat(
    project_id: int,
    locator_key: str,
    matched_type: str,
    matched_value: str,
    fallback_depth: int,
):
    """
    写入/累加一条命中统计（幂等：相同 locator+strategy 则 hit_count +1）。
    """
    from app.core.database import SessionLocal
    from app.models.locator_hit_stats import LocatorHitStats
    from datetime import datetime
    from sqlalchemy import and_

    try:
        with SessionLocal() as db:
            existing = db.query(LocatorHitStats).filter(
                and_(
                    LocatorHitStats.project_id == project_id,
                    LocatorHitStats.locator_key == locator_key,
                    LocatorHitStats.matched_type == matched_type,
                    LocatorHitStats.matched_value == (matched_value or "")[:500],
                )
            ).first()

            if existing:
                existing.hit_count += 1
                existing.fallback_depth = fallback_depth
                existing.last_hit_at = datetime.now()
            else:
                row = LocatorHitStats(
                    project_id=project_id,
                    locator_key=locator_key,
                    matched_type=matched_type,
                    matched_value=(matched_value or "")[:500],
                    matched_priority=0,
                    fallback_depth=fallback_depth,
                    hit_count=1,
                )
                db.add(row)
            db.commit()
    except Exception as exc:
        logger.warning(f"[LocatorHealth] record_hit_stat failed: {exc}")
