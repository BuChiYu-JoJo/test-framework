# Test Framework 产品需求文档（PRD）

**文档版本：** v1.1  
**日期：** 2026-04-22  
**作者：** TestMaster  
**状态：** 正式完整版

---

## 文档说明

本文档为 `test-framework`（通用自动化测试框架）的完整产品需求文档，包含以下两部分：

- **第一部分：当前产品基线 PRD**  
  基于当前项目源码整理，准确描述已具备能力、当前边界和正式纳入范围的功能。
- **第二部分：规划建设 PRD**  
  描述后续拟建设的 6 个功能模块需求、目标能力、边界和实施优先级。

与原 `PRD_v1.0.md` 相比，本版本有以下修订原则：

1. 不再将“源码现状”和“目标规划”混写。
2. 不再将未落地接口、模型、页面写成“已实现”。
3. 尽可能保留原始文档章节完整度和信息密度。
4. 对与源码不一致的内容做修正，但保留可复用的产品结构。

---

# 第一部分：当前产品基线 PRD

---

## 1. 用例管理

### 1.1 背景与目标

用例管理是测试框架的核心模块，用于提供测试用例的创建、编辑、批量导入和维护能力。当前实现以 YAML 文本作为执行引擎输入，以 Web 页面维护和 Excel 导入作为主要入口，目标是：

- 统一沉淀测试资产
- 降低手工编写用例门槛
- 支持项目隔离下的用例管理
- 为执行引擎提供结构稳定的输入内容

### 1.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 用例列表 | 按项目、模块、优先级、关键词展示用例 | P0 | 已实现 |
| 用例创建/编辑 | 通过表单维护用例基础信息和 YAML 内容 | P0 | 已实现 |
| Excel 导入 | 批量导入 Excel 格式用例文件并转换为 YAML 内容 | P0 | 已实现 |
| Excel 模板下载 | 提供标准模板用于批量录入 | P1 | 已实现 |
| 用例复制 | 基于已有用例复制生成新用例 | P1 | 已实现 |
| 用例删除 | 删除单条用例 | P0 | 已实现 |
| 用例版本字段 | 模型中保留版本字段 | P2 | 已实现（基础字段） |

### 1.3 当前明确不在范围

以下内容不属于当前源码已实现能力，不纳入当前基线：

- YAML 文件批量导入
- YAML 导出
- Excel 导出
- 独立的用例版本历史查询与回滚

### 1.4 用户操作流程

用户进入用例管理页面 → 选择项目 → 浏览/搜索用例列表 → 创建新用例或导入 Excel 用例 → 编辑 YAML 内容 → 保存 → 可在后续执行页面触发执行。

### 1.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/cases | 用例列表（支持 project_id/module/priority/keyword 筛选） |
| POST | /api/v1/cases | 创建用例 |
| GET | /api/v1/cases/template/download | 下载 Excel 模板 |
| GET | /api/v1/cases/{id} | 获取用例详情 |
| PUT | /api/v1/cases/{id} | 更新用例 |
| DELETE | /api/v1/cases/{id} | 删除用例 |
| POST | /api/v1/cases/{id}/duplicate | 复制用例 |
| POST | /api/v1/cases/import | 批量导入 Excel 用例 |

### 1.6 数据模型

```python
Case:
  id: int (PK)
  name: str
  case_id: str             # 业务可读 ID，如 TC001
  project_id: int (FK)
  module: str              # 模块路径
  priority: str            # P0/P1/P2/P3
  tags: text               # JSON list
  content: text            # YAML 内容
  version: str
  author: str
  created_at: datetime
  updated_at: datetime
```

### 1.7 关键实现细节

- **Excel 解析**：使用 `engine/parser/excel_parser.py`，支持 `.xlsx/.xls`。
- **内容存储**：导入后的步骤内容统一转为 YAML 文本，存储在 `content` 字段。
- **唯一性约束**：同一项目下以 `case_id` 作为主要业务唯一标识。
- **复制策略**：复制时自动生成新 `case_id`，避免主键冲突。

### 1.8 业务规则

- 同一项目下 `case_id` 不允许重复。
- 导入文件仅支持 `.xlsx` 和 `.xls`。
- 用例执行内容以 `content` 为准，而非表单字段拼装结果。
- 当前列表不提供分页能力，返回结果按 `id desc` 排序。

### 1.9 验收标准

- 用户可创建、编辑、删除、复制用例。
- Excel 导入生成的 YAML 内容可直接被执行引擎消费。
- 用例列表支持按项目、模块、优先级、关键词过滤。

---

## 2. 项目管理

### 2.1 背景与目标

