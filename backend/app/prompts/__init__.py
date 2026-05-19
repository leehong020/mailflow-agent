"""Prompt 读取工具。

提示词改为独立 txt 文件后，产品同学或开发者可以直接编辑 prompts 目录下的
文本文件，不需要改 Python 代码。load_prompt 使用缓存，避免每次 Agent 调用都
重复读取磁盘。
"""

from functools import lru_cache
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_prompt(filename: str) -> str:
    """按文件名读取系统提示词。

    Args:
        filename: prompts 目录下的 txt 文件名。

    Returns:
        去除首尾空白后的提示词文本。
    """

    path = (PROMPT_DIR / filename).resolve()
    if path.parent != PROMPT_DIR:
        raise ValueError("只能读取 prompts 目录下的提示词文件。")
    if path.suffix.lower() != ".txt":
        raise ValueError("提示词文件必须使用 .txt 后缀。")
    return path.read_text(encoding="utf-8").strip()


__all__ = ["load_prompt"]
