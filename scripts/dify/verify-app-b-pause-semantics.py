"""Verify published App B through Dify's public API without exposing its API key."""

from __future__ import annotations

import argparse
import json

import requests
from app_factory import create_app
from extensions.ext_database import db
from models import ApiToken
from sqlalchemy import select


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--api-url", default="http://nginx/v1")
    args = parser.parse_args()

    script_plan = {
        "version": 1,
        "target_duration_seconds": 180,
        "blocks": [
            {
                "id": "b1",
                "text": "现在，让自己找到一个舒适的位置。",
                "pause_after": {"kind": "paragraph"},
            },
            {
                "id": "b2",
                "text": "感受三次自然的呼吸。",
                "pause_after": {"kind": "breath", "count": 3},
            },
            {
                "id": "b3",
                "text": "安静地观察身体此刻的感受。",
                "pause_after": {"kind": "observe", "suggested_seconds": 20},
            },
        ],
    }
    pause_profile = {
        "id": "standard_v1",
        "version": 1,
        "durations": {
            "short": 700,
            "paragraph": 1800,
            "breath": 5000,
            "observe": 15000,
            "practice": 18000,
            "transition": 2500,
            "ending": 5000,
        },
        "suggested_seconds_factor": 1.0,
    }
    tts_context = {
        "provider": "aliyun",
        "model": "qwen-audio-3.0-tts-plus",
        "allowed_voices": ["longanlingxin", "longanlufeng"],
        "default_voice": "longanlingxin",
    }
    voice_prompt = "温柔、平静，语速稍慢，避免播音腔"

    _, flask_app = create_app()
    with flask_app.app_context():
        token = db.session.scalar(
            select(ApiToken.token)
            .where(ApiToken.app_id == args.app_id)
            .order_by(ApiToken.created_at.desc())
            .limit(1)
        )
    if not token:
        raise RuntimeError("App B API token not found")

    response = requests.post(
        f"{args.api_url}/chat-messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inputs": {
                "script_plan": json.dumps(script_plan, ensure_ascii=False, separators=(",", ":")),
                "pause_profile": json.dumps(
                    pause_profile, ensure_ascii=False, separators=(",", ":")
                ),
                "voice_prompt": voice_prompt,
                "tts_context": json.dumps(tts_context, ensure_ascii=False, separators=(",", ":")),
            },
            "query": voice_prompt,
            "response_mode": "blocking",
            "conversation_id": "",
            "user": "ops-check",
        },
        timeout=120,
    )
    response.raise_for_status()
    answer = response.json()["answer"]
    try:
        result = json.loads(answer)
    except json.JSONDecodeError as error:
        print(
            json.dumps(
                {
                    "status": "invalid_json",
                    "answer_length": len(answer),
                    "answer_prefix": answer[:200],
                    "answer_suffix": answer[-200:],
                },
                ensure_ascii=False,
            )
        )
        raise error

    segments = result["segments"]
    assert [segment["pause_after_ms"] for segment in segments] == [1800, 15000, 20000]
    assert [segment["pause_strategy"] for segment in segments] == ["silence"] * 3
    assert [segment["id"] for segment in segments] == [block["id"] for block in script_plan["blocks"]]
    assert [segment["text"] for segment in segments] == [
        block["text"] for block in script_plan["blocks"]
    ]
    assert result["voice"]["voice_id"] in tts_context["allowed_voices"]
    forbidden = {"emotion", "speed", "output_format"}
    assert forbidden.isdisjoint(result)
    assert forbidden.isdisjoint(result["voice"])
    assert "<speak" not in answer.lower()

    print(
        json.dumps(
            {
                "status": "passed",
                "pause_after_ms": [segment["pause_after_ms"] for segment in segments],
                "voice_id": result["voice"]["voice_id"],
                "segment_count": len(segments),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
