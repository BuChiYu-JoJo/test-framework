# Test Framework 产品需求文档（PRD）

**文档版本：** v1.0
**日期：** 2026-04-22
**作者：** TestMaster
**状态：** 待评审

---

## 文档说明

本文档为 test-framework（通用自动化测试框架）的完整产品需求文档，包含以下两部分：

- **第一部分：现有功能 PRD** — 基于源码分析整理，已实现功能条目
- **第二部分：新增功能 PRD** — 6个计划开发功能模块的需求分析

---

# 第一部分：现有功能 PRD

---

## 1. 用例管理

### 1.1 背景与目标

用例管理是测试框架的核心模块，提供测试用例的创建、编辑、导入导出功能，支持 YAML 和 Excel 两种格式，实现测试资产的统一管理和复用，降低手工编写用例的门槛。

### 1.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 用例列表 | 按项目筛选、分页展示用例，支持搜索和排序 | P0 | 已实现 |
| 用例创建/编辑 | 通过表单或 YAML 内容编辑用例 | P0 | 已实现 |
| YAML 导入 | 批量导入 YAML 格式用例文件 | P0 | 已实现 |
| Excel 导入 | 批量导入 Excel 格式用例文件（openpyxl 解析） | P0 | 已实现 |
| YAML 导出 | 导出单条或多条用例为 YAML 文件 | P1 | 已实现 |
| Excel 导出 | 导出单条或多条用例为 Excel 文件 | P1 | 已实现 |
| 用例版本管理 | 用例内容版本记录 | P2 | 已实现 |

### 1.3 用户操作流程

用户进入用例管理页面 → 选择项目 → 浏览/搜索用例列表 → 创建新用例或导入现有用例 → 编辑用例内容（YAML 格式） → 保存 → 可选导出分享

### 1.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/cases | 用例列表（支持 project_id 筛选、分页） |
| POST | /api/v1/cases | 创建用例 |
| GET | /api/v1/cases/{id} | 获取用例详情 |
| PUT | /api/v1/cases/{id} | 更新用例 |
| DELETE | /api/v1/cases/{id} | 删除用例 |
| POST | /api/v1/cases/import/yaml | YAML 批量导入 |
| POST | /api/v1/cases/import/excel | Excel 批量导入 |
| GET | /api/v1/cases/{id}/export/yaml | 导出 YAML |
| GET | /api/v1/cases/{id}/export/excel | 导出 Excel |

### 1.5 数据模型

```python
Case:
  id: int (PK)
  project_id: int (FK)
  module: str          # 模块路径
  name: str
  priority: str        # P0/P1/P2/P3
  tags: list[str]
  content: text        # YAML 格式用例内容
  created_by: str
  created_at: datetime
  updated_at: datetime
```

### 1.6 关键实现细节

- **YAML 解析**：使用 `engine/parser/yaml_parser.py` 解析用例内容，验证 steps/actions/assertions 结构
- **Excel 解析**：使用 `openpyxl` 库，支持多 Sheet 导入，每行对应一个步骤
- **内容存储**：YAML 内容以 text 形式存储在 content 字段，解析在引擎执行时进行
- **导入冲突**：同名用例按 name+module 唯一键处理

---

## 2. 项目管理

### 2.1 背景与目标

项目管理提供测试资产的顶层隔离能力，每个项目独立管理用例、Locators、执行记录，实现多业务线/多环境的测试资源分离。

### 2.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 项目列表 | 展示所有项目，支持搜索 | P0 | 已实现 |
| 项目创建 | 创建新项目（名称/描述） | P0 | 已实现 |
| 项目编辑 | 修改项目信息 | P0 | 已实现 |
| 项目删除 | 删除项目（级联删除关联数据） | P1 | 已实现 |
| 项目环境配置 | 支持多环境变量配置（dev/test/prod） | P1 | 已实现 |

### 2.3 用户操作流程

管理员进入项目管理页面 → 创建新项目 → 配置环境变量 → 在项目内创建用例/Locators → 触发执行

### 2.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/projects | 项目列表 |
| POST | /api/v1/projects | 创建项目 |
| GET | /api/v1/projects/{id} | 项目详情 |
| PUT | /api/v1/projects/{id} | 更新项目 |
| DELETE | /api/v1/projects/{id} | 删除项目 |

### 2.5 数据模型

```python
Project:
  id: int (PK)
  name: str
  description: str
  created_at: datetime
  updated_at: datetime
```

### 2.6 关键实现细节

- **级联删除**：删除项目时需处理关联的 cases、locators、executions、schedulers，建议软删除或强制确认
- **隔离性**：项目间数据完全隔离，执行时按 project_id 路由

---

## 3. 执行引擎

### 3.1 背景与目标

执行引擎是测试框架的核心运行时，负责解析 YAML 用例、驱动 Playwright 浏览器、执行关键字步骤、收集断言结果，支持实时日志推送和步骤级报告生成。

### 3.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 执行触发 | 通过 API 触发单个或批量用例执行 | P0 | 已实现 |
| YAML 用例解析 | 解析用例 content 字段，提取 steps | P0 | 已实现 |
| 45 个关键字执行 | navigate/click/type/select/wait/assert_*/api_request/screenshot 等 | P0 | 已实现 |
| 实时日志推送 | SSE 事件总线实时推送执行日志 | P0 | 已实现 |
| 步骤级报告 | 每个 step 的 status/actual/error 单独记录 | P0 | 已实现 |
| 截图捕获 | 执行失败/成功时自动截图 | P0 | 已实现 |
| API 请求支持 | 独立 api_request 关键字执行 HTTP 调用 | P0 | 已实现 |
| 失败继续 | 单步失败后可选择继续执行后续步骤 | P1 | 已实现 |
| 并发执行 | 支持多用例并发执行 | P1 | 已实现 |
| Locator 解析 | 从 locators.json 动态解析定位符 | P0 | 已实现 |

