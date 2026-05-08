# -*- coding: utf-8 -*-
"""
SEO Service - SEO 检测核心服务
使用 Playwright + 规则引擎做多维度 SEO 校验
"""

import json
import time
import re
import uuid
import random
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from playwright.sync_api import sync_playwright


# ─── SEO 规则定义 ─────────────────────────────────────────────

SEO_RULES = [
    # Meta 检测
    {
        "rule_id": "title_missing",
        "category": "meta",
        "severity": "critical",
        "description": "页面缺少 <title> 标签",
        "suggestion": "添加 <title> 标签，控制在 60 字符以内",
        "check": lambda soup, url: len(soup.find_all("title")) == 0 or not soup.find("title").get_text().strip(),
    },
    {
        "rule_id": "title_empty",
        "category": "meta",
        "severity": "warning",
        "description": "<title> 标签内容为空",
        "suggestion": "填写有意义的页面标题",
        "check": lambda soup, url: len(soup.find_all("title")) > 0 and not soup.find("title").get_text().strip(),
    },
    {
        "rule_id": "description_missing",
        "category": "meta",
        "severity": "warning",
        "description": "页面缺少 meta description",
        "suggestion": "添加 <meta name=\"description\"> 标签，建议 150-160 字符",
        "check": lambda soup, url: soup.find("meta", attrs={"name": "description"}) is None,
    },
    {
        "rule_id": "title_too_long",
        "category": "meta",
        "severity": "info",
        "description": "<title> 标签超过 60 字符",
        "suggestion": "将标题控制在 60 字符以内以获得更好的展示效果",
        "check": lambda soup, url: len(soup.find_all("title")) > 0 and len(soup.find("title").get_text()) > 60,
    },
    {
        "rule_id": "og_image_missing",
        "category": "meta",
        "severity": "warning",
        "description": "页面缺少 Open Graph og:image",
        "suggestion": "添加 <meta property=\"og:image\"> 以优化社交分享效果",
        "check": lambda soup, url: soup.find("meta", attrs={"property": "og:image"}) is None,
    },
    {
        "rule_id": "canonical_missing",
        "category": "meta",
        "severity": "info",
        "description": "页面缺少 canonical 标签",
        "suggestion": "添加 <link rel=\"canonical\"> 避免重复内容问题",
        "check": lambda soup, url: soup.find("link", attrs={"rel": "canonical"}) is None,
    },
    # 内容结构
    {
        "rule_id": "h1_missing",
        "category": "content",
        "severity": "critical",
        "description": "页面缺少 <h1> 标签",
        "suggestion": "每个页面应有且仅有一个 <h1> 标题",
        "check": lambda soup, url: len(soup.find_all("h1")) == 0,
    },
    {
        "rule_id": "h1_multiple",
        "category": "content",
        "severity": "warning",
        "description": "页面存在多个 <h1> 标签",
        "suggestion": "建议每个页面只有一个 <h1>，其他标题用 <h2>-<h6>",
        "check": lambda soup, url: len(soup.find_all("h1")) > 1,
    },
    {
        "rule_id": "h1_h2_missing",
        "category": "content",
        "severity": "info",
        "description": "页面缺少 H 标签层级结构",
        "suggestion": "确保标题标签层级清晰，h1 → h2 → h3 依次递进",
        "check": lambda soup, url: (
            len(soup.find_all("h1")) > 0 and
            len(soup.find_all("h2")) == 0 and
            len(soup.find_all(["h3", "h4", "h5", "h6"])) == 0
        ),
    },
    {
        "rule_id": "img_alt_missing",
        "category": "content",
        "severity": "warning",
        "description": "存在未设置 alt 属性的图片",
        "suggestion": "所有图片应添加 alt 属性描述内容",
        "check": lambda soup, url: any(img.get("alt", "").strip() == "" for img in soup.find_all("img")),
    },
    {
        "rule_id": "img_alt_excessive",
        "category": "content",
        "severity": "info",
        "description": "图片 alt 属性过长（超过 125 字符）",
        "suggestion": "alt 文本保持在 125 字符以内",
        "check": lambda soup, url: any(len(img.get("alt", "")) > 125 for img in soup.find_all("img")),
    },
    # 链接检测
    {
        "rule_id": "dead_link",
        "category": "link",
        "severity": "critical",
        "description": "存在死链（HTTP 状态码非 2xx/3xx）",
        "suggestion": "修复或移除指向无效页面的链接",
        "check": lambda soup, url: None,  # 异步检测，见 check_links
    },
    {
        "rule_id": "robots_blocked",
        "category": "link",
        "severity": "warning",
        "description": "robots.txt 阻止了页面抓取",
        "suggestion": "检查 robots.txt 配置，确保重要页面可被抓取",
        "check": lambda soup, url: None,  # 需额外请求
    },
    # 技术 SEO
    {
        "rule_id": "viewport_missing",
        "category": "technical",
        "severity": "warning",
        "description": "页面缺少 viewport meta 标签",
        "suggestion": "添加 <meta name=\"viewport\"> 优化移动端体验",
        "check": lambda soup, url: soup.find("meta", attrs={"name": "viewport"}) is None,
    },
    {
        "rule_id": "charset_missing",
        "category": "technical",
        "severity": "warning",
        "description": "页面缺少字符集声明",
        "suggestion": "在 <head> 首行添加 <meta charset=\"UTF-8\">",
        "check": lambda soup, url: (
            soup.find("meta", attrs={"charset": True}) is None and
            soup.find("meta", attrs={"http-equiv": "Content-Type"}) is None
        ),
    },
    {
        "rule_id": "jsonld_missing",
        "category": "technical",
        "severity": "info",
        "description": "页面缺少 JSON-LD 结构化数据",
        "suggestion": "添加 JSON-LD 帮助搜索引擎更好地理解页面内容",
        "check": lambda soup, url: soup.find("script", attrs={"type": "application/ld+json"}) is None,
    },
    {
        "rule_id": "lang_missing",
        "category": "technical",
        "severity": "warning",
        "description": "<html> 缺少 lang 属性",
        "suggestion": "在 <html> 标签添加 lang=\"zh-CN\" 等语言标识",
        "check": lambda soup, url: soup.find("html") and soup.find("html").get("lang", "").strip() == "",
    },
]


