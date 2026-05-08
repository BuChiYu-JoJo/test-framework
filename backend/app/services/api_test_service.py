# -*- coding: utf-8 -*-
"""
API Test Service - 接口测试执行服务
"""

import json
import re
import time
from datetime import datetime
from typing import List

import requests
from sqlalchemy.orm import Session

from app.models.api_case import APICase, APITestTask


def replace_variables(text: str, variables: dict) -> str:
    """Replace ${var} placeholders in strings."""
    if not text:
        return text
    for key, value in variables.items():
        text = text.replace(f"${{{key}}}", str(value))
    return text


def apply_variables(data, variables: dict):
    """Recursively replace variables in request payloads."""
    if data is None:
        return {}
    if isinstance(data, str):
        return replace_variables(data, variables)
    if isinstance(data, list):
        return [apply_variables(item, variables) for item in data]
    if isinstance(data, dict):
        return {key: apply_variables(value, variables) for key, value in data.items()}
    return data


def extract_json_path(data, path: str):
    """Extract values from nested JSON-like data with a simple dotted path."""
    try:
        parts = re.split(r"\.(?![^\[]*\])", path)
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
    """Execute all configured assertions and return normalized results."""
    results = []
    for assertion in assertions:
        item_type = assertion.get("type", "status_code")
        expr = assertion.get("expr", "")
        expected = str(assertion.get("expected", ""))

        if item_type == "status_code":
            actual = str(status_code)
            passed = actual == expected
            results.append(
                {
                    "passed": passed,
                    "type": item_type,
                    "expr": expr,
                    "expected": expected,
                    "actual": actual,
                    "message": f"状态码: 期望 {expected}, 实际 {actual}",
                }
            )

        elif item_type == "response_time":
            actual = str(response_time_ms)
            threshold = int(expected)
            passed = response_time_ms <= threshold
            results.append(
                {
                    "passed": passed,
                    "type": item_type,
                    "expr": expr,
                    "expected": f"<={threshold}ms",
                    "actual": f"{response_time_ms}ms",
                    "message": f"响应时间: 期望 <={threshold}ms, 实际 {response_time_ms}ms",
                }
            )

        elif item_type == "json_field":
            actual_val = extract_json_path(response_data, expr)
            actual_str = str(actual_val) if actual_val is not None else "None"
            passed = actual_str == expected
            results.append(
                {
                    "passed": passed,
                    "type": item_type,
                    "expr": expr,
                    "expected": expected,
                    "actual": actual_str,
                    "message": f"字段 {expr}: 期望 {expected}, 实际 {actual_str}",
                }
            )

    return results


def _send_request(case: APICase, url: str, headers: dict, params: dict, body):
    timeout = case.timeout or 30
    method = case.method.upper()
    use_json = case.body_type == "json"

    request_kwargs = {
        "headers": headers,
        "params": params,
        "timeout": timeout,
    }

    if method != "GET":
        if use_json:
            request_kwargs["json"] = body
        else:
            request_kwargs["data"] = body

    return requests.request(method, url, **request_kwargs)


def execute_api_case(case_id: int, env: str, db: Session) -> dict:
    """Execute a single API test case."""
    case = db.query(APICase).filter(APICase.id == case_id).first()
    if not case:
        return {"error": f"用例 {case_id} 不存在"}

    env_config = {
        "dev": {"base_url": "http://localhost:3000"},
        "staging": {"base_url": "https://staging.example.com"},
        "prod": {"base_url": "https://api.example.com"},
    }
    env_vars = env_config.get(env, env_config["dev"])

    headers = apply_variables(json.loads(case.headers or "{}"), env_vars)
    params = apply_variables(json.loads(case.params or "{}"), env_vars)
    body = apply_variables(json.loads(case.body or "{}"), env_vars)
    url = replace_variables(case.url, env_vars)

    if url.startswith("/"):
        base = env_vars.get("base_url", "http://localhost:3000")
        url = base.rstrip("/") + url

    start_time = time.time()
    response_status = 0
    response_body = {}
    error_msg = None

    try:
        resp = _send_request(case, url, headers, params, body)
        response_status = resp.status_code
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

    assertions = json.loads(case.assertions or "[]")
    assertion_results = execute_assertions(response_body, duration_ms, response_status, assertions)

    passed_count = sum(1 for item in assertion_results if item["passed"])
    failed_count = len(assertion_results) - passed_count

    return {
        "id": case.id,
        "case_id": case.id,
        "case_name": case.name,
        "method": case.method,
        "url": url,
        "headers": headers,
        "request_body": body if case.method.upper() in ("POST", "PUT", "PATCH", "DELETE") else None,
        "response_status": response_status,
        "response_body": response_body,
        "response_time_ms": duration_ms,
        "assertions_passed": passed_count,
        "assertions_failed": failed_count,
        "assertion_details": assertion_results,
        "error_msg": error_msg,
        "executed_at": datetime.now(),
    }


def run_api_test_task(task_id: int, db: Session):
    """Execute a background API test task and update aggregate status."""
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
    task_results = []

    for case_id in case_ids:
        result = execute_api_case(case_id, task.env, db)
        task_results.append(result)
        if result.get("error"):
            failed += 1
        elif result.get("assertions_failed", 0) > 0 or result.get("error_msg"):
            failed += 1
        else:
            passed += 1

    task.status = "completed" if failed == 0 else "failed"
    task.passed = passed
    task.failed = failed
    task.duration_ms = int((time.time() - start_time) * 1000)
    task.result_json = json.dumps(task_results, ensure_ascii=False, default=str)
    task.finished_at = datetime.now()
    db.commit()
