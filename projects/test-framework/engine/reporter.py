"""
Reporter - 测试报告生成器
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import CaseResult, StepResult


class Reporter:
    """测试报告生成器"""
    
    def __init__(self, output_dir: str = "reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, result) -> Dict:
        """
        生成用例执行报告
        
        Args:
            result: 用例执行结果
            
        Returns:
            报告数据字典
        """
        report = {
            'case_id': result.case_id,
            'case_name': result.case_name,
            'status': result.status.value,
            'duration_ms': result.duration_ms,
            'duration_formatted': self._format_duration(result.duration_ms),
            
            'started_at': result.started_at,
            'finished_at': result.finished_at,
            
            'steps_count': len(result.steps),
            'steps_passed': sum(1 for s in result.steps if s.status.value == 'passed'),
            'steps_failed': sum(1 for s in result.steps if s.status.value == 'failed'),
            
            'steps': [self._step_to_dict(s) for s in result.steps],
            
            'error_msg': result.error_msg,
            'screenshots': result.screenshots,
            
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return report
    
    def _step_to_dict(self, step) -> Dict:
        """将步骤结果转换为字典"""
        return {
            'step_no': step.step_no,
            'action': step.action,
            'target': step.target,
            'value': step.value,
            'status': step.status.value,
            'actual': step.actual,
            'error_msg': step.error_msg,
            'duration_ms': step.duration_ms,
            'screenshot': step.screenshot
        }
    
    def _format_duration(self, ms: int) -> str:
        """格式化时长"""
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return f"{ms/1000:.2f}s"
        else:
            minutes = ms // 60000
            seconds = (ms % 60000) / 1000
            return f"{minutes}m {seconds:.1f}s"
    
    def save_json(self, report: Dict, filename: str = None) -> str:
        """
        保存JSON格式报告
        
        Args:
            report: 报告数据
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        if not filename:
            case_id = report.get('case_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{case_id}_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def save_html(self, report: Dict, template: str = None, filename: str = None) -> str:
        """
        保存HTML格式报告
        
        Args:
            report: 报告数据
            template: HTML模板（可选）
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        html = self._generate_html(report)
        
        if not filename:
            case_id = report.get('case_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{case_id}_{timestamp}.html"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return str(filepath)
    
    def _generate_html(self, report: Dict) -> str:
        """生成HTML报告"""
        status = report.get('status', 'unknown')
        status_color = {
            'passed': '#52c41a',
            'failed': '#f5222d',
            'blocked': '#faad14',
            'skipped': '#8c8c8c'
        }.get(status, '#8c8c8c')
        
        # 步骤行
        steps_html = ""
        for step in report.get('steps', []):
            step_status = step.get('status', 'pending')
            step_color = {
                'passed': '#52c41a',
                'failed': '#f5222d'
            }.get(step_status, '#8c8c8c')
            
            screenshot_btn = ""
            if step.get('screenshot'):
                screenshot_btn = f'<a href="{step["screenshot"]}" target="_blank">📷</a>'
            
            steps_html += f"""
            <tr>
                <td>{step.get('step_no', '')}</td>
                <td>{step.get('action', '')}</td>
                <td>{step.get('target', '')}</td>
                <td>{step.get('value', '')}</td>
                <td style="color: {step_color}; font-weight: bold;">{step_status.upper()}</td>
                <td>{step.get('duration_ms', 0)}ms</td>
                <td>{screenshot_btn}</td>
                <td class="error-msg">{step.get('error_msg', '')}</td>
            </tr>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {report.get('case_name', '')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            padding: 40px;
            max-width: 1200px;
            margin: 0 auto;
            background: #f5f5f5;
        }}
        .report-card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .status-badge {{
            padding: 8px 16px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            background: {status_color};
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }}
        .summary-item {{
            background: #f5f5f5;
            padding: 16px;
            border-radius: 4px;
            text-align: center;
        }}
        .summary-item .label {{
            color: #8c8c8c;
            font-size: 12px;
            margin-bottom: 4px;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            background: #fafafa;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #e8e8e8;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .error-msg {{
            color: #f5222d;
            font-size: 12px;
        }}
        .footer {{
            text-align: center;
            color: #8c8c8c;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="header">
            <h1>{report.get('case_name', '')}</h1>
            <span class="status-badge">{status.upper()}</span>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="label">用例ID</div>
                <div class="value">{report.get('case_id', '')}</div>
            </div>
            <div class="summary-item">
                <div class="label">执行时长</div>
                <div class="value">{report.get('duration_formatted', '')}</div>
            </div>
            <div class="summary-item">
                <div class="label">通过</div>
                <div class="value" style="color: #52c41a;">{report.get('steps_passed', 0)}</div>
            </div>
            <div class="summary-item">
                <div class="label">失败</div>
                <div class="value" style="color: #f5222d;">{report.get('steps_failed', 0)}</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>步骤</th>
                    <th>操作</th>
                    <th>目标</th>
                    <th>值</th>
                    <th>状态</th>
                    <th>耗时</th>
                    <th>截图</th>
                    <th>错误信息</th>
                </tr>
            </thead>
            <tbody>
                {steps_html}
            </tbody>
        </table>
        
        {self._generate_error_section(report.get('error_msg', ''))}
        
        <div class="footer">
            报告生成时间: {report.get('generated_at', '')}
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_error_section(self, error_msg: str) -> str:
        """生成错误信息区块"""
        if not error_msg:
            return ""
        
        return f"""
        <div class="error-section" style="margin-top: 20px; padding: 16px; background: #fff2f0; border-radius: 4px; border-left: 4px solid #ff4d4f;">
            <strong style="color: #f5222d;">执行错误：</strong>
            <pre style="color: #f5222d; margin: 8px 0 0 0;">{error_msg}</pre>
        </div>
        """
    
    def save_markdown(self, report: Dict, filename: str = None) -> str:
        """
        保存Markdown格式报告
        
        Args:
            report: 报告数据
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        md = self._generate_markdown(report)
        
        if not filename:
            case_id = report.get('case_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{case_id}_{timestamp}.md"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        return str(filepath)
    
    def _generate_markdown(self, report: Dict) -> str:
        """生成Markdown报告"""
        status = report.get('status', 'unknown')
        status_icon = {
            'passed': '✅',
            'failed': '❌',
            'blocked': '⏸',
            'skipped': '⏭'
        }.get(status, '❓')
        
        # 步骤
        steps_md = ""
        for step in report.get('steps', []):
            step_status = step.get('status', 'pending')
            icon = '✅' if step_status == 'passed' else '❌'
            error = f" | *{step.get('error_msg', '')}*" if step.get('error_msg') else ''
            screenshot = f" | [📷]({step['screenshot']})" if step.get('screenshot') else ''
            
            steps_md += f"| {step.get('step_no', '')} | {step.get('action', '')} | {step.get('target', '')} | {step.get('value', '')} | {icon} {step_status.upper()} | {step.get('duration_ms', 0)}ms{screenshot}{error}\n"
        
        md = f"""# 测试报告

## 基本信息

| 项目 | 值 |
|------|-----|
| 用例名称 | {report.get('case_name', '')} |
| 用例ID | {report.get('case_id', '')} |
| 状态 | {status_icon} {status.upper()} |
| 执行时长 | {report.get('duration_formatted', '')} |
| 开始时间 | {report.get('started_at', '')} |
| 结束时间 | {report.get('finished_at', '')} |

## 执行统计

- **总步骤数：** {report.get('steps_count', 0)}
- **通过：** {report.get('steps_passed', 0)}
- **失败：** {report.get('steps_failed', 0)}

## 步骤详情

| # | 操作 | 目标 | 值 | 状态 | 耗时 |
|---|------|------|-----|------|------|
{steps_md}
"""
        
        if report.get('error_msg'):
            md += f"""
## 执行错误

```
{report.get('error_msg', '')}
```
"""
        
        md += f"""
---
*报告生成时间: {report.get('generated_at', '')}*
"""
        
        return md


def generate_report(result, output_dir: str = "reports") -> Dict:
    """
    快捷函数：生成报告
    
    Args:
        result: 用例执行结果
        output_dir: 输出目录
        
    Returns:
        报告数据
    """
    reporter = Reporter(output_dir)
    report = reporter.generate(result)
    reporter.save_json(report)
    reporter.save_html(report)
    return report
