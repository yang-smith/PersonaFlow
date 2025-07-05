"""
PersonaFlow Memory System - 仿生记忆模块

为无状态LLM提供双层记忆架构：
- 短期记忆: HP=1的记忆条，近期对话摘要
- 长期记忆: HP>1的记忆条，重要历史信息
"""

from .interface import MemorySystem
from .config import MemoryConfig, DEFAULT_CONFIG
from .Item import MemoryItem

__all__ = [
    'MemorySystem',
    'MemoryConfig', 
    'DEFAULT_CONFIG',
    'MemoryItem'
]

__version__ = "0.1.0"
