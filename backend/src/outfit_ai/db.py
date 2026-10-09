"""SQLAlchemy 同步引擎 + SQLite。单用户零运维。"""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from shutil import copy2

from sqlalchemy import create_engine, inspect, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _engine_url() -> str:
    """SQLite 路径相对 cwd；确保父目录存在。"""
    url = settings.database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        # 处理相对/绝对路径
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return url


engine = create_engine(
    _engine_url(),
    connect_args={"check_same_thread": False},  # FastAPI 同步处理器跑在线程池
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """启动时建表 + 确保上传目录存在。"""
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    from . import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)
    _add_outfit_history_context_column(engine)
    _run_additive_migrations(engine, backup_path=_default_migration_backup_path(engine))
    with SessionLocal() as db:
        recover_interrupted_analyses(db)
        recover_interrupted_references(db)
        db.commit()


def _add_outfit_history_context_column(db_engine: Engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return
    if "outfit_history" not in inspect(db_engine).get_table_names():
        return
    columns = inspect(db_engine).get_columns("outfit_history")
    if "context_json" in {column["name"] for column in columns}:
        return
    with db_engine.begin() as connection:
        connection.execute(text("ALTER TABLE outfit_history ADD COLUMN context_json TEXT"))


_ADDITIVE_COLUMNS = {
    "profile": {
        "taste_memo_last_change": "TEXT NOT NULL DEFAULT ''",
        "taste_memo_source_feedback_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        "taste_memo_source_event_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        "taste_memo_refresh_status": "TEXT NOT NULL DEFAULT 'idle'",
        "taste_memo_refresh_error": "TEXT",
        "taste_memo_revision": "INTEGER NOT NULL DEFAULT 0",
    },
    "feedback": {
        "history_id": "TEXT",
        "action": "TEXT",
        "rating": "INTEGER",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
        "positive_signals_json": "TEXT NOT NULL DEFAULT '[]'",
        "negative_signals_json": "TEXT NOT NULL DEFAULT '[]'",
        "adjustment_signals_json": "TEXT NOT NULL DEFAULT '[]'",
        "wore_it": "INTEGER NOT NULL DEFAULT 0",
    },
}


def _default_migration_backup_path(db_engine: Engine) -> Path | None:
    if db_engine.dialect.name != "sqlite" or not db_engine.url.database:
        return None
    database = Path(db_engine.url.database)
    if not database.exists():
        return None
    return database.with_name(
        f"{database.name}.pre-migration-{datetime.now():%Y%m%d%H%M%S}.bak"
    )


def _run_additive_migrations(
    db_engine: Engine,
    backup_path: Path | None = None,
) -> bool:
    """Add missing SQLite columns transactionally, preserving all existing rows.

    A caller may provide ``backup_path`` for a recoverable local snapshot. SQLite
    rolls back the DDL transaction on failure; the snapshot is retained so a
    local operator can restore it if a later verification step fails.
    """
    if db_engine.dialect.name != "sqlite":
        return False
    inspector = inspect(db_engine)
    tables = set(inspector.get_table_names())
    missing: list[tuple[str, str, str]] = []
    for table, columns in _ADDITIVE_COLUMNS.items():
        if table not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        missing.extend(
            (table, name, definition)
            for name, definition in columns.items()
            if name not in existing
        )
    if not missing:
        return False

    if backup_path is not None and db_engine.url.database:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(Path(db_engine.url.database), backup_path)

    with db_engine.begin() as connection:
        for table, name, definition in missing:
            connection.execute(
                text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')
            )
    return True


def recover_interrupted_analyses(db: Session) -> int:
    from .models import WardrobeItem

    # ponytail: single-process restart recovery; multiple workers need a DB lease/fence.
    return db.execute(
        update(WardrobeItem)
        .where(WardrobeItem.status == "analyzing")
        .values(
            status="failed",
            ai_raw_response="任务因服务重启中断，请重试",
        )
    ).rowcount


def recover_interrupted_references(db: Session) -> int:
    from .models import StyleReference

    return db.execute(
        update(StyleReference)
        .where(StyleReference.status == "analyzing")
        .values(
            status="failed",
            ai_raw_response="任务因服务重启中断，请重试",
        )
    ).rowcount
