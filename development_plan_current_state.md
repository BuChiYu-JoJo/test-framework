# 基于现有项目现况的自动化测试平台开发方案

**版本**：V1.0  
**适用项目**：通用自动化测试框架 / AI 自动化测试平台  
**建议落地目录**：`docs/development_plan_current_state.md`  
**编写目的**：基于当前设计文档与源码对齐说明，制定一份可执行、可验收、可逐步落地的开发方案。

---

## 1. 项目现况判断

### 1.1 当前项目不是从 0 开始

当前系统已经具备自动化测试平台的核心骨架，包括：

- Web 管理平台
- 后端 API 服务
- 执行引擎
- 用例管理
- 项目配置
- Locators 管理
- 执行中心
- 报告中心
- 定时任务
- SSE 实时日志
- AI 工具集
- API 检测
- SEO 检测
- 性能检测

因此，后续开发不应继续按“新建一套平台”推进，而应按“现有系统增强与闭环化”推进。

### 1.2 当前已落地能力

当前已存在：

```text
frontend/src/views/api-test/
frontend/src/views/performance/
frontend/src/views/seo/

backend/app/api/v1/api_test.py
backend/app/api/v1/performance.py
backend/app/api/v1/seo.py
```

并且对应模型和服务层已经存在。

### 1.3 当前仍属于规划态的模块

以下模块不应被误认为已经完成：

```text
blackwhite.py
proxy.py
crawler.py
```

对应的前端页面、服务层、模型目前仍属于规划态。

### 1.4 当前执行引擎真实状态

当前执行引擎仍以以下模块为核心：

```text
engine.py
keyword_executor.py
locator_resolver.py
playwright_client.py
api_client.py
reporter.py
parser/yaml_parser.py
parser/excel_parser.py
```

不建议立即强行拆成大量子引擎目录，而应先通过 service 层和 dispatcher 层做任务分发。

### 1.5 当前 Locator 设计重点

当前 locator 已经升级为多策略模型，执行时支持优先级 fallback。

后续开发重点应放在：

- 多策略存储结构稳定
- fallback 命中日志
- 执行报告中展示命中策略
- AI Locator 生成后的自动验证
- 失败时可快速定位到底是哪个 selector 失效

---

## 2. 总体开发目标

### 2.1 一句话目标

将当前自动化测试框架从“功能可用”推进到“平台可持续使用、可扩展、可回归、可分析”的状态。

### 2.2 阶段性目标

| 阶段 | 目标 |
|---|---|
| 阶段 1 | 稳定核心执行链路 |
| 阶段 2 | 增强 API / SEO / 性能三类已落地专项能力 |
| 阶段 3 | 建立 AI 生成 → 人工确认 → 入库 → 执行的闭环 |
| 阶段 4 | 统一报告、日志、通知和执行状态 |
| 阶段 5 | 后置扩展代理、爬虫巡检、黑白盒测试 |

---

## 3. 开发原则

### 3.1 不大拆现有核心引擎

当前 `engine.py`、`keyword_executor.py`、`locator_resolver.py` 已经是核心稳定模块。

短期不建议大规模重构为：

```text
engine/seo/
engine/performance/
engine/api_test/
engine/proxy/
engine/crawler/
```

推荐做法是：

```text
保留现有 engine 核心
在 backend services 层做专项任务封装
通过 dispatcher 统一调度
逐步沉淀可复用能力
```

### 3.2 已落地模块优先补强

优先处理：

```text
API 检测
SEO 检测
性能检测
AI 用例生成
AI Locator
智能回归
```

暂缓处理：

```text
代理池
爬虫巡检
黑白盒测试
```

### 3.3 AI 能力必须可控

AI 生成内容不能直接写入生产用例库。

必须采用：

```text
AI 生成
  ↓
人工确认
  ↓
自动校验
  ↓
入库
  ↓
执行验证
```

### 3.4 报告和日志先统一

新增功能不能各自生成完全不同格式的报告。

所有任务都应统一拥有：

- task_id
- task_type
- project_id
- env
- status
- started_at
- finished_at
- duration
- passed
- failed
- warnings
- artifacts
- logs

---

## 4. 推荐目标架构

