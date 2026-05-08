# Test Framework 优化实施方案（V1.0）

| 文档项 | 内容 |
| --- | --- |
| 文档名称 | 测试平台体验闭环优化实施方案 |
| 文档版本 | V1.0 |
| 适用项目 | `test-framework`（通用 AI 自动化测试平台） |
| 文档目的 | 在不破坏现有架构的前提下，将"功能可用"提升为"工作流可用"，使平台真正具备 AI 时代的测试效率红利 |
| 落地路径 | `docs/optimization_implementation_plan.md` |
| 编制依据 | `development_plan_current_state.md`、`ai_web_automation_closed_loop_plan.md`、当前代码库实测审计 |
| 实施周期 | 6 周（迭代式增量交付） |
| 状态 | 待评审 |

---

## 修订记录

| 版本 | 日期 | 修订人 | 说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-05-07 | 平台研发组 | 首次发布。基于代码实测的体验闭环优化方案 |

---

## 1. 文档目的与范围

### 1.1 文档目的

当前 `test-framework` 项目已具备较完整的功能矩阵，包括用例管理、Locator 管理、UI / API / SEO / 性能多类执行、AI Locator 自愈、AI 步骤验证、AI 用例生成等。然而在实际使用过程中，存在 **"单功能可用、组合不流畅"** 的体验问题。

本文档旨在：

1. 基于现有代码的真实状态，识别出影响测试工程师日常使用流畅度的核心断点；
2. 给出一套**不重构核心引擎**、**渐进式增强**的优化实施方案；
3. 提供具体到模块、接口、数据结构、前后端代码骨架级别的实施细则；
4. 明确里程碑、交付物、验收标准与风险对策。

### 1.2 适用范围

| 模块 | 是否覆盖 |
| --- | --- |
| 执行引擎（`engine/`） | 仅做接口扩展，不重构核心 |
| 后端服务（`backend/app/`） | 新增统一调度层，强化 AI 服务闭环 |
| 前端（`frontend/src/`） | 新增 PRD/AI 工作台，串联现有页面 |
| 数据模型 | 新增任务统一表、Locator 修复记录表、Locator 命中统计表 |
| 报告中心 | 统一格式与展示 |
| 代理池 / 爬虫 / 黑白盒 | 不在本期范围 |

### 1.3 与既有规划文档的关系

| 既有文档 | 关系 |
| --- | --- |
| `development_plan_current_state.md` | 本文档继承其阶段划分与 TaskDispatcher 思想，并对 AI 闭环做更深入的实施细化 |
| `ai_web_automation_closed_loop_plan.md` | 本文档将其规划态闭环转化为可落地的代码与里程碑 |
| `PRD_v1.x.md`、`设计文档_v1.x.md` | 本文档不修改产品需求，仅补强工程实现 |

---

## 2. 术语表

| 术语 | 含义 |
| --- | --- |
| Task | 平台中所有可调度的执行单元，含 UI / API / SEO / Performance / AI 类任务 |
| TaskDispatcher | 后端任务统一调度入口，负责按 task_type 路由到具体服务 |
| Locator Healer | AI Locator 自愈器，当 fallback 策略全部失败时由 AI 视觉识别新策略 |
| Step Observer | AI 步骤观察器，每步执行后用 AI 视觉判断操作是否真正生效 |
| Repair Record | 一次 Locator 自愈事件的完整记录，含旧策略、新策略、置信度、是否被人工确认 |
| 命中策略 | LocatorResolver 在多策略中实际命中并完成定位的那一条策略 |
| 工作台（Workbench） | 用户打开后无需在多个页面间切换即可完成"PRD→用例→执行→报告→修复"全流程的统一前端入口 |

---

## 3. 现状评估（基于代码实测）

### 3.1 已具备的能力

| 能力 | 实现位置 | 完成度 |
| --- | --- | --- |
| 多策略 Locator 解析 + fallback | `engine/locator_resolver.py` | ✅ 已落地 |
| AI Locator 自愈 + 自动写回 JSON | `engine/ai_locator_healer.py:40-294` | ✅ 已落地 |
| AI 步骤观察验证 | `engine/ai_step_observer.py:45-240` | ✅ 已落地 |
| AI 服务统一基类（MiniMax 模型） | `backend/app/services/ai_base.py` | ✅ 已落地 |
| AI Locator 生成接口 | `backend/app/api/v1/ai_locators.py` | ✅ 已落地 |
| AI 用例生成（含 PRD 解析） | `backend/app/services/ai_case_from_prd.py`、`prd_parser.py`、`ai_case_orchestrator.py` | ⚠️ 服务层已实现，前端入口缺失 |
| 用例自动修复（失败重写） | `backend/app/services/case_auto_fix.py` | ⚠️ 服务存在，未串接到执行流程 |
| Locators DB↔JSON 同步 | `engine/engine.py:308-392` | ✅ 已落地 |
| SSE 实时日志 | `backend/app/services/events.py` + `event_bus` | ✅ 已落地 |
| 多任务类型独立执行 | `execution.py`、`api_test.py`、`seo.py`、`performance.py` | ⚠️ 各走各路，无统一入口 |
| 项目 / 用例 / Locator 管理后台 | `frontend/src/views/{cases,projects,locators}` | ✅ 已落地 |

### 3.2 体验断点清单

