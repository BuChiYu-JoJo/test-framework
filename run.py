#!/usr/bin/env python3
"""
Test Framework - 统一入口脚本

用法:
    python run.py --project dataify --case tc001_login
    python run.py --project dataify --case tc001_login --env test
    python run.py --project dataify --all --env test
    python run.py --project dataify --case tc001_login,tc002_task_list --report html
"""

import argparse
import sys
import json
from pathlib import Path

# 添加engine目录到路径
sys.path.insert(0, str(Path(__file__).parent / "engine"))

from engine import TestEngine, Reporter, generate_report


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Test Framework - 通用自动化测试框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --project dataify --case tc001_login
  python run.py --project dataify --case tc001_login --env test
  python run.py --project dataify --all
  python run.py --project dataify --case tc001_login,tc002 --report html,json
        """
    )
    
    parser.add_argument(
        '--project', '-p',
        required=True,
        help='项目名称 (如: dataify)'
    )
    
    parser.add_argument(
        '--case', '-c',
        help='用例名称(不含.yaml), 多个用逗号分隔 (如: tc001_login,tc002)'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='运行该项目的所有用例'
    )
    
    parser.add_argument(
        '--env', '-e',
        default='test',
        help='运行环境 (test/dev/staging), 默认: test'
    )
    
    parser.add_argument(
        '--report', '-r',
        default='html,json',
        help='报告格式, 多个用逗号分隔 (html/json/markdown), 默认: html,json'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='无头模式运行浏览器'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    return parser.parse_args()


def find_case_file(project_path: Path, case_name: str) -> Path:
    """
    查找用例文件
    
    Args:
        project_path: 项目路径
        case_name: 用例名称
        
    Returns:
        用例文件路径
    """
    # 尝试在yaml目录查找
    yaml_path = project_path / "cases" / "yaml" / f"{case_name}.yaml"
    if yaml_path.exists():
        return yaml_path
    
    # 尝试在excel目录查找
    excel_path = project_path / "cases" / "excel" / f"{case_name}.xlsx"
    if excel_path.exists():
        return excel_path
    
    raise FileNotFoundError(f"Case file not found: {case_name}")


def find_all_cases(project_path: Path) -> list:
    """
    查找所有用例文件
    
    Args:
        project_path: 项目路径
        
    Returns:
        用例文件路径列表
    """
    cases = []
    
    yaml_dir = project_path / "cases" / "yaml"
    if yaml_dir.exists():
        cases.extend(yaml_dir.glob("*.yaml"))
    
    excel_dir = project_path / "cases" / "excel"
    if excel_dir.exists():
        cases.extend(excel_dir.glob("*.xlsx"))
    
    return cases


def run_case(engine: TestEngine, case_path: Path, args) -> dict:
    """
    运行单个用例
    
    Args:
        engine: TestEngine实例
        case_path: 用例文件路径
        args: 命令行参数
        
    Returns:
        执行结果
    """
    print(f"\n{'='*60}")
    print(f"Running: {case_path.name}")
    print(f"{'='*60}")
    
    try:
        # 加载用例
        case_data = engine.load_case(str(case_path))
        print(f"Case: {case_data.get('name', case_path.stem)}")
        print(f"Priority: {case_data.get('priority', 'N/A')}")
        print(f"Steps: {len(case_data.get('steps', []))}")
        
        # 执行用例
        result = engine.execute_case(case_data)
        
        # 输出结果
        status_icon = {
            'passed': '✅',
            'failed': '❌',
            'blocked': '⏸',
            'skipped': '⏭'
        }.get(result.status.value, '❓')
        
        print(f"\nResult: {status_icon} {result.status.value.upper()}")
        print(f"Duration: {result.duration_ms}ms")
        
        if result.error_msg:
            print(f"Error: {result.error_msg}")
        
        # 生成报告
        report = engine.get_report(result)
        
        # 保存报告
        formats = args.report.split(',')
        for fmt in formats:
            fmt = fmt.strip()
            if fmt == 'html':
                path = engine.reporter.save_html(report)
                print(f"HTML Report: {path}")
            elif fmt == 'json':
                path = engine.reporter.save_json(report)
                print(f"JSON Report: {path}")
            elif fmt == 'markdown' or fmt == 'md':
                path = engine.reporter.save_markdown(report)
                print(f"Markdown Report: {path}")
        
        return {
            'case': case_path.name,
            'status': result.status.value,
            'passed': result.status.value == 'passed',
            'duration': result.duration_ms
        }
        
    except Exception as e:
        print(f"Error running case: {e}")
        import traceback
        traceback.print_exc()
        return {
            'case': case_path.name,
            'status': 'error',
            'passed': False,
            'error': str(e)
        }


def main():
    """主函数"""
    args = parse_args()
    
    # 获取项目路径
    project_path = Path(__file__).parent / "projects" / args.project
    
    if not project_path.exists():
        print(f"Error: Project not found: {project_path}")
        sys.exit(1)
    
    # 切换环境
    if args.env != 'test':
        project_path = project_path.parent / args.env
    
    print(f"Project: {args.project}")
    print(f"Environment: {args.env}")
    print(f"Project Path: {project_path}")
    
    # 初始化引擎
    engine = TestEngine(args.project, str(project_path))
    
    # 确定要运行的用例
    if args.all:
        case_files = find_all_cases(project_path)
        print(f"\nFound {len(case_files)} cases")
    elif args.case:
        case_names = [c.strip() for c in args.case.split(',')]
        case_files = []
        for name in case_names:
            try:
                case_path = find_case_file(project_path, name)
                case_files.append(case_path)
            except FileNotFoundError:
                print(f"Warning: Case not found: {name}")
        print(f"\nSelected {len(case_files)} cases")
    else:
        print("Error: Please specify --case or --all")
        sys.exit(1)
    
    if not case_files:
        print("No cases to run")
        sys.exit(0)
    
    # 运行用例
    results = []
    for case_path in case_files:
        result = run_case(engine, case_path, args)
        results.append(result)
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    total = len(results)
    passed = sum(1 for r in results if r.get('passed'))
    failed = total - passed
    
    print(f"Total: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    for r in results:
        icon = '✅' if r.get('passed') else '❌'
        print(f"  {icon} {r.get('case')}: {r.get('status')}")
    
    # 返回退出码
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
