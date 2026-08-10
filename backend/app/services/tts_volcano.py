import asyncio
import base64
import hashlib
import hmac
import time
import uuid

import httpx

from app.services.tts_base import TTSBase

TOKEN_ENDPOINT = "https://openspeech.bytedance.com/api/v1/auth/token"
TTS_ENDPOINT = "https://openspeech.bytedance.com/api/v1/tts"


class VolcanoTTS(TTSBase):
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        appid: str = "",
        cluster: str = "volcano_tts",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.appid = appid
        self.cluster = cluster
        self._transport = transport
        self._token = ""
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    def is_available(self):
        return bool(self.api_key and self.secret_key and self.appid)

    async def _fetch_access_token(self) -> str:
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        signature = hmac.new(
            self.secret_key.encode(),
            f"{timestamp}\n{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Appid": self.appid,
            "X-Access-Key": self.api_key,
            "X-Access-Nonce": nonce,
            "X-Access-Timestamp": timestamp,
            "X-Access-Signature": signature,
            "X-Resource-Id": "volc.tts.app",
        }
        async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as client:
            response = await client.post(
                TOKEN_ENDPOINT, headers=headers, json={"appid": self.appid}
            )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 3000:
            raise RuntimeError(f"火山 TTS 获取 token 失败: {data.get('message', data)}")
        self._token = data["data"]["token"]
        ttl = float(data.get("data", {}).get("expire_time") or 604800)
        self._token_expires_at = time.time() + ttl
        return self._token

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        async with self._token_lock:
            if self._token and time.time() < self._token_expires_at:
                return self._token
            return await self._fetch_access_token()

    async def synthesize(
        self, text, voice_id, speed=1.0, volume=1.0, output_format="mp3", instruction=None
    ):
        token = await self._ensure_token()
        audio_bytes = await self._call_tts(text, voice_id, speed, volume, output_format, token)
        if not audio_bytes:
            self._token = ""
            self._token_expires_at = 0.0
            token = await self._ensure_token()
            audio_bytes = await self._call_tts(text, voice_id, speed, volume, output_format, token)
        return audio_bytes

    async def _call_tts(self, text, voice_id, speed, volume, output_format, token) -> bytes | None:
        payload = {
            "app": {"appid": self.appid, "token": token, "cluster": self.cluster},
            "user": {"uid": "local-user"},
            "audio": {
                "voice_type": voice_id,
                "encoding": output_format,
                "speed_ratio": speed,
                "volume_ratio": volume,
            },
            "request": {
                "reqid": uuid.uuid4().hex,
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }
        async with httpx.AsyncClient(transport=self._transport, timeout=60.0) as client:
            response = await client.post(
                TTS_ENDPOINT,
                headers={"Authorization": f"Bearer; {token}"},
                json=payload,
            )
        if response.status_code == 401:
            return None
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 3000:
            raise RuntimeError(f"火山 TTS 合成失败: {data.get('message', data)}")
        frames = data.get("data", [])
        return b"".join(
            base64.b64decode(frame["data"]) for frame in frames if frame.get("type") == "binary"
        )
