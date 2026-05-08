# -*- coding: utf-8 -*-
"""
PRD Parser Service - AI 解析 PRD 文档为结构化功能点
输入 PRD Markdown → 输出 [{module, name, description, priority, test_points}, ...]
"""

import json
import logging
import re
from typing import List, Dict, Any

from app.services.ai_base import AiBaseService, AIAPIError

logger = logging.getLogger(__name__)

PRD_PARSER_SYSTEM_PROMPT = """你是一个专业的测试架构师，擅长从 PRD 文档中提取测试要点。

输出格式（严格 JSON，不要任何其他内容）：
[{"module":"模块名","name":"功能名","description":"描述","priority":"P0","test_points":[{"point":"测试点","action_type":"click","expected":"预期"}],"ui_elements":[{"name":"元素名","description":"作用"}]}]

重要规则：
- 只输出 3 个最核心的功能点
- 一个功能点最多 3 个 test_points
- 使用紧凑 JSON 格式（无缩进无换行）
- 不要 markdown 代码块包裹
- 不要输出任何解释性文字
- 确保输出完整的 JSON 数组
"""


class PRDParseError(Exception):
    """PRD 解析异常"""
    pass


class PRDParserService:
    """
    PRD 文档 AI 解析服务
    
    将 PRD Markdown 输入 → 结构化功能点列表
    """

    def __init__(self):
        self.ai = AiBaseService()

    def parse(self, prd_content: str, product_name: str = "") -> List[Dict[str, Any]]:
        """
        解析 PRD 文档
        
        Args:
            prd_content: PRD Markdown 内容
            product_name: 产品名称（可选，用于增强上下文）
        
        Returns:
            List[Dict]，每个元素是一个功能点的结构化描述
        """
        prompt = self._build_prompt(prd_content, product_name)

        try:
            result_text = self.ai.generate(
                prompt,
                system_prompt=PRD_PARSER_SYSTEM_PROMPT,
                max_tokens=4096,
            )
            return self._parse_json_response(result_text)
        except AIAPIError as e:
            logger.error(f"[PRDParser] AI API failed: {e}")
            raise PRDParseError(f"PRD 解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"[PRDParser] Unexpected error: {e}")
            raise PRDParseError(f"PRD 解析异常: {str(e)}")

    def _build_prompt(self, prd_content: str, product_name: str) -> str:
        """构建解析 prompt"""
        parts = []
        if product_name:
            parts.append(f"产品：{product_name}\n")
        parts.append(f"PRD：\n{prd_content[:8000]}\n")
        parts.append("\n输出3个核心功能点的紧凑JSON数组，不要其他内容。")
        return "".join(parts)

    def _parse_json_response(self, text: str) -> List[Dict[str, Any]]:
        """解析 AI 返回的 JSON"""
        text = text.strip()

        # 尝试直接解析（无 markdown 包裹）
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"[PRDParser] direct parse failed: {e}")

        # 尝试提取代码块
        json_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])```", text, re.MULTILINE)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 JSON 数组
        array_match = re.search(r"(\[\s*\{[\s\S]*\])", text)
        if array_match:
            try:
                return json.loads(array_match.group(1))
            except json.JSONDecodeError:
                pass

        raise PRDParseError(f"无法解析 PRD 返回内容: {text[:300]}")
