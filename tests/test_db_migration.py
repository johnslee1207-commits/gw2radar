from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


ALEMBIC_0004 = "0004_add_refresh_queue_and_api_key_secrets"
ALEMBIC_HEAD = "head"


def _run_alembic(target: str, db_url: str) -> None:
    import os
    os.environ["ALEMBIC_CONFIG"] = str(Path(__file__).resolve().parent.parent / "alembic.ini")
    from alembic.config import Config
    from alembic import command
    cfg = Config(os.environ["ALEMBIC_CONFIG"])
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "alembic"))
    command.upgrade(cfg, target)


def test_db_migration_adds_columns_without_losing_data() -> None:
    temp_dir = Path(".test_tmp") / f"db-migration-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / "test.db"
    db_url = f"sqlite:///{db_path}"
    try:
        _run_alembic(ALEMBIC_0004, db_url)

        old_cols = {"request_id", "endpoint", "params_json", "priority", "status", "attempts", "retry_after_seconds", "next_attempt_at", "last_error", "created_at", "updated_at"}
        new_cols = {"task_type", "method", "params_hash", "max_attempts", "account_id", "feature_scope", "leased_until", "worker_id", "last_status_code", "last_error_code", "completed_at"}

        engine = create_engine(db_url)
        with Session(engine) as session:
            session.execute(
                text("""
                    INSERT INTO refresh_queue (request_id, endpoint, params_json, priority, status, attempts, created_at, updated_at)
                    VALUES (:rid, :ep, :pj, :pr, :st, 0, datetime('now'), datetime('now'))
                """),
                {"rid": "test-001", "ep": "/v2/account/wallet", "pj": "{}", "pr": "P2", "st": "queued"},
            )
            session.commit()

            old_row = session.execute(text("SELECT request_id, endpoint, params_json, priority, status FROM refresh_queue WHERE request_id = 'test-001'")).fetchone()
            assert old_row is not None
            assert old_row._mapping["request_id"] == "test-001"

        engine.dispose()

        _run_alembic(ALEMBIC_HEAD, db_url)

        engine = create_engine(db_url)
        with Session(engine) as session:
            migrated = session.execute(text("SELECT * FROM refresh_queue WHERE request_id = 'test-001'")).fetchone()
            assert migrated is not None
            assert migrated._mapping["request_id"] == "test-001"
            assert migrated._mapping["endpoint"] == "/v2/account/wallet"
            assert migrated._mapping["status"] == "queued"

            for col in sorted(new_cols):
                assert col in migrated._mapping, f"Column {col} missing after migration"

            head_rev = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            assert head_rev is not None
            assert head_rev._mapping["version_num"] is not None

            column_names = {col.name for col in session.execute(text("PRAGMA table_info(refresh_queue)")).fetchall()}
            assert old_cols <= column_names, f"Old columns missing: {old_cols - column_names}"
            assert new_cols <= column_names, f"New columns missing: {new_cols - column_names}"

        engine.dispose()
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_init_db_after_migration_does_not_break() -> None:
    temp_dir = Path(".test_tmp") / f"db-init-after-migrate-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / "test.db"
    db_url = f"sqlite:///{db_path}"
    try:
        _run_alembic(ALEMBIC_HEAD, db_url)
        configure_database(db_url)
        init_db()

        engine = create_engine(db_url)
        with Session(engine) as session:
            tables = {row._mapping["name"] for row in session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
            assert "refresh_queue" in tables
            assert "alembic_version" in tables
        engine.dispose()
        close_database()
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
