import sqlite3
import json
import numpy as np
from typing import List, Optional, Tuple
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path: str = 'personaflow.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库，创建表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建 source 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS source (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL DEFAULT 'RSS',
                    name TEXT NOT NULL,
                    last_fetched_at DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建 articles 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    ai_summary TEXT,
                    score FLOAT,
                    ai_rationale TEXT,
                    published_at DATETIME,
                    interaction_status INTEGER DEFAULT 0,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES source(id)
                )
            ''')
            
            # 创建 user 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建 feed 表（队列）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    article_id INTEGER NOT NULL,
                    final_score FLOAT NOT NULL,
                    status TEXT DEFAULT 'unread',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(id),
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_interaction_status ON articles(interaction_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_status ON feed(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_article_id ON feed(article_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON source(url)')
            
            conn.commit()
    
    # Source 相关方法
    def add_source(self, url: str, name: str, source_type: str = 'RSS') -> Optional[int]:
        """添加新的RSS源或URL源"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO source (url, name, type)
                    VALUES (?, ?, ?)
                ''', (url, name, source_type))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # URL已存在
            return None
        except Exception as e:
            print(f"添加源失败: {e}")
            return None
    
    def get_all_sources(self) -> List[dict]:
        """获取所有源"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM source ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_source_last_fetched(self, source_id: int) -> bool:
        """更新源的最后抓取时间"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE source 
                    SET last_fetched_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (source_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新源抓取时间失败: {e}")
            return False
    
    # Articles 相关方法
    def add_article(self, source_id: int, url: str, title: str, content: str = None, 
                   published_at: datetime = None) -> Optional[int]:
        """添加新文章，返回文章ID，如果URL已存在则返回None"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO articles (source_id, url, title, content, published_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (source_id, url, title, content, published_at))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # URL已存在
            return None
        except Exception as e:
            print(f"添加文章失败: {e}")
            return None
    
    def get_article_by_id(self, article_id: int) -> Optional[dict]:
        """根据ID获取文章"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_articles_without_embedding(self) -> List[dict]:
        """获取还未向量化的文章"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE embedding IS NULL ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_articles_without_ai_score(self) -> List[dict]:
        """获取还未AI评分的文章"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE score IS NULL AND embedding IS NOT NULL ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_article_embedding(self, article_id: int, embedding: List[float]) -> bool:
        """更新文章的向量"""
        try:
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET embedding = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (embedding_bytes, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文章向量失败: {e}")
            return False
    
    def update_article_ai_score(self, article_id: int, score: float, summary: str = None, 
                               rationale: str = None) -> bool:
        """更新文章的AI评分和相关信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET score = ?, ai_summary = ?, ai_rationale = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (score, summary, rationale, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文章AI评分失败: {e}")
            return False
    
    def update_article_ai_summary(self, article_id: int, summary: str) -> bool:
        """更新文章的AI总结"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET ai_summary = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (summary, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文章AI总结失败: {e}")
            return False

    def update_article_ai_rationale(self, article_id: int, rationale: str) -> bool:
        """更新文章的AI理由"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET ai_rationale = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (rationale, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文章AI理由失败: {e}")
            return False

    def update_article_interaction_status(self, article_id: int, status: int) -> bool:
        """更新文章交互状态 (0=未交互, 1=已喜欢, 2=已不喜欢, 3=已跳过)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET interaction_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新文章交互状态失败: {e}")
            return False
    
    def get_article_embedding(self, article_id: int) -> Optional[List[float]]:
        """获取文章的向量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT embedding FROM articles WHERE id = ?', (article_id,))
                row = cursor.fetchone()
                
                if row and row[0]:
                    vector_array = np.frombuffer(row[0], dtype=np.float32)
                    return vector_array.tolist()
                return None
        except Exception as e:
            print(f"获取文章向量失败: {e}")
            return None
    
    # User 相关方法
    def save_user_intent_vector(self, vector: List[float]) -> bool:
        """保存用户意图向量"""
        try:
            vector_bytes = np.array(vector, dtype=np.float32).tobytes()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user (id, embedding, updated_at)
                    VALUES (1, ?, CURRENT_TIMESTAMP)
                ''', (vector_bytes,))
                conn.commit()
                return True
        except Exception as e:
            print(f"保存用户向量失败: {e}")
            return False
    
    def get_user_intent_vector(self) -> Optional[List[float]]:
        """获取用户意图向量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT embedding FROM user WHERE id = 1')
                row = cursor.fetchone()
                
                if row and row[0]:
                    vector_array = np.frombuffer(row[0], dtype=np.float32)
                    return vector_array.tolist()
                return None
        except Exception as e:
            print(f"获取用户向量失败: {e}")
            return None
    
    # Feed 队列相关方法
    def add_to_feed_queue(self, article_id: int, final_score: float, user_id: int = 1) -> Optional[int]:
        """将文章添加到用户的推荐队列"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO feed (user_id, article_id, final_score)
                    VALUES (?, ?, ?)
                ''', (user_id, article_id, final_score))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"添加到推荐队列失败: {e}")
            return None
    
    def get_unread_feed(self, user_id: int = 1) -> List[dict]:
        """获取用户未读的推荐文章列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.*, a.title, a.content, a.ai_summary, a.url, s.name as source_name
                FROM feed f
                JOIN articles a ON f.article_id = a.id
                JOIN source s ON a.source_id = s.id
                WHERE f.user_id = ? AND f.status = 'unread'
                ORDER BY f.final_score DESC, f.created_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_feed_status(self, feed_id: int, status: str) -> bool:
        """更新推荐队列中文章的状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE feed 
                    SET status = ?
                    WHERE id = ?
                ''', (status, feed_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新推荐队列状态失败: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 源数量
            cursor.execute('SELECT COUNT(*) FROM source')
            total_sources = cursor.fetchone()[0]
            
            # 总文章数
            cursor.execute('SELECT COUNT(*) FROM articles')
            total_articles = cursor.fetchone()[0]
            
            # 已向量化文章数
            cursor.execute('SELECT COUNT(*) FROM articles WHERE embedding IS NOT NULL')
            vectorized_articles = cursor.fetchone()[0]
            
            # 已AI评分文章数
            cursor.execute('SELECT COUNT(*) FROM articles WHERE score IS NOT NULL')
            scored_articles = cursor.fetchone()[0]
            
            # 已交互文章数
            cursor.execute('SELECT COUNT(*) FROM articles WHERE interaction_status > 0')
            interacted_articles = cursor.fetchone()[0]
            
            # 推荐队列中未读文章数
            cursor.execute('SELECT COUNT(*) FROM feed WHERE status = "unread"')
            unread_feed = cursor.fetchone()[0]
            
            # 用户配置是否存在
            cursor.execute('SELECT COUNT(*) FROM user WHERE id = 1')
            has_user_profile = cursor.fetchone()[0] > 0
            
            return {
                'total_sources': total_sources,
                'total_articles': total_articles,
                'vectorized_articles': vectorized_articles,
                'scored_articles': scored_articles,
                'interacted_articles': interacted_articles,
                'unread_feed': unread_feed,
                'has_user_profile': has_user_profile
            }
    
    def close(self):
        """关闭数据库连接"""
        pass

    def delete_source(self, source_id: int) -> bool:
        """删除订阅源"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 先删除相关文章
                cursor.execute('DELETE FROM articles WHERE source_id = ?', (source_id,))
                # 删除源
                cursor.execute('DELETE FROM source WHERE id = ?', (source_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"删除源失败: {e}")
            return False

    def update_source(self, source_id: int, name: str = None, source_type: str = None) -> bool:
        """更新订阅源信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if source_type is not None:
                    updates.append("type = ?")
                    params.append(source_type)
                
                if not updates:
                    return True  # 没有更新内容
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(source_id)
                
                query = f"UPDATE source SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新源失败: {e}")
            return False

    def get_feed_item_by_article_id(self, article_id: int, user_id: int = 1) -> Optional[dict]:
        """根据文章ID获取feed队列项"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM feed 
                WHERE article_id = ? AND user_id = ?
            ''', (article_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_feed_status_by_article_id(self, article_id: int, status: str, user_id: int = 1) -> bool:
        """根据文章ID更新feed状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE feed 
                    SET status = ?
                    WHERE article_id = ? AND user_id = ?
                ''', (status, article_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新feed状态失败: {e}")
            return False

# 使用示例
if __name__ == "__main__":
    # 创建数据库管理器
    db = DatabaseManager()
    
    # 添加测试源
    source_id = db.add_source(
        url="https://example.com/rss",
        name="测试RSS源",
        source_type="RSS"
    )
    
    if source_id:
        print(f"源添加成功，ID: {source_id}")
        
        # 添加测试文章
        article_id = db.add_article(
            source_id=source_id,
            url="https://example.com/article1",
            title="测试文章标题",
            content="这是一篇测试文章的内容...",
            published_at=datetime.now()
        )
        
        if article_id:
            print(f"文章添加成功，ID: {article_id}")
            
            # 获取统计信息
            stats = db.get_database_stats()
            print("数据库统计:", stats) 