```text
用户层
├── Web 管理平台
├── Excel / YAML / JSON 导入
└── API / CLI 调用

后端服务层
├── 用例管理服务
├── 执行任务服务
├── Locator 服务
├── API 检测服务
├── SEO 检测服务
├── 性能检测服务
├── AI 用例生成服务
├── AI Locator 服务
├── 智能回归服务
└── 报告服务

任务调度层
├── Task Dispatcher
├── Scheduler
└── SSE Log Stream

执行引擎层
├── UI 自动化执行引擎
├── API Client
├── Playwright Client
├── Locator Resolver
├── Keyword Executor
└── Reporter

存储层
├── MySQL / SQLite
├── 文件存储
├── 报告目录
├── 截图目录
└── Trace / HAR 文件
```

---

## 5. 统一任务模型设计

### 5.1 任务类型

```python
# NEW CODE: backend/app/constants/task_type.py

from enum import Enum


class TaskType(str, Enum):
    UI = "ui"
    API = "api"
    SEO = "seo"
    PERFORMANCE = "performance"
    AI_CASE = "ai_case"
    AI_LOCATOR = "ai_locator"
    REGRESSION = "regression"
```

### 5.2 统一任务状态

```python
# NEW CODE: backend/app/constants/task_status.py

from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELED = "canceled"
```

### 5.3 统一执行任务字段

建议每类任务最终都能映射到统一结构：

```json
{
  "id": 1001,
  "task_type": "seo",
  "project_id": 1,
  "env": "test",
  "status": "passed",
  "total": 20,
  "passed": 18,
  "failed": 2,
  "warnings": 5,
  "duration_ms": 32000,
  "started_at": "2026-04-24 10:00:00",
  "finished_at": "2026-04-24 10:00:32",
  "artifacts": {
    "html_report": "reports/seo/1001/index.html",
    "json_report": "reports/seo/1001/result.json"
  }
}
```

---

## 6. Task Dispatcher 方案

### 6.1 设计目的

避免前端和 API 层分别调用不同执行入口，导致后续维护困难。

统一入口：

```text
POST /api/v1/tasks/{task_type}/{task_id}/run
```

### 6.2 新增代码

```python
# NEW CODE: backend/app/services/task_dispatcher.py

from backend.app.constants.task_type import TaskType
from backend.app.services.execution_service import ExecutionService
from backend.app.services.api_test_service import ApiTestService
from backend.app.services.seo_service import SeoService
from backend.app.services.performance_service import PerformanceService


class TaskDispatcher:
    def __init__(self):
        self.execution_service = ExecutionService()
        self.api_test_service = ApiTestService()
        self.seo_service = SeoService()
        self.performance_service = PerformanceService()

    async def dispatch(self, task_type: str, task_id: int):
        if task_type == TaskType.UI:
            return await self.execution_service.run(task_id)

        if task_type == TaskType.API:
            return await self.api_test_service.run(task_id)

        if task_type == TaskType.SEO:
            return await self.seo_service.run(task_id)

        if task_type == TaskType.PERFORMANCE:
            return await self.performance_service.run(task_id)

        raise ValueError(f"Unsupported task type: {task_type}")
```

### 6.3 不用修改的代码

短期不建议大改：

```text
engine/engine.py
engine/keyword_executor.py
engine/locator_resolver.py
engine/playwright_client.py
engine/reporter.py
```

只在外层做统一调度。

---

## 7. Locator 多策略增强方案

### 7.1 当前目标

当前 locator 已支持多策略 fallback，后续应补强可观测性。

### 7.2 推荐 Locator 数据结构

```json
{
  "locator_key": "login.agree_terms_checkbox",
  "description": "登录页同意条款复选框",
  "strategies": [
    {
      "type": "css",
      "value": "button[data-testid='agree-terms-checkbox']",
      "priority": 1
    },
    {
      "type": "css",
      "value": "button[aria-label='Agree terms']",
      "priority": 2
    },
    {
      "type": "xpath",
      "value": "//button[contains(@class, 'w-[16px]')]",
      "priority": 3
    }
  ],
  "enabled": true
}
```

### 7.3 命中日志

每次执行 locator 都应记录：

