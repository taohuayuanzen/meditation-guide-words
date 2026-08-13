import pytest

from app.services.music_provider import MusicServiceError, generate_music


async def test_unsupported_provider_model_combination_never_falls_back():
    with pytest.raises(MusicServiceError) as error:
        await generate_music("minimax", "fun-music-v1", {}, "prompt")
    assert error.value.code == "MUSIC_PROVIDER_UNSUPPORTED"
