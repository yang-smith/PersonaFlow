"""
长期记忆模块 - 实现"新陈代谢模型"，管理记忆条的HP、晋升和遗忘
"""
from typing import List, Optional
from datetime import datetime

from ..Item import MemoryItem
from ..storage.memory_store import MemoryStore
from ..utils.llm_adapter import LLMAdapter
from ..config import MemoryConfig


class LongTermMemoryManager:
    """长期记忆管理器"""
    
    def __init__(self, config: MemoryConfig, store: MemoryStore, llm_adapter: LLMAdapter):
        self.config = config
        self.store = store
        self.llm_adapter = llm_adapter
        
        # 内存热缓存
        self._hot_cache: dict = {}  # user_id -> List[MemoryItem]
    
    def promote_from_short_term(self, short_memory: MemoryItem) -> List[MemoryItem]:
        """将短期记忆晋升为长期记忆，可能生成多条长期记忆"""
        try:
            print(f"开始晋升短期记忆: {short_memory.id}")
            
            # 使用LLM提取长期事实，返回多条记忆
            extracted_memories = self.llm_adapter.extract_long_term_facts(short_memory.content)
            
            if not extracted_memories:
                print("没有提取到长期记忆")
                return []
            
            saved_memories = []
            for long_content, initial_hp in extracted_memories:
                # 创建长期记忆（HP > 1）
                long_memory = MemoryItem(
                    content=long_content,
                    embedding=short_memory.embedding,  # 复用向量
                    timestamp=short_memory.timestamp,
                    hp=initial_hp,  # 长期记忆的HP > 1
                    user_id=short_memory.user_id
                )
                
                # 保存到存储
                if self.store.save_memory(long_memory):
                    print(f"长期记忆已保存: {long_memory.id}, HP: {initial_hp}")
                    print(f"内容: {long_content[:100]}...")
                    saved_memories.append(long_memory)
                else:
                    print(f"长期记忆保存失败: {long_content[:50]}...")
            
            if saved_memories:
                # 更新热缓存
                self._update_hot_cache(short_memory.user_id)
            
            return saved_memories
                
        except Exception as e:
            print(f"晋升失败: {e}")
            return []
    
    def get_top_memories(self, user_id: str, limit: int = None) -> List[MemoryItem]:
        """获取HP最高的长期记忆"""
        if limit is None:
            limit = self.config.LONG_TERM_HOT_CACHE_SIZE
        
        # 先从热缓存获取
        if user_id in self._hot_cache:
            cached = self._hot_cache[user_id]
            if len(cached) >= limit:
                return cached[:limit]
        
        # 从数据库获取
        memories = self.store.get_long_term_memories(user_id, limit)
        self._hot_cache[user_id] = memories
        
        return memories
    
    def get_all_memories(self, user_id: str) -> List[MemoryItem]:
        """获取所有长期记忆（用于深度搜索）"""
        return self.store.get_all_long_term_memories(user_id)
    
    def boost_memory_hp(self, memory: MemoryItem):
        """增强记忆HP"""
        memory.hp += self.config.HP_BOOST_ON_ACCESS
        self.store.update_memory_hp(memory.id, self.config.HP_BOOST_ON_ACCESS)
        
        # 如果HP提升后可能进入热缓存，则更新缓存
        self._update_hot_cache(memory.user_id)
    
    def decay_all_memories(self, user_id: str):
        """衰减所有长期记忆的HP"""
        self.store.decay_all_hp(user_id, self.config.HP_DECAY_RATE)
        
        # 更新热缓存
        self._update_hot_cache(user_id)
    
    def cleanup_expired_memories(self) -> int:
        """清理HP为0的记忆"""
        deleted_count = self.store.cleanup_expired_memories()
        
        # 清空所有热缓存，强制重新加载
        self._hot_cache.clear()
        
        return deleted_count
    
    def _update_hot_cache(self, user_id: str):
        """更新热缓存"""
        self._hot_cache[user_id] = self.store.get_long_term_memories(
            user_id, self.config.LONG_TERM_HOT_CACHE_SIZE
        )
    
    def clear_user_memories(self, user_id: str):
        """清除用户的长期记忆"""
        # 清除热缓存
        if user_id in self._hot_cache:
            del self._hot_cache[user_id]
        
        # 从数据库删除长期记忆
        memories = self.store.get_all_long_term_memories(user_id)
        for memory in memories:
            self.store.delete_memory(memory.id) 