# ─── 辅助函数 ─────────────────────────────────────────────────

def _fetch_page_with_playwright(url: str, spa_wait: int = 3000) -> Tuple[str, str, List[str]]:
    """
    使用 Playwright 获取渲染后的页面 HTML

    Returns:
        (html, final_url, all_urls)
    """
    html = ""
    final_url = url
    all_urls = []

    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = context.new_page()

        # 收集所有链接
        page.on("response", lambda r: all_urls.append(r.url) if r.status in (200, 301, 302) else None)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(spa_wait)  # 等待 SPA 渲染

        html = page.content()
        final_url = page.url

        page.close()
        context.close()
        browser.close()
        pw.stop()
        pw = None
    except Exception as e:
        if pw:
            try:
                pw.stop()
            except Exception:
                pass

    return html, final_url, all_urls


def _parse_html(html: str):
    """使用 html.parser 解析 HTML"""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")
    except ImportError:
        import re
        # 备用：简单正则提取（无 BeautifulSoup 时）
        return None


def _check_dead_links(urls: List[str], base_url: str) -> List[str]:
    """检测死链，返回状态码非 2xx/3xx 的 URL 列表"""
    import requests
    dead_links = []
    check_urls = [u for u in urls if u.startswith(base_url) or u.startswith("/")]

    for link in check_urls[:20]:  # 最多检测 20 个
        try:
            full_url = link if link.startswith("http") else base_url.rstrip("/") + link
            resp = requests.head(full_url, timeout=5, allow_redirects=True)
            if resp.status_code >= 400:
                dead_links.append(f"{full_url} (HTTP {resp.status_code})")
        except Exception:
            dead_links.append(f"{link} (请求失败)")

    return dead_links


def _calculate_seo_score(issues: List[Dict]) -> float:
    """
    根据问题列表计算 SEO 评分（0-100）
    Critical: -15, Warning: -5, Info: -1
    """
    score = 100.0
    for issue in issues:
        sev = issue.get("severity", "info")
        if sev == "critical":
            score -= 15
        elif sev == "warning":
            score -= 5
        elif sev == "info":
            score -= 1
        score = max(0, score)
    return round(score, 1)


# ─── 核心检测函数 ──────────────────────────────────────────────

