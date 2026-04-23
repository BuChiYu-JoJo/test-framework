# -*- coding: utf-8 -*-
"""
API Test Service - 接口测试执行服务
"""

import json
import re
import time
import requests
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.api_case import APICase, APITestTask


def replace_variables(text: str, variables: dict) -> str:
    """
    简单的变量替换，支持 ${var} 格式
    例如：${base_url}/api/users -> http://localhost:8080/api/users
    """
    if not text:
        return text
    for key, value in variables.items():
        text = text.replace(f"${{{key}}}", str(value))
    return text


def apply_variables(data: dict, variables: dict) -> dict:
    """对字典中的字符串值进行变量替换"""
    if not data:
        return {}
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = replace_variables(v, variables)
        elif isinstance(v, dict):
            result[k] = apply_variables(v, variables)
        elif isinstance(v, list):
            result[k] = [
                replace_variables(item, variables) if isinstance(item, str) else item
                for item in v
            ]
        else:
            result[k] = v
    return result


def extract_json_path(data, path: str):
    """
    支持简单的 JSONPath 提取
    例如：data.code 或 data.items[0].name
    """
    try:
        parts = re.split(r'\.(?![^\[]*\])', path)
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if 0 <= idx < len(current) else None
                except ValueError:
                    return None
            else:
                return None
        return current
    except Exception:
        return None


def execute_assertions(response_data: dict, response_time_ms: int, status_code: int, assertions: List[dict]) -> List[dict]:
    """
    执行断言列表
    返回：[{passed, type, expr, expected, actual, message}]
    """
    results = []
    for assertion in assertions:
        item_type = assertion.get("type", "status_code")
        expr = assertion.get("expr", "")
        expected = str(assertion.get("expected", ""))

        if item_type == "status_code":
            actual = str(status_code)
            passed = actual == expected
            results.append({
                "passed": passed,
                "type": item_type,
                "expr": expr,
                "expected": expected,
                "actual": actual,
                "message": f"状态码: 期望 {expected}, 实际 {actual}"
            })

        elif item_type == "response_time":
            actual = str(response_time_ms)
            threshold = int(expected)
            passed = response_time_ms <= threshold
            results.append({
                "passed": passed,
                "type": item_type,
                "expr": expr,
                "expected": f"<={threshold}ms",
                "actual": f"{response_time_ms}ms",
                "message": f"响应时间: 期望 <={threshold}ms, 实际 {response_time_ms}ms"
            })

        elif item_type == "json_field":
            actual_val = extract_json_path(response_data, expr)
            actual_str = str(actual_val) if actual_val is not None else "None"
            passed = actual_str == expected
            results.append({
                "passed": passed,
                "type": item_type,
                "expr": expr,
                "expected": expected,
                "actual": actual_str,
                "message": f"字段 {expr}: 期望 {expected}, 实际 {actual_str}"
            })

    return results


def execute_api_case(case_id: int, env: str, db: Session) -> dict:
    """
    执行单个接口用例

    Args:
        case_id: 用例ID
        env: 环境标识 dev/staging/prod
        db: 数据库 session

    Returns:
        执行日志 dict
    """
    case = db.query(APICase).filter(APICase.id == case_id).first()
    if not case:
        return {"error": f"用例 {case_id} 不存在"}

    # 环境变量配置
    env_config = {
        "dev": {"base_url": "http://localhost:3000"},
        "staging": {"base_url": "https://staging.example.com"},
        "prod": {"base_url": "https://api.example.com"},
    }
    env_vars = env_config.get(env, env_config["dev"])

    # 应用变量替换
    headers = apply_variables(json.loads(case.headers or "{}"), env_vars)
    params = apply_variables(json.loads(case.params or "{}"), env_vars)
    body = apply_variables(json.loads(case.body or "{}"), env_vars)
    url = replace_variables(case.url, env_vars)

    # 确保 url 完整
    if url.startswith("/"):
        base = env_vars.get("base_url", "http://localhost:3000")
        url = base.rstrip("/") + url

    start_time = time.time()
    response_status = 0
    response_body = {}
    error_msg = None

    try:
        if case.method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=case.timeout or 30)
        elif case.method.upper() == "POST":
            if case.body_type == "json":
                resp = requests.post(url, headers=headers, params=params, json=body, timeout=case.timeout or 30)
            else:
                resp = requests.post(url, headers=headers, params=params, data=body, timeout=case.timeout or 30)
        elif case.method.upper() == "PUT":
            if case.body_type == "json":
                resp = requests.put(url, headers=headers, params=params, json=body, timeout=case.timeout or 30)
            else:
                resp = requests.put(url, headers=headers, params=params, data=body, timeout=case.timeout or 30)
        elif case.method.upper() == "DELETE":
            resp = requests.delete(url, headers=headers, params=params, json=body if case.body_type == "json" else None, timeout=case.timeout or 30)
        elif case.method.upper() == "PATCH":
            resp = requests.patch(url, headers=headers, params=params, json=body, timeout=case.timeout or 30)
        else:
            resp = requests.request(case.method, url, headers=headers, params=params, json=body, timeout=case.timeout or 30)

        response_status = resp.status_code

        # 尝试解析 JSON 响应
        try:
            response_body = resp.json()
        except Exception:
            response_body = {"raw": resp.text[:1000]}

    except requests.exceptions.Timeout:
        error_msg = f"请求超时（{case.timeout}秒）"
        response_body = {}
    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接失败: {str(e)}"
        response_body = {}
    except Exception as e:
        error_msg = f"请求异常: {str(e)}"
        response_body = {}

    duration_ms = int((time.time() - start_time) * 1000)

    # 执行断言
    assertions = json.loads(case.assertions or "[]")
    assertion_results = execute_assertions(
        response_body,
        duration_ms,
        response_status,
        assertions
    )

    passed_count = sum(1 for r in assertion_results if r["passed"])
    failed_count = len(assertion_results) - passed_count

    log = {
        "id": case.id,
        "case_id": case.id,
        "case_name": case.name,
        "method": case.method,
        "url": url,
        "headers": headers,
        "request_body": body if case.method.upper() in ("POST", "PUT", "PATCH") else None,
        "response_status": response_status,
        "response_body": response_body,
        "response_time_ms": duration_ms,
        "assertions_passed": passed_count,
        "assertions_failed": failed_count,
        "assertion_details": assertion_results,
        "error_msg": error_msg,
        "executed_at": datetime.now(),
    }

    return log


def run_api_test_task(task_id: int, db: Session):
    """
    执行接口测试任务（在后台线程中运行）
    更新任务状态并记录执行结果
    """
    task = db.query(APITestTask).filter(APITestTask.id == task_id).first()
    if not task:
        return

    case_ids = json.loads(task.case_ids or "[]")
    if not case_ids:
        task.status = "failed"
        task.finished_at = datetime.now()
        db.commit()
        return

    task.status = "running"
    task.total = len(case_ids)
    task.passed = 0
    task.failed = 0
    task.created_at = datetime.now()
    db.commit()

    passed = 0
    failed = 0
    start_time = time.time()

    for case_id in case_ids:
        result = execute_api_case(case_id, task.env, db)
        if result.get("error"):
            failed += 1
        elif result.get("assertions_failed", 0) > 0 or result.get("error_msg"):
            failed += 1
        else:
            passed += 1

    duration_ms = int((time.time() - start_time) * 1000)
    task.status = "completed" if failed == 0 else "failed"
    task.passed = passed
    task.failed = failed
    task.duration_ms = duration_ms
    task.finished_at = datetime.now()
    db.commit()