```json
{
  "locator_key": "login.agree_terms_checkbox",
  "used_strategy": "css",
  "used_value": "button[data-testid='agree-terms-checkbox']",
  "priority": 1,
  "fallback_count": 0,
  "matched_count": 1,
  "duration_ms": 18
}
```

### 7.4 AI Locator 的落地规则

AI 生成 locator 后必须自动验证：

```text
AI 生成 locator
  ↓
实际页面验证命中数量
  ↓
命中数量 = 1 才允许保存为高优先级
  ↓
命中数量 > 1 降级为候选
  ↓
命中数量 = 0 标记为无效
```

---

## 8. API 检测开发方案

### 8.1 当前定位

API 检测已经落地可用，下一步应增强为“链式接口测试能力”。

### 8.2 必须支持的能力

| 能力 | 优先级 |
|---|---|
| REST 请求 | P0 |
| 环境变量替换 | P0 |
| Bearer Token | P0 |
| JSONPath 断言 | P0 |
| 响应时间断言 | P0 |
| 上下文变量提取 | P0 |
| 接口依赖编排 | P1 |
| GraphQL | P1 |
| WebSocket | P2 |
| 并发摸高 | P2 |

### 8.3 用例格式建议

```yaml
name: realname status api
module: realname
env: test
steps:
  - name: get token
    request:
      method: POST
      url: /api/login
      body:
        username: ${username}
        password: ${password}
    extract:
      token: $.data.token
    assertions:
      - type: status_code
        expected: 200
      - type: jsonpath
        path: $.code
        expected: 0

  - name: get realname status
    request:
      method: GET
      url: /api/auth/realname/status
      headers:
        Authorization: Bearer ${token}
    assertions:
      - type: status_code
        expected: 200
      - type: jsonpath
        path: $.code
        expected: 0
      - type: response_time
        max_ms: 1000
```

### 8.4 新增断言执行器

```python
# NEW CODE: engine/api_test/asserter.py

from jsonpath_ng import parse


class ApiAsserter:
    def assert_status_code(self, response, expected_code: int):
        assert response.status_code == expected_code, (
            f"Expected status code {expected_code}, got {response.status_code}"
        )

    def assert_jsonpath(self, json_data: dict, path: str, expected):
        jsonpath_expr = parse(path)
        matches = [match.value for match in jsonpath_expr.find(json_data)]

        assert matches, f"JSONPath not found: {path}"
        assert matches[0] == expected, (
            f"Expected {path}={expected}, got {matches[0]}"
        )

    def assert_response_time(self, elapsed_ms: float, max_ms: int):
        assert elapsed_ms <= max_ms, (
            f"Expected response time <= {max_ms}ms, got {elapsed_ms}ms"
        )

    def run_assertions(self, response, assertions: list):
        json_data = None

        for assertion in assertions:
            assertion_type = assertion["type"]

            if assertion_type == "status_code":
                self.assert_status_code(response, assertion["expected"])

            elif assertion_type == "jsonpath":
                if json_data is None:
                    json_data = response.json()

                self.assert_jsonpath(
                    json_data,
                    assertion["path"],
                    assertion["expected"]
                )

            elif assertion_type == "response_time":
                elapsed_ms = response.elapsed.total_seconds() * 1000
                self.assert_response_time(elapsed_ms, assertion["max_ms"])

            else:
                raise ValueError(f"Unsupported assertion type: {assertion_type}")
```

### 8.5 验收标准

```text
1. 可完成登录接口 → 提取 token → 调业务接口 → 执行断言
2. 支持 JSONPath 提取变量
3. 支持响应时间断言
4. 报告中展示每个请求的 request / response / assertions
5. 失败时可定位具体断言失败原因
```

---

## 9. SEO 检测开发方案

### 9.1 当前定位

SEO 检测页面、API、模型、服务层已经存在。下一步不是重写，而是补强规则、报告和历史对比。

### 9.2 MVP 规则清单

