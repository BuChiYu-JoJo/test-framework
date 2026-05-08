# AI Web 自动化测试闭环平台开发方案

**版本**：V1.0  
**适用范围**：Web 自动化测试平台 / AI 用例生成 / AI 元素定位 / Playwright 自动执行 / 自动修复闭环  
**建议保存路径**：`docs/ai_web_automation_closed_loop_plan.md`  
**核心目标**：让测试人员可以从 PRD 出发，自动生成用例，自动识别元素，执行 Web 自动化测试，生成报告，并在元素变化后通过 AI 自动修复定位，形成持续可维护闭环。

---

## 1. 核心需求定义

当前需求不是单纯的 Web 自动化脚本，也不是单独的 AI 用例生成工具，而是一套完整的 **AI Web 自动化测试闭环平台**。

核心链路如下：

```text
PRD 文档
  ↓
AI 解析需求
  ↓
生成测试点
  ↓
生成结构化测试用例
  ↓
人工确认 / 编辑
  ↓
AI 识别页面元素
  ↓
生成多策略 Locator
  ↓
执行自动化测试
  ↓
生成报告 / 截图 / Trace
  ↓
失败分析
  ↓
AI 自动修复 Locator
  ↓
验证新 Locator
  ↓
人工确认 / 自动回写
  ↓
沉淀测试资产
```

平台最终沉淀 6 类资产：

```text
1. PRD 需求资产
2. 测试用例资产
3. 元素定位资产
4. 执行结果资产
5. 报告与日志资产
6. AI 修复资产
```

---

## 2. 建设目标

### 2.1 业务目标

| 目标 | 说明 |
|---|---|
| 降低用例编写门槛 | 非代码人员可以基于 PRD 生成测试用例 |
| 降低自动化维护成本 | 元素变化后由 AI 辅助修复定位 |
| 提升执行效率 | 用例可批量执行、定时执行、按标签执行 |
| 提升问题定位效率 | 报告包含截图、Trace、失败原因、Locator 命中记录 |
| 形成可复用资产库 | PRD、用例、Locator、执行报告持续沉淀 |

### 2.2 技术目标

| 目标 | 说明 |
|---|---|
| 配置驱动 | 用例、定位、环境、数据不硬编码 |
| 分层隔离 | 用例 DSL、Locator、执行引擎、报告分离 |
| 多策略定位 | 每个元素支持多个 Locator fallback |
| AI 可控 | AI 结果必须验证，可人工确认 |
| 可回滚 | AI 修复后的定位变更可追踪、可回退 |
| 可扩展 | 后续可扩展 API 测试、SEO、性能检测等模块 |

---

## 3. 总体架构

```text
┌───────────────────────────────────────────────────────────────┐
│                         用户层                                 │
├───────────────────────────────────────────────────────────────┤
│  PRD上传  │ AI用例生成 │ 用例管理 │ Locator管理 │ 执行中心 │ 报告中心 │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         后端服务层                              │
├───────────────────────────────────────────────────────────────┤
│ PRD Service                                                    │
│ AI Case Service                                                │
│ Case Service                                                   │
│ Locator Service                                                │
│ AI Locator Service                                             │
│ Execution Service                                              │
│ Report Service                                                 │
│ Locator Repair Service                                         │
│ Notification Service                                           │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         执行引擎层                              │
├───────────────────────────────────────────────────────────────┤
│ Engine                                                         │
│ Keyword Executor                                               │
│ Locator Resolver                                               │
│ Playwright Client                                              │
│ Self Healing Engine                                            │
│ Reporter                                                       │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         存储层                                  │
├───────────────────────────────────────────────────────────────┤
│ MySQL / SQLite                                                 │
│ 文件存储                                                       │
│ 截图                                                           │
│ Trace                                                          │
│ HTML Report                                                    │
│ JSON Report                                                    │
└───────────────────────────────────────────────────────────────┘
```

---

## 4. 推荐目录结构

