# -*- coding: utf-8 -*-
"""
Settings API - 系统设置 API
目前支持：飞书通知配置读写
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings


router = APIRouter(prefix="/settings", tags=["Settings"])

# 配置文件路径（放在项目根目录的 .env.local）
SETTINGS_FILE = Path(__file__).parent.parent.parent.parent / ".env.local"


class NotifySettings(BaseModel):
    feishu_webhook: str = ""
    notify_on_completion: bool = False


def _load_settings() -> dict:
    """从本地配置文件加载设置"""
    if not SETTINGS_FILE.exists():
        return {}
    settings_obj = {}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    settings_obj[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        pass
    return settings_obj


def _save_settings(feishu_webhook: str, notify_on_completion: bool):
    """保存设置到本地配置文件"""
    settings_obj = _load_settings()
    settings_obj["FEISHU_WEBHOOK"] = feishu_webhook
    settings_obj["NOTIFY_ON_COMPLETION"] = str(notify_on_completion).lower()

    lines = [f'{k}="{v}"\n' for k, v in settings_obj.items()]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


@router.get("/notify")
def get_notify_settings():
    """获取当前通知设置"""
    obj = _load_settings()
    return {
        "feishu_webhook": obj.get("FEISHU_WEBHOOK", ""),
        "notify_on_completion": obj.get("NOTIFY_ON_COMPLETION", "false").lower() == "true",
    }


@router.post("/notify")
def save_notify_settings(data: NotifySettings):
    """保存通知设置"""
    _save_settings(data.feishu_webhook, data.notify_on_completion)
    # 同时更新运行时 settings（当前进程内生效，重启后从文件加载）
    settings.feishu_webhook = data.feishu_webhook
    settings.notify_on_completion = data.notify_on_completion
    return {"message": "设置已保存"}


class TestNotifyRequest(BaseModel):
    feishu_webhook: str


@router.post("/notify/test")
def test_notify(data: TestNotifyRequest):
    """发送测试消息"""
    if not data.feishu_webhook:
        raise HTTPException(status_code=400, detail="Webhook 地址不能为空")

    from app.services.notify import FeishuNotifier
    notifier = FeishuNotifier(webhook_url=data.feishu_webhook)
    success = notifier.send("🧪 这是一条测试消息，来自 Test Framework 通知配置。")

    if success:
        return {"message": "测试消息发送成功"}
    else:
        raise HTTPException(status_code=500, detail="发送失败，请检查 Webhook 地址是否正确")
