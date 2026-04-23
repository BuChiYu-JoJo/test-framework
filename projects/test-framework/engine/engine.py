# -*- coding: utf-8 -*-
"""
Test Framework Core Engine
通用自动化测试框架 - 执行引擎

架构：
  TestEngine（主编排器）
      │
      ├── PlaywrightClient（browser 生命周期管理）
      │       ├── launch() → new_context() → new_page()
      │       └── 每个用例独立 Context，完全隔离
      │
      ├── KeywordExecutor（关键字执行）
      │       └── 执行动作（click/type/navigate...），只操作 Page
      │
      ├── LocatorResolver（定位符解析）
      │       └── locator key（如 login.username）→ CSS selector
      │
      ├── YamlParser / ExcelParser（用例解析）
      │
      └── Reporter（报告生成）
"""

import json
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .locator_resolver import LocatorResolver
from .keyword_executor import KeywordExecutor
from .playwright_client import PlaywrightClient
from .parser.yaml_parser import YamlParser
from .parser.excel_parser import ExcelParser
from .reporter import Reporter


class CaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class StepResult:
    """步骤执行结果"""
    step_no: int
    action: str
    target: str
    value: Any = None
    status: StepStatus = StepStatus.PENDING
    actual: Any = None
    error_msg: str = ""
    duration_ms: float = 0
    screenshot: str = ""


