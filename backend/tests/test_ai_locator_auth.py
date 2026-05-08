import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.ai_locator import AILocatorService


class FakeContext:
    def __init__(self):
        self.storage_state_calls = []

    def storage_state(self, path):
        self.storage_state_calls.append(path)


class FakePage:
    def __init__(self, redirect_to_login_on_probe=False):
        self.url = "about:blank"
        self._title = ""
        self.context = FakeContext()
        self.goto_history = []
        self.redirect_to_login_on_probe = redirect_to_login_on_probe

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_history.append(url)
        if "dashboard/tasks" in url and self.redirect_to_login_on_probe:
            self.url = "https://dataify.com/login"
            self._title = "Login"
            return
        self.url = url
        self._title = "Dashboard"

    def wait_for_timeout(self, timeout):
        return None

    def wait_for_load_state(self, state, timeout=None):
        return None

    def title(self):
        return self._title

    def close(self):
        return None


class FakeBrowser:
    def __init__(self, page):
        self.page = page

    def new_context(self, viewport=None, storage_state=None):
        return FakeBrowserContext(self.page)


class FakeBrowserContext:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page

    def close(self):
        return None


class FakePlaywrightClient:
    def __init__(self, page):
        self._browser = FakeBrowser(page)
        self.viewport = {"width": 1920, "height": 1080}

    def launch(self):
        return None


class FakeResult:
    def __init__(self, status="passed", error_msg=""):
        self.status = types.SimpleNamespace(value=status)
        self.error_msg = error_msg


class FakeEngine:
    def __init__(self, project_name, **kwargs):
        self.project_name = project_name
        self.kwargs = kwargs

    def load_case(self, path):
        return {"url": "https://dataify.com/login"}

    def execute_case_on_page(self, case_data, page):
        page.url = "https://dataify.com/dashboard"
        page._title = "Dashboard"
        return FakeResult(status="passed")


class AILocatorAuthTests(unittest.TestCase):
    def setUp(self):
        self.service = AILocatorService(playwright_client=None)
        self.login_case = types.SimpleNamespace(id=8, content="id: CASE-8")

    def test_probe_authenticated_page_rejects_login_redirect(self):
        page = FakePage(redirect_to_login_on_probe=True)

        with self.assertRaises(RuntimeError):
            self.service._probe_authenticated_page(
                page,
                probe_url="https://dataify.com/dashboard/tasks",
                login_case=self.login_case,
            )

    def test_build_login_state_cache_saves_state_only_after_successful_probe(self):
        page = FakePage(redirect_to_login_on_probe=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "auth.json"
            with patch.dict("sys.modules", {"engine": types.SimpleNamespace(TestEngine=FakeEngine)}):
                result = self.service._build_login_state_cache(
                    state_path=state_path,
                    page=page,
                    login_case=self.login_case,
                    project_name="dataify",
                    base_url="https://dataify.com",
                    probe_url="https://dataify.com/dashboard/tasks",
                )

        self.assertTrue(result)
        self.assertEqual(page.context.storage_state_calls, [str(state_path)])
        self.assertIn("https://dataify.com/dashboard/tasks", page.goto_history)

    def test_build_login_state_cache_does_not_save_state_when_probe_fails(self):
        page = FakePage(redirect_to_login_on_probe=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "auth.json"
            with patch.dict("sys.modules", {"engine": types.SimpleNamespace(TestEngine=FakeEngine)}):
                with self.assertRaises(RuntimeError):
                    self.service._build_login_state_cache(
                        state_path=state_path,
                        page=page,
                        login_case=self.login_case,
                        project_name="dataify",
                        base_url="https://dataify.com",
                        probe_url="https://dataify.com/dashboard/tasks",
                    )

        self.assertEqual(page.context.storage_state_calls, [])

    def test_generate_with_auth_waits_for_settle_before_auth_check(self):
        page = FakePage()
        page.url = "https://dataify.com/dashboard/tasks"
        page._title = "Tasks"
        settle_calls = []

        service = AILocatorService(playwright_client=FakePlaywrightClient(page))
        service._is_auth_state_fresh = lambda path: True
        service._validate_locators_on_page = lambda current_page, locators: {"total_elements": 0, "validated_elements": 0, "validated_strategies": 0}
        service._analyze_html_content = lambda structured, page_name: {"locators": {}, "page_identifier": page_name, "raw_ai_response": "{}"}
        service._build_login_state_cache = lambda *args, **kwargs: None

        def fake_wait_for_page_settle(current_page, timeout_ms=15000):
            settle_calls.append(timeout_ms)
            current_page.url = "https://dataify.com/login"
            current_page._title = "Login"

        service._wait_for_page_settle = fake_wait_for_page_settle

        class FakeQuery:
            def __init__(self, result):
                self.result = result

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return self.result

        class FakeSession:
            def query(self, model):
                name = getattr(model, "__name__", "")
                if name == "Case":
                    return FakeQuery(types.SimpleNamespace(id=8, content="id: CASE-8"))
                if name == "Project":
                    return FakeQuery(types.SimpleNamespace(id=1, name="dataify", env_config='{"base_url": "https://dataify.com/"}'))
                return FakeQuery(None)

            def close(self):
                return None

        with patch("app.core.database.SessionLocal", return_value=FakeSession()):
            with self.assertRaises(RuntimeError):
                service.generate_with_auth(
                    target_url="https://dataify.com/dashboard/tasks",
                    page_name="任务列表",
                    login_case_id=8,
                    project_id=1,
                    viewport={"width": 1920, "height": 1080},
                    intent="",
                )

        self.assertTrue(settle_calls)


if __name__ == "__main__":
    unittest.main()