| 编号 | 断点 | 现象 | 根因 |
| --- | --- | --- | --- |
| B-01 | 任务入口分散 | 前端为每种任务（UI/API/SEO/性能/AI 回归）维护不同的请求与状态码 | 后端无 `POST /tasks/{type}/{id}/run` 统一入口 |
| B-02 | 用例 → 执行无快捷链路 | 编辑用例后需切到执行中心重新选项目和用例 | `CasesView` 行内缺"立即运行"按钮 |
| B-03 | 执行 → 报告无回链 | 任务结束后需自行去报告中心查找 | `Execution` 完成事件不携带报告 ID |
| B-04 | 报告 → 修复无快捷链路 | 失败后需手动去 Locators 页修策略 | 报告详情页缺"AI 修复并重跑"按钮 |
| B-05 | AI Locator 生成结果未做命中数验证 | 生成的 selector 可能匹配 0 或 >1 个元素，仍被保存为高优先级 | `ai_locators.py` 缺 Playwright 校验环节 |
| B-06 | Locator 自愈缺修复记录 | 自愈成功后只更新 JSON，没有审计、对比、回滚机制 | 缺 `locator_repair_record` 表与对应服务 |
| B-07 | Locator 健康度无可见性 | 用户不知道哪些 Locator 经常 fallback、哪些已失效 | 缺命中统计表与前端展示组件 |
| B-08 | 报告格式各模块不统一 | UI/API/SEO/性能产出的报告字段、目录结构、HTML 模板各异 | 缺统一 Report 模型 |
| B-09 | PRD → 用例的前端入口缺失 | 服务层 `prd_parser.py` 已实现，但 `AiToolsView.vue` 只有 Locator Tab | 前端工作台缺失 |
| B-10 | 智能回归推荐未串接 | `ai_regression.py` 服务存在，但前端无"基于 git diff 推荐"入口 | 缺前后端衔接 |

### 3.3 体验断点与本方案的对应关系

| 断点 | 解决层 |
| --- | --- |
| B-01、B-08 | Layer 2：TaskDispatcher 统一任务模型 |
| B-02、B-03、B-04 | Layer 3：工作流串联与导航闭环 |
| B-05、B-06、B-07 | Layer 1：AI 闭环深度集成 |
| B-09、B-10 | Layer 1（PRD 入口） + Layer 3（前端串联） |

---

## 4. 优化总目标与设计原则

### 4.1 总目标

将测试工程师的核心日常路径从"在 11 个独立功能页之间手动切换"压缩为**一条由 AI 全程在场的工作流**：

```
PRD（或缺陷单 / Git diff）
  → AI 解析并生成测试点
  → 人工确认 / 编辑
  → 一键入库（用例 + Locator）
  → 一键执行（统一调度）
  → 实时日志与命中策略
  → 自动 AI 自愈失败 Locator（带修复记录）
  → AI 验证步骤是否真正生效
  → 统一报告（含命中策略、修复记录、截图、Trace）
  → 一键回归（基于变更影响分析）
```

### 4.2 设计原则

1. **不动核心引擎**：`engine.py`、`keyword_executor.py`、`locator_resolver.py`、`playwright_client.py` 仅做对外接口扩展，绝不大规模重构。
2. **以 service 为分发层**：所有跨任务类型的统一逻辑下沉到 `backend/app/services` 中的 dispatcher，避免污染 engine。
3. **AI 必须可追溯、可回滚**：所有 AI 产出（Locator、用例、修复）必须留底，可在前端审计、可回退到上一版本。
4. **前端改造以"加链接"为主**：尽量复用现有页面与组件，新增导航与工作台，避免推倒重写。
5. **数据库以加表 + 加列为主**：不修改现有表语义，确保旧数据不受影响。
6. **观察先行、决策后行**：先沉淀命中策略统计与修复记录，再基于真实数据决定后续是否需要更复杂的策略调整算法。

### 4.3 不在本期范围

- 代理池 / 爬虫巡检 / 黑白盒测试
- 多租户 / 权限体系
- 跨执行节点的分布式调度（仍走单机后台线程）
- 移动端 App 自动化
- 引擎子目录大规模拆分

---

## 5. 总体架构与改造路线

### 5.1 改造前后对比

```
[改造前]
前端 ──(11 套独立调用)──→ 11 个 router ──→ 11 个 service ──→ engine

[改造后]
前端 ──(1 套统一调用)──→ TaskDispatcher ──┬─→ ui_execution_service
                                         ├─→ api_test_service
                                         ├─→ seo_service
                                         ├─→ performance_service
                                         └─→ ai_regression_service
                                                        │
                                              （内部均落到统一 task 表）
                                                        │
                                              event_bus（统一 SSE 事件契约）
```

### 5.2 四层改造路线

| 层 | 主题 | 周期 | 关键交付 |
| --- | --- | --- | --- |
| Layer 1 | AI 闭环深度集成 | W1–W3 | Locator 命中验证、修复记录、PRD 工作台、用例自动修复串接 |
| Layer 2 | TaskDispatcher 统一任务模型 | W1–W2 | 统一任务表、统一接口、统一 SSE 事件、统一报告字段 |
| Layer 3 | 工作流串联与导航闭环 | W3–W4 | 用例→执行→报告→修复全链路跳转、统一执行中心、AI 工作台 |
| Layer 4 | 可观测性与资产沉淀 | W4–W6 | Locator 命中统计、健康度面板、统一报告查看器、智能回归推荐 |

各层互相独立，可单独上线，不存在强制顺序约束。但建议按上述时间窗推进以最大化体验改善幅度。

---

## 6. Layer 1：AI 闭环深度集成

### 6.1 目标

将散落在 `services/ai_*.py` 与 `engine/ai_*.py` 中的能力，串成一条**可追溯、可回滚、可量化**的 AI 闭环：

```
PRD 上传 → AI 解析 → 用例草稿 → 人工确认 → 入库
            ↓
       执行时 Locator fallback 全部失败 → AI Healer
            ↓
       Healer 现场 Playwright 验证命中数=1
            ↓
       写入 locator_repair_record 表
            ↓
       写回 locators.json（priority=0）
            ↓
       Step Observer 验证步骤是否生效
            ↓
       失败时调用 case_auto_fix 重写步骤
            ↓
       全部记录在统一报告 artifacts 中
```

### 6.2 子任务 1.1：Locator 生成命中数自动校验

**问题**：当前 `backend/app/api/v1/ai_locators.py` 生成的 selector 直接保存，未在 Playwright 中校验"命中数 = 1"。

**改造点**：在 `services/ai_locator.py` 中增加校验阶段：