```text
test-framework/
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── prd/                    # PRD管理
│       │   ├── ai-cases/               # AI用例生成
│       │   ├── cases/                  # 用例管理
│       │   ├── locators/               # Locator管理
│       │   ├── execution/              # 执行中心
│       │   ├── reports/                # 报告中心
│       │   └── repair/                 # AI修复中心
│       ├── components/
│       └── router/
│
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       ├── prd.py
│       │       ├── ai_cases.py
│       │       ├── cases.py
│       │       ├── locators.py
│       │       ├── ai_locators.py
│       │       ├── execution.py
│       │       ├── reports.py
│       │       └── locator_repair.py
│       ├── models/
│       │   ├── prd_document.py
│       │   ├── generated_case.py
│       │   ├── test_case.py
│       │   ├── locator.py
│       │   ├── locator_strategy.py
│       │   ├── execution.py
│       │   └── locator_repair_record.py
│       ├── schemas/
│       ├── services/
│       │   ├── prd_service.py
│       │   ├── ai_case_service.py
│       │   ├── case_service.py
│       │   ├── locator_service.py
│       │   ├── ai_locator_service.py
│       │   ├── execution_service.py
│       │   ├── report_service.py
│       │   └── locator_repair_service.py
│       └── core/
│
├── engine/
│   ├── engine.py
│   ├── keyword_executor.py
│   ├── web_keyword_executor.py
│   ├── locator_resolver.py
│   ├── locator_resolver_v2.py
│   ├── playwright_client.py
│   ├── self_healing.py
│   ├── reporter.py
│   └── parser/
│       ├── yaml_parser.py
│       ├── excel_parser.py
│       └── json_parser.py
│
├── projects/
│   └── dataify/
│       ├── env/
│       ├── cases/
│       ├── locators/
│       ├── test_data/
│       └── prd/
│
├── reports/
│   ├── execution/
│   ├── screenshots/
│   ├── traces/
│   └── repair/
│
└── docs/
    └── ai_web_automation_closed_loop_plan.md
```

---

## 5. 核心闭环设计

### 5.1 PRD 到用例闭环

```text
上传 PRD
  ↓
AI 解析页面、字段、按钮、校验规则、异常逻辑
  ↓
生成测试点
  ↓
生成结构化测试用例
  ↓
人工确认
  ↓
导入用例库
```

### 5.2 用例到自动化闭环

```text
测试用例
  ↓
转换为 DSL
  ↓
关联 Locator Key
  ↓
执行引擎解析
  ↓
Playwright 执行
  ↓
生成报告
```

### 5.3 元素定位闭环

```text
页面 DOM / 截图 / 元素语义
  ↓
AI 生成多策略 Locator
  ↓
实际页面验证
  ↓
命中唯一元素
  ↓
保存 Locator 资产库
  ↓
执行时 fallback
```

### 5.4 自动修复闭环

```text
执行失败
  ↓
判断是否 Locator 问题
  ↓
采集 DOM + 截图 + 原 Locator + 用例语义
  ↓
AI 生成新 Locator
  ↓
验证新 Locator
  ↓
重放失败步骤
  ↓
生成修复记录
  ↓
人工确认 / 自动回写
```

---

## 6. PRD 解析模块设计

### 6.1 输入

```text
1. Markdown PRD
2. Word PRD
3. PDF PRD
4. 纯文本需求
5. 页面截图或设计稿说明
```

### 6.2 输出结构

```json
{
  "project": "dataify",
  "module": "实名认证",
  "pages": [
    {
      "name": "实名认证入口页",
      "elements": [
        "个人认证选项卡",
        "企业认证选项卡",
        "去认证按钮",
        "刷新按钮"
      ],
      "rules": [
        "页面加载时必须先查询认证状态",
        "接口失败时显示错误提示和刷新按钮"
      ]
    }
  ],
  "validations": [
    {
      "field": "身份证号码",
      "rule": "必须为18位，尾号X必须大写"
    }
  ],
  "apis": [
    {
      "method": "GET",
      "path": "/api/auth/realname/status"
    }
  ]
}
```

### 6.3 PRD 解析结果应包含

| 类型 | 示例 |
|---|---|
| 页面 | 实名认证入口页、个人认证填写页 |
| 元素 | 按钮、输入框、弹窗、上传区域 |
| 操作 | 点击、输入、上传、等待 |
| 校验 | 必填、格式、长度、状态 |
| 异常 | 接口失败、二维码失败、轮询超时 |
| 状态 | 未认证、审核中、已认证、失败 |
| 接口 | 状态查询、提交、轮询 |
| 文案 | 错误提示、按钮文案、状态提示 |

---

## 7. AI 用例生成模块设计

### 7.1 生成策略

AI 用例生成不应只生成主流程，应覆盖以下类型：

