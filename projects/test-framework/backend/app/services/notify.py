# -*- coding: utf-8 -*-
"""
Notify Service - 执行完成通知服务
支持飞书 Webhook 推送
"""
import json
import urllib.request
from typing import Optional
from app.core.config import settings


class FeishuNotifier:
    """飞书 Webhook 通知器"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or getattr(settings, 'feishu_webhook', None)
        self.enabled = bool(self.webhook_url)

    def send(self, msg: str, msg_type: str = "text") -> bool:
        """
        发送飞书消息
        
        Args:
            msg: 消息内容
            msg_type: text 或 interactive
        """
        if not self.enabled:
            print(f"[FeishuNotifier] Webhook 未配置，跳过通知: {msg[:50]}", flush=True)
            return False

        payload = {"msg_type": msg_type}
        if msg_type == "text":
            payload["content"] = {"text": msg}
        else:
            payload["card"] = msg  # interactive card

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    print(f"[FeishuNotifier] 发送成功", flush=True)
                    return True
                else:
                    print(f"[FeishuNotifier] 发送失败: {result}", flush=True)
                    return False
        except Exception as e:
            print(f"[FeishuNotifier] 发送异常: {e}", flush=True)
            return False

    def send_execution_result(
        self,
        execution_id: str,
        case_name: str,
        result: str,
        duration_ms: int,
        error_msg: str = None,
        report_url: str = None,
    ):
        """发送执行结果通知"""
        # 状态标签
        if result == "passed":
            emoji = "✅"
            status_text = "通过"
        elif result == "failed":
            emoji = "❌"
            status_text = "失败"
        else:
            emoji = "⚠️"
            status_text = "异常"

        duration_s = duration_ms / 1000 if duration_ms else 0
        lines = [
            f"{emoji} **用例执行{status_text}**",
            f"",
            f"**用例名称**：{case_name}",
            f"**执行ID**：{execution_id}",
            f"**执行结果**：{status_text}",
            f"**耗时**：{duration_s:.1f}s",
        ]
        if error_msg:
            lines.append(f"**错误信息**：{error_msg[:100]}")
        if report_url:
            lines.append(f"**报告链接**：[查看报告]({report_url})")

        msg = "\n".join(lines)
        self.send(msg)  # send() 内部处理 enabled=False 的情况


# 全局单例（延迟初始化）
_notifier: Optional[FeishuNotifier] = None


def get_notifier() -> FeishuNotifier:
    global _notifier
    if _notifier is None:
        _notifier = FeishuNotifier()
    return _notifier


def notify_execution_complete(
    execution_id: str,
    case_name: str,
    result: str,
    duration_ms: int,
    error_msg: str = None,
    report_url: str = None,
):
    """快捷函数：发送执行完成通知"""
    get_notifier().send_execution_result(
        execution_id=execution_id,
        case_name=case_name,
        result=result,
        duration_ms=duration_ms,
        error_msg=error_msg,
        report_url=report_url,
    )