```python
# NEW CODE: backend/app/services/ai_locator.py 增量

from playwright.sync_api import sync_playwright


class LocatorVerificationResult:
    def __init__(self, hit_count: int, sample_html: str = "", error: str = ""):
        self.hit_count = hit_count
        self.sample_html = sample_html
        self.error = error

    @property
    def verdict(self) -> str:
        if self.error:
            return "error"
        if self.hit_count == 1:
            return "verified"
        if self.hit_count == 0:
            return "miss"
        return "ambiguous"


def verify_locator_strategy(
    page_url: str,
    selector: str,
    selector_type: str = "css",
    storage_state: dict | None = None,
    timeout_ms: int = 8000,
) -> LocatorVerificationResult:
    """在真实 Playwright 中校验 selector 命中数。"""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(storage_state=storage_state)
            page = context.new_page()
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)  # SPA 缓冲

            if selector_type == "xpath":
                count = page.locator(f"xpath={selector}").count()
            else:
                count = page.locator(selector).count()

            sample = ""
            if count >= 1:
                sample = page.locator(selector).first.evaluate("el => el.outerHTML")[:500]

            context.close()
            browser.close()
            return LocatorVerificationResult(hit_count=count, sample_html=sample)
    except Exception as exc:
        return LocatorVerificationResult(hit_count=0, error=str(exc))
```

API 层调用：

```python
# CHANGE CODE: backend/app/api/v1/ai_locators.py 内部 generate 接口

verification = verify_locator_strategy(
    page_url=req.page_url,
    selector=ai_strategy["selector"],
    selector_type=ai_strategy.get("selector_type", "css"),
    storage_state=context.get("storage_state"),
)

ai_strategy["verified"] = verification.verdict == "verified"
ai_strategy["hit_count"] = verification.hit_count
ai_strategy["verify_error"] = verification.error
ai_strategy["sample_html"] = verification.sample_html

# 落库规则：
#   verdict=verified → priority=1
#   verdict=ambiguous → priority=99（仅作候选）
#   verdict=miss → 不入库，前端直接展示告警
```

### 6.3 子任务 1.2：Locator Repair Record（修复记录）

**目标**：每次 AI Healer 触发都写入审计记录，提供前端"查看 / 接受 / 回滚"操作。

**新增数据表**：

```sql
-- NEW TABLE: locator_repair_record
CREATE TABLE locator_repair_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    locator_key     VARCHAR(200) NOT NULL,        -- 如 login.submit_btn
    triggered_by    VARCHAR(40) NOT NULL,         -- ui_run / locator_scan / manual
    execution_id    VARCHAR(64),                  -- 关联 task / execution
    old_strategies  TEXT,                         -- JSON：旧 strategies 数组
    new_strategy    TEXT,                         -- JSON：AI 给出的新策略（含 confidence/reason）
    hit_count       INTEGER DEFAULT 0,            -- 校验时命中数
    verdict         VARCHAR(20) NOT NULL,         -- verified / ambiguous / miss / error
    review_status   VARCHAR(20) DEFAULT 'pending',-- pending / accepted / rejected / rolled_back
    review_user     VARCHAR(80),
    reviewed_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project_locator (project_id, locator_key),
    INDEX idx_review_status (review_status)
);
```

**改造点**：在 `engine/ai_locator_healer.py` 的 `_persist` 流程中，增加调用后端 API 写入记录。考虑到 `engine/` 不应直接依赖 backend ORM，采用**回调注入**方式：

```python
# CHANGE CODE: engine/ai_locator_healer.py

class AILocatorHealer:
    def __init__(
        self,
        locators_json_path: str = None,
        auto_save: bool = True,
        repair_recorder=None,        # NEW: 可选回调，签名 (target_key, old_strategies, new_strategy, verification) -> None
    ):
        self.locators_json_path = locators_json_path
        self.auto_save = auto_save
        self._ai = self._load_ai()
        self._healed_cache: Dict[str, str] = {}
        self._repair_recorder = repair_recorder
```

```python
    def heal(self, page, target_key, description="", execution_id=None):
        # ...原有逻辑

        # 在 _persist 之前增加 Playwright 命中数校验
        verification = self._verify_in_page(page, new_selector, result.get("selector_type", "css"))

        # 调用 recorder（不阻塞主流程，失败仅 warn）
        if self._repair_recorder:
            try:
                self._repair_recorder(
                    target_key=target_key,
                    old_strategies=self._snapshot_strategies(target_key),
                    new_strategy={**result, "selector": new_selector},
                    verification=verification,
                    execution_id=execution_id,
                )
            except Exception as exc:
                logger.warning(f"[AILocatorHealer] repair_recorder failed: {exc}")

        if verification["verdict"] == "verified" and self.auto_save:
            self._persist(target_key, new_selector, result)
        return new_selector if verification["verdict"] == "verified" else None
```

`engine.py` 在初始化 Healer 时注入 recorder（recorder 通过 HTTP 回调到 `POST /api/v1/locator-repair/records`，避免 engine 直接耦合 ORM）。

### 6.4 子任务 1.3：PRD → 用例工作台

**目标**：把 `prd_parser.py`、`ai_case_from_prd.py`、`ai_case_orchestrator.py` 已实现的能力暴露给前端。

**前端**：在 `frontend/src/views/ai/AiToolsView.vue` 中**新增 Tab "PRD 解析"**：

| UI 元素 | 说明 |
| --- | --- |
| 项目选择 | 必填 |
| PRD 上传 | 接受 .md / .docx / .pdf / 粘贴文本 |
| 解析按钮 | 调 `POST /api/v1/ai/cases/from-prd` |
| 测试点列表 | 展示 AI 提取的页面、状态、字段、规则 |
| 用例草稿表格 | 字段：title / module / priority / steps / expected / automation；可逐行编辑 |
| 批量入库 | 调 `POST /api/v1/cases/batch` |
| 放弃 | 仅清空草稿，不入库 |

**接口契约**：

```yaml
POST /api/v1/ai/cases/from-prd
Content-Type: multipart/form-data 或 application/json
Body:
  project_id: int
  prd_file: file        # 二选一
  prd_text: string      # 二选一
  options:
    extract_test_points: bool    # 默认 true
    generate_cases: bool         # 默认 true
    target_modules: [string]     # 可空
Response:
  task_id: string                # AI 异步任务 id
  test_points: [...]
  case_drafts: [
    {
      draft_id: string,
      title: string,
      module: string,
      priority: P0|P1|P2,
      steps: [{ no, action, target, value }],
      expected: [{ url_contains: "..." }, ...],
      automation: bool,
      data: { ... },
      source_test_point: { id, summary }
    }
  ]
```

