import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from app.models.audio_task import AudioTask
from app.services.audio_postprocessor import assemble_wav, create_silence, encode_mp3, probe_audio
from app.services.audio_render_files import final_path, load_manifest, save_manifest, work_dir
from app.services.tts_capabilities import TTSCapabilities, get_tts_capabilities

MAX_TTS_REQUESTS = 40


def canonical_digest(value: dict) -> str:
    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        if isinstance(item, float) and item.is_integer():
            return int(item)
        return item

    encoded = json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class SpeechSegment:
    index: int
    text: str
    pause_after_ms: int
    pause_strategy: str
    enable_ssml: bool = False


def build_speech_segments(
    render_plan: dict, capabilities: TTSCapabilities | None = None
) -> list[SpeechSegment]:
    if capabilities and capabilities.supports_ssml:
        return _build_ssml_segments(render_plan, capabilities)
    result: list[SpeechSegment] = []
    pending: list[str] = []
    for item in render_plan.get("segments", []):
        text = item.get("text", "").strip()
        if text:
            pending.append(text)
        if item.get("pause_strategy") == "silence":
            if pending:
                result.append(
                    SpeechSegment(
                        len(result), "\n".join(pending), int(item["pause_after_ms"]), "silence"
                    )
                )
                pending = []
    if pending:
        result.append(SpeechSegment(len(result), "\n".join(pending), 0, "natural"))
    if len(result) > MAX_TTS_REQUESTS:
        raise ValueError(f"语音分段数超过单任务上限 {MAX_TTS_REQUESTS}")
    return result


def _build_ssml_segments(render_plan: dict, capabilities: TTSCapabilities) -> list[SpeechSegment]:
    result: list[SpeechSegment] = []
    pending: list[str] = []
    for item in render_plan.get("segments", []):
        text = item.get("text", "").strip()
        if text:
            pending.append(escape(text))
        if item.get("pause_strategy") != "silence":
            continue
        pause_ms = int(item.get("pause_after_ms", 0))
        if 0 < pause_ms <= capabilities.max_ssml_break_ms:
            pending.append(f'<break time="{pause_ms}ms"/>')
            continue
        if pending:
            result.append(
                SpeechSegment(
                    len(result),
                    f"<speak>{''.join(pending)}</speak>",
                    pause_ms,
                    "silence" if pause_ms else "natural",
                    True,
                )
            )
            pending = []
    if pending:
        result.append(
            SpeechSegment(len(result), f"<speak>{''.join(pending)}</speak>", 0, "natural", True)
        )
    if len(result) > MAX_TTS_REQUESTS:
        raise ValueError(f"语音分段数超过单任务上限 {MAX_TTS_REQUESTS}")
    return result


class AudioRenderer:
    def __init__(self, tts_service, output_dir: str):
        self.tts = tts_service
        self.output_dir = output_dir

    async def render(self, task: AudioTask, progress=None) -> tuple[Path, float]:
        plan = task.render_plan or {}
        snapshot = task.tts_snapshot or {}
        if canonical_digest(plan) != task.render_plan_digest:
            raise ValueError("render plan digest 不一致，禁止复用缓存")
        if canonical_digest(snapshot) != task.tts_snapshot_digest:
            raise ValueError("TTS snapshot digest 不一致，禁止复用缓存")
        capabilities = get_tts_capabilities(
            snapshot.get("provider", ""),
            snapshot.get("model", ""),
            snapshot.get("voice_id", ""),
        )
        segments = build_speech_segments(plan, capabilities)
        directory = work_dir(task.id, self.output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        manifest = load_manifest(task.id, self.output_dir)
        expected = {
            "task_id": task.id,
            "render_plan_digest": task.render_plan_digest,
            "tts_snapshot_digest": task.tts_snapshot_digest,
        }
        if manifest and any(manifest.get(key) != value for key, value in expected.items()):
            raise ValueError("缓存 manifest 与任务快照不一致")
        manifest = manifest or {**expected, "segments": []}
        entries = manifest["segments"]
        parts: list[Path] = []
        expected_channels: int | None = None
        sample_rate = int(snapshot.get("sample_rate", 48000))
        for segment in segments:
            speech = directory / f"speech_{segment.index:03d}.wav"
            entry = entries[segment.index] if segment.index < len(entries) else None
            reusable = bool(entry and entry.get("speech_completed") and speech.is_file())
            if reusable:
                try:
                    probe_audio(speech)
                except Exception:
                    reusable = False
            if not reusable:
                audio = await self.tts.synthesize(
                    text=segment.text,
                    voice_id=snapshot["voice_id"],
                    speed=float(snapshot["rate"]),
                    volume=float(snapshot["volume"]),
                    pitch=float(snapshot.get("pitch", 1.0)),
                    output_format="wav",
                    sample_rate=int(snapshot.get("sample_rate", 48000)),
                    instruction=snapshot.get("instruction"),
                    task_id=task.id,
                    segment_index=segment.index,
                    enable_ssml=segment.enable_ssml,
                )
                speech.write_bytes(audio)
                probe_audio(speech)
                item = {
                    "index": segment.index,
                    "speech_file": speech.name,
                    "speech_completed": True,
                    "pause_after_ms": segment.pause_after_ms,
                    "pause_strategy": segment.pause_strategy,
                    "ssml": segment.enable_ssml,
                    "text_sha256": hashlib.sha256(segment.text.encode()).hexdigest(),
                }
                if entry is None:
                    entries.append(item)
                else:
                    entries[segment.index] = item
                save_manifest(task.id, manifest, self.output_dir)
                if progress:
                    await progress(segment.index + 1, "synthesizing")
            speech_info = probe_audio(speech)
            if speech_info.sample_rate != sample_rate:
                raise ValueError("TTS 中间 WAV 采样率与任务快照不一致")
            if expected_channels is None:
                expected_channels = speech_info.channels
            elif speech_info.channels != expected_channels:
                raise ValueError("TTS 中间 WAV 声道数不一致")
            parts.append(speech)
            if segment.pause_after_ms:
                silence = (
                    directory
                    / f"silence_{segment.pause_after_ms}_{sample_rate}_{expected_channels}.wav"
                )
                if not silence.is_file():
                    create_silence(silence, segment.pause_after_ms, sample_rate, expected_channels)
                silence_info = probe_audio(silence)
                if abs(silence_info.duration_seconds - segment.pause_after_ms / 1000) > 0.02:
                    raise ValueError("确定性静音时长校验失败")
                parts.append(silence)
        if progress:
            await progress(len(segments), "assembling")
        target = final_path(task.id, self.output_dir)
        assembled = directory / "assembled.wav"
        assemble_wav(parts, assembled, sample_rate)
        if progress:
            await progress(len(segments), "encoding")
        encode_mp3(assembled, target, sample_rate)
        if progress:
            await progress(len(segments), "verifying")
        info = probe_audio(target)
        return target, info.duration_seconds
