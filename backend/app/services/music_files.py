from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.models.music_task import MusicTask
from app.utils.file_utils import sanitize_filename


@dataclass(frozen=True)
class MusicFile:
    kind: str
    format: str
    label: str
    path: Path
    duration_seconds: float | int | None


def source_root() -> Path:
    return Path(settings.music_source_dir).resolve()


def final_root() -> Path:
    return Path(settings.music_final_dir).resolve()


def canonical_source_path(task: MusicTask) -> Path:
    source_format = task.source_format if task.source_format in {"wav", "mp3"} else "wav"
    return source_root() / f"{task.id}.{source_format}"


def canonical_final_path(task: MusicTask) -> Path:
    minutes = task.target_duration_seconds // 60
    return final_root() / f"{task.id}_{minutes}min.mp3"


def _controlled_path(raw_path: str | None, root: Path) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate


def _existing_file(candidates: list[Path | None]) -> Path | None:
    for candidate in candidates:
        if candidate and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def find_source_file(task: MusicTask) -> Path | None:
    return _existing_file(
        [
            canonical_source_path(task),
            _controlled_path(task.source_file_path, source_root()),
            source_root() / f"{task.id}.wav",
        ]
    )


def find_final_file(task: MusicTask) -> Path | None:
    return _existing_file(
        [
            _controlled_path(task.file_path, final_root()),
            canonical_final_path(task),
        ]
    )


def list_music_files(task: MusicTask) -> list[MusicFile]:
    items: list[MusicFile] = []
    source = find_source_file(task)
    if source:
        source_format = source.suffix.lower().lstrip(".")
        items.append(
            MusicFile(
                kind="source",
                format=source_format,
                label=f"原始 {source_format.upper()}",
                path=source,
                duration_seconds=task.source_duration_seconds,
            )
        )
    final = find_final_file(task)
    if final:
        items.append(
            MusicFile(
                kind="final",
                format="mp3",
                label=f"{task.target_duration_seconds // 60} 分钟 MP3",
                path=final,
                duration_seconds=task.final_duration_seconds,
            )
        )
    return items


def get_music_file(task: MusicTask, kind: str) -> MusicFile | None:
    return next((item for item in list_music_files(task) if item.kind == kind), None)


def delete_music_files(task: MusicTask) -> None:
    source = source_root()
    final = final_root()
    candidates = {
        canonical_source_path(task),
        source / f"{task.id}.wav",
        source / f"{task.id}.mp3",
        source / f"{task.id}.wav.part",
        source / f"{task.id}.mp3.part",
        canonical_final_path(task),
        canonical_final_path(task).with_suffix(".mp3.part"),
        canonical_final_path(task).with_suffix(".loop.part.wav"),
        _controlled_path(task.source_file_path, source),
        _controlled_path(task.file_path, final),
    }
    for path in candidates:
        if path is not None:
            path.unlink(missing_ok=True)


def rename_final_file(task: MusicTask, new_name: str) -> Path:
    current = find_final_file(task)
    if current is None:
        raise FileNotFoundError("Music file not found")
    safe_name = sanitize_filename(new_name)
    target = final_root() / f"{safe_name}.mp3"
    if target != current and target.exists():
        raise FileExistsError("File already exists")
    current.replace(target)
    return target