项目管理提供测试资产的顶层隔离能力。每个项目独立管理用例、Locators、执行记录和定时任务，实现多业务线和多环境下的测试资源隔离。

### 2.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 项目列表 | 展示所有项目 | P0 | 已实现 |
| 项目创建 | 创建新项目（名称/描述/环境配置） | P0 | 已实现 |
| 项目编辑 | 修改项目信息 | P0 | 已实现 |
| 项目删除 | 删除项目 | P1 | 已实现 |
| 项目环境配置 | 存储项目环境 JSON 配置 | P0 | 已实现 |

### 2.3 用户操作流程

管理员进入项目管理页面 → 创建新项目 → 配置环境变量 → 在项目内创建用例/Locators → 触发执行。

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
  env_config: text         # JSON
  created_at: datetime
  updated_at: datetime
```

### 2.6 关键实现细节

- **唯一性**：项目名称全局唯一。
- **环境配置**：使用 `env_config` 保存项目运行参数，执行时可读取 `base_url`。
- **隔离性**：项目是用例、Locators、执行记录和调度任务的归属维度。

### 2.7 业务规则

- 当前删除项目时，只保证项目对象可删除；关联数据级联清理策略需要在后续增强中明确。
- 项目环境配置当前为自由 JSON，不做强约束 Schema 校验。

### 2.8 验收标准

- 可通过接口完成项目 CRUD。
- 执行流程可从项目配置中读取环境信息。

---

## 3. 执行引擎

### 3.1 背景与目标

执行引擎是测试框架的核心运行时，负责解析 YAML 用例、驱动 Playwright 浏览器、执行关键字步骤、收集执行结果、生成 HTML 报告，并通过 SSE 实时反馈执行进度。

### 3.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 执行触发 | 通过 API 触发单用例执行 | P0 | 已实现 |
| 执行列表 | 获取执行记录列表 | P0 | 已实现 |
| YAML 用例解析 | 从 Case.content 中解析步骤 | P0 | 已实现 |
| 关键字执行 | 支持页面、等待、断言、截图、API 等操作 | P0 | 已实现 |
| SSE 步骤流 | 实时推送执行步骤事件 | P0 | 已实现 |
| 调试日志流 | 推送调试日志 | P1 | 已实现 |
| 步骤级落库 | 每个 step 结果单独记录 | P0 | 已实现 |
| 截图捕获 | 执行过程中保存截图路径 | P0 | 已实现 |
| HTML 报告 | 执行完成生成 HTML 报告 | P0 | 已实现 |
| 执行前校验 | 校验项目配置/定位符路径等 | P1 | 已实现 |

### 3.3 当前明确不在范围

- 多用例批量并发执行平台化能力
- 独立执行节点集群
- 分布式队列编排
- 可视化重试与断点续跑

### 3.4 用户操作流程

用户进入执行页面 → 选择用例 → 点击执行 → 实时观看步骤日志和调试日志 → 执行完成后查看步骤结果、截图和 HTML 报告。

### 3.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/executions | 创建执行任务 |
| GET | /api/v1/executions | 查询执行列表 |
| GET | /api/v1/executions/{execution_id} | 查询执行详情 |
| GET | /api/v1/executions/{execution_id}/steps | 获取步骤级结果 |
| GET | /api/v1/executions/{execution_id}/stream | SSE 步骤流 |
| GET | /api/v1/executions/{execution_id}/debug-stream | SSE 调试日志流 |
| GET | /api/v1/executions/{execution_id}/debug-logs | 调试日志历史 |
| POST | /api/v1/executions/validate | 执行前校验 |

### 3.6 数据模型

```python
Execution:
  id: int (PK)
  execution_id: str (UUID/唯一执行号)
  case_id: int (FK)
  project_id: int (FK)
  env: str
  status: str              # pending/running/passed/failed/error/...
  result: str              # passed/failed/error
  duration_ms: int
  error_msg: text
  report_path: str
  screenshots: text        # JSON list
  started_at: datetime
  finished_at: datetime
  created_at: datetime

ExecutionStep:
  id: int (PK)
  execution_id: int (FK)
  step_no: int
  action: str
  target: str
  value: str
  status: str
  actual: text
  error_msg: text
  duration_ms: int
  screenshot: str
