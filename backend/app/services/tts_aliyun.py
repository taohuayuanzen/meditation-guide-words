import httpx

from app.services.tts_base import TTSBase


class AliyunTTS(TTSBase):
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self._transport = transport
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation"

    def is_available(self):
        return bool(self.api_key)

    async def synthesize(self, text, voice_id, speed=1.0, volume=1.0, output_format="mp3"):
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
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(transport=self._transport, timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content
