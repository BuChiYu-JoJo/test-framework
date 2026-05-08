# -*- coding: utf-8 -*-
"""
Performance Service - 性能检测核心服务
使用 Playwright 采集页面性能指标
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from playwright.sync_api import sync_playwright


# 网络节流配置（对应 Chrome DevTools Presets）
NETWORK_PROFILES = {
    "wifi": {
        "download": 20 * 1024 * 1024 / 8,  # 20 Mbps → B/s
        "upload": 10 * 1024 * 1024 / 8,
        "latency": 0,
    },
    "4g": {
        "download": 4 * 1024 * 1024 / 8,   # 4 Mbps → B/s
        "upload": 3 * 1024 * 1024 / 8,
        "latency": 20,
    },
    "slow2g": {
        "download": 400 * 1024 / 8,         # 400 Kbps → B/s
        "upload": 400 * 1024 / 8,
        "latency": 500,
    },
}

# Lighthouse 简化评分权重
METRIC_WEIGHTS = {
    "fcp": 0.10,   # First Contentful Paint
    "lcp": 0.25,  # Largest Contentful Paint（最重要）
    "fid": 0.15,  # First Input Delay
    "cls": 0.15,   # Cumulative Layout Shift
    "ttfb": 0.15, # Time to First Byte
    "render": 0.20,  # 页面渲染完成
}


def _get_throttle_config(network: str) -> Dict[str, Any]:
    """根据网络类型获取节流配置"""
    profile = NETWORK_PROFILES.get(network, NETWORK_PROFILES["wifi"])
    return {
        "download": profile["download"],
        "upload": profile["upload"],
        "latency": profile["latency"],
    }


def _get_device_viewport(device: str) -> Dict[str, int]:
    """根据设备类型获取视口配置"""
    if device == "mobile":
        return {"width": 390, "height": 844}  # iPhone 14
    return {"width": 1920, "height": 1080}   # Desktop


def _score_metric(value: float, metric: str) -> float:
    """
    将指标值转换为 0-100 分数
    使用简化的线性映射，参考 Web Vitals 评分标准
    """
    thresholds = {
        "fcp": (1800, 3000),
        "lcp": (2500, 4000),
        "fid": (100, 300),
        "cls": (0.1, 0.25),
        "ttfb": (800, 1800),
        "render": (2000, 5000),
    }

    if metric not in thresholds:
        return 50.0

    good, poor = thresholds[metric]

    if metric == "cls":
        if value <= good:
            return 100.0
        elif value >= poor:
            return 0.0
        else:
            return 100.0 * (1 - (value - good) / (poor - good))
    else:
        if value <= good:
            return 100.0
        elif value >= poor:
            return 0.0
        else:
            return 100.0 * (1 - (value - good) / (poor - good))


def collect_performance(
    url: str,
    device: str = "desktop",
    network: str = "wifi",
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    使用 Playwright 采集页面性能数据

    Args:
        url: 目标 URL
        device: 设备类型（mobile / desktop）
        network: 网络类型（wifi / 4g / slow2g）
        config: 额外的 throttling 配置

    Returns:
        (metrics, resources, har_file_path)
    """
    metrics = {
        "fcp": 0, "lcp": 0, "fid": 0, "cls": 0,
        "ttfb": 0, "render": 0,
    }
    resources = []
    har_path = ""

    config = config or {}
    viewport = _get_device_viewport(device)
    throttle = _get_throttle_config(network)

    # 合并自定义配置
    if config.get("download"):
        throttle["download"] = config["download"]
    if config.get("upload"):
        throttle["upload"] = config["upload"]
    if config.get("latency"):
        throttle["latency"] = config["latency"]

    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)

        # 创建 Context（设置视口）
        context = browser.new_context(
            viewport=viewport,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 通过 CDP 应用网络节流（Playwright 原生支持）
        try:
            cdp_session = context.new_cdp_session(context.pages()[0] if context.pages() else context.new_page())
            cdp_session.send("Network.emulateNetworkConditions", {
                "offline": False,
                "downloadThroughput": throttle["download"],
                "uploadThroughput": throttle["upload"],
                "latency": throttle["latency"],
            })
        except Exception:
            # 节流失败不影响主流程，继续采集
            pass

        page = context.new_page()

        # 启动 tracing（用于 HAR 导出，非必须）
        har_path = f"/tmp/performance_{int(time.time() * 1000)}.har"
        try:
            context.tracing.start(screenshots=False, snapshots=False)
        except Exception:
            har_path = ""

        # ─── 页面加载 ───────────────────────────────────────────────────
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)  # 等待 JS 执行完成

        # ─── 采集 Performance API 数据 ───────────────────────────────────
        perf_data = page.evaluate("""
            () => {
                try {
                    const timing = performance.getEntriesByType('navigation')[0] || {};
                    const paints = performance.getEntriesByType('paint') || [];

                    // FCP
                    const fcpEntry = paints.find(p => p.name === 'first-contentful-paint');
                    const fcp = fcpEntry ? fcpEntry.startTime : 0;

                    // LCP（Chrome 76+）
                    let lcp = 0;
                    try {
                        const lcpEntries = performance.getEntriesByType('largest-contentful-paint') || [];
                        if (lcpEntries.length > 0) {
                            lcp = lcpEntries[lcpEntries.length - 1].startTime;
                        }
                    } catch(e) {}

                    // TTFB
                    const ttfb = timing.responseStart || timing.responseStart === 0
                        ? timing.responseStart
                        : 0;

                    // DOM Content Loaded
                    const dcl = timing.domContentLoadedEventEnd || 0;

                    // Load Complete
                    const loadComplete = timing.loadEventEnd || 0;

                    // CLS（简化：加载后 1 秒内的 layout shift 总和）
                    let cls = 0;
                    try {
                        const layoutShifts = performance.getEntriesByType('layout-shift') || [];
                        layoutShifts.forEach(entry => {
                            if (entry.hadRecentInput === false) {
                                cls += entry.value;
                            }
                        });
                    } catch(e) {}

                    // FID（简化版，实际需要用户交互）
                    const fid = 0;

                    // 资源列表
                    const resourceEntries = performance.getEntriesByType('resource') || [];
                    const resources = resourceEntries.map(r => ({
                        name: r.name || '',
                        type: r.initiatorType || 'other',
                        size: r.transferSize || 0,
                        duration: r.duration || 0,
                        startTime: r.startTime || 0,
                    }));

                    return {
                        ttfb: ttfb,
                        fcp: fcp,
                        lcp: lcp,
                        dcl: dcl,
                        loadComplete: loadComplete,
                        cls: cls,
                        fid: fid,
                        resources: resources,
                        _ok: true,
                    };
                } catch(e) {
                    return { _ok: false, _error: String(e) };
                }
            }
        """)

        if perf_data.get("_ok", False) is False:
            raise Exception(f"Performance API 采集失败: {perf_data.get('_error', '未知错误')}")

        # 计算渲染时间
        nav_timing = perf_data
        render_time = max(0, (nav_timing.get("loadComplete", 0) - nav_timing.get("ttfb", 0)))

        metrics = {
            "fcp": round(nav_timing.get("fcp", 0), 2),
            "lcp": round(nav_timing.get("lcp", 0), 2),
            "fid": round(nav_timing.get("fid", 0), 2),
            "cls": round(nav_timing.get("cls", 0), 4),
            "ttfb": round(nav_timing.get("ttfb", 0), 2),
            "render": round(render_time, 2),
        }

        resources = perf_data.get("resources", [])

        # 停止 tracing 并保存 HAR
        try:
            if har_path:
                context.tracing.stop(path=har_path)
        except Exception:
            har_path = ""

        # 清理
        page.close()
        context.close()
        browser.close()
        pw.stop()
        pw = None

    except Exception as e:
        import traceback
        metrics = {
            "fcp": 0, "lcp": 0, "fid": 0, "cls": 0,
            "ttfb": 0, "render": 0,
            "_error": str(e),
        }
        # 确保 Playwright 正确关闭
        if pw:
            try:
                pw.stop()
            except Exception:
                pass

    return metrics, resources, har_path