```

### 3.7 关键实现细节

- **异步执行模型**：API 创建执行记录后，后台线程运行执行逻辑。
- **YAML 临时文件**：将 `Case.content` 写入临时 YAML 文件，再交给 `TestEngine` 执行。
- **SSE 事件总线**：通过 `services/events.py` 发布步骤事件，客户端订阅 `/stream`。
- **HTML 报告生成**：执行结束后调用 `engine/reporter.py` 生成 HTML 文件。
- **通知集成**：执行完成后通过飞书通知结果。

### 3.8 业务规则

- 创建执行后状态先为 `pending`，实际运行后切换为 `running`。
- 每个步骤都必须独立入库。
- 报告生成失败不能影响执行结果本身入库。
- 通知发送失败不能影响主执行链路。

### 3.9 验收标准

- 执行任务可成功创建并异步完成。
- 前端可通过 SSE 实时接收步骤更新。
- 执行完成后可查看步骤结果和报告。

---

## 4. Locators 管理

### 4.1 背景与目标

Locators 管理用于统一维护页面元素定位符，避免测试用例中硬编码 selector，并为执行引擎提供可复用、可维护的元素映射关系。

### 4.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 定位符列表 | 按项目、页面查询定位符 | P0 | 已实现 |
| 页面列表 | 获取项目下页面维度分组 | P1 | 已实现 |
| 创建/编辑 Locator | 维护 selector 和类型 | P0 | 已实现 |
| 删除 Locator | 删除定位符 | P0 | 已实现 |
| 初始化样例 | 从项目 `locators.json` 初始化样例数据 | P1 | 已实现 |
| 导入/导出 | 与 `locators.json` 做双向同步 | P1 | 已实现 |
| AI 生成联动 | AI 工具产出的定位符可在后续落入此模块使用 | P1 | 已部分实现 |

### 4.3 当前明确不在范围

- 独立版本历史查询接口
- 页面高亮预览能力
- 定位符回滚

### 4.4 用户操作流程

用户进入 Locators 页面 → 选择项目 → 选择页面分组 → 查看并编辑元素 selector → 保存 → 在执行前由引擎同步写入项目文件。

### 4.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/locators | 获取定位符列表 |
| GET | /api/v1/locators/pages/{project_id} | 获取页面列表 |
| POST | /api/v1/locators | 创建 Locator |
| GET | /api/v1/locators/init-sample/{project_id} | 从样例文件初始化 |
| GET | /api/v1/locators/{id} | 获取详情 |
| PUT | /api/v1/locators/{id} | 更新 Locator |
| DELETE | /api/v1/locators/{id} | 删除 Locator |
| GET | /api/v1/locators/export/{project_id} | 导出为 locators.json |
| POST | /api/v1/locators/import/{project_id} | 导入 locators.json |

### 4.6 数据模型

```python
Locator:
  id: int (PK)
  project_id: int
  page_name: str
  element_key: str
  selector: str
  selector_type: str       # css/xpath 等
  priority: int
  description: str
  ai_confidence: str
  version: str
  updated_by: str
  created_at: datetime
  updated_at: datetime
