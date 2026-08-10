import os
import re


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """将字符串转换为安全的文件名（不含路径分隔符与非法字符）。"""
    # 去除前后空白
    name = name.strip()
    # 替换 Windows / Unix 非法字符
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    # 合并连续下划线/空格
    name = re.sub(r"[\s_]+", "_", name)
    # 去除首尾部残留下划线
    name = name.strip("_")
    if not name:
        name = "untitled"
    # 限制长度，保留尾部以便加 id 后缀时不丢失
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")
    return name


def ensure_dir(path: str) -> None:
    """确保目录存在，不存在则递归创建。"""
    os.makedirs(path, exist_ok=True)


def get_script_output_dir(audio_output_dir: str) -> str:
    """根据音频输出目录推断脚本产物目录。"""
    return os.path.join(os.path.dirname(os.path.abspath(audio_output_dir)), "scripts")