```yaml
POST /api/v1/cases/batch
Body:
  project_id: int
  drafts: [draft_id 列表]   # 由前端在 PRD 解析返回的 case_drafts 中挑选
Response:
  created_case_ids: [int]
  skipped: [{ draft_id, reason }]
```

### 6.5 子任务 1.4：Step Observer 升级与 Auto Fix 串接

**现状**：`engine/ai_step_observer.py` 已接入主流程（engine.py:602-614），但失败时仅打 warn，未触发 `case_auto_fix`。

**改造**：在 `engine.py` 中，当 Step Observer 判定失败且 confidence ≥ 阈值时，按以下顺序处理：

1. 当前步骤标 FAILED；
2. 触发 `case_auto_fix` 回调（同样通过依赖注入注入 service 层），让 `case_auto_fix` 基于截图和 DOM 重写本步骤；
3. 重新执行重写后的步骤一次（限 1 次重试）；
4. 若仍失败则按原流程上报。

```python
# engine/engine.py 内 _execute_steps 末尾的 obs 块

if not obs_ok and self._auto_fix_callback:
    fixed_step = self._auto_fix_callback(
        case_id=self.current_case.case_id,
        step_no=step_no,
        action=action,
        target=target,
        value=value,
        page_snapshot=self._capture_lite_dom(page),
        screenshot_path=step_result.screenshot,
    )
    if fixed_step:
        # 重试一次
        retry_actual = self.keyword_executor.execute(
            action=fixed_step["action"],
            target=fixed_step["target"],
            value=fixed_step.get("value", ""),
            page=page,
        )
        step_result.actual = retry_actual
        step_result.status = StepStatus.PASSED
        step_result.error_msg = ""
```

### 6.6 子任务 1.5：AI 调用配额与失败降级

为避免 AI 调用导致执行性能与成本失控：

| 配置项 | 默认值 | 作用 |
| --- | --- | --- |
| `AI_HEAL_MAX_PER_CASE` | 5 | 单用例 Healer 触发上限，超过后视为定位维护问题，停止再触发 |
| `AI_OBSERVE_SAMPLE_RATE` | 1.0 | Step Observer 抽样率（核心用例 1.0，回归用例可降至 0.3） |
| `AI_CALL_TIMEOUT_MS` | 15000 | 单次 AI 调用超时；超时直接降级为 ok=true |
| `AI_DAILY_BUDGET_TOKENS` | 5_000_000 | 项目日级配额，超额后所有 AI 接口返回 503 |

新增 `backend/app/services/ai_budget.py` 做计数与阻断。

---

## 7. Layer 2：TaskDispatcher 统一任务模型

### 7.1 目标

让前端、CLI、定时任务、外部触发都通过同一个入口下发任务，并且每种任务在数据库中以同一张 `task` 表为主键，方便统一查询、统一展示、统一通知。

### 7.2 数据模型

```sql
-- NEW TABLE: task （执行任务统一表）
CREATE TABLE task (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type     VARCHAR(20) NOT NULL,       -- ui / api / seo / performance / ai_case / regression
    project_id    INTEGER NOT NULL,
    target_id     INTEGER,                    -- case_id / api_case_id / seo_target_id ...
    target_kind   VARCHAR(20),                -- case / batch / suite / url
    env           VARCHAR(20) DEFAULT 'test',
    trigger_type  VARCHAR(20) NOT NULL,       -- manual / schedule / webhook / regression
    triggered_by  VARCHAR(80),
    status        VARCHAR(20) DEFAULT 'pending',  -- pending/running/passed/failed/partial/canceled
    summary_json  TEXT,                       -- {total, passed, failed, warnings, ...}
    artifacts_json TEXT,                      -- {html, json, trace, har, screenshots[]}
    duration_ms   INTEGER DEFAULT 0,
    started_at    DATETIME,
    finished_at   DATETIME,
    error_msg     TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project_status (project_id, status),
    INDEX idx_type_started (task_type, started_at)
);
```

兼容策略：原有 `Execution` 表仍保留，新建 `Task` 表通过 `task.target_id + task.target_kind` 与具体业务表关联；老接口在内部转写为 Task 操作以保证向前兼容。

### 7.3 统一接口契约

```yaml
# 创建任务（不立即执行）
POST /api/v1/tasks
Body:
  task_type: ui | api | seo | performance | regression | ai_case
  project_id: int
  target_id: int
  target_kind: case | batch | suite | url
  env: test|staging|prod
  trigger_type: manual|schedule|webhook
  options: { ... }   # 任务专属配置（如 ai_heal=true / ai_observe=false）
Response: { task_id: int, status: "pending" }

# 立即执行
POST /api/v1/tasks/{task_id}/run
Response: { task_id, status: "running", sse_url: "/api/v1/tasks/{task_id}/events" }

# 一步合并（创建+执行）
POST /api/v1/tasks/run
Body: 同 POST /tasks 的 Body
Response: { task_id, status: "running", sse_url }

# 查询
GET /api/v1/tasks?task_type=&project_id=&status=&page=&size=
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/events    # SSE
GET /api/v1/tasks/{task_id}/report    # 统一报告 JSON
GET /api/v1/tasks/{task_id}/artifacts/{file}   # 下载产物

# 操作
POST /api/v1/tasks/{task_id}/cancel
POST /api/v1/tasks/{task_id}/rerun
```

### 7.4 TaskDispatcher 服务

