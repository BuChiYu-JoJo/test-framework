# -*- coding: utf-8 -*-
"""
Test Framework API - FastAPI 主应用
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import router as api_v1_router


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="通用自动化测试框架 - 后端 API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS（允许前端跨域访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 初始化数据库
    @app.on_event("startup")
    def on_startup():
        init_db()
        from app.services.scheduler import start_scheduler
        start_scheduler()

    @app.on_event("shutdown")
    def on_shutdown():
        from app.services.scheduler import stop_scheduler
        stop_scheduler()

    # 健康检查
    @app.get("/health")
    def health_check():
        return {"status": "ok", "version": settings.app_version}

    # 注册路由
    app.include_router(api_v1_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
