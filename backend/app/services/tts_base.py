from abc import ABC, abstractmethod


class TTSBase(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        volume: float = 1.0,
        output_format: str = "mp3",
    ) -> bytes:
        """返回音频二进制数据"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查配置是否可用"""
        pass
