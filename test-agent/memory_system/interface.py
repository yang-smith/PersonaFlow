"""
记忆系统的干净外部接口
"""
import asyncio
from typing import List, Any, Optional
from datetime import datetime

from .config import MemoryConfig, DEFAULT_CONFIG
from .storage.memory_store import MemoryStore
from .utils.llm_adapter import LLMAdapter
from .core.short_term_memory import ShortTermMemoryManager
from .core.long_term_memory import LongTermMemoryManager
from .core.retrieval import MemoryRetriever
from .Item import MemoryItem


class MemorySystem:
    """记忆系统主接口"""
    
    def __init__(self, config: MemoryConfig = None, llm_client=None):
        self.config = config or DEFAULT_CONFIG
        
        # 初始化组件
        self.store = MemoryStore(self.config)
        self.llm_adapter = LLMAdapter(llm_client)
        self.short_term_mgr = ShortTermMemoryManager(self.config, self.store, self.llm_adapter)
        self.long_term_mgr = LongTermMemoryManager(self.config, self.store, self.llm_adapter)
        self.retriever = MemoryRetriever(self.config, self.short_term_mgr, self.long_term_mgr, self.llm_adapter)
        
        print("记忆系统初始化完成")
    
    def get_relevant_memories(self, user_input: str, user_id: str = "default") -> str:
        """
        读取接口：闪念检索 - 获取相关记忆用于context
        输入：当前的用户输入，用户标识
        输出：格式化的记忆片段字符串
        """
        if not user_input.strip():
            return ""
        
        try:
            # 执行闪念检索
            memories = self.retriever.reflexive_recall(user_input, user_id)
            
            if not memories:
                return ""
            
            # 格式化为context字符串
            return self._format_memories_for_context(memories)
            
        except Exception as e:
            print(f"记忆检索失败: {e}")
            return ""
    
    def update_memory(self, states: List[Any], user_id: str = "default"):
        """
        写入接口：处理新的states，更新记忆
        输入：对话states，用户标识
        动作：启动短期记忆存储与长期记忆晋升判断
        """
        if not states:
            return
        
        try:
            # 1. 处理states，生成短期记忆
            short_memory = self.short_term_mgr.process_states(states, user_id)
            
            if short_memory:
                # 2. 同步检查是否需要晋升（修复异步问题）
                self._check_and_promote_sync(user_id)
                
        except Exception as e:
            print(f"更新记忆失败: {e}")
    
    def deep_recall(self, user_input: str, user_id: str = "default") -> str:
        """
        深度检索接口：深思检索 - 全面搜索长期记忆
        供LLM作为tool调用
        """
        if not user_input.strip():
            return "请提供具体的回忆关键词或问题"
        
        try:
            # 执行深度检索
            memories = self.retriever.deep_thought(user_input, user_id)
            
            if not memories:
                return "没有找到相关的历史记忆"
            
            # 格式化为用户可读的结果
            return self._format_memories_for_display(memories)
            
        except Exception as e:
            print(f"深度检索失败: {e}")
            return f"深度检索过程中出现错误: {str(e)}"
    
    def _check_and_promote_sync(self, user_id: str):
        """同步版本的检查和晋升逻辑"""
        try:
            # 检查短期记忆是否超过数量限制
            if self.short_term_mgr.check_overflow(user_id):
                print(f"用户 {user_id} 短期记忆超过限制，开始晋升...")
                
                # 获取最老的短期记忆
                oldest_memory = self.short_term_mgr.get_oldest_memory(user_id)
                
                if oldest_memory:
                    # 晋升为长期记忆
                    long_memories = self.long_term_mgr.promote_from_short_term(oldest_memory)
                    
                    # 无论晋升是否成功，都要删除原短期记忆，避免无限循环
                    self.short_term_mgr.delete_memory(oldest_memory.id, user_id)
                    
                    if long_memories:
                        print(f"晋升完成: {oldest_memory.id} -> {len(long_memories)}条长期记忆")
                    else:
                        print(f"晋升失败，但已删除短期记忆: {oldest_memory.id}")
                    
                    # 递归检查是否还需要继续晋升
                    if self.short_term_mgr.check_overflow(user_id):
                        self._check_and_promote_sync(user_id)
            
            # 定期维护：HP衰减和清理
            self._periodic_maintenance_sync(user_id)
            
        except Exception as e:
            print(f"晋升检查失败: {e}")
    
    def _periodic_maintenance_sync(self, user_id: str):
        """同步版本的定期维护任务"""
        try:
            # HP衰减
            self.long_term_mgr.decay_all_memories(user_id)
            
            # 清理过期记忆
            deleted_count = self.long_term_mgr.cleanup_expired_memories()
            
            if deleted_count > 0:
                print(f"清理完成：删除 {deleted_count} 条过期记忆")
                
        except Exception as e:
            print(f"维护任务失败: {e}")
    
    def _format_memories_for_context(self, memories: List[MemoryItem]) -> str:
        """格式化记忆用于插入context"""
        if not memories:
            return ""
        
        formatted_parts = []
        for i, memory in enumerate(memories, 1):
            memory_type = "近期" if memory.is_short_term else "历史"
            time_ago = self._format_time_ago(memory.timestamp)
            
            formatted_parts.append(
                f"记忆{i} ({memory_type}, {time_ago}): {memory.content}"
            )
        
        return "<relevant_memories>\n" + "\n".join(formatted_parts) + "\n</relevant_memories>"
    
    def _format_memories_for_display(self, memories: List[MemoryItem]) -> str:
        """格式化记忆用于显示给用户"""
        if not memories:
            return "没有找到相关记忆"
        
        formatted_parts = []
        for i, memory in enumerate(memories, 1):
            memory_type = "短期记忆" if memory.is_short_term else "长期记忆"
            time_ago = self._format_time_ago(memory.timestamp)
            hp_info = f"HP:{memory.hp}" if memory.hp > 1 else ""
            
            formatted_parts.append(
                f"{i}. [{memory_type}] {time_ago} {hp_info}\n{memory.content}\n"
            )
        
        return "找到以下相关记忆：\n\n" + "\n".join(formatted_parts)
    
    def _format_time_ago(self, timestamp: datetime) -> str:
        """格式化时间差"""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}小时前"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}分钟前"
        else:
            return "刚刚"
    
    # === 管理接口 ===
    
    def get_memory_stats(self, user_id: str = "default") -> dict:
        """获取记忆统计信息"""
        try:
            short_memories = self.short_term_mgr.get_recent_memories(user_id, 100)
            long_memories = self.long_term_mgr.get_all_memories(user_id)
            
            return {
                "short_term": {
                    "count": len(short_memories),
                    "avg_hp": sum(m.hp for m in short_memories) / len(short_memories) if short_memories else 0
                },
                "long_term": {
                    "count": len(long_memories),
                    "avg_hp": sum(m.hp for m in long_memories) / len(long_memories) if long_memories else 0
                }
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {
                "short_term": {"count": 0, "avg_hp": 0},
                "long_term": {"count": 0, "avg_hp": 0}
            }
    
    def clear_user_memories(self, user_id: str):
        """清除指定用户的所有记忆"""
        self.short_term_mgr.clear_user_memories(user_id)
        self.long_term_mgr.clear_user_memories(user_id)
        print(f"已清除用户 {user_id} 的所有记忆") 