### 3.3 用户操作流程

用户进入执行页面 → 选择用例 → 点击执行 → 实时观看日志滚动 → 执行完成后查看步骤级报告和截图

### 3.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/executions | 触发执行（单用例/批量） |
| GET | /api/v1/executions/{id} | 查询执行状态 |
| GET | /api/v1/executions/{id}/steps | 获取步骤级报告 |
| GET | /api/v1/executions/{id}/screenshots | 获取截图列表 |
| GET | /api/v1/executions/{id}/logs | SSE 实时日志流 |

### 3.5 数据模型

```python
Execution:
  id: int (PK)
  execution_id: str (UUID)
  case_id: int (FK)
  project_id: int (FK)
  env: str  # test/dev/prod
  status: str  # pending/running/passed/failed/blocked/skipped
  result: str  # passed/failed/error
  duration_ms: int
  error_msg: text
  report_path: str  # HTML 报告路径
  screenshots: list[str]
  started_at: datetime
  finished_at: datetime

ExecutionStep:
  id: int (PK)
  execution_id: int (FK)
  step_no: int
  action: str
  target: str
  value: str
  status: str  # passed/failed/skipped
  actual: text
  error_msg: text
  duration_ms: int
  screenshot: str
```

### 3.6 关键实现细节

- **SSE 事件总线**：使用 `services/events.py` 中的 event_bus.publish，客户端通过 `/logs` 端点订阅
- **Playwright 封装**：`engine/playwright_client.py` 管理 browser/context/page 生命周期，执行后截图存文件
- **关键字执行**：`engine/keyword_executor.py` 中 45 个关键字通过 action 名称反射调用
- **Locator 解析**：`engine/locator_resolver.py` 根据 element_key 从 locators.json 查找对应定位符
- **断言验证**：`engine/validator.py` 处理 assertEquals/assertContains 等断言
- **API 测试**：`engine/api_client.py` 封装 requests，支持 header/token 注入

---

## 4. Locators 管理

### 4.1 背景与目标

Locators 管理提供页面元素的定位符统一存储和版本管理，支持树形可视化编辑，避免在用例中硬编码定位符，实现定位符的复用和集中维护。

### 4.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| Locators 树形展示 | 按 page_name 组织元素节点 | P0 | 已实现 |
| 创建/编辑 Locator | 添加 element_key 和 selector | P0 | 已实现 |
| 可视化编辑 | 前端 Vue 组件支持点选和编辑 | P0 | 已实现 |
| Selector 类型支持 | css/xpath/id/text/aria 等 | P0 | 已实现 |
| 版本管理 | selector 变更时自动创建新版本 | P1 | 已实现 |
| 定位符预览 | 在页面中高亮定位元素 | P2 | 已实现 |
| 导入/导出 | locators.json 批量导入导出 | P1 | 已实现 |
| AI 生成 Locators | URL/截图/描述三种 AI 生成模式 | P0 | 已实现 |

### 4.3 用户操作流程

用户进入 Locators 页面 → 选择项目 → 浏览页面树 → 点击元素节点 → 编辑 selector 和类型 → 保存自动生成版本

### 4.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/locators | 获取 locators 列表（按 project_id/page_name 筛选） |
| POST | /api/v1/locators | 创建 Locator |
| PUT | /api/v1/locators/{id} | 更新 Locator（触发版本+1） |
| DELETE | /api/v1/locators/{id} | 删除 Locator |
| GET | /api/v1/locators/{id}/versions | 获取版本历史 |
| POST | /api/v1/locators/preview | 预览定位（渲染页面高亮） |
| POST | /api/v1/ai/locators/from_url | AI 从 URL 生成 Locators |
| POST | /api/v1/ai/locators/from_screenshot | AI 从截图生成 Locators |
| POST | /api/v1/ai/locators/from_description | AI 从描述生成 Locators |

### 4.5 数据模型

```python
Locator:
  id: int (PK)
  project_id: int (FK)
  page_name: str
  element_key: str
  selector: str
  selector_type: str  # css/xpath/id/name/aria
  version: int
  ai_confidence: float  # AI 生成置信度
  created_at: datetime
  updated_at: datetime
```

### 4.6 关键实现细节

- **树形结构**：前端按 page_name 分组，element_key 作为叶子节点
- **版本控制**：每次 update 时 version 字段+1，保留历史 selector 用于回滚
- **Playwright 渲染**：`ai_locators.py` 中通过 Playwright 加载 URL 并截图，AI 辅助生成定位符
- **AI 三模式**：URL 模式（自动渲染）+ 截图模式（Base64上传）+ 描述模式（自然语言）

---

## 5. 报告中心

### 5.1 背景与目标

报告中心提供执行结果的集中查询和可视化展示，支持 HTML 报告生成、执行统计、失败分析，提升测试结果的可读性和追溯效率。

### 5.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 报告列表 | 按项目/时间/状态筛选执行记录 | P0 | 已实现 |
| 报告详情 | 步骤级结果、截图、日志 | P0 | 已实现 |
| HTML 报告生成 | 自动生成可下载的 HTML 报告 | P0 | 已实现 |
| 执行统计 | 通过率/失败率/平均时长看板 | P1 | 已实现 |
| 报告导出 | PDF/HTML 格式导出 | P2 | 已实现 |
| 失败分类统计 | 按错误类型聚合失败用例 | P2 | 已实现 |

### 5.3 用户操作流程

用户进入报告中心 → 筛选查看历史执行记录 → 点击查看详情 → 查看步骤级日志和截图 → 下载 HTML 报告

