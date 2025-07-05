"""
短期记忆模块 - 负责处理和存储对话摘要
"""
from typing import List, Any, Optional
from datetime import datetime

from ..Item import MemoryItem
from ..storage.memory_store import MemoryStore
from ..utils.llm_adapter import LLMAdapter
from ..config import MemoryConfig


class ShortTermMemoryManager:
    """短期记忆管理器"""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore, llm_adapter: LLMAdapter):
        self.config = config
        self.store = store
        self.llm_adapter = llm_adapter
        
        # 内存热缓存
        self._hot_cache: dict = {}  # user_id -> List[MemoryItem]
    
    def process_states(self, states: List[Any], user_id: str) -> Optional[MemoryItem]:
        """处理states，生成短期记忆"""
        if not states:
            return None
        
        # 估算token数量
        token_count = self.llm_adapter.estimate_token_count(states)
        
        # 检查是否达到阈值
        if token_count < self.config.STATES_TOKEN_THRESHOLD:
            print(f"Token数量({token_count})未达到阈值({self.config.STATES_TOKEN_THRESHOLD})")
            return None
        
        print(f"处理states: {len(states)}个事件, {token_count} tokens")
        
        # 生成摘要
        summary_content = self.llm_adapter.summarize_states(states)
        
        print(f"summary_content: {summary_content}")
        
        # 创建短期记忆（HP=1）
        short_memory = MemoryItem(
            content=summary_content,
            timestamp=datetime.now(),
            hp=1,  # 短期记忆的标志
            user_id=user_id
        )
        
        # 生成向量
        short_memory.embedding = self.llm_adapter.get_text_embedding(summary_content)
        
        # 保存到存储
        if self.store.save_memory(short_memory):
            print(f"短期记忆已保存: {short_memory.id}")
            print(f"摘要: {summary_content[:100]}...")
            
            # 更新热缓存
            self._update_hot_cache(user_id)
            
            return short_memory
        else:
            print("短期记忆保存失败")
            return None
    
    def get_recent_memories(self, user_id: str, limit: int = None) -> List[MemoryItem]:
        """获取最近的短期记忆"""
        if limit is None:
            limit = self.config.SHORT_TERM_HOT_CACHE_SIZE
        
        # 先从热缓存获取
        if user_id in self._hot_cache:
            cached = self._hot_cache[user_id]
            if len(cached) >= limit:
                return cached[:limit]
        
        # 从数据库获取
        memories = self.store.get_short_term_memories(user_id, limit)
        self._hot_cache[user_id] = memories
        
        return memories
    
    def get_short_term_total_tokens(self, user_id: str) -> int:
        """获取短期记忆的token总数"""
        total_tokens = 0
        for memory in self._hot_cache[user_id]:
            total_tokens += self.llm_adapter.estimate_token_count(memory.content)
        return total_tokens
    
    def check_overflow(self, user_id: str) -> bool:
        """检查短期记忆是否超过数量限制"""
        count = self.store.count_short_term_memories(user_id)
        return count > self.config.SHORT_TERM_MAX_COUNT
    
    def get_oldest_memory(self, user_id: str) -> Optional[MemoryItem]:
        """获取最老的短期记忆（用于晋升）"""
        return self.store.get_oldest_short_term_memory(user_id)
    
    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """删除短期记忆"""
        success = self.store.delete_memory(memory_id)
        if success:
            # 更新热缓存
            self._update_hot_cache(user_id)
        return success
    
    def boost_memory_hp(self, memory: MemoryItem):
        """增强记忆HP"""
        memory.hp += self.config.HP_BOOST_ON_ACCESS
        self.store.update_memory_hp(memory.id, self.config.HP_BOOST_ON_ACCESS)
    
    def _update_hot_cache(self, user_id: str):
        """更新热缓存"""
        self._hot_cache[user_id] = self.store.get_short_term_memories(
            user_id, self.config.SHORT_TERM_HOT_CACHE_SIZE
        )
    
    def clear_user_memories(self, user_id: str):
        """清除用户的短期记忆"""
        # 清除热缓存
        if user_id in self._hot_cache:
            del self._hot_cache[user_id]
        
        # 从数据库删除短期记忆
        memories = self.store.get_short_term_memories(user_id, 1000)  # 获取所有
        for memory in memories:
            self.store.delete_memory(memory.id) 