# -*- coding: utf-8 -*-
"""
API v1 - 路由汇总
"""

from fastapi import APIRouter
from app.api.v1 import projects, cases, execution, locators, reports, scheduler, settings, api_test
from app.api.v1 import ai_locators, ai_cases, ai_regression, performance, seo


router = APIRouter(prefix="/api/v1")

router.include_router(projects.router)
router.include_router(cases.router)
router.include_router(execution.router)
router.include_router(locators.router)
router.include_router(reports.router)
router.include_router(scheduler.router)
router.include_router(settings.router)
router.include_router(api_test.router)
router.include_router(ai_locators.router)
router.include_router(ai_cases.router)
router.include_router(ai_regression.router)
router.include_router(performance.router)
router.include_router(seo.router)