```python
# NEW CODE: backend/app/services/task_dispatcher.py

from enum import Enum
from typing import Any, Dict
from app.core.database import SessionLocal
from app.models.task import Task
from app.services import (
    execution_service,
    api_test_service,
    seo_service,
    performance_service,
    ai_regression,
    ai_case_orchestrator,
)


class TaskType(str, Enum):
    UI = "ui"
    API = "api"
    SEO = "seo"
    PERFORMANCE = "performance"
    REGRESSION = "regression"
    AI_CASE = "ai_case"


class TaskDispatcher:
    """统一任务分发：根据 task_type 路由到具体 service。"""

    _ROUTES = {
        TaskType.UI:         "_run_ui",
        TaskType.API:        "_run_api",
        TaskType.SEO:        "_run_seo",
        TaskType.PERFORMANCE:"_run_performance",
        TaskType.REGRESSION: "_run_regression",
        TaskType.AI_CASE:    "_run_ai_case",
    }

    def create(self, payload: Dict[str, Any]) -> int:
        with SessionLocal() as db:
            task = Task(
                task_type=payload["task_type"],
                project_id=payload["project_id"],
                target_id=payload.get("target_id"),
                target_kind=payload.get("target_kind"),
                env=payload.get("env", "test"),
                trigger_type=payload.get("trigger_type", "manual"),
                triggered_by=payload.get("triggered_by", "system"),
                status="pending",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task.id

    def run(self, task_id: int) -> Dict[str, Any]:
        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).one()
            method_name = self._ROUTES.get(TaskType(task.task_type))
            if not method_name:
                raise ValueError(f"Unsupported task_type: {task.task_type}")
            handler = getattr(self, method_name)
            return handler(task)

    # 各 _run_* 方法：内部仅做参数转换 + 调用既有 service
    # 不修改 service 内部，保证向前兼容
    def _run_ui(self, task):           ...
    def _run_api(self, task):          ...
    def _run_seo(self, task):          ...
    def _run_performance(self, task):  ...
    def _run_regression(self, task):   ...
    def _run_ai_case(self, task):      ...
```

各 `_run_*` 实现要点：

1. 调用对应 service 的现有方法，传入既有参数；
2. 监听该 service 的进度回调，统一转换为 SSE 事件格式（见 7.5）；
3. service 完成后，将其原生结果（如 ExecutionResult / SeoReport）映射到统一的 `summary_json` 与 `artifacts_json`；
4. 失败时将 `error_msg` 写入 task 表。

### 7.5 统一 SSE 事件契约

```json
{
  "task_id": 1001,
  "task_type": "ui",
  "level": "info",
  "event": "step_started",
  "message": "Start step: click submit button",
  "ts": "2026-05-07T10:00:01Z",
  "data": { "case_id": "REALNAME-P0-001", "step_no": 3 }
}
```

事件名称白名单：

```
task_started, task_finished, task_canceled,
case_started, case_finished,
step_started, step_finished,
assertion_failed, locator_fallback, locator_healed,
screenshot_saved, observer_warning,
ai_call_started, ai_call_finished,
report_generated, error
```

### 7.6 兼容策略

| 老接口 | 处理方式 |
| --- | --- |
| `POST /api/v1/executions/run` | 内部改造为 `dispatcher.create({task_type:"ui"})` + `dispatcher.run()` |
| `POST /api/v1/api-test/cases/{id}/run` | 同上，task_type=api |
| `POST /api/v1/seo/scan` | 同上，task_type=seo |
| `POST /api/v1/performance/scan` | 同上，task_type=performance |
| 老 SSE URL | 短期保留并发布相同事件 |

老接口在 V1.5 版本前继续可用，V1.5 后官宣废弃但仍保留 6 个月过渡期。

---

## 8. Layer 3：工作流串联与导航闭环

### 8.1 设计核心

**不增加新页面、只新增链接**。把现有 13 个 view 用 4 类跳转串成闭环：

| 来源 | 触发 | 目标 | 携带参数 |
| --- | --- | --- | --- |
| `CasesView` 行内 | "立即运行" | `ExecutionView` | project_id, case_id, auto_run=1 |
| `CasesView` 行内 | "AI 体检" | `AiToolsView`(Tab=自检) | project_id, case_id |
| `ExecutionView` 任务结束 toast | "查看报告" | `ReportsView` | task_id |
| `ExecutionView` 任务结束 toast | "重跑" | `ExecutionView` | 新建同参数 task |
| `ExecutionView` 任务结束 toast | "修 Locator" | `LocatorsView` | project_id, locator_key=失败步骤命中 key |
| `ReportsView` 失败步骤 | "AI 修复并重跑" | 调用 `POST /tasks/{id}/heal-and-rerun` | task_id, step_id |
| `LocatorsView` 行内 | "扫描失效" | 调用 `POST /api/v1/locators/scan` | project_id |
| `AiToolsView`(PRD Tab) | "入库" | `CasesView` | project_id, highlight=新建 case_ids |

### 8.2 ExecutionView 重构（统一执行中心）

将 `ExecutionView` 升级为**多任务类型通用执行中心**：

```
┌─────────────────────────────────────────────────────────────┐
│ [+ 新建任务]                                                 │
│   类型：UI ▾   项目：dataify ▾   目标：选用例/选 API/输入 URL │
│   环境：test ▾   高级：[ ] AI 自愈 [ ] AI 步骤验证            │
│ [ 提交并运行 ]                                              │
├─────────────────────────────────────────────────────────────┤
│ [运行中] task#1024 ui · dataify · case_5 · 进行中 12s        │
│   日志（SSE）：                                              │
│     [step_started] step3 click login.submit                 │
│     [locator_fallback] login.submit primary→fallback#2      │
│     [locator_healed] login.submit healed by AI verified      │
│     [step_finished] step3 ok 1.2s                            │
│   操作：[ 取消 ] [ 跳报告 ] [ 修 Locator ]                  │
├─────────────────────────────────────────────────────────────┤
│ [历史] 表格：task_id / type / project / status / duration   │
│       行操作：[ 详情 ] [ 重跑 ] [ AI 修复并重跑 ]             │
└─────────────────────────────────────────────────────────────┘
```

实现要点：

- 表头与日志组件按 `task_type` 字段动态渲染；
- 日志组件统一消费 `/api/v1/tasks/{id}/events` SSE；
- 历史表与"老 Execution 列表"合并，显示 `task` 表数据；
- "AI 修复并重跑"封装为 `POST /tasks/{id}/heal-and-rerun` 一键操作。

### 8.3 AiToolsView 工作台扩展

在现有 `AiToolsView.vue` 中扩展 Tab 列表为：