| 分类 | 规则ID | 严重级别 |
|---|---|---|
| Meta | title_missing | critical |
| Meta | title_too_short | warning |
| Meta | title_too_long | warning |
| Meta | meta_description_missing | warning |
| Content | h1_missing | warning |
| Content | h1_multiple | warning |
| Content | heading_order_invalid | info |
| Image | img_alt_missing | warning |
| Link | href_empty | warning |
| Link | broken_link | critical |
| Technical | canonical_missing | info |
| Technical | robots_unreachable | warning |
| Technical | sitemap_unreachable | warning |
| Mobile | viewport_missing | warning |
| SPA | rendered_content_empty | critical |

### 9.3 SEO 规则配置

```python
# NEW CODE: engine/seo/rules.py

SEO_RULES = [
    {
        "rule_id": "title_missing",
        "category": "meta",
        "severity": "critical",
        "description": "页面缺少 title 标签",
        "suggestion": "请为页面添加唯一且有业务含义的 title"
    },
    {
        "rule_id": "meta_description_missing",
        "category": "meta",
        "severity": "warning",
        "description": "页面缺少 meta description",
        "suggestion": "请添加页面描述，提升搜索结果展示质量"
    },
    {
        "rule_id": "h1_missing",
        "category": "content",
        "severity": "warning",
        "description": "页面缺少 H1 标签",
        "suggestion": "每个页面建议保留一个清晰的 H1"
    },
    {
        "rule_id": "img_alt_missing",
        "category": "content",
        "severity": "warning",
        "description": "存在未设置 alt 属性的图片",
        "suggestion": "所有有内容含义的图片应添加 alt 属性"
    },
    {
        "rule_id": "viewport_missing",
        "category": "mobile",
        "severity": "warning",
        "description": "页面缺少 viewport 配置",
        "suggestion": "请添加移动端 viewport meta 标签"
    }
]
```

### 9.4 SPA 等待配置

```json
{
  "spa_wait_ms": 3000,
  "max_wait_ms": 5000,
  "wait_until": "networkidle",
  "content_selector": "body"
}
```

### 9.5 报告结构

```json
{
  "score": 82,
  "summary": {
    "critical": 1,
    "warning": 6,
    "info": 4
  },
  "issues": [
    {
      "url": "https://www.dataify.com/",
      "rule_id": "img_alt_missing",
      "severity": "warning",
      "description": "存在未设置 alt 属性的图片",
      "suggestion": "所有图片应添加 alt 属性描述内容"
    }
  ]
}
```

### 9.6 验收标准

```text
1. 支持单 URL 扫描
2. 支持 URL 列表批量扫描
3. 支持 SPA 渲染等待配置
4. 支持 Critical / Warning / Info 分级
5. 支持 HTML / JSON 报告导出
6. 报告中能看到具体 URL、规则、问题、建议
```

---

## 10. 性能检测开发方案

### 10.1 当前定位

性能检测已经有页面、API、模型、服务层。下一步重点是指标稳定性和报告可读性。

### 10.2 核心指标

| 指标 | 说明 | 优先级 |
|---|---|---|
| TTFB | 首字节时间 | P0 |
| FCP | 首次内容绘制 | P0 |
| LCP | 最大内容绘制 | P0 |
| CLS | 布局偏移 | P0 |
| Total Requests | 总请求数 | P0 |
| JS Size | JS 总体积 | P0 |
| Image Size | 图片总体积 | P0 |
| Slow Resources | 慢资源 TOP10 | P0 |
| INP | 交互响应 | P1 |
| HAR | 网络日志 | P1 |

### 10.3 阈值配置

```python
# NEW CODE: backend/app/config/performance_thresholds.py

PERFORMANCE_THRESHOLDS = {
    "desktop": {
        "ttfb_ms": 800,
        "fcp_ms": 1800,
        "lcp_ms": 2500,
        "cls": 0.1,
        "total_js_kb": 500,
        "total_image_kb": 1500
    },
    "mobile": {
        "ttfb_ms": 1200,
        "fcp_ms": 2500,
        "lcp_ms": 3500,
        "cls": 0.1,
        "total_js_kb": 350,
        "total_image_kb": 1000
    }
}
```

### 10.4 性能报告内容

报告应包含：

```text
1. 综合评分
2. Core Web Vitals
3. 桌面 / 移动端结果
4. 资源瀑布图
5. 慢资源 TOP10
6. 大文件资源 TOP10
7. 相比历史基线是否退化
8. 优化建议
```

