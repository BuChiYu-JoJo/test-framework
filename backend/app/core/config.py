# -*- coding: utf-8 -*-
"""
Core Configuration - 应用配置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# 项目根目录（backend 的上级目录）
BASE_DIR = Path(__file__).parent.parent.parent.parent

# 加载 backend/.env 文件（注意：.env 在 backend/ 子目录下）
ENV_FILE = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_FILE)
PROJECTS_DIR = BASE_DIR / "projects"


class Settings(BaseModel):
    """应用配置"""

    # 应用
    app_name: str = "Test Framework API"
    app_version: str = "1.0.0"
    debug: bool = True

    # 数据库
    db_url: str = "sqlite:///./test_framework.db"
    db_echo: bool = False

    # 执行引擎
    engine_base_url: str = "http://test-qzxbjwry.dataify-dev.com"
    engine_headless: bool = True
    engine_timeout: int = 300

    # 报告存储
    reports_dir: str = str(BASE_DIR / "reports")
    screenshots_dir: str = str(BASE_DIR / "screenshots")

    # 文件上传
    upload_dir: str = str(BASE_DIR / "uploads")
    max_upload_size: int = 10 * 1024 * 1024

    # 秘钥
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24

    # 项目配置目录
    projects_dir: str = str(PROJECTS_DIR)

    # 飞书通知
    feishu_webhook: str = ""
    notify_on_completion: bool = False

    # MiniMax AI（直接从环境变量读取，绕过 pydantic v2 BaseModel 的 env 限制）
    minimax_api_key: str = os.getenv("MINIMAX_API_KEY", "")
    minimax_group_id: str = os.getenv("MINIMAX_GROUP_ID", "")


# 全局单例
settings = Settings()
