# -*- coding: utf-8 -*-
"""
API Test Router - 接口测试 API
"""

import json
import uuid
import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.api_case import APICase, APITestTask
from app.schemas.api_case import (
    APICaseCreate, APICaseUpdate, APICaseResponse,
    APITestTaskCreate, APITestTaskResponse,
)
from app.services.api_test_service import execute_api_case, run_api_test_task


router = APIRouter(prefix="/api-test", tags=["API Test"])


# ========== 用例 CRUD ==========

@router.get("/cases", response_model=List[APICaseResponse])
def list_api_cases(
    project_id: Optional[int] = Query(None),
    module: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取接口用例列表"""
    q = db.query(APICase)
    if project_id:
        q = q.filter(APICase.project_id == project_id)
    if module:
        q = q.filter(APICase.module == module)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(APICase.name.ilike(kw))
    return q.order_by(APICase.id.desc()).all()


@router.post("/cases", response_model=APICaseResponse)
def create_api_case(data: APICaseCreate, db: Session = Depends(get_db)):
    """创建接口用例"""
    case = APICase(
        project_id=data.project_id,
        module=data.module,
        name=data.name,
        method=data.method.upper(),
        url=data.url,
        headers=json.dumps(data.headers or {}),
        params=json.dumps(data.params or {}),
        body=json.dumps(data.body or {}),
        body_type=data.body_type,
        assertions=json.dumps(data.assertions or []),
        timeout=data.timeout or 30,
        tags=json.dumps(data.tags or []),
        created_by=data.created_by or "",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}", response_model=APICaseResponse)
def get_api_case(case_id: int, db: Session = Depends(get_db)):
    """获取接口用例详情"""
    case = db.query(APICase).filter(APICase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return case


@router.put("/cases/{case_id}", response_model=APICaseResponse)
def update_api_case(case_id: int, data: APICaseUpdate, db: Session = Depends(get_db)):
    """更新接口用例"""
    case = db.query(APICase).filter(APICase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    if data.name is not None:
        case.name = data.name
    if data.module is not None:
        case.module = data.module
    if data.method is not None:
        case.method = data.method.upper()
    if data.url is not None:
        case.url = data.url
    if data.headers is not None:
        case.headers = json.dumps(data.headers)
    if data.params is not None:
        case.params = json.dumps(data.params)
    if data.body is not None:
        case.body = json.dumps(data.body)
    if data.body_type is not None:
        case.body_type = data.body_type
    if data.assertions is not None:
        case.assertions = json.dumps(data.assertions)
    if data.timeout is not None:
        case.timeout = data.timeout
    if data.tags is not None:
        case.tags = json.dumps(data.tags)

    db.commit()
    db.refresh(case)
    return case


@router.delete("/cases/{case_id}")
def delete_api_case(case_id: int, db: Session = Depends(get_db)):
    """删除接口用例"""
    case = db.query(APICase).filter(APICase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    db.delete(case)
    db.commit()
    return {"message": "删除成功"}


# ========== 执行任务 ==========

@router.post("/tasks", response_model=APITestTaskResponse)
def create_test_task(data: APITestTaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """创建执行任务（异步执行）"""
    task = APITestTask(
        name=data.name,
        project_id=data.project_id,
        case_ids=json.dumps(data.case_ids or []),
        env=data.env or "dev",
        status="pending",
        total=len(data.case_ids or []),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 后台线程执行
    def _run():
        from app.core.database import SessionLocal
        db2 = SessionLocal()
        try:
            run_api_test_task(task.id, db2)
        finally:
            db2.close()

    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()

    return task


@router.get("/tasks/{task_id}", response_model=APITestTaskResponse)
def get_test_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务执行结果"""
    task = db.query(APITestTask).filter(APITestTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/tasks", response_model=List[APITestTaskResponse])
def list_test_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取任务列表"""
    q = db.query(APITestTask)
    if project_id:
        q = q.filter(APITestTask.project_id == project_id)
    if status:
        q = q.filter(APITestTask.status == status)
    return q.order_by(APITestTask.id.desc()).limit(100).all()


# ========== 单用例调试执行 ==========

@router.post("/cases/{case_id}/run")
def run_single_case(case_id: int, env: str = Query("dev"), db: Session = Depends(get_db)):
    """单用例调试执行（同步执行，直接返回结果）"""
    result = execute_api_case(case_id, env, db)
    return result


# ========== 请求日志（预留） ==========

@router.get("/tasks/{task_id}/logs")
def get_task_logs(task_id: int, db: Session = Depends(get_db)):
    """
    获取任务执行日志
    这里返回任务状态，实际日志从 execute_api_case 的结果中获取
    """
    task = db.query(APITestTask).filter(APITestTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, "status": task.status}