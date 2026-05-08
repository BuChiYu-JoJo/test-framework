# -*- coding: utf-8 -*-
"""
AI Case From PRD Service - PRD 文档直接生成测试用例
PRD Markdown → 结构化功能点 → 批量生成用例 → 存入数据库
"""

import json
import re
import yaml
import logging
import time
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.services.ai_base import AiBaseService, AIAPIError
from app.models.case import Case
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

CASE_FROM_PRD_SYSTEM_PROMPT = """你是一个专业的测试用例工程师，根据 PRD 文档直接生成 YAML 测试用例。

输出格式（严格 YAML，不要 markdown 包裹，不要解释）：
```yaml
id: TC{timestamp}
name: <用例名称>
module: <模块名>
priority: P0/P1/P2/P3
tags: [<标签>]
steps:
  - action: navigate/click/type/select/assert/wait/switch
    target: "[元素描述]"
    value: <值>
    description: <步骤描述>
expected: <预期结果>
---
id: TC{timestamp+1}
name: <用例名称>
module: <模块名>
priority: P0/P1/P2/P3
tags: [<标签>]
steps:
  - action: navigate
    target: "[元素描述]"
    value: <URL或值>
    description: <步骤描述>
  - action: click
    target: "[元素描述]"
    description: <步骤描述>
expected: <预期结果>
```

重要规则：
- 每个用例 id 唯一，使用时间戳后4位+序号
- steps 中的 target 使用中文元素描述如 [登录按钮]、[邮箱输入框]，不要硬编码 selector
- 一个功能点生成 1-2 个核心用例即可
- 只输出 YAML，不要任何解释文字
- 一次性输出所有用例的完整 YAML，不要截断
- 优先输出 P0 和 P1 用例
"""


class CaseFromPRDError(Exception):
    """从 PRD 生成用例异常"""
    pass


class AICaseFromPRDService:
    """
    PRD → 用例 完整流程服务
    
    直接从 PRD Markdown 生成 YAML 用例，存入数据库
    """

    def __init__(self):
        self.ai = AiBaseService()

    def generate_from_prd(
        self,
        prd_content: str,
        project_id: int,
        product_name: str = "",
        author: str = "AI",
    ) -> Dict[str, Any]:
        """
        从 PRD 生成用例完整流程
        
        Args:
            prd_content: PRD Markdown 内容
            project_id: 项目 ID
            product_name: 产品名称（可选）
            author: 用例作者
        
        Returns:
            {
                "total": 总数,
                "success": 成功数,
                "failed": 失败数,
                "cases": [{"case_id": ..., "module": ..., "name": ..., "priority": ...}, ...],
                "errors": [{"module": ..., "error": ...}, ...]
            }
        """
        # 直接从 PRD 生成 YAML 用例
        yaml_cases = self._generate_yaml_from_prd(prd_content, product_name)

        if not yaml_cases:
            raise CaseFromPRDError("PRD 解析结果为空，请检查 PRD 格式")

        # 解析 YAML 并存入数据库
        results = {
            "total": len(yaml_cases),
            "success": 0,
            "failed": 0,
            "cases": [],
            "errors": [],
        }

        for yaml_case in yaml_cases:
            try:
                case_info = self._save_case(yaml_case, project_id, author)
                results["cases"].append(case_info)
                results["success"] += 1
            except Exception as e:
                logger.error(f"[CaseFromPRD] Failed to save case: {e}")
                results["errors"].append({
                    "module": yaml_case.get("module", ""),
                    "name": yaml_case.get("name", ""),
                    "error": str(e),
                })
                results["failed"] += 1

        return results

    def _generate_yaml_from_prd(self, prd_content: str, product_name: str) -> List[Dict[str, Any]]:
        """从 PRD 直接生成 YAML 用例"""
        prompt_parts = []
        if product_name:
            prompt_parts.append(f"产品：{product_name}\n")
        prompt_parts.append(f"PRD 内容：\n{prd_content[:10000]}\n")
        prompt_parts.append("\n请根据以上 PRD 生成 3-5 个核心测试用例的 YAML，输出完整 YAML，不要截断。")

        prompt = "".join(prompt_parts)

        try:
            result_text = self.ai.generate(
                prompt,
                system_prompt=CASE_FROM_PRD_SYSTEM_PROMPT,
                max_tokens=4096,
            )
            return self._parse_yaml_cases(result_text)
        except AIAPIError as e:
            raise CaseFromPRDError(f"PRD → YAML 生成失败: {str(e)}")

    def _parse_yaml_cases(self, text: str) -> List[Dict[str, Any]]:
        """解析 AI 返回的 YAML 用例"""
        import yaml

        text = text.strip()

        # 尝试提取 yaml 代码块内容
        yaml_match = None
        # 处理多个 yaml 块（用 --- 分隔）
        parts = re.split(r"\n---\n", text)
        cases = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 去掉 markdown 代码块包裹
            code_match = re.search(r"```(?:yaml)?\s*([\s\S]*?)```", part, re.MULTILINE)
            if code_match:
                part = code_match.group(1).strip()

            if part.startswith("id:") or part.startswith("name:"):
                try:
                    case = yaml.safe_load(part)
                    if case and isinstance(case, dict):
                        cases.append(case)
                except yaml.YAMLError as e:
                    logger.warning(f"[CaseFromPRD] YAML parse failed: {e}")
                    continue

        if cases:
            return cases

        # 直接解析完整文本（可能有 --- 分隔）
        full_text = re.sub(r"```[\s\S]*?```", "", text)
        full_text = re.sub(r"^---", "\n---", full_text, flags=re.MULTILINE)
        parts = re.split(r"\n---\n", full_text)

        for part in parts:
            part = part.strip()
            if not part or not part.startswith("id:"):
                continue
            try:
                case = yaml.safe_load(part)
                if case and isinstance(case, dict):
                    cases.append(case)
            except yaml.YAMLError:
                continue

        if not cases:
            raise CaseFromPRDError(f"无法解析 YAML 用例: {text[:200]}")

        return cases

    def _save_case(
        self,
        yaml_case: Dict[str, Any],
        project_id: int,
        author: str,
    ) -> Dict[str, Any]:
        """解析用例 YAML 并存入数据库"""
        import time

        name = yaml_case.get("name", "未命名")
        module = yaml_case.get("module", "default")
        priority = yaml_case.get("priority", "P2")
        tags = yaml_case.get("tags", [])
        steps = yaml_case.get("steps", [])
        expected = yaml_case.get("expected", "")

        # 构建 case_id
        ts = int(time.time())
        case_id = yaml_case.get("id", f"TC{str(ts)[-6:]}")

        # 构建 YAML 内容
        yaml_content = yaml.dump({
            "id": case_id,
            "name": name,
            "module": module,
            "priority": priority,
            "tags": tags,
            "steps": steps,
            "expected": expected,
        }, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 存入数据库
        db = SessionLocal()
        try:
            case = Case(
                name=name,
                case_id=case_id,
                project_id=project_id,
                module=module,
                priority=priority,
                tags=json.dumps(tags if tags else [module, "ai-generated", "from-prd"]),
                content=yaml_content,
                author=author,
                version="1.0.0",
            )
            db.add(case)
            db.commit()
            db.refresh(case)

            return {
                "id": case.id,
                "case_id": case.case_id,
                "module": module,
                "name": name,
                "priority": priority,
                "yaml_content": yaml_content,
            }
        finally:
            db.close()
