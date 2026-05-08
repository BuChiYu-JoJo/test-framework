# -*- coding: utf-8 -*-
"""
Event Bus - 轻量级内存事件总线
用于执行步骤实时推送 + debug 日志
"""
import asyncio
import threading
import time
from typing import Dict, List
from collections import defaultdict


class EventBus:
    """全局事件总线"""

    def __init__(self):
        self._subscribers: Dict[str, list] = defaultdict(list)
        # debug 日志缓冲（线程安全）
        self._debug_logs: Dict[str, List[dict]] = defaultdict(list)
        self._debug_lock = threading.Lock()
        self._max_logs_per_execution = 500

    def subscribe(self, execution_id: str) -> asyncio.Queue:
        """订阅某个执行ID的事件流"""
        queue = asyncio.Queue(maxsize=50)
        self._subscribers[execution_id].append(queue)
        return queue

    def unsubscribe(self, execution_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if execution_id in self._subscribers:
            try:
                self._subscribers[execution_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[execution_id]:
                del self._subscribers[execution_id]

    def publish(self, execution_id: str, event: dict):
        """发布事件给所有订阅者"""
        if execution_id not in self._subscribers:
            return
        dead = []
        for queue in self._subscribers[execution_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self.unsubscribe(execution_id, q)

    # ─── Debug 日志（线程安全）────────────────────────

    def append_debug_log(self, execution_id: str, level: str, message: str, meta: dict = None):
        """追加 debug 日志（线程安全）"""
        with self._debug_lock:
            logs = self._debug_logs[execution_id]
            logs.append({
                "ts": time.time(),
                "level": level,
                "message": message,
                "meta": meta or {},
            })
            # 限制大小，防止内存泄漏
            if len(logs) > self._max_logs_per_execution:
                logs[:] = logs[-self._max_logs_per_execution:]

    def get_debug_logs(self, execution_id: str) -> List[dict]:
        """获取当前所有 debug 日志"""
        with self._debug_lock:
            return list(self._debug_logs.get(execution_id, []))

    def clear_debug_logs(self, execution_id: str):
        """清除 debug 日志"""
        with self._debug_lock:
            self._debug_logs.pop(execution_id, None)

    def subscribe_debug(self, execution_id: str) -> asyncio.Queue:
        """订阅 debug 日志流（返回一个新的每次消费的 queue）"""
        queue = asyncio.Queue(maxsize=200)
        self._subscribers[f"debug:{execution_id}"].append(queue)
        return queue


# 全局单例
event_bus = EventBus()