### 10.5 验收标准

```text
1. 支持桌面端 / 移动端检测
2. 支持 LCP / FCP / CLS / TTFB 采集
3. 支持资源瀑布数据
4. 支持慢资源列表
5. 支持阈值告警
6. 支持历史基线对比
```

---

## 11. AI 用例生成开发方案

### 11.1 当前定位

AI 用例生成已在开发中，但需要形成闭环。

### 11.2 推荐流程

```text
上传 PRD
  ↓
AI 提取页面、接口、状态、规则
  ↓
AI 生成测试点
  ↓
AI 生成测试用例
  ↓
人工编辑和确认
  ↓
导入用例库
  ↓
自动化标记
  ↓
执行验证
```

### 11.3 用例字段

```json
{
  "case_id": "REALNAME-P0-001",
  "module": "实名认证",
  "page": "个人认证信息填写页",
  "title": "身份证号码为空时提交按钮置灰",
  "priority": "P0",
  "type": "UI",
  "precondition": "用户已进入个人认证信息填写页",
  "steps": [
    "清空身份证号码输入框",
    "输入合法姓氏和名字",
    "观察提交按钮状态"
  ],
  "test_data": {
    "surname": "王",
    "name": "小明",
    "id_card": ""
  },
  "expected": "身份证号码输入框下方提示错误文案，提交按钮置灰不可点击",
  "automation": "Y"
}
```

### 11.4 人工确认页面必须支持

```text
1. 编辑用例标题
2. 编辑步骤
3. 编辑预期结果
4. 设置优先级
5. 设置是否自动化
6. 批量导入
7. 放弃导入
```

### 11.5 验收标准

```text
1. PRD 上传后可以生成结构化测试点
2. 可以生成可编辑测试用例
3. 可以人工确认后导入
4. 导入后可在用例管理中查看
5. 可标记自动化状态
```

---

## 12. AI Locator 开发方案

### 12.1 当前定位

AI Locator 已在开发中，重点应从“能生成”升级为“生成后可验证、可回滚”。

### 12.2 推荐流程

```text
输入页面 URL / HTML / DOM
  ↓
AI 分析目标元素
  ↓
生成多策略 locator
  ↓
Playwright 实际验证
  ↓
计算命中数量和稳定性
  ↓
人工确认
  ↓
保存到 locator 库
```

### 12.3 生成结果格式

```json
{
  "locator_key": "realname.submit_button",
  "description": "个人实名认证提交按钮",
  "strategies": [
    {
      "type": "role",
      "value": "button[name='提交']",
      "priority": 1,
      "confidence": 0.92
    },
    {
      "type": "text",
      "value": "提交",
      "priority": 2,
      "confidence": 0.78
    },
    {
      "type": "css",
      "value": "button[type='submit']",
      "priority": 3,
      "confidence": 0.62
    }
  ]
}
```

### 12.4 验收标准

```text
1. AI 可以生成至少 3 种 locator 策略
2. 系统能实际验证每个 locator 命中数量
3. 命中数量为 1 的策略可保存
4. 命中数量为 0 或多个的策略不能直接作为最高优先级
5. 执行失败时能看到 fallback 路径
```

---

## 13. 智能回归开发方案

### 13.1 当前定位

智能回归仍处于早期阶段，应先做半自动推荐，不要做全自动执行。

### 13.2 推荐输入

```text
1. Git diff
2. 变更文件列表
3. 模块标签
4. 历史失败记录
5. 用例与模块映射关系
```

### 13.3 推荐输出

```json
{
  "change_summary": "修改实名认证个人认证信息填写页",
  "affected_modules": [
    "realname_person",
    "form_validation",
    "api_verify"
  ],
  "recommended_cases": [
    {
      "case_id": "REALNAME-P0-001",
      "reason": "涉及身份证号码校验逻辑"
    },
    {
      "case_id": "REALNAME-P0-008",
      "reason": "涉及提交接口调用"
    }
  ]
}
```

### 13.4 验收标准

