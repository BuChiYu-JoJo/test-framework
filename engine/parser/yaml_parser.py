"""
YAML Parser - YAML格式用例解析器
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


class YamlParser:
    """YAML用例解析器"""
    
    def parse(self, file_path: str) -> Dict:
        """
        解析YAML用例文件
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            用例数据字典
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 验证必需字段
        self._validate(data)
        
        # 标准化数据格式
        return self._normalize(data)
    
    def _validate(self, data: Dict) -> None:
        """验证用例数据"""
        if not data:
            raise ValueError("Empty YAML file")
        
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(data.get('steps'), (list, dict)):
            raise ValueError("'steps' must be a list or dict")
    
    def _normalize(self, data: Dict) -> Dict:
        """
        标准化用例数据格式
        
        Args:
            data: 原始数据
            
        Returns:
            标准化后的数据
        """
        normalized = {
            'id': data.get('id', ''),
            'name': data.get('name', ''),
            'module': data.get('module', ''),
            'priority': data.get('priority', 'P2'),
            'tags': data.get('tags', []),
            'version': data.get('version', '1.0.0'),
            'author': data.get('author', ''),
            'created_at': data.get('created_at', ''),
            
            'setup': self._normalize_steps(data.get('setup', [])),
            'steps': self._normalize_steps(data.get('steps', [])),
            'teardown': self._normalize_steps(data.get('teardown', [])),
            
            'expected': self._normalize_expected(data.get('expected', [])),
            'data': data.get('data', {}),
            
            # 原始内容备用
            '_raw': data
        }
        
        return normalized
    
    def _normalize_steps(self, steps: Any) -> List[Dict]:
        """
        标准化步骤数据
        
        支持格式：
        1. [{no: 1, action: click, target: button}]
        2. [click: button, type: input#username|test]
        3. [{action: click, target: button}]
        """
        if not steps:
            return []
        
        result = []
        
        for i, step in enumerate(steps):
            if isinstance(step, str):
                # 简写格式: "click: button" 或 "type: input#username|test"
                normalized = self._parse_short_step(step)
                normalized['no'] = i + 1
                result.append(normalized)
                
            elif isinstance(step, dict):
                # 标准格式: {action: xxx, target: xxx, value: xxx}
                normalized = {
                    'no': step.get('no', i + 1),
                    'action': step.get('action', ''),
                    'target': step.get('target', ''),
                    'value': step.get('value', step.get('text', '')),
                    'description': step.get('description', '')
                }
                result.append(normalized)
        
        return result
    
    def _parse_short_step(self, step_str: str) -> Dict:
        """
        解析简写步骤格式
        
        支持格式：
        - "navigate: /login"
        - "click: button#submit"
        - "type: input#username|testuser"
        - "wait: 2"
        
        Returns:
            {action: xxx, target: xxx, value: xxx}
        """
        if ':' not in step_str:
            return {'action': step_str.strip(), 'target': '', 'value': ''}
        
        action, rest = step_str.split(':', 1)
        action = action.strip().lower()
        
        # 检查是否有值（用|分隔）
        if '|' in rest:
            target, value = rest.split('|', 1)
            return {'action': action, 'target': target.strip(), 'value': value.strip()}
        
        # 纯target
        return {'action': action, 'target': rest.strip(), 'value': ''}
    
    def _normalize_expected(self, expected: Any) -> List[Dict]:
        """标准化预期结果"""
        if not expected:
            return []
        
        result = []
        
        for exp in expected:
            if isinstance(exp, str):
                # 简写格式: "url_contains: /dashboard/"
                if ':' in exp:
                    key, value = exp.split(':', 1)
                    result.append({key.strip(): value.strip()})
                else:
                    result.append({'assert': exp})
            elif isinstance(exp, dict):
                result.append(exp)
        
        return result
    
    def to_yaml(self, data: Dict) -> str:
        """
        将数据转换为YAML格式
        
        Args:
            data: 用例数据
            
        Returns:
            YAML字符串
        """
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def parse_case_file(file_path: str) -> Dict:
    """
    快捷函数：解析YAML用例文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        用例数据
    """
    parser = YamlParser()
    return parser.parse(file_path)


if __name__ == '__main__':
    # 测试
    import sys
    if len(sys.argv) > 1:
        data = parse_case_file(sys.argv[1])
        print(f"Case: {data['name']}")
        print(f"Steps: {len(data['steps'])}")
        print(yaml.dump(data, allow_unicode=True))
