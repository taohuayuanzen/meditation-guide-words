import json
import shutil
from pathlib import Path

from app.config import settings


def audio_root(output_dir: str | None = None) -> Path:
    return Path(output_dir or settings.audio_output_dir).resolve()


def work_dir(task_id: int, output_dir: str | None = None) -> Path:
    return audio_root(output_dir) / "work" / str(task_id)


def final_path(task_id: int, output_dir: str | None = None) -> Path:
    return audio_root(output_dir) / f"{task_id}.mp3"


def manifest_path(task_id: int, output_dir: str | None = None) -> Path:
    return work_dir(task_id, output_dir) / "manifest.json"


def load_manifest(task_id: int, output_dir: str | None = None) -> dict | None:
    path = manifest_path(task_id, output_dir)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def save_manifest(task_id: int, manifest: dict, output_dir: str | None = None) -> None:
    directory = work_dir(task_id, output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = manifest_path(task_id, output_dir)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    part.replace(path)


def delete_audio_files(task_id: int, output_dir: str | None = None) -> None:
    root = audio_root(output_dir)
    for path in (root / f"{task_id}.mp3", root / f"{task_id}.mp3.part"):
        path.unlink(missing_ok=True)
    shutil.rmtree(work_dir(task_id, output_dir), ignore_errors=True)
