"""
Test Framework - 通用自动化测试框架
"""

from .engine import TestEngine, CaseResult, CaseStatus, StepResult, StepStatus
from .locator_resolver import LocatorResolver
from .keyword_executor import KeywordExecutor
from .playwright_client import PlaywrightClient
from .reporter import Reporter, generate_report
from .validator import CaseValidator, validate_case, validate_case_file

__version__ = "1.1.0"

__all__ = [
    'TestEngine',
    'CaseResult',
    'CaseStatus',
    'StepResult',
    'StepStatus',
    'LocatorResolver',
    'KeywordExecutor',
    'PlaywrightClient',
    'Reporter',
    'generate_report',
    'CaseValidator',
    'validate_case',
    'validate_case_file',
]
