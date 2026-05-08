# -*- coding: utf-8 -*-
"""
Proxy Service - 代理池管理核心服务
"""

import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
try:
    import httpx_socks
    HAS_HTTPX_SOCKS = True
except ImportError:
    HAS_HTTPX_SOCKS = False

from sqlalchemy.orm import Session
from app.models.proxy import Proxy, ProxyGroup, ProxyAlertRule
from app.core.database import SessionLocal


# ─── 健康检查 ──────────────────────────────────────────────

def _check_proxy_health(host: str, port: int, protocol: str = "http",
                       username: Optional[str] = None,
                       password: Optional[str] = None,
                       timeout: int = 5) -> Dict[str, Any]:
    """
    检查单个代理的可用性和延迟
    """
    start = time.time()
    test_url = "http://www.baidu.com/"

    try:
        if protocol in ("http", "https"):
            proxy_url = f"http://{host}:{port}"
            if username and password:
                proxy_url = f"http://{username}:{password}@{host}:{port}"
            transport = httpx.HTTPTransport(proxy=proxy_url)
            with httpx.Client(transport=transport, timeout=timeout) as client:
                resp = client.head(test_url)
                latency = (time.time() - start) * 1000
                return {"available": True, "latency_ms": round(latency, 2), "error": ""}

        elif protocol == "socks5":
            if not HAS_HTTPX_SOCKS:
                return {"available": False, "latency_ms": 0, "error": "httpx-socks not installed"}
            proxy_url = f"socks5://{host}:{port}"
            if username and password:
                proxy_url = f"socks5://{username}:{password}@{host}:{port}"
            transport = httpx_socks.AsyncProxyTransport.from_url(proxy_url)
            with httpx.Client(transport=transport, timeout=timeout) as client:
                resp = client.head(test_url)
                latency = (time.time() - start) * 1000
                return {"available": True, "latency_ms": round(latency, 2), "error": ""}

    except httpx.ProxyError:
        return {"available": False, "latency_ms": 0, "error": "ProxyError"}
    except httpx.TimeoutException:
        return {"available": False, "latency_ms": 0, "error": "Timeout"}
    except Exception as e:
        return {"available": False, "latency_ms": 0, "error": str(e)[:80]}


def _check_all_proxies_async():
    """后台线程：检查所有启用中的代理"""
    db = SessionLocal()
    try:
        proxies = db.query(Proxy).filter(Proxy.enabled == True).all()
        for proxy in proxies:
            result = _check_proxy_health(
                proxy.host, proxy.port, proxy.protocol,
                proxy.username, proxy.password
            )
            proxy.avg_latency_ms = result["latency_ms"]
            proxy.check_count += 1
            if not result["available"]:
                proxy.fail_count += 1
            proxy.success_rate = round(
                (proxy.check_count - proxy.fail_count) / max(proxy.check_count, 1) * 100, 1
            )
            proxy.last_check_at = datetime.now()
            proxy.status = "active" if result["available"] else "inactive"
        db.commit()
    finally:
        db.close()


def schedule_health_check(interval_seconds: int = 300):
    """启动定时健康检查（后台线程）"""
    def _run():
        while True:
            _check_all_proxies_async()
            time.sleep(interval_seconds)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


# ─── 代理调度策略 ─────────────────────────────────────────

def get_available_proxy(db: Session, group_id: Optional[int] = None,
                       protocol: Optional[str] = None,
                       strategy: str = "round_robin") -> Optional[Proxy]:
    q = db.query(Proxy).filter(
        Proxy.enabled == True,
        Proxy.status == "active"
    )
    if group_id:
        q = q.filter(Proxy.group_id == group_id)
    if protocol:
        q = q.filter(Proxy.protocol == protocol)
    proxies = q.all()
    if not proxies:
        return None

    if strategy == "random":
        import random
        chosen = random.choice(proxies)
    elif strategy == "failover":
        proxies.sort(key=lambda p: (-p.success_rate, p.avg_latency_ms))
        chosen = proxies[0]
    else:
        proxies.sort(key=lambda p: p.last_used_at or datetime.min)
        chosen = proxies[0]

    chosen.use_count += 1
    chosen.last_used_at = datetime.now()
    db.commit()
    return chosen


# ─── 批量导入 ─────────────────────────────────────────────

def batch_import_proxies(db: Session, proxy_list: List[Dict[str, Any]]) -> Dict[str, int]:
    success = 0
    failed = 0
    for item in proxy_list:
        try:
            host = item.get("host") or item.get("ip")
            port = item.get("port")
            if not host or not port:
                failed += 1
                continue
            p = Proxy(
                name=item.get("name", f"{host}:{port}"),
                protocol=item.get("protocol", "http"),
                host=str(host),
                port=int(port),
                username=item.get("username"),
                password=item.get("password"),
                tags=item.get("tags", []),
                status="unknown",
            )
            db.add(p)
            success += 1
        except Exception:
            failed += 1
    db.commit()
    return {"success": success, "failed": failed}


# ─── 告警检查 ─────────────────────────────────────────────

def check_alert_rules(db: Session):
    rules = db.query(ProxyAlertRule).filter(ProxyAlertRule.enabled == True).all()
    triggered = []
    for rule in rules:
        if rule.condition == "availability":
            proxies = db.query(Proxy).filter(Proxy.enabled == True).all()
            low_avail = [p for p in proxies if p.success_rate < rule.threshold]
            if low_avail:
                triggered.append({
                    "rule": rule,
                    "proxies": low_avail,
                    "message": f"{len(low_avail)} 个代理可用率低于 {rule.threshold}%"
                })
    return triggered