### 5.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/reports | 报告列表（支持分页、筛选） |
| GET | /api/v1/reports/{id} | 报告详情 |
| GET | /api/v1/reports/{id}/download | 下载 HTML 报告文件 |
| GET | /api/v1/reports/stats | 执行统计数据 |

### 5.5 数据模型

```python
# 复用 Execution 模型，报告通过 Execution.id 关联
# Execution.report_path: HTML 报告文件路径
# Execution.screenshots: JSON list of screenshot paths
# ExecutionStep: 步骤详情通过 FK 关联获取
```

### 5.6 关键实现细节

- **HTML 报告生成**：`engine/reporter.py` 使用模板渲染，执行数据填充，支持截图内嵌
- **SSE 实时日志**：执行过程中日志通过 `services/events.py` 推送，前端实时滚动展示
- **截图存储**：截图以文件形式存储，通过 report_path 相对路径引用

---

## 6. 定时任务

### 6.1 背景与目标

定时任务模块集成 APScheduler，支持 cron 表达式配置自动化执行，实现无人值守的持续测试，支持六段式 cron 配置（秒级精度）。

### 6.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 定时任务列表 | 查看所有定时任务及状态 | P0 | 已实现 |
| 创建定时任务 | 配置 name/cron/用例/环境 | P0 | 已实现 |
| 编辑定时任务 | 修改 cron 表达式或目标用例 | P0 | 已实现 |
| 启用/禁用任务 | 开关控制任务执行 | P0 | 已实现 |
| 立即执行 | 手动触发定时任务立刻执行 | P1 | 已实现 |
| cron 六段式配置 | 支持秒/分/时/日/月/周全量配置 | P0 | 已实现 |
| 执行完成通知 | 任务完成后触发飞书通知 | P1 | 已实现 |

### 6.3 用户操作流程

用户进入定时任务页面 → 创建任务 → 配置 cron 表达式（如 `0 0 2 * * *`） → 关联用例和项目 → 启用任务 → 查看下次执行时间

### 6.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/scheduler/jobs | 定时任务列表 |
| POST | /api/v1/scheduler/jobs | 创建定时任务 |
| PUT | /api/v1/scheduler/jobs/{id} | 更新定时任务 |
| DELETE | /api/v1/scheduler/jobs/{id} | 删除定时任务 |
| POST | /api/v1/scheduler/jobs/{id}/run | 立即执行 |
| POST | /api/v1/scheduler/jobs/{id}/enable | 启用任务 |
| POST | /api/v1/scheduler/jobs/{id}/disable | 禁用任务 |

### 6.5 数据模型

```python
ScheduledJob:
  id: int (PK)
  name: str
  cron_expr: str  # 六段式: 秒 分 时 日 月 周
  cron_second/minute/hour/day/month/weekday: 各字段独立存储
  case_id: int (FK, 可选)
  project_id: int (FK)
  env: str  # 环境变量
  enabled: bool
  notify_on_complete: bool
  description: str
  created_at: datetime
  updated_at: datetime
```

### 6.6 关键实现细节

- **APScheduler 集成**：`services/scheduler.py` 使用 APScheduler 的 BackgroundScheduler，add_job 注册任务
- **cron 解析**：支持六段式，需验证表达式合法性
- **任务持久化**：任务信息存 DB，进程重启后通过 DB 恢复调度
- **run_now**：调用 APScheduler 的 run_job 直接触发，跳过 cron 调度

---

## 7. 通知系统

### 7.1 背景与目标

通知系统将执行结果通过飞书/钉钉 Webhook 实时推送，实现测试执行状态的快速同步，支持自定义通知时机和内容模板。

### 7.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 飞书 Webhook 配置 | 在设置页配置 Webhook URL | P0 | 已实现 |
| 钉钉 Webhook 配置 | 支持钉钉机器人通知 | P0 | 已实现 |
| 执行完成通知 | 执行成功/失败时自动推送 | P0 | 已实现 |
| 通知内容定制 | 包含执行结果/耗时/失败原因 | P1 | 已实现 |
| 通知开关 | 可按项目或任务单独关闭 | P1 | 已实现 |
| 告警规则 | 失败超过阈值时触发通知 | P2 | 未实现 |

### 7.3 用户操作流程

管理员进入设置页面 → 配置飞书/钉钉 Webhook URL → 开启通知 → 执行用例 → 飞书群收到执行结果卡片

### 7.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/settings | 获取系统设置 |
| PUT | /api/v1/settings | 更新系统设置（包含 webhook 配置） |
| POST | /api/v1/settings/test_webhook | 测试 webhook 连通性 |

### 7.5 数据模型

```python
Settings:
  feishu_webhook_url: str
  dingtalk_webhook_url: str
  notify_on_success: bool
  notify_on_failure: bool
```

### 7.6 关键实现细节

- **FeishuNotifier**：`services/notify.py` 封装飞书 Webhook 调用，send_execution_result 方法构建卡片消息
- **消息格式**：使用飞书卡片消息格式，包含执行 ID、状态、耗时、错误信息、报告链接
- **异步发送**：通知发送为异步，不阻塞执行流程
- **失败处理**：Webhook 调用失败时记录日志，不影响主流程

---

## 8. AI 工具集

### 8.1 背景与目标

AI 工具集集成 MiniMax 大模型，提供智能化的 Locators 生成、用例生成和回归测试选择能力，降低手工编写用例的成本，提升 AI 辅助测试效率。

### 8.2 功能清单

#### 8.2.1 AI Locators 生成

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| URL 模式 | 输入 URL，AI 自动分析页面生成 Locators | P0 | 已实现 |
| 截图模式 | 上传页面截图，AI 识别元素生成 Locators | P0 | 已实现 |
| 描述模式 | 输入自然语言描述，AI 生成对应 Locator | P0 | 已实现 |
| Playwright 渲染 | 自动打开 URL 渲染页面供 AI 分析 | P0 | 已实现 |

