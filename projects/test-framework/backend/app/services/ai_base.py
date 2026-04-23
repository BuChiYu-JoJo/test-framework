# -*- coding: utf-8 -*-
"""
AI Base Service - MiniMax API 统一封装
支持 text 和 vision 模式，内置重试和错误处理
"""

import json
import base64
import time
import logging
from typing import Optional, Union, List
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAPIError(Exception):
    """AI API 调用异常"""
    pass


class AiBaseService:
    """
    MiniMax AI API 基类服务

    支持：
    - text mode: 文本对话
    - vision mode: 图片分析（Vision API）

    环境变量：
    - MINIMAX_API_KEY: API 密钥
    - MINIMAX_BASE_URL: API 地址（默认 https://api.minimaxi.com）
    - MINIMAX_GROUP_ID: Group ID
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.minimaxi.com",
        model: str = "MiniMax-M2.7",
        vision_model: str = "MiniMax-M2.7",
        timeout: int = 120,
        max_retries: int = 2,
        group_id: str = "",
    ):
        self.api_key = api_key or settings.minimax_api_key or ""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.group_id = group_id or settings.minimax_group_id or ""

    # ─── 核心请求方法 ────────────────────────────────────────────────

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _do_request(self, url: str, body: dict) -> dict:
        """
        通用 HTTP POST 请求（内置重试）
        """
        import urllib.request
        import urllib.error

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._build_headers(),
            method="POST",
        )

        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read())
                    base_resp = result.get("base_resp", {})
                    status = base_resp.get("status_code", result.get("status_code", 0))
                    if status == 0:
                        return result
                    # 限流重试
                    if status in (429, 1301):
                        wait = float(base_resp.get("next_process_time", 2))
                        logger.warning(f"[AiBase] rate limit, retry in {wait}s")
                        time.sleep(min(wait, 30))
                        continue
                    raise AIAPIError(f"API error: {result}")
            except urllib.error.HTTPError as e:
                body_str = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    logger.warning(f"[AiBase] 429 rate limit, retry {attempt+1}")
                    time.sleep(5 * (attempt + 1))
                    last_err = e
                    continue
                raise AIAPIError(f"HTTP {e.code}: {body_str[:200]}")
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise AIAPIError(f"Request failed after {self.max_retries} retries: {e}")

        raise last_err or AIAPIError("Unknown error")

    # ─── Text Mode ───────────────────────────────────────────────────

    def chat(
        self,
        messages: List[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        文本对话模式

        Args:
            messages: [{"role": "user"/"assistant"/"system", "content": "...", "name": "..."}, ...]
            model: 模型名称（默认使用 self.model）
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            AI 回复文本
        """
        model = model or self.model
        url = f"{self.base_url}/v1/text/chatcompletion_v2"

        # 为每条消息补充 name 字段（MiniMax 要求 role 有 name）
        enhanced_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            name = msg.get("name")
            if role == "system":
                name = name or "MiniMax AI"
            elif role == "user":
                name = name or "用户"
            else:  # assistant
                name = name or "MiniMax AI"
            enhanced_messages.append({
                "role": role,
                "content": msg["content"],
                "name": name,
            })

        body = {
            "model": model,
            "messages": enhanced_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        result = self._do_request(url, body)
        try:
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except (KeyError, IndexError) as e:
            raise AIAPIError(f"Unexpected response format: {result}")

    # ─── Vision Mode ──────────────────────────────────────────────────

    def vision(
        self,
        image: Union[str, Path],
        prompt: str,
        model: str = "",
    ) -> str:
        """
        Vision 模式：分析图片并回答问题

        Args:
            image: 图片路径或 URL
            prompt: 分析指令
            model: Vision 模型名称

        Returns:
            AI 对图片的分析结果文本
        """
        model = model or self.vision_model
        url = f"{self.base_url}/v1/text/chatcompletion_v2"

        # 处理图片（本地文件转 base64，URL 则直接传递）
        if str(image).startswith(("http://", "https://")):
            img_data = str(image)
        else:
            img_path = Path(image)
            if not img_path.exists():
                raise AIAPIError(f"Image not found: {image}")
            with open(img_path, "rb") as f:
                img_data = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

        # MiniMax Vision：图片通过 messages 中的 image_url 类型传递
        enhanced_messages = [
            {
                "role": "user",
                "name": "用户",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_data}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        body = {
            "model": model,
            "messages": enhanced_messages,
        }

        result = self._do_request(url, body)
        try:
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except (KeyError, IndexError):
            raise AIAPIError(f"Unexpected vision response: {result}")

    # ─── 便捷工具方法 ────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        """
        简化的 generate 接口（单轮对话）

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            **kwargs: 透传给 chat
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)
