from sqlalchemy.ext.asyncio import create_async_engine

from app.db_migrations import migrate_database


async def test_script_plan_migration_is_idempotent_and_preserves_old_content(tmp_path):
    path = tmp_path / "legacy.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE scripts (id INTEGER PRIMARY KEY, title TEXT NOT NULL, "
            "content TEXT NOT NULL, session_id TEXT, created_at DATETIME, updated_at DATETIME)"
        )
        await conn.exec_driver_sql(
            "INSERT INTO scripts (id, title, content) VALUES (1, '旧脚本', '保持不变')"
        )
    await migrate_database(engine)
    await migrate_database(engine)
    async with engine.connect() as conn:
        columns = await conn.exec_driver_sql("PRAGMA table_info(scripts)")
        row = await conn.exec_driver_sql("SELECT content, script_plan FROM scripts WHERE id=1")
        assert "script_plan" in {item[1] for item in columns.fetchall()}
        assert row.first() == ("保持不变", None)
    await engine.dispose()
