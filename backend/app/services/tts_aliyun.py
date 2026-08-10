import base64
import json
import logging
import unicodedata

import httpx

from app.services.tts_base import TTSBase

logger = logging.getLogger(__name__)


class AliyunTTS(TTSBase):
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        model: str = "qwen-audio-3.0-tts-plus",
        base_url: str = "https://dashscope.aliyuncs.com/api/v1",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._transport = transport

    def is_available(self):
        return bool(self.api_key)

    async def synthesize(
        self,
        text,
        voice_id,
        speed=1.0,
        volume=1.0,
        output_format="mp3",
        instruction=None,
    ):
        logger.debug(
            "[AliyunTTS] synthesize called: model=%s voice=%s text_len=%s "
            "instruction_len=%s speed=%s volume=%s format=%s",
            self.model,
            voice_id,
            len(text) if isinstance(text, str) else type(text),
            len(instruction) if isinstance(instruction, str) else 0,
            speed,
            volume,
            output_format,
        )
        if self.model.startswith("sambert"):
            return await self._synthesize_sambert(
                text, voice_id, speed, volume, output_format
            )
        return await self._synthesize_qwen(
            text, voice_id, speed, volume, output_format, instruction
        )

    async def _synthesize_sambert(self, text, voice_id, speed, volume, output_format):
        url = f"{self.base_url}/services/aigc/text2audio/generation"
        payload = {
            "model": voice_id,
            "input": {"text": text},
            "parameters": {
                "format": output_format,
                "sample_rate": 48000,
                "volume": int(round(volume * 100)),
                "rate": speed,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.debug(
            "[AliyunTTS] sambert request: url=%s model=%s text_len=%s",
            url,
            voice_id,
            len(text) if isinstance(text, str) else type(text),
        )
        async with httpx.AsyncClient(transport=self._transport, timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        logger.debug(
            "[AliyunTTS] sambert response: status=%s content_len=%s",
            response.status_code,
            len(response.content),
        )
        response.raise_for_status()
        return response.content

    async def _synthesize_qwen(
        self, text, voice_id, speed, volume, output_format, instruction
    ):
        url = f"{self.base_url}/services/audio/tts/SpeechSynthesizer"
        input_payload: dict = {
            "text": text,
            "voice": voice_id,
            "format": output_format,
            "sample_rate": 48000,
            "volume": max(0, min(100, int(round(volume * 50)))),
            "rate": max(0.5, min(2.0, float(speed))),
        }
        if instruction and self.model.startswith("qwen-audio"):
            input_payload["instruction"] = _truncate_instruction(instruction)
        payload = {"model": self.model, "input": input_payload}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",
        }
        logger.debug(
            "[AliyunTTS] qwen request: url=%s model=%s voice=%s text_len=%s "
            "instruction_len=%s payload_keys=%s",
            url,
            self.model,
            voice_id,
            len(text) if isinstance(text, str) else type(text),
            len(input_payload.get("instruction", "")),
            list(input_payload.keys()),
        )

        async with httpx.AsyncClient(transport=self._transport, timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                logger.debug(
                    "[AliyunTTS] qwen response: status=%s headers=%s",
                    response.status_code,
                    dict(response.headers),
                )
                response.raise_for_status()
                return await self._parse_sse(response)

    async def _parse_sse(self, response):
        chunks: list[bytes] = []
        event_count = 0
        async for raw_line in response.aiter_lines():
            line = raw_line
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if not data:
                continue
            event_count += 1
            try:
                event = json.loads(data)
            except json.JSONDecodeError as exc:
                logger.error("[AliyunTTS] SSE JSON decode failed: line=%s", raw_line)
                raise RuntimeError(f"阿里云 TTS SSE 解析失败: {raw_line}") from exc

            if event.get("code"):
                logger.error(
                    "[AliyunTTS] SSE business error: code=%s message=%s request_id=%s",
                    event.get("code"),
                    event.get("message"),
                    event.get("request_id"),
                )
                raise RuntimeError(
                    f"阿里云 TTS 合成失败: [{event.get('code')}] {event.get('message', event)}"
                )

            output = event.get("output") or {}
            if output.get("finish_reason") == "stop":
                logger.debug(
                    "[AliyunTTS] SSE finished after %s events, total chunks=%s",
                    event_count,
                    len(chunks),
                )
                break

            audio = output.get("audio") or {}
            b64_data = audio.get("data")
            if b64_data:
                chunks.append(base64.b64decode(b64_data))
        logger.debug(
            "[AliyunTTS] SSE parsed: events=%s chunks=%s audio_bytes=%s",
            event_count,
            len(chunks),
            sum(len(c) for c in chunks),
        )
        return b"".join(chunks)


def _truncate_instruction(text: str, max_chars: int = 100) -> str:
    """按阿里云规则截断 instruction：CJK 汉字计 2，其他计 1。"""
    count = 0
    end = 0
    for idx, ch in enumerate(text):
        if unicodedata.category(ch).startswith("Lo") and _is_cjk(ch):
            count += 2
        else:
            count += 1
        if count > max_chars:
            return text[:idx]
        end = idx + 1
    return text[:end]


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    # CJK Unified Ideographs blocks
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2EBEF
    )
