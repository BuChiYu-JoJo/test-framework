"""
Locator Resolver - 元素定位符解析器
根据locators.json配置解析元素定位
"""

import json
from pathlib import Path
from typing import Dict, Optional


class LocatorResolver:
    """元素定位符解析器"""
    
    def __init__(self, locators_path: str = None):
        """
        初始化定位符解析器
        
        Args:
            locators_path: locators.json文件路径
        """
        self.locators_path = locators_path
        self.locators: Dict = {}
        self.version: str = ""
        
        if locators_path and Path(locators_path).exists():
            self.load(locators_path)
    
    def load(self, locators_path: str) -> None:
        """加载locators配置文件"""
        with open(locators_path, encoding='utf-8') as f:
            data = json.load(f)
        
        self.locators = data.get('pages', {})
        self.version = data.get('version', '1.0.0')
        self.locators_path = locators_path
    
    def resolve(self, key: str) -> Optional[Dict]:
        """
        解析定位符 key格式: page.element 或 element
        
        Args:
            key: 定位符键 (如: "login.username" 或 "username")
            
        Returns:
            包含selector和type的字典，或None
        """
        if '.' not in key:
            # 尝试在所有页面中查找
            for page_elements in self.locators.values():
                if key in page_elements.get('elements', {}):
                    return page_elements['elements'][key]
            return None
        
        page_name, element_name = key.split('.', 1)
        
        if page_name not in self.locators:
            return None
        
        page = self.locators[page_name]
        elements = page.get('elements', {})
        
        return elements.get(element_name)
    
    def get_selector(self, key: str) -> Optional[str]:
        """
        获取元素的CSS/XPath选择器
        
        Args:
            key: 定位符键 (如: "login.username")
            
        Returns:
            选择器字符串，或None
        """
        locator = self.resolve(key)
        if locator:
            return locator.get('selector')
        return None
    
    def get_type(self, key: str) -> Optional[str]:
        """
        获取定位符类型
        
        Args:
            key: 定位符键
            
        Returns:
            类型 (css/xpath)，或None
        """
        locator = self.resolve(key)
        if locator:
            return locator.get('type', 'css')
        return 'css'
    
    def get_description(self, key: str) -> Optional[str]:
        """
        获取元素描述
        
        Args:
            key: 定位符键
            
        Returns:
            描述字符串
        """
        locator = self.resolve(key)
        if locator:
            return locator.get('description', '')
        return ''
    
    def resolve_with_fallback(self, key: str) -> Dict:
        """
        解析定位符，带备用方案
        
        Returns:
            {
                'selector': str,  # 主选择器
                'type': str,      # 类型
                'fallback': str,  # 备用选择器
                'description': str
            }
        """
        locator = self.resolve(key)
        
        if locator:
            return {
                'selector': locator.get('selector', ''),
                'type': locator.get('type', 'css'),
                'fallback': '',
                'description': locator.get('description', '')
            }
        
        # 找不到时的备用方案
        return {
            'selector': key,  # 直接使用key作为selector
            'type': 'css',
            'fallback': '',
            'description': f'未配置的定位符: {key}'
        }
    
    def get_all_pages(self) -> Dict:
        """获取所有页面配置"""
        return self.locators
    
    def get_page_elements(self, page_name: str) -> Dict:
        """获取指定页面的所有元素"""
        page = self.locators.get(page_name, {})
        return page.get('elements', {})
    
    def validate(self) -> Dict:
        """
        验证locators配置
        
        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        for page_name, page_data in self.locators.items():
            elements = page_data.get('elements', {})
            
            for elem_name, elem_data in elements.items():
                key = f"{page_name}.{elem_name}"
                
                # 检查必需字段
                if 'selector' not in elem_data:
                    errors.append(f"{key}: 缺少selector字段")
                
                # 检查selector是否为空
                selector = elem_data.get('selector', '')
                if not selector:
                    errors.append(f"{key}: selector为空")
                
                # 检查priority
                priority = elem_data.get('priority', 0)
                if priority == 0:
                    warnings.append(f"{key}: 未设置priority")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def add_element(self, page_name: str, element_name: str, 
                   selector: str, elem_type: str = 'css', 
                   description: str = '', priority: int = 1) -> None:
        """
        添加元素定位符
        
        Args:
            page_name: 页面名称
            element_name: 元素名称
            selector: CSS/XPath选择器
            elem_type: 选择器类型 (css/xpath)
            description: 描述
            priority: 优先级 (1-4)
        """
        if page_name not in self.locators:
            self.locators[page_name] = {
                'name': page_name,
                'elements': {}
            }
        
        self.locators[page_name]['elements'][element_name] = {
            'selector': selector,
            'type': elem_type,
            'description': description,
            'priority': priority
        }
    
    def save(self, output_path: str = None) -> None:
        """
        保存locators配置
        
        Args:
            output_path: 输出路径，默认覆盖原文件
        """
        path = output_path or self.locators_path
        
        data = {
            'version': self.version,
            'updated_at': self._get_timestamp(),
            'pages': self.locators
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def __repr__(self) -> str:
        pages = list(self.locators.keys())
        return f"LocatorResolver(pages={pages}, version={self.version})"