```text
1. 正向流程
2. 反向流程
3. 边界值
4. 异常流
5. UI交互
6. 状态流转
7. 接口失败
8. 权限与登录态
9. 上传类场景
10. 定时 / 轮询场景
```

### 7.2 用例字段设计

```json
{
  "case_id": "REALNAME-P0-001",
  "module": "实名认证",
  "page": "个人认证信息填写页",
  "title": "身份证号码为空时提交按钮置灰",
  "priority": "P0",
  "case_type": "ui",
  "precondition": "用户已登录并进入个人认证信息填写页",
  "steps": [
    "输入合法姓氏",
    "输入合法名字",
    "清空身份证号码输入框",
    "观察提交按钮状态"
  ],
  "test_data": {
    "surname": "王",
    "name": "小明",
    "id_card": ""
  },
  "expected_result": "身份证号码输入框显示错误提示，提交按钮置灰不可点击",
  "automation_recommended": true,
  "ai_reason": "该用例覆盖身份证必填校验，属于P0表单校验场景"
}
```

### 7.3 AI 用例生成后的人工确认

AI 生成的用例必须进入确认页，确认页支持：

```text
1. 编辑标题
2. 编辑前置条件
3. 编辑步骤
4. 编辑测试数据
5. 编辑预期结果
6. 设置优先级
7. 设置是否自动化
8. 批量导入
9. 丢弃用例
```

### 7.4 用例导入规则

| 条件 | 处理 |
|---|---|
| 人工确认通过 | 导入正式用例库 |
| 未确认 | 保留在生成草稿 |
| 重复用例 | 提示合并或覆盖 |
| 缺少预期结果 | 禁止导入 |
| 缺少步骤 | 禁止导入 |

---

## 8. 用例 DSL 设计

### 8.1 为什么使用 DSL

不建议让 AI 直接生成 Python 自动化代码作为主资产。

推荐生成 DSL，原因：

```text
1. 非技术人员可读
2. 方便 Web 页面编辑
3. 执行引擎统一解释
4. 后续可以转换成 Playwright
5. 易于版本管理和回归
```

### 8.2 DSL 示例

```yaml
case_id: REALNAME-P0-001
title: Personal real-name authentication success flow
module: realname
page: personal_auth
priority: P0
case_type: ui
tags:
  - smoke
  - realname
  - personal

preconditions:
  - User is logged in
  - User has not completed real-name authentication

steps:
  - action: goto
    value: /account/security/realname

  - action: wait_for
    locator: realname.page_title
    timeout: 5000

  - action: click
    locator: realname.personal_tab

  - action: click
    locator: realname.go_auth_button

  - action: assert_visible
    locator: realname.personal_notice_dialog

  - action: click
    locator: realname.notice_continue_button

  - action: fill
    locator: realname.surname_input
    value: 王

  - action: fill
    locator: realname.name_input
    value: 小明

  - action: fill
    locator: realname.id_card_input
    value: "11010119900307411X"

  - action: click
    locator: realname.submit_button

  - action: assert_visible
    locator: realname.face_verify_dialog

expected:
  - type: visible
    locator: realname.face_verify_dialog
  - type: text_contains
    locator: realname.face_verify_title
    value: 人脸核验
```

### 8.3 支持的关键字

| 关键字 | 说明 |
|---|---|
| goto | 打开页面 |
| click | 点击元素 |
| fill | 输入内容 |
| upload | 上传文件 |
| wait_for | 等待元素出现 |
| wait_hidden | 等待元素消失 |
| wait_network_idle | 等待网络空闲 |
| assert_visible | 断言元素可见 |
| assert_hidden | 断言元素不可见 |
| assert_text | 断言文本 |
| assert_url | 断言 URL |
| assert_enabled | 断言按钮可用 |
| assert_disabled | 断言按钮置灰 |
| screenshot | 截图 |
| sleep | 固定等待，不推荐大量使用 |

---

## 9. AI Locator 模块设计

### 9.1 Locator 设计原则

每个元素不应只存一个定位方式，而应存多策略：

```text
1. data-testid
2. role
3. aria-label
4. text
5. css
6. xpath
7. relative locator
```

优先级建议：

```text
data-testid > role > aria-label > text > css > xpath
```

### 9.2 Locator 数据结构