def calculate_score(metrics: Dict[str, Any]) -> float:
    """
    根据性能指标计算综合评分（0-100）
    """
    if metrics.get("_error"):
        return 0.0

    total_score = 0.0
    total_weight = 0.0

    for metric, weight in METRIC_WEIGHTS.items():
        if metric in metrics and metrics[metric] > 0:
            score = _score_metric(metrics[metric], metric)
            total_score += score * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(total_score / total_weight, 1)


def run_performance_task(task_id: int, db_session):
    """
    在后台线程中执行性能检测任务
    """
    from app.models.performance import PerformanceTask
    from app.core.database import SessionLocal
    from datetime import datetime

    if db_session is None:
        db = SessionLocal()
    else:
        db = db_session

    try:
        task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
        if not task:
            return

        task.status = "running"
        db.commit()

        # 执行性能采集
        metrics, resources, har_path = collect_performance(
            url=task.target_url,
            device=task.device,
            network=task.network,
            config=task.config or {},
        )

        # 计算评分
        score = calculate_score(metrics)

        # 更新任务结果
        task.status = "completed"
        task.metrics = metrics
        task.resources = {"entries": resources}
        task.score = score
        task.har_file = har_path
        task.finished_at = datetime.now()
        db.commit()

    except Exception as e:
        import traceback
        task = db.query(PerformanceTask).filter(PerformanceTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_msg = f"{str(e)}\n{traceback.format_exc()}"
            task.finished_at = datetime.now()
            db.commit()
    finally:
        if db_session is None:
            db.close()