```text
1. 输入变更文件后能推荐相关用例
2. 推荐结果包含原因
3. 用户可以手动勾选最终执行范围
4. 推荐结果可以生成执行任务
```

---

## 14. 报告中心统一方案

### 14.1 报告类型

```text
UI 执行报告
API 检测报告
SEO 检测报告
性能检测报告
AI 生成记录
智能回归推荐报告
```

### 14.2 统一报告字段

```json
{
  "task_id": 1001,
  "task_type": "api",
  "project": "dataify",
  "env": "test",
  "status": "failed",
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "warnings": 0
  },
  "duration_ms": 12800,
  "artifacts": {
    "html": "reports/api/1001/index.html",
    "json": "reports/api/1001/result.json",
    "screenshots": [],
    "trace": null,
    "har": null
  }
}
```

### 14.3 报告页面要求

```text
1. 支持按 task_type 筛选
2. 支持按项目筛选
3. 支持按状态筛选
4. 支持查看详情
5. 支持下载 HTML / JSON
6. 支持查看失败日志
7. 支持查看截图、trace、HAR
```

---

## 15. SSE 实时日志统一方案

### 15.1 日志事件格式

```json
{
  "task_id": 1001,
  "task_type": "ui",
  "level": "info",
  "event": "step_started",
  "message": "Start step: click submit button",
  "timestamp": "2026-04-24 10:00:01",
  "data": {
    "case_id": "REALNAME-P0-001",
    "step_index": 3
  }
}
```

### 15.2 事件类型

```text
task_started
task_finished
case_started
case_finished
step_started
step_finished
assertion_failed
locator_fallback
screenshot_saved
report_generated
error
```

### 15.3 验收标准

```text
1. 执行中心能实时显示日志
2. 日志可按级别过滤
3. 失败日志能跳转到报告详情
4. Locator fallback 能显示具体命中策略
```

---

## 16. 通知方案

### 16.1 当前建议

当前以飞书通知为主，短期不要同时扩展多个通知渠道。

优先保证：

```text
飞书 Webhook 通知稳定
```

### 16.2 通知场景

| 场景 | 是否通知 |
|---|---|
| P0 用例失败 | 是 |
| API 任务失败 | 是 |
| SEO 分数低于阈值 | 是 |
| 性能退化超过阈值 | 是 |
| 定时任务失败 | 是 |
| AI 生成失败 | 否 |
| 普通 P2 用例失败 | 可配置 |

### 16.3 通知内容

```json
{
  "title": "自动化测试任务失败",
  "project": "dataify",
  "env": "test",
  "task_type": "api",
  "task_id": 1001,
  "summary": "total=20, passed=18, failed=2",
  "report_url": "https://test-platform/reports/1001"
}
```

---

## 17. 暂缓模块方案

### 17.1 代理模块

短期只做项目级 proxy 配置，不做完整代理池。

MVP：

```text
1. 项目配置中增加 proxy_url
2. API / SEO / 性能检测可选择是否使用 proxy
3. 记录 proxy 请求失败日志
```

暂不做：

```text
代理服务商 API
代理池调度
代理可用率统计
SOCKS5 复杂认证
```

### 17.2 爬虫巡检

短期只做 URL 存活巡检和简单字段完整性检测。

MVP：

```text
1. 配置巡检 URL
2. 定时访问
3. 校验状态码
4. 校验页面关键文本
5. 失败通知
```

暂不做：

```text
复杂爬虫脚本注册
反爬检测
数据新鲜度分析
字段 schema 完整巡检
```

### 17.3 黑白盒测试

短期暂缓。

原因：

```text
1. 白盒测试涉及代码执行安全
2. 需要隔离环境或容器
3. 覆盖率报告合并复杂
4. 当前 API / SEO / 性能更值得优先稳定
```

---

## 18. 推荐开发里程碑

### 第 1 周：核心执行链路统一

交付：

```text
1. TaskType 枚举
2. TaskStatus 枚举
3. TaskDispatcher
4. 统一任务运行入口
5. 统一执行日志格式
6. Locator fallback 日志
```

验收：

```text
UI / API / SEO / Performance 四类任务可以通过统一入口触发。
执行中心能看到统一状态和实时日志。
```

