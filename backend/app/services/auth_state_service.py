# -*- coding: utf-8 -*-
"""
Auth State Service

复用登录前置用例生成/读取 storage_state，提高探索执行效率。
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional

from app.core.database import SessionLocal
from app.models.case import Case
from app.models.project import Project


class AuthStateService:
    def __init__(self):
        self.auth_state_dir = Path(__file__).parent.parent.parent / ".auth_states"
        self.auth_state_dir.mkdir(parents=True, exist_ok=True)

    def get_state_path(self, project_name: str, login_case_id: int, base_url: str) -> Path:
        cache_key = hashlib.md5(f"{project_name}:{login_case_id}:{base_url}".encode("utf-8")).hexdigest()[:12]
        return self.auth_state_dir / f"{project_name}_case{login_case_id}_{cache_key}.json"

    def is_fresh(self, state_path: Path, max_age_seconds: int = 1800) -> bool:
        if not state_path.exists():
            return False
        return (time.time() - state_path.stat().st_mtime) <= max_age_seconds

    def ensure_auth_state(
        self,
        project_id: int,
        login_case_id: int,
        base_url: str,
        max_age_seconds: int = 1800,
    ) -> Optional[Path]:
        db = SessionLocal()
        try:
            login_case = db.query(Case).filter(Case.id == login_case_id).first()
            project = db.query(Project).filter(Project.id == project_id).first()
            if not login_case or not project:
                return None

            project_name = project.name
            state_path = self.get_state_path(project_name, login_case_id, base_url)
            if self.is_fresh(state_path, max_age_seconds=max_age_seconds):
                return state_path

            import tempfile
            import sys

            _eng_parent = str(Path(__file__).parent.parent.parent.parent)
            if _eng_parent not in sys.path:
                sys.path.insert(0, _eng_parent)
            from engine import TestEngine
            from playwright.sync_api import sync_playwright

            case_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
            case_file.write(login_case.content)
            case_file.close()

            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(viewport={"width": 1440, "height": 900})
                    page = context.new_page()
                    engine = TestEngine(project_name, base_url=base_url, headless=True, execution_id=f"auth_cache_{login_case_id}")
                    engine.execute_case_on_page(engine.load_case(case_file.name), page=page, debug=False)
                    context.storage_state(path=str(state_path))
                    browser.close()
            finally:
                Path(case_file.name).unlink(missing_ok=True)

            return state_path if state_path.exists() else None
        finally:
            db.close()