#### 8.2.2 AI 用例生成

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 自然语言转 YAML | 输入测试场景描述，AI 生成 YAML 用例 | P0 | 已实现 |
| 用例优化 | 对现有用例提出改进建议 | P1 | 已实现 |
| 用例导出 | 直接将生成的用例导入用例库 | P1 | 已实现 |

#### 8.2.3 智能回归选择

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 代码变更分析 | 基于 git diff 分析影响范围 | P0 | 已实现 |
| 智能选用例 | 根据变更自动选择需要回归的用例 | P0 | 已实现 |
| 风险评估 | 对选中用例进行风险打分 | P1 | 已实现 |

### 8.3 用户操作流程

用户进入 AI 工具页面 → 选择工具类型（Locators/用例/回归） → 按需输入 URL/截图/描述 → AI 处理并返回结果 → 确认后批量导入/执行

### 8.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/ai/locators/from_url | URL 模式生成 Locators |
| POST | /api/v1/ai/locators/from_screenshot | 截图模式生成 Locators |
| POST | /api/v1/ai/locators/from_description | 描述模式生成 Locators |
| POST | /api/v1/ai/cases/generate | 自然语言生成用例 |
| POST | /api/v1/ai/regression/select | 智能回归用例选择 |

### 8.5 数据模型

```python
# AI Locators
AiLocatorRequest:
  url: str              # URL 模式
  screenshot: str       # Base64，截图模式
  description: str      # 描述模式
  page_name: str

AiLocatorResult:
  locators: list[{element_key, selector, selector_type, ai_confidence}]

# AI Case 生成
AiCaseRequest:
  description: str  # 自然语言描述
  project_id: int

AiCaseResult:
  content: str  # YAML 格式用例内容

# AI 回归选择
AiRegressionRequest:
  git_diff: str  # 代码变更 diff

AiRegressionResult:
  selected_cases: list[{case_id, reason, risk_score}]
```

### 8.6 关键实现细节

- **MiniMax API 封装**：`services/ai_base.py` 封装 MiniMax API 调用，统一异常处理和重试
- **URL 模式**：使用 Playwright 打开 URL，截图发送给 AI 分析页面 DOM 结构
- **截图模式**：前端上传截图，Base64 传后端，AI 计算机视觉识别 UI 元素
- **描述模式**：LLM 理解自然语言，映射为合理的 selector 策略
- **回归选择**：`services/ai_regression.py` 解析 git diff，识别涉及的模块/页面，匹配关联用例

---

# 第二部分：新增功能 PRD

---

## 9. 网站 SEO 检测

### 9.1 背景与目标

为测试框架增加网站 SEO 健康度检测能力，覆盖站内 SEO、技术 SEO、页面质量等多个维度，支持定时巡检与历史基线对比，帮助发现 SEO 问题并量化改进效果。

### 9.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 页面抓取 | 支持 SSR 和 SPA（Playwright 渲染），支持设置 User-Agent/等待条件 | P2 |
| Meta 检测 | title/description/og:image/og:title/canonical/meta robots | P2 |
| 内容结构分析 | H1-H6 层级、标题唯一性、图片 alt 属性、重复内容检测 | P2 |
| 链接检测 | 死链检测（HTTP 状态）、内链/外链统计、robots.txt 可访问性 | P2 |
| 技术 SEO | sitemap.xml 解析、面包屑结构、JSON-LD 结构化数据验证 | P2 |
| SEO 评分 | Critical/Warning/Info 三级评分，输出综合得分 0-100 | P2 |
| 定时巡检 | APScheduler 定时执行，支持 cron 表达式，巡检报告自动归档 | P2 |
| 基线对比 | 与历史基线对比，突出新增问题/退化项，支持告警 | P2 |

### 9.3 用户操作流程

1. 用户在 Web 界面输入目标 URL/站点入口，选择检测范围（全站/单页）
2. 配置抓取深度、并发数、SPA 等待时间等参数
3. 发起检测任务，可选择立即执行或排期
4. 任务完成后查看报告，包含评分、H1-H6 结构图、死链列表、SEO 问题清单
5. 设定基线后，定期任务自动对比历史，生成退化告警

### 9.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/seo/tasks | 创建 SEO 检测任务 |
| GET | /api/v1/seo/tasks | 获取任务列表 |
| GET | /api/v1/seo/tasks/{id} | 获取任务详情（含报告） |
| GET | /api/v1/seo/tasks/{id}/issues | 获取问题列表 |
| GET | /api/v1/seo/tasks/{id}/report | 获取 HTML 报告 |
| POST | /api/v1/seo/tasks/{id}/run | 立即执行 |
| DELETE | /api/v1/seo/tasks/{id} | 删除任务 |

### 9.5 数据模型

```python
SEOTask:
  id: int (PK)
  name: str
  project_id: int (FK)
  target_url: str
  urls: list[str]           # 批量 URL
  config: dict              # 深度、并发等配置
  status: str               # pending/running/completed/failed
  score: float              # 综合评分 0-100
  started_at: datetime
  finished_at: datetime
  created_by: str
  created_at: datetime

SEOIssue:
  id: int (PK)
  task_id: int (FK)
  url: str
  severity: str             # critical/warning/info
  category: str             # meta/content/link/technical
  rule_id: str
  description: str
  suggestion: str
  screenshot: str
```

### 9.6 技术实现要点

- **复用已有模块**：Playwright 引擎（已有）、requests、SQLAlchemy
- **SPA 抓取**：使用 Playwright 等待 networkidle 后提取内容
- **评分算法**：加权求和（Meta 30% + 内容结构 30% + 链接 25% + 技术SEO 15%）
- **死链检测**：异步并发请求，超时 5s，状态码非 2xx 视为死链
- **基线存储**：SQLite 按 site_id 归档，每次巡检结果快照独立存储

