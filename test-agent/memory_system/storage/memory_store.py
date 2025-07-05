"""
统一的存储接口层 - 封装所有数据库操作
"""
import sqlite3
import json
import hashlib
import numpy as np
from typing import List, Optional, Any
from datetime import datetime

from ..Item import MemoryItem
from ..config import MemoryConfig


class MemoryStore:
    """统一的记忆存储接口"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self._init_database()
    
    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        # 简化的记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB,
                timestamp TEXT NOT NULL,
                hp INTEGER DEFAULT 1,
                user_id TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_user_time ON memories(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_user_hp ON memories(user_id, hp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_hp ON memories(hp)')
        
        conn.commit()
        conn.close()
    
    def save_memory(self, memory: MemoryItem) -> bool:
        """保存记忆条目"""
        try:
            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()
            
            embedding_blob = np.array(memory.embedding, dtype=np.float32).tobytes() if memory.embedding else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO memories 
                (id, content, embedding, timestamp, hp, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                memory.id, memory.content, embedding_blob, 
                memory.timestamp.isoformat(), memory.hp, memory.user_id
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"保存记忆失败: {e}")
            return False
    
    def get_short_term_memories(self, user_id: str, limit: int = 5) -> List[MemoryItem]:
        """获取短期记忆（HP=1）"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM memories 
            WHERE user_id = ? AND hp = 1
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [self._row_to_memory_item(row) for row in results]
    
    def get_long_term_memories(self, user_id: str, limit: int = 10) -> List[MemoryItem]:
        """获取长期记忆（HP>1），按HP降序"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM memories 
            WHERE user_id = ? AND hp > 1
            ORDER BY hp DESC, timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [self._row_to_memory_item(row) for row in results]
    
    def get_all_long_term_memories(self, user_id: str) -> List[MemoryItem]:
        """获取所有长期记忆"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM memories 
            WHERE user_id = ? AND hp > 1
            ORDER BY hp DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [self._row_to_memory_item(row) for row in results]
    
    def get_oldest_short_term_memory(self, user_id: str) -> Optional[MemoryItem]:
        """获取最老的短期记忆"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM memories 
            WHERE user_id = ? AND hp = 1
            ORDER BY timestamp ASC 
            LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return self._row_to_memory_item(result) if result else None
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除记忆失败: {e}")
            return False
    
    def update_memory_hp(self, memory_id: str, hp_delta: int):
        """更新记忆HP"""
        try:
            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE memories 
                SET hp = MAX(0, hp + ?)
                WHERE id = ?
            ''', (hp_delta, memory_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"更新HP失败: {e}")
    
    def cleanup_expired_memories(self) -> int:
        """清理HP为0的记忆"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM memories WHERE hp <= 0')
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def decay_all_hp(self, user_id: str, decay_rate: float):
        """衰减所有长期记忆的HP"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        # 只衰减长期记忆（HP > 1）
        cursor.execute('''
            UPDATE memories 
            SET hp = CAST(hp * (1 - ?) AS INTEGER)
            WHERE user_id = ? AND hp > 1
        ''', (decay_rate, user_id))
        
        conn.commit()
        conn.close()
    
    def count_short_term_memories(self, user_id: str) -> int:
        """统计短期记忆数量"""
        conn = sqlite3.connect(self.config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM memories WHERE user_id = ? AND hp = 1', (user_id,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def _row_to_memory_item(self, row) -> MemoryItem:
        """将数据库行转换为MemoryItem对象"""
        embedding = np.frombuffer(row[2], dtype=np.float32).tolist() if row[2] else []
        
        return MemoryItem(
            id=row[0],
            content=row[1],
            embedding=embedding,
            timestamp=datetime.fromisoformat(row[3]),
            hp=row[4],
            user_id=row[5]
        )
    
    @staticmethod
    def hash_states(states: List[Any]) -> str:
        """生成states的哈希值"""
        states_str = json.dumps([str(state) for state in states], sort_keys=True, ensure_ascii=False)
        return hashlib.md5(states_str.encode()).hexdigest() 