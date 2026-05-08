#!/usr/bin/env python3
"""
快速运行脚本 - 跑一个用例测试

用法：
    python quick_run.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import TestEngine, Reporter


def main():
    project = "dataify"
    case_file = "projects/dataify/cases/yaml/tc001_login.yaml"

    print(f"Starting test: {project} / {case_file}")
    print("=" * 60)

    # 直接使用 TestEngine，它内部管理 Playwright 生命周期
    engine = TestEngine(project, headless=True)

    try:
        # 加载用例
        case_data = engine.load_case(case_file)
        print(f"\nCase: {case_data.get('name')}")
        print(f"Priority: {case_data.get('priority')}")
        print(f"Steps: {len(case_data.get('steps', []))}")

        # 执行
        print("\nExecuting...")
        result = engine.execute_case(case_data)

        # 输出结果
        print("\n" + "=" * 60)
        print(f"Result: {result.status.value.upper()}")
        print(f"Duration: {result.duration_ms}ms")

        passed = sum(1 for s in result.steps if s.status.value == "passed")
        failed = sum(1 for s in result.steps if s.status.value == "failed")
        print(f"Steps: {len(result.steps)} | Passed: {passed} | Failed: {failed}")

        if result.error_msg:
            print(f"\nError: {result.error_msg}")

        print("\nSteps:")
        for s in result.steps:
            icon = "✅" if s.status.value == "passed" else "❌"
            print(f"  {icon} Step {s.step_no}: {s.action} -> {s.target}")
            if s.error_msg:
                print(f"      Error: {s.error_msg}")

        # 生成报告
        print("\nGenerating report...")
        report = engine.get_report(result)
        reporter = Reporter()
        html_path = reporter.save_html(report)
        json_path = reporter.save_json(report)
        print(f"HTML: {html_path}")
        print(f"JSON: {json_path}")

        return 0 if result.status.value == "passed" else 1

    finally:
        # engine.execute_case 内部已清理，这里确保极端情况也被清理
        engine._cleanup()


if __name__ == "__main__":
    sys.exit(main())