### 9.7 风险与对策

| 风险 | 对策 |
|------|------|
| 大型站点抓取耗时长，资源占用高 | 限制并发数，设置超时，任务队列限流 |
| SPA 页面内容渲染不一致 | 增加等待条件和重试机制，记录渲染前后 diff |
| SEO 评分主观性强，不同工具差异大 | 评分模型文档化，支持自定义权重配置 |
| 定时任务堆积，APScheduler 阻塞 | 任务持久化到 DB，中断恢复后自动续跑 |

---

## 10. 性能检测

### 10.1 背景与目标

通过 Playwright 自动采集真实用户感知的性能指标（Core Web Vitals），生成资源瀑布图和 Lighthouse 风格评分，支持多设备模拟，帮助发现页面性能瓶颈并追踪回归。

### 10.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| Core Web Vitals 采集 | FCP/LCP/FID/CLS/TTFB 全量采集 | P1 |
| 资源瀑布图 | JS/CSS/IMG/FONT 各类资源加载时序 | P1 |
| Lighthouse 风格评分 | Performance/Speed/SEO 评分，输出 0-100 分 | P1 |
| 移动端/桌面端模拟 | viewport/UA/网络节流（4G/WiFi/慢 2G） | P1 |
| 历史基线对比 | 指标基线存储，阈值告警，退化检测 | P1 |
| HAR 文件导出 | 完整网络请求记录导出的 HAR 文件 | P1 |
| 多 URL 批量检测 | 支持批量 URL 并行检测，汇总报告 | P2 |

### 10.3 用户操作流程

1. 用户输入目标 URL，选择设备类型（Mobile/Desktop）和网络条件
2. 点击"开始检测"，Playwright 启动无头浏览器访问
3. 页面加载完成后采集 Web Vitals、录制网络请求
4. 生成报告：评分雷达图、资源瀑布图、各指标时序变化
5. 设定基线后，异常指标自动标红并触发告警

### 10.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/performance/tasks | 创建性能检测任务 |
| GET | /api/v1/performance/tasks | 获取任务列表 |
| GET | /api/v1/performance/tasks/{id} | 获取任务详情（含指标） |
| GET | /api/v1/performance/tasks/{id}/waterfall | 获取瀑布图数据 |
| GET | /api/v1/performance/tasks/{id}/har | 下载 HAR 文件 |
| POST | /api/v1/performance/tasks/{id}/compare | 与历史基线对比 |
| DELETE | /api/v1/performance/tasks/{id} | 删除任务 |

### 10.5 数据模型

```python
PerformanceTask:
  id: int (PK)
  name: str
  project_id: int (FK)
  target_url: str
  device: str               # mobile/desktop
  network: str              # 4g/wifi/slow2g
  config: dict              # throttling 配置
  status: str
  score: float              # Lighthouse Performance Score
  metrics: dict            # {fcp, lcp, fid, cls, ttfb}
  resources: dict          # 资源瀑布图数据
  har_file: str            # HAR 文件路径
  created_at: datetime
  finished_at: datetime

PerfBaseline:
  id: int (PK)
  project_id: int (FK)
  device: str
  network: str
  metrics: dict
  created_at: datetime
```

### 10.6 技术实现要点

- **复用已有模块**：Playwright 引擎（已有）、Web Vitals 脚本
- **LCP 检测**：监听 largestContentfulPaint，LCP 元素截图
- **瀑布图**：解析 devtools 协议 Network.resourceReceivedTiming 事件
- **评分算法**：参考 Lighthouse 权重（FCP 10%, LCP 25%, CLS 15%, TTFB 20%, TBT 30%）
- **HAR 导出**：使用 har-api 将录制的请求序列化为 HAR 1.2 格式

### 10.7 风险与对策

| 风险 | 对策 |
|------|------|
| 无头浏览器启动慢，首次检测延迟高 | 预启动浏览器池，复用 browser context |
| 网络波动导致指标不稳定 | 每个 URL 多次采样取中位数，允许配置采样次数 |
| 移动端模拟与真实设备差异 | 明确告知用户是模拟值，提供真实设备检测指引 |

---

## 11. 接口检测

### 11.1 背景与目标

构建全面的接口自动化测试能力，支持 REST/GraphQL/WebSocket 多种协议，实现参数化驱动、断言验证、用例编排、并发检测，覆盖功能测试和性能摸高场景。

### 11.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 多协议支持 | REST（GET/POST/PUT/DELETE/PATCH）、GraphQL、WebSocket | P1 |
| 参数化驱动 | `${var}` 语法，支持 YAML/Excel 数据源，变量注入 | P1 |
| 断言验证 | 状态码、响应时间、JSONPath 取值断言，支持自定义 JS 断言 | P1 |
| 用例编排 | 支持依赖链（前置用例输出作为后置输入），支持 DAG 编排 | P1 |
| 并发检测 | 多线程并发执行，摸高线程安全 | P1 |
| 环境管理 | 多环境配置（dev/staging/prod），环境变量覆盖 | P1 |
| 历史报告 | 每次执行记录，报告对比，历史趋势图 | P2 |

### 11.3 用户操作流程

1. 用户在接口管理页面导入或手写 API 定义（支持 Swagger/OpenAPI 导入）
2. 编辑测试用例：设置断言规则，配置数据源参数化
3. 将多个用例编排成测试场景，设定依赖关系
4. 执行单用例调试或批量执行
5. 查看执行报告：请求详情、响应对比、断言结果、耗时分布
6. 压测模式下设置并发数，执行摸高测试