| Tab | 功能 |
| --- | --- |
| Locator 生成 | 现有 |
| Locator 修复审计 | 新增。展示待审 / 已接受 / 已回滚的修复记录，可单条 / 批量审核 |
| PRD 解析 | 新增。文件/文本上传 → 用例草稿 → 入库 |
| 用例自检 | 新增。选用例 → 干跑 + AI 校验，输出失败步骤、可疑断言 |
| 智能回归 | 新增。粘 git diff 或选 commit → 输出推荐用例 |

### 8.4 LocatorsView 扩展

在现有定位维护页基础上新增 4 个能力：

1. **失效扫描**：扫描所有 enabled locators，逐条用 Playwright 校验命中数；产出"失效列表"。
2. **健康度颜色**：红（>30% fallback 或最近 24h 命中 0）/ 黄（10–30% fallback）/ 绿（<10%）。
3. **修复记录入口**：点行展开，展示该 locator 历史修复记录，支持回滚到任一历史策略。
4. **批量 AI 修复**：选中红色 / 黄色 locators，点"AI 一键修复"批量触发。

---

## 9. Layer 4：可观测性与资产沉淀

### 9.1 Locator 命中统计

```sql
-- NEW TABLE: locator_hit_stats
CREATE TABLE locator_hit_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    locator_key     VARCHAR(200) NOT NULL,
    matched_type    VARCHAR(40),
    matched_value   TEXT,
    matched_priority INTEGER,
    fallback_depth  INTEGER DEFAULT 0,    -- 0 表示首选命中，>0 表示 fallback
    hit_count       INTEGER DEFAULT 1,
    last_hit_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (project_id, locator_key, matched_type, matched_value)
);
```

写入时机：`engine.engine._execute_steps` 每步完成后，由注入的 `hit_stats_callback` 异步上报（HTTP POST）。

### 9.2 健康度评分公式

对每个 locator：

```
fallback_rate = sum(fallback_depth>0 hits, 7d) / sum(all hits, 7d)
last_24h_hits = sum(hits, 24h)

color:
  红：fallback_rate ≥ 0.3 或 (last_24h_hits = 0 且 历史曾被命中)
  黄：0.1 ≤ fallback_rate < 0.3
  绿：fallback_rate < 0.1
```

### 9.3 统一报告查看器

后端 `services/report_renderer.py`：

```python
def render_unified_report(task_id: int) -> dict:
    """根据 task.summary_json/artifacts_json + 任务类型，输出统一结构。"""
    return {
      "task_id": ...,
      "task_type": ...,
      "summary": {...},
      "timeline": [ {ts, event, message, data}, ...],   # 复用 SSE 事件
      "steps": [...],                # task_type=ui 才有
      "requests": [...],             # task_type=api 才有
      "issues": [...],               # task_type=seo 才有
      "metrics": {...},              # task_type=performance 才有
      "artifacts": {...},
    }
```

前端 `ReportsView` 用一个统一组件 `<UnifiedReport :data="report" />`，按 `task_type` 切换 5 种细节面板。

### 9.4 智能回归推荐

```yaml
POST /api/v1/regression/recommend
Body:
  project_id: int
  source: git_diff | commit_sha | file_list
  payload: <对应内容>
Response:
  change_summary: string
  affected_modules: [string]
  recommended_cases: [
    { case_id, reason, score }    # score 0-100
  ]
  recommended_seo_targets: [...]
  recommended_api_cases: [...]
```

后端 `services/ai_regression.py`：

1. 解析变更（路径 → 模块标签）；
2. 模块标签 → 候选用例（基于 `case.tags / case.module`）；
3. 用 AI 对候选做相关度评分；
4. 输出含 reason 的推荐列表。

前端 `AiToolsView.PRD` 同级 Tab "智能回归"，结果可一键转为批量任务（`POST /tasks/run` task_type=regression）。

---

## 10. 数据库 Schema 演进

### 10.1 新增表

| 表名 | 用途 |
| --- | --- |
| `task` | 任务统一表 |
| `locator_repair_record` | Locator 修复审计 |
| `locator_hit_stats` | Locator 命中统计 |

### 10.2 字段扩展

| 表 | 字段 | 类型 | 说明 |
| --- | --- | --- | --- |
| `locators` | `health_color` | VARCHAR(8) | 由后台定时计算后写入 |
| `locators` | `last_healed_at` | DATETIME | 最近一次自愈时间 |
| `cases` | `tags_json` | TEXT | 用于回归推荐的标签数组 |
| `cases` | `automation` | BOOLEAN | 是否自动化用例（PRD 入库时填入） |
| `executions` | `task_id` | INTEGER | 关联到 task 表（迁移期填空可空） |

### 10.3 迁移脚本

新增 `backend/scripts/migrations/2026_05_optimization_v1/`：

```
01_create_task_table.sql
02_create_locator_repair_record.sql
03_create_locator_hit_stats.sql
04_alter_locators_health.sql
05_alter_cases_tags.sql
06_alter_executions_task_id.sql
07_backfill_executions_to_task.py     # 把历史 execution 反向回填一条 task，保证报告中心可统一展示
```

回填脚本采用幂等设计：以 `executions.execution_id` 为锚点，已存在对应 task 的跳过。

---

## 11. 前端改造清单

### 11.1 路由新增

无新增路由，仅复用现有路由 + Tab 与 query 参数控制。

### 11.2 视图改动

| 视图 | 改动类型 | 说明 |
| --- | --- | --- |
| `CasesView.vue` | 行内增按钮 | 立即运行 / AI 体检 |
| `ExecutionView.vue` | 重构 | 升级为统一执行中心，新建任务 / 历史 / 实时日志三段 |
| `ReportsView.vue` | 详情用统一组件 | `<UnifiedReport>` |
| `LocatorsView.vue` | 行内增能力 | 健康度色块 / 失效扫描 / 修复记录抽屉 / 批量 AI 修复 |
| `AiToolsView.vue` | 新增 Tab | PRD 解析 / 修复审计 / 用例自检 / 智能回归 |
| 全局 Header | 新增徽标 | 当日待审修复记录数 / 待入库用例草稿数 |

### 11.3 共享组件新增

