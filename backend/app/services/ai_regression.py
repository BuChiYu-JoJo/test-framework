# -*- coding: utf-8 -*-
"""
AI Regression Service - 智能回归选择服务
根据代码/配置变动，智能选择需要回归的用例
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.services.ai_base import AiBaseService, AIAPIError

logger = logging.getLogger(__name__)


REGRESSION_SYSTEM_PROMPT = """你是一个专业的测试策略分析师，擅长根据代码变更范围确定需要回归的测试用例。

你的任务：
1. 分析变更文件列表，判断影响范围
2. 将变更映射到相关模块/页面
3. 识别需要回归的高风险用例

输出格式（严格 JSON）：
{
  "selected_cases": [
    {"case_id": "TC001", "module": "login", "risk_score": 0.9, "reason": "直接修改了登录核心逻辑"},
    ...
  ],
  "reason": "总述影响范围和选择理由",
  "impact_modules": ["login", "auth"],
  "risk_level": "HIGH|MEDIUM|LOW"
}

risk_score 规则：
- 0.9-1.0：核心模块直接变更，影响登录/支付等关键流程
- 0.7-0.9：重要模块变更，UI 或 API 接口修改
- 0.5-0.7：辅助模块变更，相关联动功能可能受影响
- 0.3-0.5：边缘配置变更，影响较小

重要规则：
- 只选择与变更直接相关的用例，不要泛选
- 如果模块名能从文件名推断（如 login.vue → login 模块），优先精确映射
- 配置文件变更（如 .env、config.json）通常需要全量回归
- 直接修改数据库 schema 需要最高级别关注"""


class AIRegressionService:
    """
    智能回归选择服务
    
    工作流程：
    1. 接收变更文件列表
    2. 调用 MiniMax AI 分析影响范围
    3. 从数据库查询相关用例
    4. 输出带风险评分的用例列表
    """

    def __init__(self):
        self.ai = AiBaseService()

    def select_regression_cases(
        self,
        changed_files: List[str],
        project_id: int,
        db=None,
        module_case_map: Optional[Dict[str, List]] = None,
    ) -> Dict[str, Any]:
        """
        智能选择需要回归的用例
        
        Args:
            changed_files: 变更文件列表
            project_id: 项目 ID
            db: SQLAlchemy session（用于查询用例）
            module_case_map: 可选的 module → case_id 映射（如果没传 db，则用此映射）
        
        Returns:
            {
              "selected_cases": [...],
              "reason": "...",
              "impact_modules": [...],
              "risk_level": "HIGH",
            }
        """
        # 1. AI 分析影响范围
        analysis = self._analyze_impact(changed_files)

        # 2. 收集相关用例
        selected_cases = []
        if db and module_case_map is None:
            # 从数据库查询
            selected_cases = self._query_cases_from_db(
                analysis["impact_modules"],
                project_id,
                db,
            )
        elif module_case_map:
            # 使用内存映射
            selected_cases = self._map_cases_from_list(
                analysis["impact_modules"],
                module_case_map,
            )
        else:
            # 无用例源，返回 AI 分析结果
            selected_cases = analysis.get("selected_cases", [])

        return {
            "selected_cases": selected_cases,
            "reason": analysis.get("reason", ""),
            "impact_modules": analysis.get("impact_modules", []),
            "risk_level": analysis.get("risk_level", "MEDIUM"),
        }

    # ─── 内部方法 ───────────────────────────────────────────────────

    def _analyze_impact(self, changed_files: List[str]) -> Dict[str, Any]:
        """
        调用 AI 分析变更影响
        
        Returns:
            AI 返回的结构化分析结果
        """
        files_str = "\n".join(f"- {f}" for f in changed_files)

        prompt = (
            f"请分析以下变更文件列表，判断影响范围并选择需要回归的用例。\n"
            f"变更文件：\n{files_str}\n\n"
            f"请输出 JSON 格式的分析结果。"
        )

        result_text = self.ai.generate(prompt, system_prompt=REGRESSION_SYSTEM_PROMPT)

        return self._parse_analysis_response(result_text)

    def _parse_analysis_response(self, text: str) -> Dict[str, Any]:
        """解析 AI 返回的分析 JSON"""
        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块提取
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 块
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"[AIRegression] could not parse analysis: {text[:200]}")
        return {
            "selected_cases": [],
            "reason": f"AI 分析失败，人工检查以下文件：{', '.join(changed_files)}",
            "impact_modules": [],
            "risk_level": "MEDIUM",
            "changed_files": changed_files,
        }

    def _query_cases_from_db(
        self,
        modules: List[str],
        project_id: int,
        db,
    ) -> List[Dict[str, Any]]:
        """从数据库查询相关用例"""
        from app.models.case import Case

        if not modules:
            return []

        cases = (
            db.query(Case)
            .filter(Case.project_id == project_id)
            .filter(Case.module.in_(modules))
            .all()
        )

        return [
            {
                "id": c.id,
                "case_id": c.case_id,
                "name": c.name,
                "module": c.module,
                "priority": c.priority,
            }
            for c in cases
        ]

    def _map_cases_from_list(
        self,
        modules: List[str],
        module_case_map: Dict[str, List],
    ) -> List[Dict[str, Any]]:
        """从内存映射表收集用例"""
        result = []
        for module in modules:
            cases = module_case_map.get(module, [])
            for c in cases:
                result.append(c)
        return result