### 11.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/api-test/cases | 获取接口用例列表 |
| POST | /api/v1/api-test/cases | 创建接口用例 |
| GET | /api/v1/api-test/cases/{id} | 获取用例详情 |
| PUT | /api/v1/api-test/cases/{id} | 更新用例 |
| DELETE | /api/v1/api-test/cases/{id} | 删除用例 |
| POST | /api/v1/api-test/tasks | 创建执行任务 |
| GET | /api/v1/api-test/tasks/{id} | 获取执行结果 |
| GET | /api/v1/api-test/tasks/{id}/logs | 获取请求日志 |
| POST | /api/v1/api-test/cases/batch-run | 批量执行用例 |

### 11.5 数据模型

```python
APICase:
  id: int (PK)
  project_id: int (FK)
  module: str
  name: str
  method: str               # GET/POST/PUT/DELETE/PATCH
  url: str
  headers: dict
  params: dict              # Query 参数
  body: dict               # Body 参数
  body_type: str            # json/form-data/raw
  protocol: str             # REST/GraphQL/WebSocket
  assertions: list[dict]    # [{type, expr, expected, timeout}]
  dependencies: list[dict]  # 前置依赖用例
  timeout: int              # 默认 30s
  tags: list[str]
  created_by: str
  created_at: datetime

APITestTask:
  id: int (PK)
  name: str
  project_id: int (FK)
  case_ids: list[int]
  env: str
  status: str
  passed: int
  failed: int
  total: int
  duration_ms: int
  created_at: datetime
  finished_at: datetime
```

### 11.6 技术实现要点

- **复用现有模块**：扩展已有 `engine/api_client.py`，增加 GraphQL/WebSocket 支持
- **参数化解析**：自定义模板引擎，遇到 `${var}` 从 context 中查找并替换
- **数据源**：YAML 直接解析，Excel 使用 openpyxl
- **用例编排**：拓扑排序检测循环依赖，构建 DAG 执行计划
- **并发执行**：使用 Python `concurrent.futures.ThreadPoolExecutor`，线程安全 context

### 11.7 风险与对策

| 风险 | 对策 |
|------|------|
| 参数化循环引用导致死循环 | 执行前做拓扑排序，检测到循环依赖时拒绝执行 |
| 数据源文件损坏导致测试中断 | try-except 包裹解析逻辑，失败跳过该行并记录 |
| 并发摸高时系统资源耗尽 | 可配置最大并发数，默认 100，内存超限自动熔断 |
| WebSocket 长连接占用大量 file descriptors | 连接池上限控制，超时自动关闭 |

---

## 12. 黑白盒测试

### 12.1 背景与目标

整合 Web 自动化（黑盒）和单元/集成测试（白盒）能力，提供统一的测试编排和报告平台，支持跨浏览器测试、pytest 集成、覆盖率统计，满足 Web 功能测试和代码质量验证需求。

### 12.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 黑盒业务流程编排 | 录制/编写页面操作步骤，支持条件分支和循环 | P3 |
| 跨浏览器测试 | Chromium/Firefox/WebKit 三大引擎并行执行 | P3 |
| 截图录屏 | 每步操作截图，失败时自动录制操作视频 | P3 |
| 用例隔离 | 每个用例独立浏览器 Context，测试间完全隔离 | P3 |
| 白盒测试接入 | 接收 pytest 执行结果，集成 coverage.py 覆盖率报告 | P3 |
| 统一报告平台 | 黑盒+白盒测试结果汇总到同一报告页 | P3 |
| 测试套件管理 | 用例分组、标签管理、批量执行 | P3 |

### 12.3 用户操作流程

1. 用户录制或编写测试步骤（黑盒），或上传 pytest 项目（白盒）
2. 配置测试套件：选择浏览器、指定用例标签、设定超时
3. 发起执行，实时查看进度（当前步骤、通过/失败状态）
4. 任务完成后查看统一报告：黑盒截图+白盒覆盖率，失败步骤高亮
5. 支持 CI 触发：接收 webhook 调用执行指定套件

### 12.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/blackwhite/suites | 创建测试套件 |
| GET | /api/v1/blackwhite/suites | 获取套件列表 |
| GET | /api/v1/blackwhite/suites/{id} | 获取套件详情 |
| PUT | /api/v1/blackwhite/suites/{id} | 更新套件配置 |
| DELETE | /api/v1/blackwhite/suites/{id} | 删除套件 |
| POST | /api/v1/blackwhite/suites/{id}/run | 执行测试套件 |
| GET | /api/v1/blackwhite/suites/{id}/report | 获取套件报告 |
| GET | /api/v1/blackwhite/tasks/{id}/coverage | 获取覆盖率报告 |
| GET | /api/v1/blackwhite/browser/versions | 获取支持的浏览器版本 |

### 12.5 数据模型

```python
TestSuite:
  id: int (PK)
  name: str
  task_type: str           # black/white/both
  browsers: list[str]      # [chromium/firefox/webkit]
  case_ids: list[int]      # UI 用例 ID 列表（黑盒）
  pytest_paths: list[str]   # pytest 用例路径（白盒）
  coverage_enabled: bool
  timeout: int
  retry_count: int
  status: str
  created_at: datetime
  finished_at: datetime

BlackWhiteTask:
  id: int (PK)
  name: str
  project_id: int (FK)
  suite_id: int (FK)
  status: str
  results: dict            # 综合结果
  coverage_report: str     # 覆盖率报告路径
  created_at: datetime
  finished_at: datetime
```

### 12.6 技术实现要点

- **复用已有模块**：Playwright（黑盒引擎）、pytest（白盒集成）
- **跨浏览器**：Playwright 多 browser_type，通过配置切换 engine
- **用例隔离**：每个 case 启动独立 browser context，测试完成后销毁
- **白盒集成**：subprocess 运行 pytest，解析 pytest-json-report 输出
- **截图/录屏**：Playwright screenshot API，失败时触发录屏

### 12.7 风险与对策

