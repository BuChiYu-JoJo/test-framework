#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quickly update the admin DingTalk callback URL used by the reusable login precondition case.

Usage:
  python scripts/update_admin_login_callback.py ^
    --callback-url "http://10.0.8.164:8000/user/login?uid=...&account=...&nickname=...&sign=...&code=0&timestamp=..."

This updates:
1. projects/dataify/cases/yaml/tc_admin_ding_google_pre.yaml
2. The matching DB case content in backend/test_framework.db when present
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "projects" / "dataify" / "cases" / "yaml" / "tc_admin_ding_google_pre.yaml"
BACKEND_DIR = ROOT / "backend"
CASE_ID = "TC_ADMIN_DING_GOOGLE_PRE"
FIELD_NAME = "ADMIN_LOGIN_CALLBACK_URL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update admin login callback URL")
    parser.add_argument("--callback-url", required=True, help="New DingTalk callback URL")
    return parser.parse_args()


def update_yaml(callback_url: str) -> str:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    data.setdefault("data", {})[FIELD_NAME] = callback_url
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    YAML_PATH.write_text(content, encoding="utf-8")
    return content


def update_db(content: str) -> bool:
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))
    from app.core.database import SessionLocal
    from app.models.case import Case

    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_id == CASE_ID).first()
        if not case:
            return False
        case.content = content
        db.commit()
        return True
    finally:
        db.close()


def main() -> int:
    args = parse_args()
    content = update_yaml(args.callback_url)
    updated_db = update_db(content)
    print(f"Updated YAML: {YAML_PATH}")
    print(f"Updated {FIELD_NAME}: {args.callback_url}")
    print(f"Updated DB case: {'yes' if updated_db else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