| 组件 | 路径 |
| --- | --- |
| `<UnifiedReport>` | `frontend/src/components/report/UnifiedReport.vue` |
| `<TaskTimeline>` | `frontend/src/components/task/TaskTimeline.vue` |
| `<AiCallBadge>` | `frontend/src/components/ai/AiCallBadge.vue` |
| `<HealthDot>` | `frontend/src/components/locator/HealthDot.vue` |
| `<DraftCaseTable>` | `frontend/src/components/ai/DraftCaseTable.vue` |

### 11.4 全局状态

新增 Pinia store：

```js
// frontend/src/stores/task.js
//  - currentRunningTasks: 当前正在运行的 task 列表（用于头部徽标）
//  - subscribe(taskId): 建立 SSE 连接，自动入队事件
//  - cancel(taskId)、rerun(taskId)、healAndRerun(taskId)
```

```js
// frontend/src/stores/ai.js
//  - pendingRepairs: 待审修复记录数
//  - pendingDrafts: 待入库 PRD 用例草稿数
//  - dailyTokenBudget: 配额信息
```

---

## 12. 接口契约（汇总）

| 模块 | 方法 + 路径 | 说明 |
| --- | --- | --- |
| Task | POST /api/v1/tasks | 创建任务 |
| Task | POST /api/v1/tasks/run | 创建并立即执行 |
| Task | GET  /api/v1/tasks | 列表 |
| Task | GET  /api/v1/tasks/{id} | 详情 |
| Task | GET  /api/v1/tasks/{id}/events | SSE |
| Task | GET  /api/v1/tasks/{id}/report | 统一报告 JSON |
| Task | POST /api/v1/tasks/{id}/cancel | 取消 |
| Task | POST /api/v1/tasks/{id}/rerun | 重跑 |
| Task | POST /api/v1/tasks/{id}/heal-and-rerun | AI 修复后重跑 |
| Locator | POST /api/v1/locators/scan | 失效扫描 |
| Locator | POST /api/v1/locators/{key}/heal | 单条 AI 修复 |
| Locator | POST /api/v1/locators/heal-batch | 批量 AI 修复 |
| Repair | GET  /api/v1/locator-repair/records | 修复记录列表 |
| Repair | POST /api/v1/locator-repair/records | 写入修复记录（engine 回调） |
| Repair | POST /api/v1/locator-repair/records/{id}/accept | 接受 |
| Repair | POST /api/v1/locator-repair/records/{id}/reject | 拒绝 |
| Repair | POST /api/v1/locator-repair/records/{id}/rollback | 回滚 |
| AI Case | POST /api/v1/ai/cases/from-prd | PRD 解析为用例草稿 |
| AI Case | GET  /api/v1/ai/cases/drafts | 草稿列表 |
| AI Case | POST /api/v1/cases/batch | 草稿批量入库 |
| Regression | POST /api/v1/regression/recommend | 推荐回归用例 |
| Self-check | POST /api/v1/cases/{id}/self-check | 单用例 AI 自检 |

所有响应统一返回结构：

```json
{
  "code": 0,
  "msg": "ok",
  "data": { ... },
  "request_id": "..."
}
```

---

## 13. 里程碑与交付物

| 周次 | 主题 | 交付物 | 上线开关 |
| --- | --- | --- | --- |
| W1 | Task 模型 + Dispatcher 骨架 | `task` 表 + `task_dispatcher.py` + 兼容老 Execution | `feature_task_dispatcher` |
| W2 | UI/API/SEO/Perf 接入 Dispatcher + 统一 SSE | 5 类任务可走新接口；ExecutionView 第一版 | `feature_unified_execution_view` |
| W3 | Locator 修复闭环 + 命中统计 | `locator_repair_record`、`locator_hit_stats`、命中验证、修复审计 Tab | `feature_locator_audit` |
| W4 | PRD 工作台 + 用例自检 | AiToolsView 新 Tab，端到端打通 PRD→草稿→入库 | `feature_prd_workbench` |
| W5 | 统一报告查看器 + 健康度面板 | `<UnifiedReport>`、LocatorsView 健康度可视化 | `feature_unified_report` |
| W6 | 智能回归 + AI Auto Fix 串接 | 推荐推送 + 回归任务一键执行 + Step Observer 触发 Auto Fix | `feature_ai_regression` |

每个里程碑都按以下阶段推进：

1. **设计评审**（1 天）
2. **后端落地**（2–3 天）
3. **前端落地**（2 天）
4. **联调与回归**（1 天）
5. **灰度开关上线**（1 天）

每周交付物入库时同步更新 `docs/changelog/` 与 `docs/optimization_implementation_plan.md` 的"修订记录"。

---

## 14. 验收标准

### 14.1 通用验收标准

- 所有新增数据表迁移脚本可独立执行，含回滚 SQL；
- 所有新增接口具备 OpenAPI 文档与至少 3 个 pytest 用例；
- 前端组件具备本地 mock + 生产联调两套数据；
- 老接口在功能开关关闭时行为与改造前 100% 一致。

### 14.2 体验验收标准（一句话场景）

| 场景 | 期望操作步数 | 验收方式 |
| --- | --- | --- |
| 上传 PRD → 看到测试报告 | ≤ 5 次点击 | 全流程录屏验收 |
| 编辑用例 → 立即跑通 | ≤ 2 次点击 | 同上 |
| 一个用例失败 → 修好并重跑 | ≤ 3 次点击 | 同上 |
| 改了前端页面 → 知道哪些用例要修 | ≤ 1 次操作（粘贴 diff） | 同上 |
| 知道哪些 Locator 不健康 | 进入 LocatorsView 即可见 | 红黄绿色块覆盖率 100% |

### 14.3 量化指标

| 指标 | 改造前基线 | 目标 |
| --- | --- | --- |
| 单用例平均维护时长（分钟） | TBD | -50% |
| Locator fallback 率 | TBD | -30% |
| 失败用例首次 AI 自愈成功率 | 未度量 | ≥ 60% |
| AI 调用 token / 用例（成本） | 未度量 | 在 W6 形成基线，下季度优化 |

基线数据将在 W1 起通过新增的命中统计与 task summary 自动采集。

---

## 15. 风险与对策

