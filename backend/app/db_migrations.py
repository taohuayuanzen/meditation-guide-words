import json

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import engine
from app.schemas.setting import MusicConfig


async def migrate_database(database_engine: AsyncEngine = engine) -> None:
    """Apply small, idempotent schema migrations needed by existing SQLite databases."""
    if database_engine.dialect.name != "sqlite":
        return

    async with database_engine.begin() as conn:
        audio_table = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audio_tasks'"
        )
        if audio_table.first() is not None:
            audio_columns = await conn.exec_driver_sql("PRAGMA table_info(audio_tasks)")
            audio_names = {row[1] for row in audio_columns.fetchall()}
            additions = {
                "render_plan": "JSON",
                "render_plan_version": "INTEGER",
                "render_plan_digest": "TEXT",
                "pause_profile_id": "TEXT",
                "tts_snapshot": "JSON",
                "tts_snapshot_digest": "TEXT",
                "estimated_speech_seconds": "FLOAT",
                "estimated_pause_seconds": "FLOAT",
                "estimated_total_seconds": "FLOAT",
                "actual_duration_seconds": "FLOAT",
                "stage": "TEXT",
                "completed_segments": "INTEGER DEFAULT 0",
                "total_segments": "INTEGER",
            }
            for name, sql_type in additions.items():
                if name not in audio_names:
                    await conn.exec_driver_sql(
                        f"ALTER TABLE audio_tasks ADD COLUMN {name} {sql_type}"
                    )

        script_table = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scripts'"
        )
        if script_table.first() is not None:
            script_columns = await conn.exec_driver_sql("PRAGMA table_info(scripts)")
            if "script_plan" not in {row[1] for row in script_columns.fetchall()}:
                await conn.exec_driver_sql("ALTER TABLE scripts ADD COLUMN script_plan JSON")

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
            migrated["aliyun"].update({key: legacy[key] for key in aliyun_keys if key in legacy})
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