```

### 4.7 关键实现细节

- **存储模式**：当前后台维护数据在数据库中。
- **执行兼容模式**：执行引擎仍从 `locators.json` 读取，因此执行前需要做 DB → JSON 同步。
- **导入策略**：已存在元素更新，不存在元素新增。
- **样例初始化**：从项目目录中的 `locators.json` 导入初始数据。

### 4.8 业务规则

- 页面元素使用 `page_name + element_key` 作为语义识别组合。
- 当前未实现严格数据库唯一索引，但逻辑上应保持唯一。
- selector 类型当前以 `css/xpath` 为主，文档中不承诺更多真实已实现类型。

### 4.9 验收标准

- 页面可查看和维护项目定位符。
- 执行引擎可读取最新同步后的定位符文件。

---

## 5. 报告中心

### 5.1 背景与目标

报告中心用于集中查看历史执行结果，并提供 HTML 报告访问能力，支撑问题追踪与回归验证。

### 5.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 历史报告摘要 | 获取历史执行摘要列表 | P0 | 已实现 |
| HTML 报告查看 | 查看执行生成的 HTML 报告 | P0 | 已实现 |

### 5.3 当前明确不在范围

- 报告统计看板
- PDF 导出
- 失败分类统计
- 报告差异对比

### 5.4 用户操作流程

用户进入报告中心 → 查询历史执行记录 → 点击某条执行 → 查看 HTML 报告内容。

### 5.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/reports/history | 历史报告摘要 |
| GET | /api/v1/reports/{execution_id} | 获取 HTML 报告 |

### 5.6 数据模型

```python
# 当前复用 Execution 模型
Execution.report_path: HTML 报告文件路径
Execution.screenshots: 截图路径 JSON list
ExecutionStep: 步骤详情通过 FK 获取
```

### 5.7 关键实现细节

- **报告生成**：由 `engine/reporter.py` 输出 HTML。
- **访问方式**：后端直接返回 HTML 文件响应。
- **历史摘要来源**：基于 `Execution` 表中已结束记录查询。

### 5.8 验收标准

- 可查询历史执行摘要。
- 可根据执行号访问 HTML 报告。

---

## 6. 定时任务

### 6.1 背景与目标

定时任务模块集成 APScheduler，支持基于 Cron 的自动执行，以满足无人值守回归、定时巡检等需求。

### 6.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 定时任务列表 | 查看定时任务及状态 | P0 | 已实现 |
| 创建定时任务 | 配置任务名称、cron、用例、项目、环境 | P0 | 已实现 |
| 编辑定时任务 | 修改任务配置 | P0 | 已实现 |
| 删除定时任务 | 删除任务 | P0 | 已实现 |
| 手动运行 | 立即触发一次任务执行 | P1 | 已实现 |
| 启用/禁用 | 通过 enabled 字段控制 | P0 | 已实现 |
| 六段式 cron | 支持秒/分/时/日/月/周字段 | P0 | 已实现 |

### 6.3 用户操作流程

用户进入定时任务页面 → 创建任务 → 配置 cron 表达式和关联用例 → 启用任务 → 查看下次执行时间 → 需要时可手动立即执行。

### 6.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/scheduler/jobs | 定时任务列表 |
| POST | /api/v1/scheduler/jobs | 创建定时任务 |
| GET | /api/v1/scheduler/jobs/{id} | 获取任务详情 |
| PUT | /api/v1/scheduler/jobs/{id} | 更新任务 |
| DELETE | /api/v1/scheduler/jobs/{id} | 删除任务 |
| POST | /api/v1/scheduler/jobs/{id}/run | 立即执行 |

### 6.5 数据模型

```python
ScheduledJob:
  id: int (PK)
  name: str
  cron_expr: str
  cron_second: str
  cron_minute: str
  cron_hour: str
  cron_day: str
  cron_month: str
  cron_weekday: str
  case_id: int
  project_id: int
  env: str
  enabled: bool
  notify_on_complete: bool
  description: str
  aps_job_id: str
  created_at: datetime
  updated_at: datetime
  last_run_at: datetime
  next_run_time: datetime
  run_count: int
```

### 6.6 关键实现细节

- **调度器**：使用 APScheduler `BackgroundScheduler`。
- **任务持久化**：任务配置保存在数据库中。
- **同步机制**：任务变更后同步到 APScheduler。
- **立即执行**：通过服务层手动触发运行。

### 6.7 业务规则

- 当前没有单独的 `/enable` 和 `/disable` 接口，启停依赖 `PUT` 更新 `enabled`。
- 任务和项目、用例存在关联关系，但当前不做复杂外键业务检查。

### 6.8 验收标准

- 能创建并保存定时任务。
- enabled 为 true 时任务应进入调度器。
- 手动运行接口可触发一次执行。

---

## 7. 通知系统

### 7.1 背景与目标

通知系统用于在执行完成后将结果同步到外部消息渠道，当前正式支持飞书 Webhook。

### 7.2 功能清单

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 飞书 Webhook 配置 | 配置飞书 webhook 地址 | P0 | 已实现 |
| 执行完成通知 | 执行成功/失败后自动推送 | P0 | 已实现 |
| 通知开关 | 控制是否在执行完成后通知 | P0 | 已实现 |
| 测试通知 | 测试 webhook 连通性 | P1 | 已实现 |

### 7.3 当前明确不在范围

- 钉钉通知
- 告警规则引擎
- 项目级通知开关
- 多渠道模板定制

### 7.4 用户操作流程

管理员进入设置页面 → 配置飞书 Webhook → 设置是否通知 → 保存 → 可发送测试消息验证 → 后续执行完成后自动推送结果。

### 7.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/settings/notify | 获取通知配置 |
| POST | /api/v1/settings/notify | 保存通知配置 |
| POST | /api/v1/settings/notify/test | 测试通知 |

### 7.6 数据模型

```python
NotifySettings:
  feishu_webhook: str
  notify_on_completion: bool