```json
{
  "locator_key": "realname.go_auth_button",
  "description": "实名认证入口页去认证按钮",
  "strategies": [
    {
      "type": "testid",
      "value": "go-auth-button",
      "priority": 1,
      "confidence": 0.96
    },
    {
      "type": "role",
      "value": "button[name='去认证']",
      "priority": 2,
      "confidence": 0.93
    },
    {
      "type": "text",
      "value": "去认证",
      "priority": 3,
      "confidence": 0.86
    },
    {
      "type": "css",
      "value": "button[type='button']",
      "priority": 4,
      "confidence": 0.55
    }
  ]
}
```

### 9.3 AI Locator 输入

```json
{
  "page_url": "https://test.dataify.com/account/security/realname",
  "element_name": "去认证按钮",
  "business_key": "realname.go_auth_button",
  "business_description": "点击后打开认证须知弹窗",
  "page_html": "...",
  "screenshot_path": "screenshots/realname_entry.png",
  "preferred_strategy": [
    "data-testid",
    "role",
    "aria-label",
    "text",
    "css",
    "xpath"
  ]
}
```

### 9.4 AI Locator 输出

```json
{
  "locator_key": "realname.go_auth_button",
  "description": "实名认证入口页去认证按钮",
  "strategies": [
    {
      "type": "role",
      "value": "button[name='去认证']",
      "priority": 1,
      "confidence": 0.94,
      "reason": "按钮可见文本与业务动作一致"
    },
    {
      "type": "text",
      "value": "去认证",
      "priority": 2,
      "confidence": 0.88,
      "reason": "页面存在可见文本"
    }
  ]
}
```

### 9.5 Locator 验证规则

AI 生成定位后必须验证：

```text
1. 页面实际执行 locator
2. 命中数量必须等于 1
3. 元素必须可见
4. 元素必须符合预期类型
5. 点击类元素必须 enabled
6. 输入类元素必须 editable
7. 验证通过后才能保存
```

---

## 10. Locator Resolver 设计

### 10.1 解析逻辑

```text
读取 locator_key
  ↓
查询所有 enabled 策略
  ↓
按 priority 排序
  ↓
逐个尝试定位
  ↓
命中唯一元素则返回
  ↓
失败则 fallback 到下一个策略
  ↓
全部失败则抛出 LocatorNotFound
```

### 10.2 示例代码

```python
# NEW CODE: engine/locator_resolver_v2.py

class LocatorResolverV2:
    def __init__(self, locator_repository, execution_logger):
        self.locator_repository = locator_repository
        self.execution_logger = execution_logger

    async def resolve(self, page, locator_key: str):
        strategies = await self.locator_repository.get_enabled_strategies(locator_key)

        last_error = None

        for strategy in sorted(strategies, key=lambda item: item.priority):
            try:
                locator = self._build_locator(page, strategy)

                count = await locator.count()
                if count != 1:
                    raise ValueError(
                        f"Expected exactly one element, got {count}"
                    )

                await locator.first().wait_for(timeout=2000)

                await self.execution_logger.log_locator_hit(
                    locator_key=locator_key,
                    strategy_type=strategy.strategy_type,
                    strategy_value=strategy.strategy_value,
                    priority=strategy.priority
                )

                return locator.first()

            except Exception as error:
                last_error = error

                await self.execution_logger.log_locator_fallback(
                    locator_key=locator_key,
                    strategy_type=strategy.strategy_type,
                    strategy_value=strategy.strategy_value,
                    error=str(error)
                )

        raise RuntimeError(
            f"All locator strategies failed for {locator_key}: {last_error}"
        )

    def _build_locator(self, page, strategy):
        if strategy.strategy_type == "testid":
            return page.get_by_test_id(strategy.strategy_value)

        if strategy.strategy_type == "css":
            return page.locator(strategy.strategy_value)

        if strategy.strategy_type == "text":
            return page.get_by_text(strategy.strategy_value)

        if strategy.strategy_type == "role":
            return page.locator(strategy.strategy_value)

        if strategy.strategy_type == "xpath":
            return page.locator(f"xpath={strategy.strategy_value}")

        raise ValueError(f"Unsupported locator strategy: {strategy.strategy_type}")
```

---

## 11. 执行引擎设计

### 11.1 执行流程

