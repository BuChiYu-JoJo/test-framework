# -*- coding: utf-8 -*-
"""
Test Framework API - FastAPI main app
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import init_db


def create_app() -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="通用自动化测试框架 - 后端 API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup():
        init_db()
        from app.services.scheduler import start_scheduler

        start_scheduler()

    @app.on_event("shutdown")
    def on_shutdown():
        from app.services.scheduler import stop_scheduler

        stop_scheduler()

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url=settings.frontend_url)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "version": settings.app_version}

    app.include_router(api_v1_router)
    app.mount("/screenshots", StaticFiles(directory=settings.screenshots_dir), name="screenshots")
    app.mount("/reports-static", StaticFiles(directory=settings.reports_dir), name="reports-static")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
