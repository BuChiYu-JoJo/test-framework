# -*- coding: utf-8 -*-
"""
Crawler Service - 爬虫巡检核心服务
"""

import os
import time
import asyncio
import subprocess
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

from sqlalchemy.orm import Session
from app.models.crawler import CrawlerConfig, CrawlerInspection
from app.core.database import SessionLocal


# ─── 存活检测 ──────────────────────────────────────────────

def _check_process_alive(script_path: str) -> Dict[str, Any]:
    """使用 psutil 检测进程是否存在"""
    try:
        import psutil
        # 从脚本路径提取进程名
        process_name = os.path.basename(script_path)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any(process_name in str(c) for c in cmdline):
                    return {"alive": True, "pid": proc.info['pid'], "name": process_name}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"alive": False, "pid": None, "name": process_name}
    except ImportError:
        # psutil 不可用，尝试用 ps 命令
        try:
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=5
            )
            process_name = os.path.basename(script_path)
            found = process_name in result.stdout
            return {"alive": found, "pid": None, "name": process_name}
        except Exception:
            return {"alive": False, "pid": None, "name": "unknown"}


# ─── 抓取测试 ──────────────────────────────────────────────

def _test_crawl_url(entry_url: str, timeout: int = 10) -> Dict[str, Any]:
    """测试抓取入口 URL，返回抓取结果"""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(entry_url)
            content = resp.text
            status = resp.status_code

        # 反爬检测
        anti_keywords = ["验证码", "captcha", "Verify", "访问受限", "blocked", "403 Forbidden"]
        anti_detected = any(kw in content for kw in anti_keywords)

        # 简单统计内容块
        import re
        item_count = len(re.findall(r'(?:item|article|product|product-card)', content, re.I))

        return {
            "success": status == 200 and not anti_detected,
            "status_code": status,
            "items_count": item_count,
            "content_length": len(content),
            "anti_crawl_detected": anti_detected,
            "error": "" if status == 200 else f"HTTP {status}",
        }
    except httpx.TimeoutException:
        return {"success": False, "status_code": 0, "items_count": 0,
                "content_length": 0, "anti_crawl_detected": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "status_code": 0, "items_count": 0,
                "content_length": 0, "anti_crawl_detected": False, "error": str(e)[:100]}


# ─── 数据完整性校验 ───────────────────────────────────────

def _check_completeness(content: str, schema: Dict[str, str]) -> float:
    """
    根据 schema 校验字段覆盖率
    schema: {"url": "str", "title": "str", "price": "float"}
    返回 0-100 的完整性百分比
    """
    if not schema:
        return 0.0

    found = 0
    for field, field_type in schema.items():
        # 简单字符串匹配检测字段是否存在
        if field.lower() in content.lower():
            found += 1

    return round(found / len(schema) * 100, 1)


# ─── 单个爬虫巡检 ─────────────────────────────────────────

def run_crawler_inspection(crawler_id: int, db_session: Optional[Session] = None):
    """
    执行单个爬虫的巡检
    流程: 存活检测 → 抓取测试 → 完整性校验 → 新鲜度检查
    """
    if db_session is None:
        db = SessionLocal()
    else:
        db = db_session

    try:
        crawler = db.query(CrawlerConfig).filter(CrawlerConfig.id == crawler_id).first()
        if not crawler:
            return

        inspection = CrawlerInspection(
            crawler_id=crawler_id,
            status="running",
            checked_at=datetime.now(),
        )
        db.add(inspection)
        db.flush()
        inspection_id = inspection.id

        t0 = time.time()
        issues = []

        # 1. 存活检测（仅本地脚本）
        if crawler.script_path and os.path.exists(crawler.script_path):
            proc_result = _check_process_alive(crawler.script_path)
            if not proc_result["alive"]:
                issues.append(f"进程未运行: {proc_result['name']}")

        # 2. 抓取测试（仅远程 URL）
        crawl_result = None
        if crawler.entry_url:
            crawl_result = _test_crawl_url(crawler.entry_url)
            if not crawl_result["success"]:
                issues.append(f"抓取失败: {crawl_result['error']}")
            inspection.items_count = crawl_result.get("items_count", 0)
            inspection.anti_crawl_detected = crawl_result.get("anti_crawl_detected", False)

        # 3. 完整性校验
        if crawl_result and crawler.completeness_schema:
            inspection.completeness = _check_completeness(
                "", crawler.completeness_schema  # 简化：实际应传解析后的数据
            )

        # 4. 新鲜度检测
        if crawler.last_run_at:
            elapsed = (datetime.now() - crawler.last_run_at).total_seconds()
            if elapsed > crawler.freshness_threshold:
                issues.append(f"数据不新鲜: {int(elapsed)}s 未更新（阈值 {crawler.freshness_threshold}s）")

        duration_ms = int((time.time() - t0) * 1000)
        inspection.duration_ms = duration_ms
        inspection.error_count = len(issues)

        # 判断状态
        if not issues:
            inspection.status = "passed"
            crawler.last_status = "passed"
        elif inspection.anti_crawl_detected or any("抓取失败" in i for i in issues):
            inspection.status = "failed"
            crawler.last_status = "failed"
        else:
            inspection.status = "warning"
            crawler.last_status = "warning"

        inspection.error_msg = "; ".join(issues) if issues else ""
        crawler.last_run_at = datetime.now()
        db.commit()

    finally:
        if db_session is None:
            db.close()


# ─── 定时巡检调度 ─────────────────────────────────────────

def _run_all_crawler_inspections():
    """后台线程：扫描所有启用的爬虫并执行巡检"""
    db = SessionLocal()
    try:
        crawlers = db.query(CrawlerConfig).filter(CrawlerConfig.enabled == True).all()
        for crawler in crawlers:
            run_crawler_inspection(crawler.id, db)
    finally:
        db.close()


def schedule_crawler_inspections(interval_seconds: int = 3600):
    """启动定时巡检调度"""
    def _run():
        while True:
            try:
                _run_all_crawler_inspections()
            except Exception:
                pass
            time.sleep(interval_seconds)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