```text
选择用例
  ↓
加载环境配置
  ↓
加载测试数据
  ↓
解析 DSL
  ↓
启动浏览器
  ↓
执行前置条件
  ↓
逐步执行关键字
  ↓
通过 Locator Resolver 获取元素
  ↓
执行断言
  ↓
保存截图 / Trace / 日志
  ↓
生成报告
```

### 11.2 Web Keyword Executor

```python
# NEW CODE: engine/web_keyword_executor.py

from playwright.async_api import Page, expect


class WebKeywordExecutor:
    def __init__(self, page: Page, locator_resolver):
        self.page = page
        self.locator_resolver = locator_resolver

    async def execute_step(self, step: dict, context: dict):
        action = step["action"]

        if action == "goto":
            await self.page.goto(context["base_url"] + step["value"])
            return

        if action == "click":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await locator.click()
            return

        if action == "fill":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await locator.fill(str(step["value"]))
            return

        if action == "upload":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await locator.set_input_files(step["value"])
            return

        if action == "wait_for":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await locator.wait_for(timeout=step.get("timeout", 5000))
            return

        if action == "assert_visible":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await expect(locator).to_be_visible()
            return

        if action == "assert_text":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await expect(locator).to_contain_text(step["value"])
            return

        if action == "assert_disabled":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await expect(locator).to_be_disabled()
            return

        if action == "assert_enabled":
            locator = await self.locator_resolver.resolve(self.page, step["locator"])
            await expect(locator).to_be_enabled()
            return

        raise ValueError(f"Unsupported action: {action}")
```

---

## 12. 自动修复模块设计

### 12.1 可自动修复的失败类型

只有 Locator 类失败才进入自动修复：

```text
1. element not found
2. locator timeout
3. strict mode violation
4. element detached
5. element invisible
6. element disabled
```

### 12.2 不应自动修复的失败类型

以下失败不应进行 Locator 修复：

```text
1. 断言文案错误
2. 接口返回错误
3. 业务流程错误
4. 权限错误
5. 页面 500
6. 测试数据错误
7. 后端状态异常
```

### 12.3 自动修复输入

```json
{
  "execution_id": 1001,
  "case_id": "REALNAME-P0-001",
  "step_index": 4,
  "action": "click",
  "locator_key": "realname.go_auth_button",
  "old_strategies": [
    {
      "type": "css",
      "value": "button.go-auth"
    }
  ],
  "failure_message": "Timeout 5000ms exceeded",
  "page_html": "...",
  "screenshot_path": "reports/1001/failure.png",
  "business_description": "点击去认证按钮，打开认证须知弹窗"
}
```

### 12.4 自动修复输出

```json
{
  "failure_type": "locator_changed",
  "repair_candidates": [
    {
      "type": "role",
      "value": "button[name='去认证']",
      "confidence": 0.94,
      "reason": "按钮文本与业务动作一致"
    },
    {
      "type": "text",
      "value": "去认证",
      "confidence": 0.87,
      "reason": "页面存在可见文本"
    }
  ]
}
```

### 12.5 自动修复流程

```text
失败发生
  ↓
识别失败类型
  ↓
如果是 Locator 失败，采集 DOM / 截图 / 原 Locator / 用例语义
  ↓
调用 AI 生成修复候选
  ↓
逐个验证候选 Locator
  ↓
命中唯一元素
  ↓
重放失败步骤
  ↓
如果通过，生成修复记录
  ↓
根据策略进入人工确认或自动回写
```

### 12.6 回写策略

| 场景 | 处理方式 |
|---|---|
| P0 用例修复成功 | 进入人工审核 |
| 非核心用例修复成功 | 可按配置自动回写 |
| 新策略命中多个元素 | 禁止回写 |
| 新策略命中 0 个元素 | 丢弃 |
| 修复后断言仍失败 | 标记为业务失败，不回写 |
| 同一新策略连续 3 次修复成功 | 可提升为高优先级策略 |

---

## 13. 报告设计

### 13.1 报告必须包含

```text
1. 执行概要
2. 用例结果
3. 步骤结果
4. 失败截图
5. Trace 文件
6. Console 日志
7. Network 日志
8. Locator 命中记录
9. Locator fallback 记录
10. AI 修复记录
11. 修复前后 Locator 对比
12. 是否回写 Locator
```

### 13.2 报告 JSON 示例

