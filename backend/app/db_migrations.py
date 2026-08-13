import json

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import engine
from app.schemas.setting import MusicConfig


async def migrate_database(database_engine: AsyncEngine = engine) -> None:
    """Apply small, idempotent schema migrations needed by existing SQLite databases."""
    if database_engine.dialect.name != "sqlite":
        return

    async with database_engine.begin() as conn:
        table_rows = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        )
        if table_rows.first() is None:
            return

        columns = await conn.exec_driver_sql("PRAGMA table_info(settings)")
        if "music_config" not in {row[1] for row in columns.fetchall()}:
            await conn.exec_driver_sql("ALTER TABLE settings ADD COLUMN music_config JSON")

        rows = await conn.exec_driver_sql("SELECT id, music_config FROM settings")
        for setting_id, raw_config in rows.fetchall():
            config = json.loads(raw_config) if raw_config else {}
            if isinstance(config, dict) and "aliyun" in config and "minimax" in config:
                continue
            legacy = config if isinstance(config, dict) else {}
            common_keys = {"worker_concurrency", "output_format", "enable_aigc_watermark"}
            migrated = {
                **MusicConfig().model_dump(),
                **{key: legacy[key] for key in common_keys if key in legacy},
                "provider": "minimax",
            }
            aliyun_keys = {"api_key", "workspace_id", "base_url", "model", "source_format"}
            migrated["aliyun"].update(
                {key: legacy[key] for key in aliyun_keys if key in legacy}
            )
            await conn.exec_driver_sql(
                "UPDATE settings SET music_config = ? WHERE id = ?",
                (json.dumps(migrated, ensure_ascii=False), setting_id),
            )

        task_table = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='music_tasks'"
        )
        if task_table.first() is None:
            return
        task_columns = await conn.exec_driver_sql("PRAGMA table_info(music_tasks)")
        names = {row[1] for row in task_columns.fetchall()}
        if "provider" not in names:
            await conn.exec_driver_sql("ALTER TABLE music_tasks ADD COLUMN provider TEXT")
        if "source_format" not in names:
            await conn.exec_driver_sql("ALTER TABLE music_tasks ADD COLUMN source_format TEXT")
        await conn.exec_driver_sql(
            "UPDATE music_tasks SET provider='aliyun' "
            "WHERE model='fun-music-v1' AND (provider IS NULL OR provider='')"
        )
        await conn.exec_driver_sql(
            "UPDATE music_tasks SET source_format='wav' "
            "WHERE model='fun-music-v1' AND (source_format IS NULL OR source_format='')"
        )
