"""
用例校验器 - 执行前检查用例问题
"""

from typing import Any, Dict, List, Optional


class CaseValidator:
    """用例校验器，检查常见错误"""

    VALID_ACTIONS = {
        'navigate', 'go', 'open',
        'click', 'dblclick', 'rightclick', 'right_click',
        'type', 'fill', 'input', 'clear',
        'select', 'check', 'uncheck',
        'wait', 'wait_for', 'wait_for_url', 'wait_for_element',
        'assert_text', 'assert_visible', 'assert_hidden', 'assert_count',
        'assert_url', 'assert_element_exists',
        'api_request', 'api_get', 'api_post',
        'screenshot', 'refresh', 'back', 'forward',
        'scroll', 'hover', 'execute_js',
        'upload', 'clear_cookies', 'clear_browser_cookies',
    }

    VALID_EXPECTATIONS = {
        'url_contains', 'url_not_contains',
        'element_visible', 'element_not_visible',
    }

    def __init__(self, locator_resolver=None):
        self.locator_resolver = locator_resolver
        self.issues: List[Dict[str, Any]] = []

    def validate(self, case_data: Dict) -> List[Dict[str, Any]]:
        """
        校验用例，返回问题列表
        
        Args:
            case_data: 用例数据字典
            
        Returns:
            issues: 问题列表，每项 {step_no, type, message, severity}
            severity: error(必须修复) / warning(建议修复)
        """
        self.issues = []
        
        case_id = case_data.get("id", "unknown")
        
        # 1. 检查 steps
        steps = case_data.get("steps", [])
        if not steps:
            self._add_issue(
                step_no=0,
                type="missing_steps",
                message=f"用例 {case_id} 没有定义 steps",
                severity="error"
            )
        
        for step in steps:
            self._validate_step(step)
        
        # 2. 检查 expected
        expected = case_data.get("expected", [])
        if not expected:
            self._add_issue(
                step_no=0,
                type="missing_expected",
                message=f"用例 {case_id} 没有定义 expected（无断言）",
                severity="warning"
            )
        else:
            for exp in expected:
                self._validate_expectation(exp)
        
        # 3. 检查 data 变量
        data = case_data.get("data", {})
        self._check_variables_in_steps(steps, data)
        
        return self.issues

    def _validate_step(self, step: Dict):
        """检查单个步骤"""
        action = step.get("action", "").strip().lower()
        target = step.get("target", "")
        value = step.get("value")
        step_no = step.get("no", "?")
        
        if not action:
            self._add_issue(
                step_no=step_no,
                type="missing_action",
                message=f"Step {step_no}: 缺少 action",
                severity="error"
            )
            return
        
        # 检查 action 是否合法
        if action not in self.VALID_ACTIONS:
            # 尝试模糊匹配
            matched = next(
                (kw for kw in self.VALID_ACTIONS if kw in action or action in kw),
                None
            )
            if matched:
                self._add_issue(
                    step_no=step_no,
                    type="typo_action",
                    message=f"Step {step_no}: action '{action}' 疑似应为 '{matched}'",
                    severity="warning"
                )
            else:
                self._add_issue(
                    step_no=step_no,
                    type="unknown_action",
                    message=f"Step {step_no}: action '{action}' 未知",
                    severity="error"
                )
        
        # 检查 locator 引用格式
        if target and isinstance(target, str):
            if "." in target:
                group, key = target.split(".", 1)
                if self.locator_resolver:
                    locator = self.locator_resolver.resolve(target)
                    if locator is None:
                        self._add_issue(
                            step_no=step_no,
                            type="locator_not_found",
                            message=f"Step {step_no}: locator '{target}' 不存在（group={group}, key={key}）",
                            severity="error"
                        )
        
        # 检查 type 步骤有 value
        if action in ("type", "fill", "input"):
            if not value and value != 0:
                self._add_issue(
                    step_no=step_no,
                    type="missing_value",
                    message=f"Step {step_no}: {action} 操作缺少 value",
                    severity="warning"
                )
        
        # 检查 wait value
        if action == "wait":
            if not value:
                self._add_issue(
                    step_no=step_no,
                    type="missing_wait_value",
                    message=f"Step {step_no}: wait 操作缺少 value（秒数）",
                    severity="warning"
                )

    def _validate_expectation(self, exp: Dict):
        """检查预期结果"""
        if not exp:
            return
        
        exp_type = list(exp.keys())[0] if exp else None
        exp_value = list(exp.values())[0] if exp else None
        
        if exp_type not in self.VALID_EXPECTATIONS:
            self._add_issue(
                step_no=0,
                type="unknown_expectation",
                message=f"expected 类型 '{exp_type}' 未知，支持: {', '.join(self.VALID_EXPECTATIONS)}",
                severity="error"
            )
        
        if exp_type in ("url_contains", "url_not_contains"):
            if not exp_value:
                self._add_issue(
                    step_no=0,
                    type="missing_expectation_value",
                    message=f"expected {exp_type} 缺少值",
                    severity="error"
                )

    def _check_variables_in_steps(self, steps: List[Dict], data: Dict):
        """检查 steps 中引用的 ${VAR} 是否在 data 中定义"""
        import re
        var_pattern = re.compile(r'\$\{(\w+)\}')
        
        for step in steps:
            for field in ("target", "value"):
                val = step.get(field, "")
                if not isinstance(val, str):
                    continue
                    
                for var_name in var_pattern.findall(val):
                    if var_name not in data:
                        self._add_issue(
                            step_no=step.get("no", "?"),
                            type="undefined_variable",
                            message=f"Step {step.get('no', '?')}: 变量 ${{{var_name}}} 未在 data 中定义",
                            severity="error"
                        )

    def _add_issue(self, step_no: int, type: str, message: str, severity: str = "error"):
        """添加问题"""
        self.issues.append({
            "step_no": step_no,
            "type": type,
            "message": message,
            "severity": severity,
        })


def validate_case(case_data: Dict, locator_resolver=None) -> List[Dict[str, Any]]:
    """
    便捷函数：校验单个用例
    """
    validator = CaseValidator(locator_resolver)
    return validator.validate(case_data)


def validate_case_file(case_path: str, locator_resolver=None) -> List[Dict[str, Any]]:
    """
    便捷函数：校验用例文件
    """
    from pathlib import Path
    
    path = Path(case_path)
    case_data = None
    
    if path.suffix in (".yaml", ".yml"):
        import yaml
        with open(path, encoding="utf-8") as f:
            case_data = yaml.safe_load(f)
    elif path.suffix in (".xlsx", ".xls"):
        # 简单读取，不依赖 excel 解析器
        case_data = {"id": path.stem, "steps": [], "expected": []}
    else:
        return [{"step_no": 0, "type": "unknown_format", "message": f"不支持的文件格式: {path.suffix}", "severity": "error"}]
    
    return validate_case(case_data, locator_resolver)