```json
{
  "execution_id": 1001,
  "project": "dataify",
  "env": "test",
  "status": "failed",
  "summary": {
    "total": 20,
    "passed": 18,
    "failed": 2,
    "repaired": 1
  },
  "cases": [
    {
      "case_id": "REALNAME-P0-001",
      "status": "passed_after_repair",
      "steps": [
        {
          "index": 4,
          "action": "click",
          "locator_key": "realname.go_auth_button",
          "status": "repaired",
          "old_locator": "button.go-auth",
          "new_locator": "button[name='去认证']"
        }
      ]
    }
  ],
  "artifacts": {
    "html_report": "reports/1001/index.html",
    "trace": "reports/1001/trace.zip",
    "screenshots": [
      "reports/1001/failure.png"
    ]
  }
}
```

### 13.3 报告页面体验要求

```text
1. 一眼看到通过率
2. 一眼看到失败用例
3. 可展开失败步骤
4. 可查看失败截图
5. 可查看 Locator fallback 路径
6. 可查看 AI 修复建议
7. 可点击批准修复
8. 可下载报告
```

---

## 14. 前端页面设计

### 14.1 PRD 管理页

功能：

```text
1. 上传 PRD
2. 查看 PRD 内容
3. 查看 AI 解析结果
4. 触发 AI 用例生成
5. 查看历史版本
```

### 14.2 AI 用例生成页

功能：

```text
1. 选择 PRD
2. 选择生成范围
3. 选择优先级策略
4. 生成测试点
5. 生成测试用例
6. 人工编辑用例
7. 批量导入用例库
```

### 14.3 用例管理页

增强字段：

```text
1. 用例来源：手工 / AI
2. 是否自动化
3. 关联 Locator 数量
4. 最近执行结果
5. 最近失败原因
6. 最近修复状态
```

### 14.4 Locator 管理页

功能：

```text
1. 查看 locator_key
2. 查看多策略
3. 查看优先级
4. 查看命中率
5. 查看失败次数
6. 查看 AI 修复候选
7. 一键验证 Locator
8. 启用 / 禁用策略
9. 调整策略优先级
```

### 14.5 执行中心

功能：

```text
1. 选择项目
2. 选择环境
3. 选择用例
4. 选择浏览器
5. 是否开启自动修复
6. 实时日志
7. 实时截图
8. 执行进度
```

### 14.6 报告中心

功能：

```text
1. 查看执行报告
2. 按项目筛选
3. 按环境筛选
4. 按结果筛选
5. 查看失败截图
6. 查看 Trace
7. 查看修复记录
8. 下载报告
```

### 14.7 AI 修复中心

功能：

```text
1. 查看修复记录
2. 对比旧 Locator / 新 Locator
3. 查看失败截图
4. 查看 AI 分析
5. 人工确认回写
6. 拒绝修复
7. 标记误判
```

---

## 15. 后端 API 设计

### 15.1 PRD API

```text
POST /api/v1/prd/upload
GET  /api/v1/prd/list
GET  /api/v1/prd/{id}
POST /api/v1/prd/{id}/parse
POST /api/v1/prd/{id}/generate-cases
```

### 15.2 AI 用例 API

```text
GET  /api/v1/ai-cases/generated
POST /api/v1/ai-cases/generate
PUT  /api/v1/ai-cases/{id}
POST /api/v1/ai-cases/import
```

### 15.3 Locator API

```text
GET  /api/v1/locators
POST /api/v1/locators
PUT  /api/v1/locators/{id}
POST /api/v1/locators/generate
POST /api/v1/locators/validate
POST /api/v1/locators/{key}/strategies
```

### 15.4 执行 API

```text
POST /api/v1/executions/run
GET  /api/v1/executions/{id}
GET  /api/v1/executions/{id}/logs
GET  /api/v1/executions/{id}/report
POST /api/v1/executions/{id}/stop
```

### 15.5 自动修复 API

```text
POST /api/v1/locator-repair/analyze
POST /api/v1/locator-repair/validate
GET  /api/v1/locator-repair/records
GET  /api/v1/locator-repair/{id}
POST /api/v1/locator-repair/{id}/approve
POST /api/v1/locator-repair/{id}/reject
```

---

## 16. 数据模型设计

### 16.1 PRD 文档模型