```

### 7.7 关键实现细节

- **持久化方式**：配置保存到 `.env.local`。
- **运行时生效**：保存后同步更新当前进程内的 settings。
- **通知实现**：`services/notify.py` 当前只有 `FeishuNotifier`。
- **容错策略**：通知失败记录日志，不影响主流程。

### 7.8 验收标准

- 可保存和读取飞书配置。
- 测试通知可成功发送。
- 执行完成后按配置自动通知。

---

## 8. AI 工具集

### 8.1 背景与目标

AI 工具集集成大模型能力，提供定位符生成、用例生成和回归选择等辅助功能，降低手工维护成本，提升回归效率。

### 8.2 功能清单

#### 8.2.1 AI Locators 生成

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| URL 模式 | 输入 URL 自动分析页面并生成定位符 | P0 | 已实现 |
| 增强模式 | 对已有定位符做补全和增强 | P1 | 已实现 |
| 登录态模式 | 先执行登录用例，再生成目标页定位符 | P1 | 已实现 |
| 登录用例辅助选择 | 获取适合作为登录态的用例列表 | P1 | 已实现 |

#### 8.2.2 AI 用例生成

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 自然语言生成 YAML | 输入场景描述生成 YAML 用例 | P0 | 已实现 |
| 截图辅助生成 | 描述 + 截图生成用例 | P1 | 已实现 |

#### 8.2.3 智能回归选择

| 功能点 | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| 变更文件分析 | 基于 changed_files 分析影响范围 | P1 | 已实现 |
| 回归用例选择 | 输出建议回归用例列表 | P1 | 已实现 |
| 风险评分 | 对候选用例输出风险分值 | P1 | 已实现 |

### 8.3 当前明确不在范围

- 截图独立输入的 Locator 生成接口
- 基于完整 git diff 文本的统一输入接口
- AI 结果自动落库闭环

### 8.4 用户操作流程

用户进入 AI 工具页面 → 选择工具类型 → 输入 URL/描述/截图或变更文件 → AI 处理后返回结构化结果 → 用户确认后人工继续使用。

### 8.5 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/ai/locators/generate | URL 模式生成 |
| POST | /api/v1/ai/locators/enhance | 定位符增强 |
| POST | /api/v1/ai/locators/generate-with-auth | 登录态生成 |
| GET | /api/v1/ai/locators/login-cases | 获取登录用例列表 |
| POST | /api/v1/ai/cases/generate | 自然语言生成用例 |
| POST | /api/v1/ai/cases/generate-with-screenshot | 截图辅助生成 |
| POST | /api/v1/ai/regression/select | 智能回归选择 |

### 8.6 数据模型

```python
# AI Locators
AiLocatorGenerateRequest:
  url: str
  page_name: str
  intent: str

AiLocatorResponse:
  locators: dict
  page_identifier: str
  raw_ai_response: str

# AI 用例生成
AiCaseGenerateRequest:
  description: str
  module: str
  priority: str

AiCaseResponse:
  yaml_content: str
  case_id: str
  raw_ai_response: str

# AI 回归选择
AiRegressionRequest:
  changed_files: list[str]
  project_id: int

AiRegressionResponse:
  selected_cases: list[dict]
  reason: str
  impact_modules: list[str]
  risk_level: str
```

### 8.7 关键实现细节

- **AI 基座**：通过 `services/ai_base.py` 封装模型调用。
- **页面分析**：Locator 场景会结合 Playwright 渲染结果。
- **登录态复用**：通过已有登录用例建立访问上下文。
- **回归选择**：基于变更文件路径与项目用例关系做匹配。

### 8.8 验收标准

- AI 接口可返回结构化结果。
- 失败时能明确返回错误信息。
- 登录态生成能在目标页上下文中输出结果。

---

# 第二部分：规划建设 PRD

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

1. 用户在 Web 界面输入目标 URL/站点入口，选择检测范围（全站/单页）。
2. 配置抓取深度、并发数、SPA 等待时间等参数。
3. 发起检测任务，可选择立即执行或排期。
4. 任务完成后查看报告，包含评分、结构分析、死链列表和问题清单。
5. 设定基线后，定期任务自动对比历史结果，生成退化告警。

### 9.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/seo/tasks | 创建 SEO 检测任务 |
| GET | /api/v1/seo/tasks | 获取任务列表 |
| GET | /api/v1/seo/tasks/{id} | 获取任务详情 |
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
  urls: list[str]
  config: dict
  status: str
  score: float
  started_at: datetime
  finished_at: datetime
  created_by: str
  created_at: datetime

SEOIssue:
  id: int (PK)
  task_id: int (FK)
  url: str
  severity: str
  category: str
  rule_id: str
  description: str
  suggestion: str
  screenshot: str
```

### 9.6 技术实现要点

- 复用 Playwright 获取渲染后页面。
- 基于规则引擎做多维度 SEO 校验。
- 问题项与评分结果分离存储。
- 报告输出 HTML + JSON。

### 9.7 风险与对策