### 第 2 周：API 检测增强

交付：

```text
1. JSONPath 断言
2. 响应时间断言
3. 变量提取
4. 环境变量替换
5. 链式接口执行
```

验收：

```text
可以完成登录 → 提取 token → 调用业务接口 → 执行断言。
报告中能看到每一步请求和响应。
```

### 第 3 周：SEO 检测增强

交付：

```text
1. 15 条核心 SEO 规则
2. SPA 等待配置
3. Critical / Warning / Info 分级
4. HTML / JSON 报告
5. SEO 历史扫描记录
```

验收：

```text
可以扫描 Dataify 页面并输出 title、description、H1、img alt、viewport、dead link 等检测结果。
```

### 第 4 周：性能检测增强

交付：

```text
1. TTFB / FCP / LCP / CLS
2. 慢资源 TOP10
3. 大资源 TOP10
4. 桌面 / 移动端检测
5. 阈值告警
6. 基线对比
```

验收：

```text
可以输出性能评分、核心指标、慢资源和退化告警。
```

### 第 5 周：AI 用例生成闭环

交付：

```text
1. PRD 上传
2. AI 测试点提取
3. AI 用例生成
4. 人工确认页
5. 导入用例库
```

验收：

```text
可以将实名认证 PRD 转换为结构化测试用例，并导入平台。
```

### 第 6 周：AI Locator 和智能回归

交付：

```text
1. AI Locator 多策略生成
2. Locator 实际命中验证
3. Git diff 影响分析
4. 推荐回归用例
5. 人工确认执行范围
```

验收：

```text
可以根据页面 DOM 生成 locator 并验证。
可以根据代码变更推荐回归用例。
```

---

## 19. 项目级验收标准

### 19.1 平台可用性

```text
1. 项目可以配置多环境
2. 用例可以通过 Web 或文件导入
3. 任务可以手动执行和定时执行
4. 执行过程有实时日志
5. 执行完成有报告
```

### 19.2 自动化能力

```text
1. UI 自动化可执行
2. API 检测可执行
3. SEO 检测可执行
4. 性能检测可执行
5. Locator fallback 可追踪
```

### 19.3 AI 能力

```text
1. AI 可生成测试用例
2. AI 可生成 Locator
3. AI 可推荐回归范围
4. 所有 AI 结果必须人工确认
```

### 19.4 报告能力

```text
1. 报告统一展示
2. 支持 HTML / JSON 导出
3. 失败可追踪到具体步骤
4. 支持截图、trace、HAR 附件
```

---

## 20. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 大规模重构执行引擎 | 影响已有功能稳定性 | 先做 dispatcher，不动核心 engine |
| AI 生成内容不稳定 | 误导测试设计 | 加人工确认和自动验证 |
| SEO 扫描 SPA 页面慢 | 任务耗时增加 | 增加 spa_wait_ms 和超时降级 |
| 性能数据波动 | 告警误报 | 使用多次采样或中位数 |
| Locator 多策略混乱 | 执行结果不可解释 | 记录 fallback 命中日志 |
| 代理池复杂度高 | 延期风险大 | MVP 只做项目级 proxy |
| 白盒测试安全风险 | 可能执行不可信代码 | 后置并使用容器隔离 |

---

## 21. 最终建议

当前项目最适合采用以下路线：

```text
稳定已有核心
  ↓
统一任务和报告
  ↓
增强 API / SEO / 性能
  ↓
闭环 AI 用例生成和 Locator
  ↓
再扩展代理、爬虫、黑白盒
```

不建议当前阶段一口气推进所有规划模块。

最优先要做的是：

```text
1. Task Dispatcher
2. 统一任务状态
3. Locator fallback 日志
4. API 链式测试
5. SEO 规则体系
6. 性能阈值与报告
7. AI 生成后的人工确认闭环
```

这样可以在不破坏现有架构的情况下，让平台快速进入可用、可演示、可持续迭代的状态。

---

## 22. 建议落地文件

建议将本方案保存为：

```text
docs/development_plan_current_state.md
```

并在 README 中增加链接：

```markdown
## 开发方案

- [基于现有项目现况的开发方案](docs/development_plan_current_state.md)
```