| 风险 | 对策 |
|------|------|
| 多浏览器并行占用大量内存 | 浏览器进程池限制并发数，按队列串行执行各浏览器 |
| WebKit 浏览器兼容性问题 | 保持 Playwright 更新，标记已知问题，报告分离展示 |
| 录屏文件占用大量存储 | 录屏仅保留失败用例，设置 TTL 自动清理 |
| pytest 项目路径不存在 | 上传时校验路径合法性 |

---

## 13. 代理模块

### 13.1 背景与目标

构建统一的代理池管理能力，支持 HTTP/HTTPS/SOCKS5 多种协议，实现代理的健康检查、智能调度、可用率统计，为爬虫和接口测试提供稳定可靠的代理资源。

### 13.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 代理池管理 | 添加/编辑/删除代理，支持 HTTP/HTTPS/SOCKS5，支持认证信息 | P2 |
| 健康检查 | 定期 ping 检测可用性，默认 5min 间隔，不可用自动标记 | P2 |
| 调度策略 | 轮询（RoundRobin）、随机（Random）、失败切换（Failover） | P2 |
| 用量统计 | 可用率、平均延迟、使用次数、最后使用时间 | P2 |
| 本地 HTTP 代理服务 | 启动本地代理端口，分发请求到代理池，支持认证 | P2 |
| 阈值告警 | 可用率低于 50% 触发告警，支持 Webhook 通知 | P2 |
| 代理分组 | 按业务/地区/成本分组，支持分组调度 | P2 |

### 13.3 用户操作流程

1. 用户在代理管理页面批量导入代理（支持格式：host:port 或 JSON）
2. 设置健康检查频率和调度策略
3. 代理池启动后自动执行健康检查，在线代理可用率实时更新
4. 使用代理时调用 API 获取可用代理，支持指定分组/协议过滤
5. 可用率低于阈值时系统自动告警，标记高危代理

### 13.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/proxy/list | 获取代理列表 |
| POST | /api/v1/proxy/add | 添加单个代理 |
| POST | /api/v1/proxy/batch | 批量导入代理 |
| PUT | /api/v1/proxy/{id} | 更新代理信息 |
| DELETE | /api/v1/proxy/{id} | 删除代理 |
| GET | /api/v1/proxy/{id}/stats | 获取代理统计 |
| POST | /api/v1/proxy/{id}/test | 手动触发健康检查 |
| GET | /api/v1/proxy/available | 获取可用代理（支持过滤） |
| POST | /api/v1/proxy/refresh | 刷新健康状态 |
| GET | /api/v1/proxy/stats | 获取代理统计汇总 |
| POST | /api/v1/proxy/alert/rules | 创建告警规则 |
| GET | /api/v1/proxy/alert/rules | 获取告警规则 |

### 13.5 数据模型

```python
Proxy:
  id: int (PK)
  name: str
  protocol: str            # http/https/socks5
  host: str
  port: int
  username: str (nullable)
  password: str (nullable, 加密存储)
  group_id: int (FK)
  tags: list[str]
  avg_latency_ms: float
  success_rate: float      # 可用率
  use_count: int
  last_check_at: datetime
  last_used_at: datetime
  status: str             # active/inactive/unknown
  created_at: datetime
  updated_at: datetime

ProxyGroup:
  id: int (PK)
  name: str
  description: str
  strategy: str           # round_robin/random/failover

AlertRule:
  id: int (PK)
  condition: str           # availability < threshold
  threshold: float
  enabled: bool
  webhook_url: str
  created_at: datetime
```

### 13.6 技术实现要点

- **健康检查**：APScheduler 定时任务，异步 ping（HTTP HEAD 请求），超时 3s，失败重试 2 次
- **调度策略**：接口获取时按策略返回，高并发下用读锁+原子计数器避免竞争
- **本地代理**：使用 aiohttp/httpx 搭建异步 HTTP 代理服务
- **认证加密**：密码使用 AES 加密存储，密钥从环境变量读取
- **代理切换**：Failover 策略失败时自动切换下一个可用代理，重试 3 次

### 13.7 风险与对策

| 风险 | 对策 |
|------|------|
| 代理池大规模不可用导致测试中断 | 分组隔离，单组不可用不影响其他组；可用率告警提前预警 |
| SOCKS5 代理认证信息明文存储 | 加密存储，不在日志中打印认证信息 |
| 健康检查频繁导致代理被封 | 可配置检查间隔和目标 URL，避免高频检测同一目标 |
| 本地代理成为单点故障 | 本地代理支持多实例部署，前端做负载均衡 |

---

## 14. 爬虫抓取功能日常巡检

### 14.1 背景与目标

实现对已注册爬虫脚本的自动化巡检验证，监控存活状态、成功率、数据质量、新鲜度，及时发现爬虫异常并告警，保障数据采集的连续性和可靠性。

### 14.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 爬虫注册 | 录入脚本路径/入口 URL/巡检策略/预期抓取量 | P3 |
| 存活检测 | 检查进程是否运行、最近执行是否有报错 | P3 |
| 成功率检测 | 抓取成功量 vs 预期量，输出成功率% | P3 |
| 数据完整性 | 字段 schema 定义，自动校验抓取数据的字段覆盖率 | P3 |
| 新鲜度检测 | 最后更新时间，>24h 未更新触发告警 | P3 |
| 反爬检测 | 识别验证码页面、封禁状态，返回反爬告警 | P3 |
| 执行日志 | 记录每次巡检的标准输出/错误输出，保留最近 100 条 | P3 |
| 告警通知 | 支持飞书/钉钉/Webhook 多种渠道 | P3 |

### 14.3 用户操作流程

