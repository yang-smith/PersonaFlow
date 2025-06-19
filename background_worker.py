import os
import time
import feedparser
import numpy as np
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from typing import List, Dict, Any, Optional
import json
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
import re

from models import DatabaseManager
from llm_client import get_embedding, ai_chat, num_tokens_from_string
from prompt import SYSTEM_PROMPT, BASE_PROMPT

# 配置
SCORE_THRESHOLD = 0.7  # 入队阈值
WEIGHT_SIMILARITY = 0.5  # 相似度权重
WEIGHT_AI_QUALITY = 0.5  # AI质量权重

class BackgroundWorker:
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_rss_sources_from_db(self) -> List[Dict]:
        """从数据库获取RSS源"""
        return self.db.get_all_sources()
    
    def fetch_rss_articles(self, source: Dict) -> List[Dict]:
        """从RSS源获取文章"""
        articles = []
        try:
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries:
                url = entry.get('link', '')
                title = entry.get('title', '')
                content = entry.get('summary', '') or entry.get('description', '')
                
                # 尝试获取发布时间
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6])
                
                if url and title:
                    articles.append({
                        'url': url,
                        'title': title,
                        'content': content,
                        'published_at': published_at
                    })
                    
            print(f"从 {source['name']} 获取到 {len(articles)} 篇文章")
            
        except Exception as e:
            print(f"抓取RSS源 {source['name']} 失败: {e}")
            
        return articles
    
    def store_articles(self, source_id: int, articles: List[Dict]) -> List[int]:
        """存储文章到数据库，返回新添加的文章ID列表"""
        new_article_ids = []
        
        for article in articles:
            article_id = self.db.add_article(
                source_id=source_id,
                url=article['url'],
                title=article['title'],
                content=article['content'],
                published_at=article['published_at']
            )
            
            if article_id:  # 新文章
                new_article_ids.append(article_id)
                print(f"新文章入库: {article['title'][:50]}...")
        
        return new_article_ids
    
    def vectorize_articles(self) -> int:
        """向量化未处理的文章"""
        articles = self.db.get_articles_without_embedding()
        vectorized_count = 0
        
        for article in articles:
            try:
                # 组合标题和内容作为向量化文本
                text = f"{article['title']}\n{article['content'] or ''}"
                
                # 检查token数量并截断
                if num_tokens_from_string(text) > 8000:  # 留192个tokens的安全余量
                    title = article['title']
                    content = article['content'] or ''
                    title_tokens = num_tokens_from_string(title)
                    
                    # 确保标题token数不超过限制
                    if title_tokens > 7500:  # 如果标题本身就很长
                        # 这种情况很少见，但需要处理
                        text = title[:1000]  # 强制截断标题
                    else:
                        # 计算内容可用的token数
                        available_tokens = 8000 - title_tokens - 10  # 留10个tokens余量
                        
                        # 使用二分法精确截断内容
                        left, right = 0, len(content)
                        while left < right:
                            mid = (left + right + 1) // 2
                            test_text = f"{title}\n{content[:mid]}"
                            if num_tokens_from_string(test_text) <= 8000:
                                left = mid
                            else:
                                right = mid - 1
                        
                        text = f"{title}\n{content[:left]}"
                    
                
                # 获取向量
                embedding = get_embedding(text)
                
                # 保存向量
                if self.db.update_article_embedding(article['id'], embedding):
                    vectorized_count += 1
                    print(f"文章向量化成功: {article['title'][:50]}...")
                
                # 避免API限制，添加延迟
                time.sleep(0.1)
                
            except Exception as e:
                print(f"向量化文章 {article['id']} 失败: {e}")
        
        return vectorized_count
    
    def ai_score_articles(self) -> int:
        """对文章进行AI评分"""
        articles = self.db.get_articles_without_ai_score()
        scored_count = 0
        
        for article in articles:
            try:
                # 构建评分请求
                message = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": BASE_PROMPT.format(content=article['content'])}
                ]
                
                # 调用AI评分
                response = ai_chat(message, model="google/gemini-2.5-flash-lite-preview-06-17")
                
                # 使用正则表达式提取分数和理由
                score_pattern = r'"score":\s*([0-9.]+)'
                rationale_pattern = r'"rationale":\s*"([^"]*)"'
                summary_pattern = r'"summary":\s*"([^"]*)"'
                
                score_match = re.search(score_pattern, response)
                rationale_match = re.search(rationale_pattern, response)
                summary_match = re.search(summary_pattern, response)
                
                if not score_match or not rationale_match or not summary_match:
                    logger.warning(f"无法从AI响应中提取分数或理由: {response}")
                    return None
                
                score = float(score_match.group(1))
                score = score/10
                rationale = rationale_match.group(1)
                summary = summary_match.group(1)
                
                # 保存AI评分
                if self.db.update_article_ai_score(article['id'], score):
                    scored_count += 1
                    print(f"文章AI评分成功: {article['title'][:50]}... (分数: {score:.2f})")
                self.db.update_article_ai_summary(article['id'], summary)
                self.db.update_article_ai_rationale(article['id'], rationale)

                # 避免API限制
                time.sleep(1)
                
            except Exception as e:
                print(f"AI评分文章 {article['id']} 失败: {e}")
        
        return scored_count
    
    def calculate_similarity_score(self, article_embedding: List[float], 
                                 user_intent_vector: List[float]) -> float:
        """计算文章与用户意图的相似度"""
        try:
            # 转换为numpy数组并重塑为2D数组
            article_vec = np.array(article_embedding).reshape(1, -1)
            user_vec = np.array(user_intent_vector).reshape(1, -1)
            
            # 计算余弦相似度
            similarity = cosine_similarity(article_vec, user_vec)[0][0]
            
            # sklearn的cosine_similarity返回值在[-1,1]范围内，转换到[0,1]
            return (similarity + 1) / 2
            
        except Exception as e:
            print(f"计算相似度失败: {e}")
            return 0
    
    def generate_initial_user_vector(self):
        """基于system prompt生成初始用户意图向量"""
        try:
            from prompt import SYSTEM_PROMPT
            # 将system prompt向量化作为初始用户偏好
            embedding = get_embedding(SYSTEM_PROMPT)
            self.db.save_user_intent_vector(embedding)
            print("基于AI人设生成了初始用户意图向量")
            return embedding
        except Exception as e:
            print(f"生成初始用户向量失败: {e}")
            return None
    
    def calculate_final_scores_and_enqueue(self) -> int:
        """计算最终分数并决定是否入队"""
        # 获取用户意图向量
        user_intent_vector = self.db.get_user_intent_vector()
        if not user_intent_vector:
            print("用户意图向量不存在，正在基于AI人设生成初始向量...")
            user_intent_vector = self.generate_initial_user_vector()
            if not user_intent_vector:
                print("无法生成初始用户向量，跳过推荐计算")
                return 0
        
        # 获取已评分但未计算最终分数的文章
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.* FROM articles a
                WHERE a.score IS NOT NULL 
                AND a.embedding IS NOT NULL
                AND a.id NOT IN (SELECT article_id FROM feed)
                ORDER BY a.created_at DESC
                LIMIT 100
            ''')
            
            articles = [dict(row) for row in cursor.fetchall()]
        
        enqueued_count = 0
        
        for article in articles:
            try:
                # 获取文章向量
                article_embedding = self.db.get_article_embedding(article['id'])
                if not article_embedding:
                    continue
                
                # 计算相似度分数
                similarity_score = self.calculate_similarity_score(
                    article_embedding, user_intent_vector
                )
                
                # 获取AI质量分数
                ai_quality_score = article['score']
                
                # 计算最终分数
                final_score = (WEIGHT_SIMILARITY * similarity_score + 
                             WEIGHT_AI_QUALITY * ai_quality_score)
                
                # 判断是否达到入队阈值
                if final_score >= SCORE_THRESHOLD:
                    # 添加到推荐队列
                    if self.db.add_to_feed_queue(article['id'], final_score):
                        enqueued_count += 1
                        print(f"文章入队: {article['title'][:50]}... "
                              f"(最终分数: {final_score:.3f}, "
                              f"相似度: {similarity_score:.3f}, "
                              f"AI质量: {ai_quality_score:.3f})")
                
            except Exception as e:
                print(f"计算文章 {article['id']} 最终分数失败: {e}")
        
        return enqueued_count
    
    def run_fetch_and_process(self):
        """执行完整的抓取和处理流程"""
        print(f"\n=== 开始后台任务 {datetime.now()} ===")
        
        try:
            # 1. 抓取 & 向量化
            print("1. 开始抓取RSS文章...")
            sources = self.load_rss_sources_from_db()
            
            if not sources:
                print("没有配置RSS源")
                return
            
            total_new_articles = 0
            for source in sources:
                if source['type'] == 'RSS':
                    # 抓取文章
                    articles = self.fetch_rss_articles(source)
                    
                    # 存储文章
                    new_article_ids = self.store_articles(source['id'], articles)
                    total_new_articles += len(new_article_ids)
                    
                    # 更新源的最后抓取时间
                    self.db.update_source_last_fetched(source['id'])
            
            print(f"本次抓取到 {total_new_articles} 篇新文章")
            
            # 2. 向量化
            print("2. 开始向量化文章...")
            vectorized_count = self.vectorize_articles()
            print(f"本次向量化 {vectorized_count} 篇文章")
            
            # 3. AI评分
            print("3. 开始AI评分...")
            scored_count = self.ai_score_articles()
            print(f"本次AI评分 {scored_count} 篇文章")
            
            # 4. 计算最终分数并入队
            print("4. 开始计算推荐分数...")
            enqueued_count = self.calculate_final_scores_and_enqueue()
            print(f"本次入队 {enqueued_count} 篇文章")
            
            # 5. 打印统计信息
            stats = self.db.get_database_stats()
            print(f"\n数据库统计: {stats}")
            
        except Exception as e:
            print(f"后台任务执行失败: {e}")
        
        print(f"=== 后台任务完成 {datetime.now()} ===\n")

def main():
    """主函数"""
    worker = BackgroundWorker()
    
    # 创建调度器
    scheduler = BlockingScheduler()
    
    # 添加定时任务 - 每12小时执行一次
    scheduler.add_job(
        worker.run_fetch_and_process, 
        'interval', 
        hours=12,
        next_run_time=datetime.now()  # 立即执行一次
    )
    
    print('PersonaFlow 后台任务已启动，每12小时执行一次。按Ctrl+C退出。')
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print('\n后台任务已停止。')

if __name__ == '__main__':
    main() 