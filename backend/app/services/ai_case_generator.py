# -*- coding: utf-8 -*-
"""
AI Case Generator Service - AI 辅助生成测试用例
解析自然语言需求 → YAML 结构，或分析页面截图 → 推断测试步骤
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from app.services.ai_base import AiBaseService, AIAPIError

logger = logging.getLogger(__name__)


CASE_GENERATOR_SYSTEM_PROMPT = """你是一个专业的测试用例工程师，擅长根据需求描述生成结构化的测试用例 YAML。

输出格式要求（严格遵循）：
```yaml
id: TC{timestamp}
name: <用例名称，简短描述测试目标>
module: <模块名称，如 login、dashboard、order>
priority: <P0/P1/P2/P3，P0 最高>
tags: [<标签1>, <标签2>]
steps:
  - action: <操作类型，如 navigate/click/type/assert等>
    target: <目标元素描述>
    value: <输入值或预期值>
    description: <步骤描述>
  - ...
expected: <预期结果描述>
```

重要规则：
- id 使用时间戳后6位确保唯一
- steps 中的 action 只允许：navigate / click / type / select / assert / wait / switch / hover
- 每个用例必须至少有 navigate 和 assert 步骤
- priority 根据用例重要性合理分配（P0=核心流程、P1=重要功能、P2=一般功能、P3=边缘情况）
- module 应与被测系统模块对应

请直接输出 YAML，不要包含任何解释文字。"""


class AICaseGeneratorService:
    """
    AI 生成测试用例服务
    
    支持两种模式：
    1. text mode: 输入自然语言描述 → YAML 结构
    2. vision mode: 输入页面截图 → 推断测试步骤
    """

    def __init__(self):
        self.ai = AiBaseService()
        self._case_counter = 0

    def generate_from_description(
        self,
        description: str,
        module: str = "",
        priority: str = "P2",
        screenshot: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        根据自然语言描述生成测试用例
        
        Args:
            description: 自然语言需求描述
            module: 模块名
            priority: 优先级
            screenshot: 可选的页面截图
        
        Returns:
            {"yaml_content": "...", "case_id": "TCxxx", "raw_ai_response": "..."}
        """
        timestamp = self._generate_case_id()
        case_id = f"TC{timestamp}"

        # 拼装 prompt
        prompt = self._build_description_prompt(description, module, priority, case_id)

        if screenshot:
            # Vision 模式：同时传入截图
            result_text = self._vision_with_text(prompt, screenshot)
        else:
            # 纯文本模式
            result_text = self.ai.generate(prompt, system_prompt=CASE_GENERATOR_SYSTEM_PROMPT)

        yaml_content = self._parse_yaml_response(result_text)

        return {
            "yaml_content": yaml_content,
            "case_id": case_id,
            "raw_ai_response": result_text,
        }

    def enhance_case_from_screenshot(
        self,
        yaml_content: str,
        screenshot: bytes,
    ) -> str:
        """
        根据页面截图补全/增强已有用例的 steps
        
        Args:
            yaml_content: 已有 YAML 内容
            screenshot: 页面截图 bytes
        
        Returns:
            增强后的 YAML 文本
        """
        prompt = (
            f"请分析这个页面截图，然后增强以下测试用例的 steps。"
            f"保持原有的 id、name、module、priority 不变，"
            f"只更新 steps 部分，使步骤与实际页面元素匹配。\n\n"
            f"已有用例：\n{yaml_content}\n\n"
            f"请直接输出增强后的完整 YAML。"
        )

        return self._vision_with_text(prompt, screenshot)

    # ─── 内部方法 ───────────────────────────────────────────────────

    def _generate_case_id(self) -> str:
        """生成唯一用例 ID"""
        import time
        self._case_counter += 1
        ts = str(int(time.time()))[-6:]
        return f"{ts}{self._case_counter:02d}"

    def _build_description_prompt(
        self,
        description: str,
        module: str,
        priority: str,
        case_id: str,
    ) -> str:
        """构建描述 prompt"""
        parts = [
            f"需求描述：{description}",
        ]
        if module:
            parts.append(f"所属模块：{module}")
        if priority:
            parts.append(f"建议优先级：{priority}")
        parts.append(f"\n请生成对应的测试用例 YAML，id 使用 {case_id}。")

        return "\n".join(parts)

    def _vision_with_text(self, prompt: str, screenshot: bytes) -> str:
        """Vision + text 双模态分析"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(screenshot)
            tmp_path = tmp.name

        try:
            enhanced_prompt = (
                prompt + "\n\n[请分析页面截图，结合实际元素生成最准确的用例]"
            )
            return self.ai.vision(tmp_path, enhanced_prompt)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _parse_yaml_response(self, text: str) -> str:
        """
        解析 AI 返回文本，提取 YAML 内容
        
        支持：
        1. 纯 YAML
        2. Markdown 代码块 ```yaml ... ```
        3. 混在文字中的 YAML 块
        """
        text = text.strip()

        # 尝试提取 markdown 代码块
        yaml_match = re.search(
            r"```(?:yaml)?\s*(id:[\s\S]*?)```",
            text,
            re.MULTILINE
        )
        if yaml_match:
            return yaml_match.group(1).strip()

        # 尝试直接找 yaml 内容
        if re.search(r"^id:", text, re.MULTILINE):
            return text.strip()

        # 尝试找 ``` 包裹的内容
        code_match = re.search(r"```([\s\S]*?)```", text)
        if code_match:
            content = code_match.group(1).strip()
            if "id:" in content or "name:" in content:
                return content

        logger.warning(f"[AICaseGenerator] could not parse YAML from response: {text[:200]}")
        return text.strip()