| 风险 | 对策 |
|------|------|
| 大型站点抓取耗时长、资源占用高 | 限制并发数，设置超时，任务队列限流 |
| SPA 页面内容渲染不一致 | 增加等待条件和重试机制 |
| SEO 评分主观性强 | 评分模型文档化，支持权重配置 |
| 定时任务堆积 | 任务持久化并做续跑/限流设计 |

---

## 10. 性能检测

### 10.1 背景与目标

通过浏览器自动采集真实用户感知的性能指标，生成资源瀑布图和 Lighthouse 风格评分，帮助用户发现页面性能瓶颈并追踪回归。

### 10.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| Core Web Vitals 采集 | FCP/LCP/FID/CLS/TTFB 等指标采集 | P1 |
| 资源瀑布图 | JS/CSS/IMG/FONT 等资源时序展示 | P1 |
| 综合评分 | 输出 0-100 分性能评分 | P1 |
| 移动端/桌面端模拟 | viewport/UA/网络节流模拟 | P1 |
| 历史基线对比 | 指标退化检测和告警 | P1 |
| HAR 导出 | 导出请求记录 | P1 |
| 多 URL 批量检测 | 支持批量 URL 汇总执行 | P2 |

### 10.3 用户操作流程

1. 用户输入目标 URL，选择设备类型和网络条件。
2. 点击开始检测，启动浏览器访问目标页面。
3. 页面加载完成后采集 Web Vitals 和网络请求数据。
4. 生成报告并展示性能指标、瀑布图和评分。
5. 用户可与历史基线做对比分析。

### 10.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/performance/tasks | 创建性能检测任务 |
| GET | /api/v1/performance/tasks | 获取任务列表 |
| GET | /api/v1/performance/tasks/{id} | 获取任务详情 |
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
  device: str
  network: str
  config: dict
  status: str
  score: float
  metrics: dict
  resources: dict
  har_file: str
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

- 复用 Playwright 和浏览器性能 API。
- 独立保存性能指标与资源明细。
- 评分算法参考 Lighthouse，但允许后续自定义。

### 10.7 风险与对策

| 风险 | 对策 |
|------|------|
| 无头浏览器启动慢 | 预热浏览器池 |
| 网络波动影响指标稳定性 | 多次采样取中位数 |
| 模拟值和真实设备存在差异 | 文档中明确说明模拟边界 |

---

## 11. 接口检测

### 11.1 背景与目标

构建独立的接口自动化测试能力，支持 REST/GraphQL/WebSocket 等协议，覆盖功能验证、参数化驱动、断言校验、依赖编排和并发检测。

### 11.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 多协议支持 | REST、GraphQL、WebSocket | P1 |
| 参数化驱动 | `${var}` 语法、YAML/Excel/CSV 数据源 | P1 |
| 断言验证 | 状态码、响应时间、字段断言 | P1 |
| 用例编排 | 前置依赖、DAG 编排 | P1 |
| 并发检测 | 并发执行与线程安全验证 | P1 |
| 环境管理 | 多环境配置 | P1 |
| 历史报告 | 每次执行结果保留和趋势展示 | P2 |

### 11.3 用户操作流程

1. 用户在接口页面导入或手工编写接口用例。
2. 配置请求、参数化数据源和断言规则。
3. 将多个用例编排成测试场景。
4. 执行单用例或批量用例。
5. 查看请求详情、响应结果和断言结论。

### 11.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/api-test/cases | 获取接口用例列表 |
| POST | /api/v1/api-test/cases | 创建接口用例 |
| GET | /api/v1/api-test/cases/{id} | 获取详情 |
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
  method: str
  url: str
  headers: dict
  params: dict
  body: dict
  body_type: str
  protocol: str
  assertions: list[dict]
  dependencies: list[dict]
  timeout: int
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

- 复用现有 `engine/api_client.py` 作为底层 HTTP 能力。
- 参数化、依赖编排和断言执行应独立组件化。
- 接口测试模型应独立于 UI 测试用例模型。

### 11.7 风险与对策

| 风险 | 对策 |
|------|------|
| 参数化循环引用 | 执行前做依赖检测 |
| 数据源文件异常 | 解析失败时记录并中止该组数据 |
| 并发导致资源耗尽 | 最大并发数可配置 |
| WebSocket 长连接资源占用高 | 连接池和超时机制控制 |

---

## 12. 黑白盒测试

### 12.1 背景与目标

整合 Web 自动化（黑盒）和单元/集成测试（白盒）能力，提供统一的测试编排和报告平台，满足 UI 功能测试与代码质量验证场景。