```python
# NEW CODE: backend/app/models/prd_document.py

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from backend.app.core.database import Base


class PRDDocument(Base):
    __tablename__ = "prd_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    file_name = Column(String(255), nullable=True)
    raw_content = Column(Text, nullable=False)
    parsed_result = Column(JSON, nullable=True)
    status = Column(String(50), default="uploaded")
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 16.2 AI 生成用例模型

```python
# NEW CODE: backend/app/models/generated_case.py

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from datetime import datetime
from backend.app.core.database import Base


class GeneratedCase(Base):
    __tablename__ = "generated_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    prd_id = Column(Integer, index=True, nullable=True)

    module = Column(String(100), nullable=False)
    page = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    priority = Column(String(20), default="P1")
    case_type = Column(String(50), default="ui")

    precondition = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False)
    test_data = Column(JSON, nullable=True)
    expected_result = Column(Text, nullable=False)

    automation_recommended = Column(Boolean, default=True)
    reviewed = Column(Boolean, default=False)
    imported = Column(Boolean, default=False)

    ai_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 16.3 Locator 策略模型

```python
# NEW CODE: backend/app/models/locator_strategy.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON
from datetime import datetime
from backend.app.core.database import Base


class LocatorStrategy(Base):
    __tablename__ = "locator_strategies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)

    locator_key = Column(String(255), index=True, nullable=False)
    description = Column(String(500), nullable=True)

    strategy_type = Column(String(50), nullable=False)
    strategy_value = Column(String(1000), nullable=False)
    priority = Column(Integer, default=1)

    confidence = Column(Float, default=0.0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    source = Column(String(50), default="manual")
    enabled = Column(Boolean, default=True)

    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

### 16.4 Locator 修复记录模型

```python
# NEW CODE: backend/app/models/locator_repair_record.py

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from datetime import datetime
from backend.app.core.database import Base


class LocatorRepairRecord(Base):
    __tablename__ = "locator_repair_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    execution_id = Column(Integer, index=True, nullable=False)

    case_id = Column(Integer, index=True, nullable=True)
    step_index = Column(Integer, nullable=False)

    locator_key = Column(String(255), nullable=False)
    old_strategy = Column(JSON, nullable=False)
    new_strategy_candidates = Column(JSON, nullable=False)

    selected_strategy = Column(JSON, nullable=True)
    repair_status = Column(String(50), default="pending")
    auto_applied = Column(Boolean, default=False)

    failure_reason = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 17. 执行配置设计

### 17.1 项目环境配置

```json
{
  "project": "dataify",
  "env": "test",
  "base_url": "https://test.dataify.com",
  "browser": "chromium",
  "headless": true,
  "timeout": 10000,
  "trace": true,
  "video": false,
  "screenshot": "only-on-failure",
  "auto_repair": true
}
```

### 17.2 自动修复配置

```json
{
  "auto_repair_enabled": true,
  "auto_apply_enabled": false,
  "max_repair_attempts": 3,
  "require_manual_approval_for_p0": true,
  "min_confidence": 0.85,
  "allow_text_locator": true,
  "allow_xpath_locator": false
}
```

---

## 18. AI 提示词设计

### 18.1 PRD 生成用例提示词要点

```text
你是资深测试架构师。
请基于 PRD 生成结构化测试用例。
必须覆盖：
1. 主流程
2. 异常流程
3. 表单校验
4. 按钮状态
5. 弹窗交互
6. 接口失败
7. 边界值
8. 状态流转

输出必须为 JSON。
每条用例必须包含：
case_id, module, page, title, priority, precondition, steps, test_data, expected_result, automation_recommended, ai_reason。
不要生成重复用例。
```

### 18.2 AI Locator 生成提示词要点

```text
你是 Web 自动化定位专家。
请根据页面 DOM、截图描述和业务目标，生成稳定的元素定位策略。
优先级：
data-testid > role > aria-label > text > css > xpath。

必须输出多个候选策略。
不要使用容易变化的 class。
如果只能使用 class，需要说明风险。
输出 JSON。
```

### 18.3 AI 修复提示词要点

```text
你是 Playwright 自动化测试修复专家。
当前测试因为元素定位失败。
请根据旧 locator、失败信息、页面 DOM、截图描述和业务动作，判断是否是 locator 变化。
如果是，请生成新的 locator 候选。
候选必须尽可能稳定。
不要修改业务断言。
不要绕过测试。
输出 JSON。
```

---

## 19. 验收标准

### 19.1 MVP 验收

