# 导入所有模型，确保 create_tables() 前模型已注册到 Base.metadata
from app.models.audio_task import AudioTask  # noqa: F401
from app.models.script import Script  # noqa: F401
from app.models.setting import Setting  # noqa: F401