### 12.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 黑盒业务流程编排 | 串联页面操作和断言步骤 | P3 |
| 跨浏览器测试 | Chromium/Firefox/WebKit | P3 |
| 截图/录屏 | 每步截图，失败自动录屏 | P3 |
| 用例隔离 | 每个用例独立浏览器上下文 | P3 |
| 白盒测试接入 | 接入 pytest 执行结果 | P3 |
| 覆盖率采集 | 集成 coverage.py | P3 |
| 统一报告 | 汇总黑盒与白盒结果 | P3 |

### 12.3 用户操作流程

1. 用户录制或编写黑盒步骤，或配置 pytest 路径。
2. 选择浏览器、超时、覆盖率等参数。
3. 发起执行，实时查看进度。
4. 查看统一报告与覆盖率结果。

### 12.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/blackwhite/suites | 创建测试套件 |
| GET | /api/v1/blackwhite/suites | 获取套件列表 |
| GET | /api/v1/blackwhite/suites/{id} | 获取套件详情 |
| PUT | /api/v1/blackwhite/suites/{id} | 更新套件 |
| DELETE | /api/v1/blackwhite/suites/{id} | 删除套件 |
| POST | /api/v1/blackwhite/suites/{id}/run | 执行套件 |
| GET | /api/v1/blackwhite/suites/{id}/report | 获取报告 |
| GET | /api/v1/blackwhite/tasks/{id}/coverage | 获取覆盖率报告 |
| GET | /api/v1/blackwhite/browser/versions | 获取支持的浏览器版本 |

### 12.5 数据模型

```python
TestSuite:
  id: int (PK)
  name: str
  task_type: str
  browsers: list[str]
  case_ids: list[int]
  pytest_paths: list[str]
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
  results: dict
  coverage_report: str
  created_at: datetime
  finished_at: datetime
```

### 12.6 技术实现要点

- 黑盒复用现有 Playwright 执行能力。
- 白盒通过受控子进程调用 pytest。
- 报告层统一聚合黑盒结果和覆盖率结果。

### 12.7 风险与对策

| 风险 | 对策 |
|------|------|
| 多浏览器并发占用内存高 | 采用浏览器池与并发限制 |
| 白盒执行用户代码存在安全风险 | 使用隔离执行策略 |
| 录屏占用存储大 | 仅保留失败用例录屏 |

---

## 13. 代理模块

### 13.1 背景与目标

构建统一的代理池管理能力，支持 HTTP/HTTPS/SOCKS5 多种协议，实现健康检查、调度、统计和告警，为接口、SEO、爬虫等模块提供稳定代理资源。

### 13.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 代理池管理 | 添加/编辑/删除代理 | P2 |
| 健康检查 | 定时检查代理可用性 | P2 |
| 调度策略 | 轮询、随机、失败切换 | P2 |
| 使用统计 | 延迟、可用率、使用次数 | P2 |
| 本地代理服务 | 提供本地代理转发能力 | P2 |
| 告警 | 可用率过低时通知 | P2 |
| 分组管理 | 代理按组隔离管理 | P2 |

### 13.3 用户操作流程

1. 导入或手工维护代理列表。
2. 设置检测频率和调度策略。
3. 系统自动维护可用性状态。
4. 上层模块按需获取可用代理。

### 13.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/proxy/list | 获取代理列表 |
| POST | /api/v1/proxy/add | 添加代理 |
| POST | /api/v1/proxy/batch | 批量导入代理 |
| PUT | /api/v1/proxy/{id} | 更新代理 |
| DELETE | /api/v1/proxy/{id} | 删除代理 |
| GET | /api/v1/proxy/{id}/stats | 获取代理统计 |
| POST | /api/v1/proxy/{id}/test | 手动检测 |
| GET | /api/v1/proxy/available | 获取可用代理 |
| POST | /api/v1/proxy/refresh | 刷新健康状态 |
| GET | /api/v1/proxy/stats | 获取统计汇总 |
| POST | /api/v1/proxy/alert/rules | 创建告警规则 |
| GET | /api/v1/proxy/alert/rules | 获取告警规则 |

### 13.5 数据模型

```python
Proxy:
  id: int (PK)
  name: str
  protocol: str
  host: str
  port: int
  username: str
  password: str
  group_id: int
  tags: list[str]
  avg_latency_ms: float
  success_rate: float
  use_count: int
  last_check_at: datetime
  last_used_at: datetime
  status: str
  created_at: datetime
  updated_at: datetime

ProxyGroup:
  id: int (PK)
  name: str
  description: str
  strategy: str

AlertRule:
  id: int (PK)
  condition: str
  threshold: float
  enabled: bool
  webhook_url: str
  created_at: datetime
```

### 13.6 技术实现要点

- 使用异步请求做健康检查。
- 密码字段需加密存储。
- 调度策略从服务层抽象。