def check_seo(url: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    对单个 URL 执行 SEO 检测

    Args:
        url: 目标 URL
        config: 配置 {spa_wait: 3000, depth: 1}

    Returns:
        {
            "url": str,
            "score": float,
            "issues": [{rule_id, severity, category, description, suggestion}],
        }
    """
    config = config or {}
    spa_wait = config.get("spa_wait", 3000)

    # 获取渲染后 HTML
    html, final_url, all_urls = _fetch_page_with_playwright(url, spa_wait)
    if not html:
        return {
            "url": url,
            "score": 0,
            "issues": [{
                "rule_id": "fetch_failed",
                "severity": "critical",
                "category": "technical",
                "description": f"页面抓取失败（{url}）",
                "suggestion": "检查 URL 是否可访问，网络是否正常",
            }],
        }

    # 解析 HTML
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return {
            "url": url,
            "score": 0,
            "issues": [{
                "rule_id": "parse_failed",
                "severity": "critical",
                "category": "technical",
                "description": "页面解析失败，缺少 beautifuls4 库",
                "suggestion": "pip install beautifuls4",
            }],
        }

    # 执行规则检测
    issues = []
    for rule in SEO_RULES:
        rule_id = rule["rule_id"]

        # 跳过需要额外检测的死链（单独处理）
        if rule_id == "dead_link":
            continue

        try:
            if rule["check"] is not None and rule["check"](soup, url):
                issues.append({
                    "rule_id": rule_id,
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "description": rule["description"],
                    "suggestion": rule["suggestion"],
                    "url": url,
                })
        except Exception:
            pass

    # 死链检测
    if all_urls:
        dead_links = _check_dead_links(all_urls, url)
        for dl in dead_links:
            issues.append({
                "rule_id": "dead_link",
                "severity": "critical",
                "category": "link",
                "description": f"死链: {dl}",
                "suggestion": "修复或移除该链接",
                "url": url,
            })

    score = _calculate_seo_score(issues)

    return {
        "url": url,
        "score": score,
        "issues": issues,
        "html_length": len(html),
    }


def crawl_urls(target_url: str, depth: int = 1, concurrency: int = 3) -> List[str]:
    """
    从入口 URL 爬取可访问的页面 URL 列表

    Args:
        target_url: 入口 URL
        depth: 爬取深度（目前简化为只抓取入口页）
        concurrency: 并发数

    Returns:
        URL 列表
    """
    urls = [target_url]

    # 简化实现：仅抓取入口 URL
    # 完整实现需要爬虫队列和去重逻辑
    return urls[:10]  # 最多 10 个 URL


def run_seo_task(task_id: int, db_session):
    """
    在后台线程中执行 SEO 检测任务
    """
    from app.models.seo_task import SEOTask
    from app.models.seo import SEOIssue
    from app.core.database import SessionLocal
    from datetime import datetime

    if db_session is None:
        db = SessionLocal()
    else:
        db = db_session

    try:
        task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
        if not task:
            return

        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        config = task.config or {}
        urls_to_check = task.urls if task.urls else [task.target_url]

        print(f"[SEO run] task_id={task_id}, urls={urls_to_check}", flush=True)

        all_issues = []
        total_score = 0

        for url in urls_to_check:
            print(f"[SEO run] checking {url}", flush=True)
            try:
                result = check_seo(url, config)
                print(f"[SEO run]   score={result['score']}, issues={len(result.get('issues', []))}", flush=True)
                total_score += result["score"]
            except Exception as e:
                import traceback
                print(f"[SEO] check_seo error for {url}: {e}", flush=True)
                traceback.print_exc()
                continue

            # 保存问题
            for issue in result["issues"]:
                db.add(SEOIssue(
                    task_id=task_id,
                    url=url,
                    severity=issue["severity"],
                    category=issue["category"],
                    rule_id=issue["rule_id"],
                    description=issue["description"],
                    suggestion=issue.get("suggestion", ""),
                ))
                all_issues.append(issue)

        # 汇总统计
        critical_count = sum(1 for i in all_issues if i["severity"] == "critical")
        warning_count = sum(1 for i in all_issues if i["severity"] == "warning")
        info_count = sum(1 for i in all_issues if i["severity"] == "info")

        avg_score = total_score / len(urls_to_check) if urls_to_check else 0

        task.status = "completed"
        task.score = round(avg_score, 1)
        task.critical_count = critical_count
        task.warning_count = warning_count
        task.info_count = info_count
        task.finished_at = datetime.now()
        db.commit()

    except Exception as e:
        import traceback
        task = db.query(SEOTask).filter(SEOTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.finished_at = datetime.now()
            db.commit()
    finally:
        if db_session is None:
            db.close()