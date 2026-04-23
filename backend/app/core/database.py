# -*- coding: utf-8 -*-
"""
Database - 数据库连接与模型基类
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


engine = create_engine(
    settings.db_url,
    echo=settings.db_echo,
    connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from app.models import case, project, execution, locator, scheduler
    Base.metadata.create_all(bind=engine)
    _ensure_locator_columns()
    _ensure_execution_step_columns()


def _ensure_locator_columns():
    """Add newly introduced locator columns for existing SQLite databases."""
    inspector = inspect(engine)
    if "locators" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("locators")}
    alter_statements = []

    if "primary_type" not in columns:
        alter_statements.append(
            "ALTER TABLE locators ADD COLUMN primary_type VARCHAR(20) DEFAULT ''"
        )
    if "strategies_json" not in columns:
        alter_statements.append(
            "ALTER TABLE locators ADD COLUMN strategies_json TEXT DEFAULT ''"
        )

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))


def _ensure_execution_step_columns():
    """Add execution step trace columns for existing SQLite databases."""
    inspector = inspect(engine)
    if "execution_steps" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("execution_steps")}
    alter_statements = []

    if "matched_strategy_type" not in columns:
        alter_statements.append(
            "ALTER TABLE execution_steps ADD COLUMN matched_strategy_type VARCHAR(50) DEFAULT ''"
        )
    if "matched_strategy_value" not in columns:
        alter_statements.append(
            "ALTER TABLE execution_steps ADD COLUMN matched_strategy_value TEXT DEFAULT ''"
        )
    if "matched_strategy_priority" not in columns:
        alter_statements.append(
            "ALTER TABLE execution_steps ADD COLUMN matched_strategy_priority INTEGER DEFAULT 0"
        )

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))