| 风险 | 影响 | 概率 | 对策 |
| --- | --- | --- | --- |
| Task 表与老 Execution 表数据不一致 | 报告中心展示乱 | 中 | 回填脚本 + 双写过渡期 + 验收 SQL 校验 |
| AI 调用成本超额 | 平台无法运转 | 中 | `AI_DAILY_BUDGET_TOKENS` 阻断 + 抽样开关 |
| AI 自愈写错 selector 导致后续用例集体失败 | 高 | 低 | 命中数=1 强校验 + 自愈写入 priority=0 不覆盖原策略 + 修复审计可回滚 |
| Step Observer 误判导致大量"假失败" | 中 | 中 | 置信度阈值 0.65 + 默认仅核心用例开启 + 失败时自动 fallback 为 ok |
| TaskDispatcher 路由 bug 影响所有任务 | 高 | 低 | 灰度开关 `feature_task_dispatcher`，可一键回退老接口 |
| PRD 解析 AI 输出不稳定 | 中 | 高 | 解析结果只生成"草稿"，必须人工确认才入库 |
| 前端组件重构带来 UI 回归 | 中 | 中 | 保留老 ExecutionView 路径 `?legacy=1` 作为应急回滚 |
| Playwright 在校验 Locator 时启动开销大 | 影响响应时间 | 中 | 复用单例 PlaywrightClient，校验任务异步入队，不阻塞用户操作 |

---

## 16. 附录 A：代码骨架清单

```
backend/app/models/task.py                      # NEW
backend/app/models/locator_repair_record.py     # NEW
backend/app/models/locator_hit_stats.py         # NEW
backend/app/schemas/task.py                     # NEW
backend/app/schemas/locator_repair.py           # NEW
backend/app/api/v1/tasks.py                     # NEW
backend/app/api/v1/locator_repair.py            # NEW
backend/app/api/v1/regression.py                # 扩展（如已存在则合并）
backend/app/services/task_dispatcher.py         # NEW
backend/app/services/ai_budget.py               # NEW
backend/app/services/locator_verifier.py        # NEW
backend/app/services/locator_health.py          # NEW
backend/app/services/report_renderer.py         # NEW
backend/app/services/ai_locator.py              # CHANGE：增加 verify_locator_strategy
backend/app/services/case_auto_fix.py           # CHANGE：暴露 fix_step(...)
backend/app/api/v1/cases.py                     # CHANGE：新增 batch / self-check
backend/app/api/v1/ai_locators.py               # CHANGE：生成接口接 verifier

engine/engine.py                                # CHANGE：注入 repair_recorder / auto_fix_callback / hit_stats_callback
engine/ai_locator_healer.py                     # CHANGE：新增 verification + recorder
engine/keyword_executor.py                      # CHANGE：上报命中策略到 hit_stats_callback

frontend/src/views/ai/AiToolsView.vue           # CHANGE：4 个新 Tab
frontend/src/views/cases/CasesView.vue          # CHANGE：行内 Run / AI 自检
frontend/src/views/execution/ExecutionView.vue  # CHANGE：升级为统一执行中心
frontend/src/views/reports/ReportsView.vue      # CHANGE：使用 UnifiedReport
frontend/src/views/locators/LocatorsView.vue    # CHANGE：健康度 + 修复记录
frontend/src/components/report/UnifiedReport.vue   # NEW
frontend/src/components/task/TaskTimeline.vue      # NEW
frontend/src/components/locator/HealthDot.vue      # NEW
frontend/src/components/ai/DraftCaseTable.vue      # NEW
frontend/src/components/ai/AiCallBadge.vue         # NEW
frontend/src/stores/task.js                        # NEW
frontend/src/stores/ai.js                          # NEW
```

---

## 17. 附录 B：升级与回滚方案

### 17.1 上线步骤

1. 备份 `test_framework.db`；
2. 执行 `migrations/2026_05_optimization_v1/` 下所有 SQL；
3. 部署后端，开启 `feature_task_dispatcher=on`、`feature_unified_execution_view=on`；
4. 验证：手动通过新接口跑一次 UI 任务、一次 SEO 任务，确认 task 表落库 + 报告生成；
5. 部署前端，灰度 10% 用户；
6. 观察 24h 后开启全量；
7. 后续每周按里程碑顺序开启对应 feature flag。

### 17.2 回滚方案

| 故障 | 回滚动作 |
| --- | --- |
| Dispatcher 异常 | 关闭 `feature_task_dispatcher`，前端走老 `?legacy=1` 路径 |
| Locator 自愈写错策略 | 关闭 `feature_locator_audit`，使用修复记录回滚到上一版本 strategy |
| PRD 解析量大爆 token | 关闭 `feature_prd_workbench`，AI 调用阻断 |
| 报告查看器渲染异常 | 关闭 `feature_unified_report`，回到老 ReportsView |

所有 feature flag 通过 `backend/app/core/config.py` 读取环境变量，重启即生效，无需改库。

### 17.3 数据回滚

`task` 表与新增字段不影响老业务，**可以保留**；

`locator_repair_record` 与 `locator_hit_stats` 仅做记录，**可以保留**；

如需彻底回退，按以下顺序：

```sql
DROP TABLE IF EXISTS locator_hit_stats;
DROP TABLE IF EXISTS locator_repair_record;
DROP TABLE IF EXISTS task;
ALTER TABLE locators DROP COLUMN health_color;
ALTER TABLE locators DROP COLUMN last_healed_at;
ALTER TABLE cases   DROP COLUMN tags_json;
ALTER TABLE cases   DROP COLUMN automation;
ALTER TABLE executions DROP COLUMN task_id;
```

---

## 结语

本方案的核心信念是：**当下平台缺的不是功能，是工作流。** 通过 6 周 4 层的渐进改造，让"PRD 进、报告出，AI 全程在场"的闭环真正在测试工程师面前每天可用，是本期工作的唯一目标。

后续版本（V1.1+）将基于本期沉淀的命中统计、修复记录、回归推荐数据，引入更深度的算法优化（如基于历史失败的优先策略学习、基于 DOM 变更的主动 Locator 同步等），届时另行立项。

---

*本文档结束。*