1. 用户注册爬虫：填写脚本路径、入口 URL、预期抓取量、字段 schema
2. 配置巡检策略：执行频率、存活/成功率/新鲜度阈值
3. 系统定时执行巡检：检查进程状态 → 执行测试抓取 → 校验数据 → 更新报告
4. 异常时自动告警，用户点击告警查看详情
5. 查看巡检历史：成功率趋势、新鲜度变化、错误日志

### 14.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/crawler/configs | 获取爬虫配置列表 |
| POST | /api/v1/crawler/configs | 添加爬虫配置 |
| GET | /api/v1/crawler/configs/{id} | 获取爬虫详情 |
| PUT | /api/v1/crawler/configs/{id} | 更新配置 |
| DELETE | /api/v1/crawler/configs/{id} | 删除配置 |
| GET | /api/v1/crawler/inspections | 获取巡检记录列表 |
| GET | /api/v1/crawler/inspections/{id} | 获取巡检详情 |
| POST | /api/v1/crawler/inspections/{id}/run | 立即巡检 |
| GET | /api/v1/crawler/stats | 获取巡检统计汇总 |
| POST | /api/v1/crawler/configs/{id}/schema | 设置数据字段 schema |

### 14.5 数据模型

```python
CrawlerConfig:
  id: int (PK)
  project_id: int (FK)
  name: str
  script_path: str         # 爬虫脚本路径
  entry_url: str           # 入口 URL
  interval: int            # 巡检间隔(秒)，默认 3600
  expected_count: int      # 预期抓取量
  completeness_schema: dict  # 字段完整性 schema
  freshness_threshold: int  # 新鲜度阈值(秒)，默认 86400
  enabled: bool
  created_at: datetime
  updated_at: datetime

CrawlerInspection:
  id: int (PK)
  crawler_id: int (FK)
  status: str              # running/passed/warning/failed
  items_count: int        # 抓取数量
  error_count: int        # 错误数量
  duration_ms: int
  error_msg: text
  anti_crawl_detected: bool
  checked_at: datetime
```

### 14.6 技术实现要点

- **存活检测**：使用 psutil 检查进程存在性，subprocess 执行脚本捕获退出码和 stderr
- **成功率**：对比抓取数据量与预期基数，低于阈值标记 warning
- **数据完整性**：用户定义 schema（如 `{"url": str, "title": str, "content": str}`），自动校验字段覆盖率
- **新鲜度**：记录每次抓取的数据更新时间，超 `freshness_threshold` 秒未更新触发告警
- **反爬检测**：检测响应中是否包含验证码/封禁关键词，标记 anti_crawl_detected

### 14.7 风险与对策

| 风险 | 对策 |
|------|------|
| 巡检本身触发反爬 | 限速 + 代理轮换 + 退出机制 |
| 爬虫脚本依赖外部环境 | 巡检需覆盖数据库/Redis 等依赖，记录依赖健康状态 |
| 成功率基线难以统一 | 支持用户自定义预期值，允许分组统计 |

---

# 附录

## A. 开发优先级汇总

| 优先级 | 功能模块 | 说明 |
|--------|----------|------|
| P0 | 现有功能维护 | bug 修复，当前功能稳定运行 |
| P1 | 接口检测 | 复用已有 api_client，收益快 |
| P1 | 性能检测 | 复用 Playwright，与 SEO 并行开发 |
| P2 | SEO 检测 | 依赖 Playwright 渲染 |
| P2 | 代理模块 | 被 SEO/爬虫/接口模块依赖，建议早做 |
| P3 | 黑白盒测试 | 涉及架构调整，白盒安全风险需审慎设计 |
| P3 | 爬虫巡检 | 依赖爬虫本身成熟度，建议后置 |

## B. 技术栈总览

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Element Plus + ECharts |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| UI 自动化 | Playwright |
| 接口测试 | requests + httpx |
| 定时任务 | APScheduler |
| AI 能力 | MiniMax API |
| 通知 | 飞书 Webhook + 钉钉 Webhook |

## C. 文档版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-04-22 | 初始版本，包含现有功能 PRD + 6 个新增功能 PRD |

---

**文档状态：** 待评审
**下一步：** 评审通过后按优先级排期开发
> 源码对齐说明（2026-04-23）
>
> 本文件为保证完整性，已恢复为原始完整版骨架；原有章节内容尽量保留不动。
> 若正文与当前源码存在冲突，以本说明和实际代码为准。
>
> 当前源码对齐结论：
>
> 1. 已完成主干模块：项目管理、用例管理、执行中心、Locators 管理、报告中心、调度任务、系统设置、AI 工具。
> 2. 已落地可用版模块：接口测试、性能检测、SEO 检测。它们在当前代码中已有前后端页面、API、模型与服务层，不应继续视为纯规划。
> 3. 仍属待开发模块：代理模块、爬虫抓取日常巡检、黑白盒测试平台。
> 4. 用例管理当前实际支持 Excel 导入和模板下载；YAML 批量导入、YAML 导出、Excel 导出并未按正文描述完整落地。
> 5. 执行中心当前 SSE 主流接口为 `/api/v1/executions/{execution_id}/stream`，而不是正文中的 `/logs`。
> 6. Locators 当前已演进为“单 selector 兼容 + 多策略 locator”模型，支持 `strategies[]`、`primary_type` 和执行命中策略回显；正文中将 locator 仅描述为单一 selector 的部分已落后于代码。
> 7. AI Locators 当前主要接口为 `/api/v1/ai/locators/generate` 与 `/api/v1/ai/locators/generate-with-auth`，不是正文中的 `from_url/from_screenshot/from_description` 三分接口。
> 8. 系统设置与通知当前以飞书为主，钉钉 Webhook、通用 `/api/v1/settings/test_webhook` 等描述与代码不完全一致。
> 9. SEO、性能、接口测试三个模块在正文后半部分如出现“规划态”表述，现应理解为“已开发，但仍是可用版而非完整平台态”。
>