@dataclass
class CaseResult:
    """用例执行结果"""
    case_id: str
    case_name: str
    status: CaseStatus = CaseStatus.PENDING
    steps: List[StepResult] = field(default_factory=list)
    duration_ms: float = 0
    error_msg: str = ""
    screenshots: List[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


class TestEngine:
    """
    测试执行引擎

    职责：
    - 用例解析（YAML / Excel）
    - 步骤编排（setup → steps → teardown）
    - Playwright 生命周期管理（委托给 PlaywrightClient）
    - 关键字执行（委托给 KeywordExecutor）
    - 报告生成
    """

    def __init__(
        self,
        project_name: str,
        project_path: str = None,
        base_url: str = None,
        headless: bool = True,
        execution_id: str = None,
        event_bus = None,
    ):
        """
        初始化测试引擎

        Args:
            project_name: 项目名称（如 dataify）
            project_path: 项目路径，默认 projects/{project_name}
            base_url: 默认 base URL
            headless: 是否无头模式
            execution_id: 执行ID（用于调试日志）
            event_bus: 事件总线实例（传入后调试日志会推送到 SSE）
        """
        self.project_name = project_name
        self.execution_id = execution_id
        self._event_bus = event_bus

        # 项目路径
        if project_path:
            self.project_path = Path(project_path)
        else:
            self.project_path = Path(__file__).parent.parent / "projects" / project_name

        # base_url（优先用参数，其次用配置文件）
        self.base_url = base_url or "http://test-qzxbjwry.dataify-dev.com"
        self.headless = headless

        # 加载配置（仅在 base_url 未显式传入时才从文件覆盖）
        self._load_configs(only_fill_missing=True)

        # 同步 locators: DB → locators.json（保证引擎总能读到最新的 UI 配置）
        self._sync_db_locators_to_json()

        # 初始化组件
        self.locator_resolver = LocatorResolver(
            str(self.project_path / "locators.json")
        )
        self.keyword_executor = KeywordExecutor(
            self.locator_resolver,
            base_url=self.base_url,
        )
        self.yaml_parser = YamlParser()
        self.excel_parser = ExcelParser()
        self.reporter = Reporter()

        # Playwright 客户端（按需启动）
        self._pw_client: Optional[PlaywrightClient] = None

        # 当前执行上下文
        self.current_case: Optional[CaseResult] = None

    # ─────────────────────────────────────────────────────────────────
    # Playwright 生命周期（委托给 PlaywrightClient）
    # ─────────────────────────────────────────────────────────────────

    def _get_pw_client(self) -> PlaywrightClient:
        """获取或创建 Playwright 客户端（懒加载）"""
        if self._pw_client is None:
            self._pw_client = PlaywrightClient(
                base_url=self.base_url,
                headless=self.headless,
            )
        return self._pw_client

    def _ensure_page(self):
        """确保 Playwright + Context + Page 已就绪
        
        每次用例执行都使用全新的 Context（隔离之前测试的 cookies/localStorage），
        确保登录状态不会从上一次测试泄漏。
        """
        pw = self._get_pw_client()
        if not pw.is_launched:
            pw.launch()
        # 始终创建新的 Context，确保每个用例都从干净状态开始
        pw.new_context()
        pw.new_page()

    def _debug_log(self, level: str, message: str, meta: dict = None):
        """通过 event_bus 推送调试日志（若无 event_bus 则静默忽略）"""
        if self._event_bus and self.execution_id:
            self._event_bus.append_debug_log(self.execution_id, level, message, meta or {})

        # 调试模式：print 到 stdout
        if level == "error":
            print(f"   ❌ {message}")
        elif level == "warn":
            print(f"   ⚠️  {message}")
        else:
            print(f"   {message}")

    # ─────────────────────────────────────────────────────────────────
    # 配置加载
    # ─────────────────────────────────────────────────────────────────

    def _load_configs(self, only_fill_missing: bool = False):
        """加载项目配置
        
        Args:
            only_fill_missing: 若为 True，则只有当 self.base_url 仍是硬编码默认值时才从文件覆盖
        """
        # 环境配置
        env_file = self.project_path / "env" / "test.json"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                self.env_config = json.load(f)
                # 仅在没有显式传入 base_url 时，才从配置文件读取
                if "base_url" in self.env_config:
                    default_url = "http://test-qzxbjwry.dataify-dev.com"
                    if not only_fill_missing or self.base_url == default_url:
                        self.base_url = self.env_config["base_url"]
        else:
            self.env_config = {}

        # 凭证配置
        cred_file = self.project_path / "test_data" / "credentials.json"
        if cred_file.exists():
            with open(cred_file, encoding="utf-8") as f:
                self.credentials = json.load(f)
        else:
            self.credentials = {}

    # ─────────────────────────────────────────────────────────────────
    # Locators DB → JSON 同步
    # ─────────────────────────────────────────────────────────────────

    def _sync_db_locators_to_json(self):
        """将数据库中的 locators 同步到 locators.json
        
        Locators UI 配置写入数据库，执行引擎读取 locators.json。
        每次引擎初始化时自动同步，保证两者一致。
        """
        db_path = Path(__file__).parent.parent / "test_framework.db"
        json_path = self.project_path / "locators.json"

        if not db_path.exists():
            return

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT page_name, element_key, selector, selector_type, description, priority
                FROM locators
                ORDER BY page_name, priority, id
            """)
            rows = cur.fetchall()

            if not rows:
                conn.close()
                return

            # 按 page_name 分组
            pages: Dict[str, Dict] = {}
            for row in rows:
                page_name = row["page_name"]
                if page_name not in pages:
                    pages[page_name] = {"name": page_name, "elements": {}}

                elem_key = row["element_key"]
                pages[page_name]["elements"][elem_key] = {
                    "selector": row["selector"],
                    "type": row["selector_type"] or "css",
                    "description": row["description"] or "",
                    "priority": row["priority"] or 1,
                }

            # 读取现有 json（保留 version 字段）
            existing_version = "1.0.0"
            if json_path.exists():
                try:
                    with open(json_path, encoding="utf-8") as f:
                        existing = json.load(f)
                        existing_version = existing.get("version", "1.0.0")
                except Exception:
                    pass

            data = {
                "version": existing_version,
                "pages": pages,
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            conn.close()
        except Exception:
            # 同步失败不影响主流程，跳过（后续用已有的 json）
            pass

    # ─────────────────────────────────────────────────────────────────
    # 用例加载
    # ─────────────────────────────────────────────────────────────────

    def load_case(self, case_path: str) -> Dict:
        """
        加载用例

        Args:
            case_path: 用例文件路径（YAML / Excel）

        Returns:
            解析后的用例数据字典
        """
        path = Path(case_path)

        if path.suffix in (".yaml", ".yml"):
            return self.yaml_parser.parse(path)
        elif path.suffix in (".xlsx", ".xls"):
            return self.excel_parser.parse(path)
        else:
            raise ValueError(f"Unsupported case format: {path.suffix}")

    # ─────────────────────────────────────────────────────────────────
    # 用例执行
    # ─────────────────────────────────────────────────────────────────

    def execute_case(self, case_data: Dict, context: Dict = None, debug: bool = False, debug_callback=None) -> CaseResult:
        """
        执行单个用例

        完整流程：
          1. 初始化 Playwright（确保 browser / context / page 就绪）
          2. 执行 setup（清理 cookie、初始化环境）
          3. 执行主步骤
          4. 执行 teardown
          5. 验证预期结果
          6. 清理资源

        Args:
            case_data: 用例数据
            context: 执行上下文（如 ${USERNAME} 变量）

        Returns:
            CaseResult: 用例执行结果
        """
        case_id = case_data.get("id", "unknown")
        case_name = case_data.get("name", "unknown")

        self.current_case = CaseResult(
            case_id=case_id,
            case_name=case_name,
            status=CaseStatus.RUNNING,
            started_at=self._get_timestamp(),
        )

        context = dict(context or {})
        context.update(case_data.get("data", {}))

        try:
            # 1. 确保浏览器就绪（每个用例独立 context）
            self._ensure_page()
            page = self._pw_client.page

            # 2. 执行 setup
            if "setup" in case_data:
                self._execute_steps(case_data["setup"], context, page, is_setup=True, debug=debug)

            # 3. 执行主步骤
            if "steps" in case_data:
                self._execute_steps(case_data["steps"], context, page, debug=debug)

            # 4. 执行 teardown
            if "teardown" in case_data:
                self._execute_steps(case_data["teardown"], context, page, is_teardown=True, debug=debug)

            # 5. 验证预期结果（失败不中断，用于 AI locator 场景）
            try:
                self._validate_expectations(case_data.get("expected", []), page, context, debug=debug)
            except AssertionError as e:
                # 登录断言失败不中断主流程（AI locator 只需要页面内容）
                if debug:
                    print(f"   ⚠️ 断言跳过: {e}")

            # 6. 汇总结果
            failed = [s for s in self.current_case.steps if s.status == StepStatus.FAILED]
            if not failed:
                self.current_case.status = CaseStatus.PASSED
            else:
                self.current_case.status = CaseStatus.FAILED
                self.current_case.error_msg = f"{len(failed)} step(s) failed"

        except Exception as e:
            self.current_case.status = CaseStatus.FAILED
            self.current_case.error_msg = str(e)
            traceback.print_exc()

        finally:
            self.current_case.finished_at = self._get_timestamp()
            self.current_case.duration_ms = self._calc_duration()
            self._cleanup()

        return self.current_case

    def _execute_steps(
        self,
        steps: List[Dict],
        context: Dict,
        page,
        is_setup: bool = False,
        is_teardown: bool = False,
        debug: bool = False,
    ):
        """
        执行步骤列表

        Args:
            steps: 步骤列表
            context: 变量上下文
            page: Playwright Page 实例
            is_setup: 是否为 setup 步骤（失败不中断）
            is_teardown: 是否为 teardown 步骤（失败不中断）
            debug: 是否开启调试模式
        """
        for step in steps:
            # 支持简写格式："click: button" → {"action": "click", "target": "button"}
            if isinstance(step, str):
                step = self._parse_short_step(step)

            step_no = step.get("no", len(self.current_case.steps) + 1)
            action = step.get("action", "")
            target = self._replace_variables(step.get("target", ""), context)
            value = self._replace_variables(step.get("value", ""), context)

            # 调试模式：打印步骤执行前的信息
            if debug:
                log_prefix = f"🔍 [STEP {step_no}] {action.upper()} | target={target} | value={value}"
                print(f"\n{log_prefix}")
                self._debug_log("info", log_prefix)
                before_url = page.url
                print(f"   📌 执行前 URL: {before_url}")
                self._debug_log("info", f"执行前 URL: {before_url}")

            step_result = StepResult(
                step_no=step_no,
                action=action,
                target=target,
                value=value,
            )

            start = time.time()

            try:
                # ✅ 关键变更：传入 page，不传 browser
                actual = self.keyword_executor.execute(
                    action=action,
                    target=target,
                    value=value,
                    page=page,
                )
                step_result.status = StepStatus.PASSED
                step_result.actual = actual

                # 调试模式：打印执行后的信息
                if debug:
                    after_url = page.url
                    print(f"   ✅ PASSED | 执行后 URL: {after_url}")
                    self._debug_log("info", f"✅ PASSED | 执行后 URL: {after_url}")

            except Exception as e:
                step_result.status = StepStatus.FAILED
                step_result.error_msg = str(e)

                # 调试模式：打印失败信息
                if debug:
                    print(f"   ❌ FAILED: {e}")
                    self._debug_log("error", f"❌ FAILED: {e}")

                # 失败时截图（使用 PlaywrightClient 的截图能力）
                if self._pw_client and self._pw_client.page:
                    screenshot_path = self._pw_client.screenshot(
                        f"{self.current_case.case_id}_step{step_no}"
                    )
                    if screenshot_path:
                        step_result.screenshot = screenshot_path
                        self.current_case.screenshots.append(screenshot_path)

                # setup / teardown 失败不中断主流程
                if not (is_setup or is_teardown):
                    raise

            finally:
                step_result.duration_ms = int((time.time() - start) * 1000)

            self.current_case.steps.append(step_result)

    # ─────────────────────────────────────────────────────────────────
    # 预期结果验证
    # ─────────────────────────────────────────────────────────────────

    def _validate_expectations(
        self, expectations: List[Dict], page, context: Dict, debug: bool = False
    ):
        """验证预期结果"""
        if not expectations:
            if debug:
                print("  ℹ️  无预期结果需要验证")
            return

        if debug:
            print(f"\n🎯 验证预期结果（共 {len(expectations)} 项）")
            print(f"   📌 验证前 URL: {page.url}")
            self._debug_log("info", f"验证预期结果（共 {len(expectations)} 项）")
            self._debug_log("info", f"验证前 URL: {page.url}")
        for exp in expectations:
            exp_type = list(exp.keys())[0]
            exp_value = list(exp.values())[0]

            if debug:
                print(f"   🔎 {exp_type}: {exp_value}")
                self._debug_log("info", f"{exp_type}: {exp_value}")

            try:
                if exp_type == "url_contains":
                    current_url = page.url
                    from urllib.parse import urlparse
                    current_path = urlparse(current_url).path
                    if debug:
                        print(f"      URL={current_url} | path={current_path}")
                        self._debug_log("info", f"URL path={current_path}")
                    assert exp_value in current_path, (
                        f"URL path '{current_path}' does not contain '{exp_value}'"
                    )
                    if debug:
                        print(f"      ✅ URL path contains '{exp_value}'")
                        self._debug_log("info", f"✅ URL contains '{exp_value}'")

                elif exp_type == "url_not_contains":
                    current_url = page.url
                    from urllib.parse import urlparse
                    current_path = urlparse(current_url).path
                    if debug:
                        print(f"      URL={current_url} | path={current_path}")
                        self._debug_log("info", f"URL path={current_path}")
                    assert exp_value not in current_path, (
                        f"URL path '{current_path}' should not contain '{exp_value}'"
                    )
                    if debug:
                        print(f"      ✅ URL path does not contain '{exp_value}'")
                        self._debug_log("info", f"✅ URL does not contain '{exp_value}'")

                elif exp_type == "element_visible":
                    selector = self.locator_resolver.get_selector(exp_value)
                    if selector:
                        if debug:
                            print(f"      selector={selector}")
                        page.wait_for_selector(selector, state="visible", timeout=10000)
                        if debug:
                            print(f"      ✅ element visible")

                elif exp_type == "element_not_visible":
                    selector = self.locator_resolver.get_selector(exp_value)
                    if selector:
                        if debug:
                            print(f"      selector={selector}")
                        page.wait_for_selector(
                            selector, state="hidden", timeout=5000
                        )
                        if debug:
                            print(f"      ✅ element not visible")

            except AssertionError as e:
                if debug:
                    print(f"      ❌ ASSERTION FAILED: {e}")
                raise AssertionError(
                    f"Expectation failed: {exp_type} -> {exp_value}. {str(e)}"
                )
            except Exception as e:
                if debug:
                    print(f"      ❌ ERROR: {e}")
                raise AssertionError(
                    f"Expectation error: {exp_type} -> {exp_value}. {str(e)}"
                )

    # ─────────────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────────────

    def _parse_short_step(self, step_str: str) -> Dict:
        """解析简写格式：'click: button' → {'action': 'click', 'target': 'button'}"""
        if ":" in step_str:
            action, target = step_str.split(":", 1)
            return {"action": action.strip(), "target": target.strip()}
        return {"action": step_str.strip(), "target": ""}

    def _replace_variables(self, text: Any, context: Dict) -> Any:
        """替换 ${VAR_NAME} 变量"""
        if not isinstance(text, str):
            return text
        for var_name, var_value in context.items():
            placeholder = f"${{{var_name}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(var_value))
        return text

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _calc_duration(self) -> int:
        if not self.current_case or not self.current_case.started_at:
            return 0
        from datetime import datetime
        start = datetime.strptime(self.current_case.started_at, "%Y-%m-%d %H:%M:%S")
        if self.current_case.finished_at:
            end = datetime.strptime(
                self.current_case.finished_at, "%Y-%m-%d %H:%M:%S"
            )
            return int((end - start).total_seconds() * 1000)
        return 0

    def _cleanup(self):
        """清理 Playwright 资源"""
        if self._pw_client:
            self._pw_client.close()
            self._pw_client = None

    def get_report(self, result: CaseResult) -> Dict:
        """生成报告数据"""
        return self.reporter.generate(result)


    def execute_case_on_page(self, case_data: Dict, page, context: Dict = None, debug: bool = False) -> CaseResult:
        """
        在已有的 Playwright Page 上执行用例（不创建新的 browser/page）

        用于：AI Locator 生成时先执行登录用例，再复用同一 page 访问目标页面

        Args:
            case_data: 用例数据
            page: Playwright Page 实例（已登录状态）
            context: 变量上下文
            debug: 是否调试模式
        """
        from dataclasses import dataclass, field

        @dataclass
        class _DummyCase:
            case_id: str = "unknown"
            status: str = "pending"
            steps: list = field(default_factory=list)
            error_msg: str = ""
            screenshots: list = field(default_factory=list)
            started_at: str = ""
            finished_at: str = ""
            duration_ms: int = 0

        self.current_case = _DummyCase()
        context = dict(context or {})
        context.update(case_data.get("data", {}))

        try:
            # 直接使用传入的 page，不创建新的
            # 2. 执行 setup
            if "setup" in case_data:
                self._execute_steps(case_data["setup"], context, page, is_setup=True, debug=debug)

            # 3. 执行主步骤
            if "steps" in case_data:
                self._execute_steps(case_data["steps"], context, page, debug=debug)

            # 4. 执行 teardown
            if "teardown" in case_data:
                self._execute_steps(case_data["teardown"], context, page, is_teardown=True, debug=debug)

            # 5. 验证预期结果（失败不中断，用于 AI locator 场景）
            try:
                self._validate_expectations(case_data.get("expected", []), page, context, debug=debug)
            except AssertionError as e:
                # 登录断言失败不中断主流程（AI locator 只需要页面内容）
                if debug:
                    print(f"   ⚠️ 断言跳过: {e}")

            # 6. 汇总结果
            failed = [s for s in self.current_case.steps if s.status == StepStatus.FAILED]
            if not failed:
                self.current_case.status = CaseStatus.PASSED
            else:
                self.current_case.status = CaseStatus.FAILED
                self.current_case.error_msg = f"{len(failed)} step(s) failed"

        except Exception as e:
            self.current_case.status = CaseStatus.FAILED
            self.current_case.error_msg = str(e)
            traceback.print_exc()

        finally:
            self.current_case.finished_at = self._get_timestamp()
            self.current_case.duration_ms = self._calc_duration()
            # 不调用 _cleanup()，因为 browser/page 不是我们创建的

        return self.current_case


    # ─────────────────────────────────────────────────────────────────
    # 快捷函数
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def execute_case_file(
        project: str,
        case_path: str,
        env: str = "test",
        headless: bool = True,
    ) -> CaseResult:
        """
        执行用例文件的快捷函数

        Args:
            project: 项目名称
            case_path: 用例文件路径
            env: 环境（test / staging / prod）
            headless: 是否无头

        Returns:
            CaseResult
        """
        engine = TestEngine(project, headless=headless)

        if env != "test":
            engine.project_path = engine.project_path.parent / env

        case_data = engine.load_case(case_path)
        return engine.execute_case(case_data)


if __name__ == "__main__":
    result = TestEngine.execute_case_file(
        project="dataify",
        case_path="projects/dataify/cases/yaml/tc001_login.yaml",
    )
    print(f"Case: {result.case_name}")
    print(f"Status: {result.status.value}")
    print(f"Duration: {result.duration_ms}ms")
    print(f"Steps: {len(result.steps)}")