### 13.7 风险与对策

| 风险 | 对策 |
|------|------|
| 代理池大面积失效 | 分组隔离与告警提前发现 |
| 敏感认证信息泄漏 | 加密存储并避免日志打印 |
| 本地代理成为单点 | 支持多实例与负载分发 |

---

## 14. 爬虫抓取功能日常巡检

### 14.1 背景与目标

实现对已注册爬虫脚本或抓取任务的自动化巡检，监控存活状态、成功率、数据质量和新鲜度，及时发现异常并告警。

### 14.2 功能清单

| 功能点 | 描述 | 优先级 |
|--------|------|--------|
| 爬虫注册 | 录入脚本路径、入口 URL、预期抓取量 | P3 |
| 存活检测 | 检查进程和运行状态 | P3 |
| 成功率检测 | 抓取量与预期值对比 | P3 |
| 数据完整性 | 校验关键字段 schema | P3 |
| 新鲜度检测 | 检查数据更新时间 | P3 |
| 反爬检测 | 标记验证码、封禁等场景 | P3 |
| 执行日志 | 保留巡检输出和错误信息 | P3 |
| 告警通知 | 支持飞书/钉钉/Webhook 等渠道 | P3 |

### 14.3 用户操作流程

1. 用户注册爬虫及巡检参数。
2. 设置巡检频率、阈值和告警规则。
3. 系统定时执行巡检。
4. 任务完成后输出状态、日志和异常信息。

### 14.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/crawler/configs | 获取配置列表 |
| POST | /api/v1/crawler/configs | 添加配置 |
| GET | /api/v1/crawler/configs/{id} | 获取详情 |
| PUT | /api/v1/crawler/configs/{id} | 更新配置 |
| DELETE | /api/v1/crawler/configs/{id} | 删除配置 |
| GET | /api/v1/crawler/inspections | 获取巡检记录 |
| GET | /api/v1/crawler/inspections/{id} | 获取巡检详情 |
| POST | /api/v1/crawler/inspections/{id}/run | 立即巡检 |
| GET | /api/v1/crawler/stats | 获取巡检统计 |
| POST | /api/v1/crawler/configs/{id}/schema | 设置字段 schema |

### 14.5 数据模型

```python
CrawlerConfig:
  id: int (PK)
  project_id: int (FK)
  name: str
  script_path: str
  entry_url: str
  interval: int
  expected_count: int
  completeness_schema: dict
  freshness_threshold: int
  enabled: bool
  created_at: datetime
  updated_at: datetime

CrawlerInspection:
  id: int (PK)
  crawler_id: int (FK)
  status: str
  items_count: int
  error_count: int
  duration_ms: int
  error_msg: text
  anti_crawl_detected: bool
  checked_at: datetime
```

### 14.6 技术实现要点

- 通过进程检测和脚本执行结果判断爬虫健康状态。
- 通过 schema 校验和更新时间检查数据质量。
- 结果以巡检记录方式持久化。

### 14.7 风险与对策

| 风险 | 对策 |
|------|------|
| 巡检本身触发反爬 | 限速 + 代理轮换 + 退出机制 |
| 外部依赖异常导致误判 | 巡检记录外部依赖健康状态 |
| 成功率基线不统一 | 允许用户自定义阈值和预期值 |

---

# 附录

## A. 开发优先级汇总

| 优先级 | 功能模块 | 说明 |
|--------|----------|------|
| P0 | 当前核心能力稳定化 | 现有功能维护、bug 修复、与源码基线对齐 |
| P1 | 接口检测 | 复用现有 API 基础能力，收益快 |
| P1 | 性能检测 | 复用 Playwright，价值明确 |
| P2 | SEO 检测 | 依赖页面渲染和规则体系 |
| P2 | 代理模块 | 被多个模块依赖，建议前置 |
| P3 | 黑白盒测试 | 涉及安全隔离和架构调整 |
| P3 | 爬虫巡检 | 依赖外部爬虫成熟度 |

## B. 技术栈总览

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Element Plus + ECharts |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| UI 自动化 | Playwright |
| 接口基础能力 | requests + httpx |
| 定时任务 | APScheduler |
| AI 能力 | MiniMax API |
| 通知 | 飞书 Webhook（当前基线） |

## C. 文档版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-04-22 | 初始版本，包含现有功能 PRD + 6 个新增功能 PRD |
| v1.1 | 2026-04-22 | 正式完整版，修正现状/规划混写问题，并按源码基线完整重构 |

---

**文档状态：** 正式完整版  
**下一步：** 以本版本作为正式需求评审基线
