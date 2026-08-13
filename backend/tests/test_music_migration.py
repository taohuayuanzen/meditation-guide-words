import json

from sqlalchemy.ext.asyncio import create_async_engine

from app.db_migrations import migrate_database


async def _old_database(path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE settings (id INTEGER PRIMARY KEY, llm_config JSON, tts_config JSON)"
        )
        await conn.exec_driver_sql(
            "INSERT INTO settings VALUES (1, '{\"api_key\": \"llm-secret\"}', "
            "'{\"voice_id\": \"voice-1\"}')"
        )
        await conn.exec_driver_sql("CREATE TABLE scripts (id INTEGER PRIMARY KEY, content TEXT)")
        await conn.exec_driver_sql("INSERT INTO scripts VALUES (7, '原有脚本')")
        await conn.exec_driver_sql(
            "CREATE TABLE audio_tasks (id INTEGER PRIMARY KEY, status TEXT)"
        )
        await conn.exec_driver_sql("INSERT INTO audio_tasks VALUES (9, 'completed')")
    return engine


async def test_music_config_migration_is_idempotent_and_preserves_data(tmp_path):
    engine = await _old_database(tmp_path / "old.db")
    await migrate_database(engine)
    await migrate_database(engine)

    async with engine.connect() as conn:
        columns = await conn.exec_driver_sql("PRAGMA table_info(settings)")
        assert [row[1] for row in columns.fetchall()].count("music_config") == 1
        setting = (
            await conn.exec_driver_sql(
                "SELECT llm_config, tts_config, music_config FROM settings WHERE id=1"
            )
        ).one()
        assert json.loads(setting[0]) == {"api_key": "llm-secret"}
        assert json.loads(setting[1]) == {"voice_id": "voice-1"}
        music_config = json.loads(setting[2])
        assert music_config["provider"] == "minimax"
        assert music_config["aliyun"]["model"] == "fun-music-v1"
        assert music_config["minimax"]["model"] == "music-3.0"
        assert (await conn.exec_driver_sql("SELECT content FROM scripts WHERE id=7")).scalar() == (
            "原有脚本"
        )
        assert (
            await conn.exec_driver_sql("SELECT status FROM audio_tasks WHERE id=9")
        ).scalar() == "completed"
    await engine.dispose()


async def test_existing_music_config_is_not_overwritten(tmp_path):
    engine = await _old_database(tmp_path / "existing.db")
    async with engine.begin() as conn:
        await conn.exec_driver_sql("ALTER TABLE settings ADD COLUMN music_config JSON")
        config = {
            "provider": "aliyun",
            "aliyun": {"api_key": "keep-me", "workspace_id": "workspace"},
            "minimax": {"api_key": "minimax-keep"},
        }
        await conn.exec_driver_sql(
            "UPDATE settings SET music_config = ? WHERE id=1",
            (json.dumps(config),),
        )
    await migrate_database(engine)
    async with engine.connect() as conn:
        value = (
            await conn.exec_driver_sql("SELECT music_config FROM settings WHERE id=1")
        ).scalar()
    assert json.loads(value) == config
    await engine.dispose()


async def test_old_music_tasks_are_snapshotted_as_aliyun_wav(tmp_path):
    engine = await _old_database(tmp_path / "tasks.db")
    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE music_tasks ("
            "id INTEGER PRIMARY KEY, model TEXT, status TEXT, error_msg TEXT, file_path TEXT)"
        )
        await conn.exec_driver_sql(
            "INSERT INTO music_tasks VALUES "
            "(1, 'fun-music-v1', 'failed', 'keep-error', 'source.wav')"
        )
    await migrate_database(engine)
    await migrate_database(engine)
    async with engine.connect() as conn:
        row = (
            await conn.exec_driver_sql(
                "SELECT provider, source_format, status, error_msg, file_path "
                "FROM music_tasks WHERE id=1"
            )
        ).one()
    assert row == ("aliyun", "wav", "failed", "keep-error", "source.wav")
    await engine.dispose()
