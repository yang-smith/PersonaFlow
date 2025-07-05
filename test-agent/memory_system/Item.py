"""
记忆系统的数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import uuid4


@dataclass
class MemoryItem:
    """统一的记忆条目"""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    embedding: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    hp: int = 1  # 默认HP为1（短期记忆）
    user_id: str = ""

    @property
    def is_alive(self) -> bool:
        """是否还活着"""
        return self.hp > 0
    
    @property
    def is_short_term(self) -> bool:
        """是否为短期记忆（HP=1）"""
        return self.hp == 1
    
    @property
    def is_long_term(self) -> bool:
        """是否为长期记忆（HP>1）"""
        return self.hp > 1
    
    @property
    def memory_type(self) -> str:
        """记忆类型"""
        return "short_term" if self.is_short_term else "long_term" 