```text
1. 可以上传 PRD
2. 可以生成测试用例
3. 可以人工确认并导入
4. 可以生成或维护 Locator
5. 可以执行 UI 自动化用例
6. 可以生成报告
```

### 19.2 AI Locator 验收

```text
1. 每个元素支持多个定位策略
2. 定位策略执行前经过验证
3. 执行时支持 fallback
4. 报告记录实际命中的策略
5. 失败时能看到所有失败策略
```

### 19.3 自动修复验收

```text
1. 能识别 Locator 类失败
2. 能采集 DOM 和失败截图
3. 能生成修复候选
4. 能验证候选是否唯一命中
5. 能重放失败步骤
6. 能生成修复记录
7. 能人工确认回写
```

### 19.4 易用性验收

```text
1. 测试人员不写代码也能生成用例
2. 测试人员可以通过页面编辑用例
3. 测试人员可以通过页面查看和确认 Locator
4. 失败报告能看懂
5. AI 修复建议可视化展示
```

---

## 20. 六周落地计划

### 第 1 周：PRD 到用例

交付：

```text
1. PRD 上传
2. PRD 解析
3. AI 生成测试点
4. AI 生成测试用例
5. 人工确认页
6. 导入用例库
```

验收：

```text
上传实名认证 PRD 后，可以生成 Page1~Page7 的结构化用例。
```

### 第 2 周：用例到执行

交付：

```text
1. 用例 DSL
2. Keyword Executor 增强
3. Playwright 执行
4. 截图
5. Trace
6. 基础报告
```

验收：

```text
可以执行实名认证入口页、须知弹窗、表单校验等 UI 用例。
```

### 第 3 周：AI Locator

交付：

```text
1. DOM 采集
2. AI Locator 生成
3. 多策略保存
4. Locator 验证
5. fallback 执行
```

验收：

```text
一个元素至少保存 2~3 个定位策略，主策略失败后可 fallback。
```

### 第 4 周：自动修复

交付：

```text
1. 识别 Locator 失败
2. 采集失败上下文
3. AI 生成修复候选
4. 验证候选
5. 生成修复记录
```

验收：

```text
修改按钮 class 后，系统可以通过文本/role 重新识别元素并给出修复建议。
```

### 第 5 周：修复回写和报告

交付：

```text
1. 修复中心
2. 人工确认回写
3. 报告展示修复过程
4. Locator 成功率统计
```

验收：

```text
报告能展示旧 Locator、失败原因、新 Locator、是否回写。
```

### 第 6 周：体验优化

交付：

```text
1. 批量执行
2. 执行日志
3. 失败筛选
4. 用例标签
5. 通知
6. 权限
7. 操作审计
```

验收：

```text
测试人员可以从上传 PRD 到执行报告完整走通，不需要写代码。
```

---

## 21. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| AI 生成用例不准确 | 用例质量下降 | 必须人工确认 |
| AI Locator 命中多个元素 | 执行不稳定 | 命中数量必须等于 1 |
| class 经常变化 | Locator 易失效 | 优先 data-testid / role / text |
| 自动修复误判 | 错误回写 | P0 用例必须人工确认 |
| 报告不可读 | 排查困难 | 报告必须展示截图、Trace、Locator 记录 |
| PRD 描述不完整 | 用例缺失 | 生成结果标记不确定项 |
| 业务失败被误认为定位失败 | 修复方向错误 | 失败分类规则必须严格 |

---

## 22. 最终建议

本平台不应做成三个分散工具：

```text
1. AI 用例生成工具
2. Playwright 自动化工具
3. Locator 修复工具
```

而应该做成一个统一闭环：

```text
需求资产
  ↓
用例资产
  ↓
元素资产
  ↓
执行资产
  ↓
报告资产
  ↓
修复资产
```

最关键的设计原则：

```text
1. 用例不要直接生成代码，先生成 DSL
2. Locator 不要单策略，必须多策略 fallback
3. AI 生成内容必须验证后入库
4. 自动修复必须先验证，再人工确认或规则化回写
5. 报告必须展示“为什么失败”和“如何修复”
```

最终平台形态：

```text
AI Web 自动化测试闭环平台
```

它的核心价值不是“自动跑脚本”，而是：

```text
让测试资产可以从需求自动生成，
让执行可以稳定复用，
让失败可以自动分析，
让元素变化可以自动修复，
让整个平台越用越准。
```
