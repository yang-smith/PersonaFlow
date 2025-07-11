import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager

from models import DatabaseManager
from llm_client import get_embedding, ai_chat, num_tokens_from_string
from prompt import SYSTEM_PROMPT, BASE_PROMPT, GEN_HTML_PROMPT
from config import settings
from logger import app_logger
from utils import clean_text, cosine_similarity_score
from exceptions import RSSFetchException, LLMException, VectorException
from reader.reader import article_reader

class BackgroundTaskManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
    async def store_articles(self, source_id: int, articles: List[Dict]) -> List[int]:
        """存储文章到数据库，返回新添加的文章ID列表"""
        new_article_ids = []
        
        for article in articles:
            try:
                article_id = self.db.add_article(
                    source_id=source_id,
                    url=article['url'],
                    title=article['title'],
                    content=article['content'],
                    published_at=article['published_at']
                )
                
                if article_id:  # 新文章
                    new_article_ids.append(article_id)
                    app_logger.info(f"新文章入库: {article['title'][:50]}...")
            except Exception as e:
                app_logger.error(f"存储文章失败: {e}")
        
        return new_article_ids
    
    async def vectorize_articles(self) -> int:
        """向量化未处理的文章"""
        articles = self.db.get_articles_without_embedding()
        vectorized_count = 0
        
        app_logger.info(f"开始向量化 {len(articles)} 篇文章")
        
        for article in articles:
            try:
                # 组合标题和内容作为向量化文本
                text = f"{article['title']}\n{article['content'] or ''}"
                
                # 检查token数量并截断
                if num_tokens_from_string(text) > 8000:
                    title = article['title']
                    content = article['content'] or ''
                    title_tokens = num_tokens_from_string(title)
                    
                    if title_tokens > 7500:
                        text = title[:1000]
                    else:
                        available_tokens = 8000 - title_tokens - 10
                        
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
                    app_logger.debug(f"文章向量化成功: {article['title'][:50]}...")
                
                # 避免API限制
                await asyncio.sleep(0.1)
                
            except Exception as e:
                app_logger.error(f"向量化文章 {article['id']} 失败: {e}")
        
        app_logger.info(f"完成向量化 {vectorized_count} 篇文章")
        return vectorized_count
    
    async def ai_score_articles(self) -> int:
        """对文章进行AI评分"""
        # 直接查询没有AI评分的文章，确保包含新文章
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询score为NULL或者content不为空但score为NULL的文章
            cursor.execute('''
                SELECT * FROM articles 
                WHERE (score IS NULL OR score = 0) 
                AND content IS NOT NULL 
                AND content != ''
                ORDER BY created_at DESC
                LIMIT 100
            ''')
            
            articles = [dict(row) for row in cursor.fetchall()]
        
        scored_count = 0
        
        app_logger.info(f"开始AI评分 {len(articles)} 篇文章")
        
        for article in articles:
            try:
                # 构建评分请求
                content = article['content']
                if not content or len(content.strip()) < 10:
                    app_logger.warning(f"文章内容太短，跳过评分: {article['title'][:50]}...")
                    continue
                    
                message = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": BASE_PROMPT.format(content=content)}
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
                    app_logger.warning(f"无法从AI响应中提取分数或理由: {response}")
                    continue
                
                score = float(score_match.group(1)) / 10  # 转换为0-1范围
                rationale = rationale_match.group(1)
                summary = summary_match.group(1)
                
                # 保存AI评分
                if self.db.update_article_ai_score(article['id'], score):
                    scored_count += 1
                    app_logger.info(f"文章AI评分成功: {article['title'][:50]}... (分数: {score:.2f})")
                
                self.db.update_article_ai_summary(article['id'], summary)
                self.db.update_article_ai_rationale(article['id'], rationale)

                # 避免API限制
                await asyncio.sleep(1)
                
            except Exception as e:
                app_logger.error(f"AI评分文章 {article['id']} 失败: {e}")
        
        app_logger.info(f"完成AI评分 {scored_count} 篇文章")
        return scored_count
    
    async def calculate_final_scores_and_enqueue(self) -> int:
        """计算最终分数并决定是否入队"""
        # 获取用户意图向量
        user_intent_vector = self.db.get_user_intent_vector()
        if not user_intent_vector:
            app_logger.info("用户意图向量不存在，正在基于AI人设生成初始向量...")
            user_intent_vector = await self.generate_initial_user_vector()
            if not user_intent_vector:
                app_logger.warning("无法生成初始用户向量，跳过推荐计算")
                return 0
        
        # 获取已评分但未计算最终分数的文章
        import sqlite3
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
        app_logger.info(f"开始计算 {len(articles)} 篇文章的推荐分数")
        
        for article in articles:
            try:
                # 获取文章向量
                article_embedding = self.db.get_article_embedding(article['id'])
                if not article_embedding:
                    continue
                
                # 计算相似度分数
                similarity_score = cosine_similarity_score(article_embedding, user_intent_vector)
                
                # 获取AI质量分数
                ai_quality_score = article['score']
                
                # 计算最终分数
                final_score = (settings.SIMILARITY_WEIGHT * similarity_score + 
                             settings.AI_QUALITY_WEIGHT * ai_quality_score)
                
                # 判断是否达到入队阈值
                if final_score >= settings.SCORE_THRESHOLD:
                    # 进行AI排版
                    formatted_content = await self.ai_format_article(article)
                    
                    # 添加到推荐队列
                    if self.db.add_to_feed_queue(article['id'], final_score):
                        # 直接用排版后的内容覆盖原来的content
                        if formatted_content:
                            try:
                                self.db.update_article_content(article['id'], formatted_content)
                                app_logger.debug(f"文章排版内容已更新: {article['title'][:50]}...")
                            except Exception as e:
                                app_logger.warning(f"更新排版内容失败: {e}")
                        
                        enqueued_count += 1
                        app_logger.debug(f"文章入队: {article['title'][:50]}... "
                                      f"(最终分数: {final_score:.3f}, "
                                      f"相似度: {similarity_score:.3f}, "
                                      f"AI质量: {ai_quality_score:.3f})")
                
            except Exception as e:
                app_logger.error(f"计算文章 {article['id']} 最终分数失败: {e}")
        
        app_logger.info(f"完成推荐计算，入队 {enqueued_count} 篇文章")
        return enqueued_count
    
    async def generate_initial_user_vector(self):
        """基于system prompt生成初始用户意图向量"""
        try:
            embedding = get_embedding(SYSTEM_PROMPT)
            self.db.save_user_intent_vector(embedding)
            app_logger.info("基于AI人设生成了初始用户意图向量")
            return embedding
        except Exception as e:
            app_logger.error(f"生成初始用户向量失败: {e}")
            return None
    
    async def run_full_update_cycle(self):
        """执行完整的更新周期"""
        app_logger.info(f"=== 开始后台任务周期 {datetime.now()} ===")
        
        try:
            # 1. 抓取文章
            app_logger.info("1. 开始抓取RSS文章...")
            sources = self.db.get_all_sources()
            
            if not sources:
                app_logger.warning("没有配置RSS源")
                return
            
            total_new_articles = 0
            for source in sources:
                if source['type'] == 'RSS':
                    try:
                        # 使用reader抓取文章
                        articles = await article_reader.fetch_rss_articles(source=source, num_articles=10)
                        
                        # 存储文章
                        new_article_ids = await self.store_articles(source['id'], articles)
                        total_new_articles += len(new_article_ids)
                        
                        # 更新源的最后抓取时间
                        self.db.update_source_last_fetched(source['id'])
                        
                    except Exception as e:
                        app_logger.error(f"处理源 {source['name']} 失败: {e}")
            
            app_logger.info(f"本次抓取到 {total_new_articles} 篇新文章")
            
            # 2. AI评分（优先进行，用于过滤低质量文章）
            app_logger.info("2. 开始AI评分...")
            scored_count = await self.ai_score_articles()
            
            # 3. 向量化（只处理评分≥0.2的文章）
            app_logger.info("3. 开始向量化高质量文章...")
            vectorized_count = await self.vectorize_high_quality_articles()
            
            # 4. 计算最终分数并入队
            app_logger.info("4. 开始计算推荐分数...")
            enqueued_count = await self.calculate_final_scores_and_enqueue()
            
            # 5. 打印统计信息
            stats = self.db.get_database_stats()
            app_logger.info(f"数据库统计: {stats}")
            
            app_logger.info(f"本次任务完成 - 新文章: {total_new_articles}, "
                          f"评分: {scored_count}, 向量化: {vectorized_count}, "
                          f"入队: {enqueued_count}")
            
        except Exception as e:
            app_logger.error(f"后台任务执行失败: {e}")
        
        app_logger.info(f"=== 后台任务周期完成 {datetime.now()} ===")
    
    async def start_scheduler(self):
        """启动定时任务调度器"""
        if self.is_running:
            app_logger.warning("后台任务调度器已在运行")
            return
        
        # 添加定时任务
        self.scheduler.add_job(
            self.run_full_update_cycle,
            IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
            id='full_update_cycle',
            name='完整更新周期',
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        self.is_running = True
        
        app_logger.info(f"后台任务调度器已启动，每 {settings.FETCH_INTERVAL_HOURS} 小时执行一次")
        
        # 立即执行一次
        await self.run_full_update_cycle()
    
    async def stop_scheduler(self):
        """停止定时任务调度器"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        app_logger.info("后台任务调度器已停止")

    async def vectorize_high_quality_articles(self) -> int:
        """向量化高质量文章（AI评分≥0.3的文章）"""
        # 获取AI评分≥0.2且未向量化的文章
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM articles 
                WHERE score >= 0.3 
                AND embedding IS NULL
                ORDER BY created_at DESC
            ''')
            
            articles = [dict(row) for row in cursor.fetchall()]
        
        vectorized_count = 0
        
        app_logger.info(f"开始向量化 {len(articles)} 篇高质量文章（评分≥0.2）")
        
        for article in articles:
            try:
                # 组合标题和内容作为向量化文本
                text = f"{article['title']}\n{article['content'] or ''}"
                
                # 检查token数量并截断
                if num_tokens_from_string(text) > 8000:
                    title = article['title']
                    content = article['content'] or ''
                    title_tokens = num_tokens_from_string(title)
                    
                    if title_tokens > 7500:
                        text = title[:1000]
                    else:
                        available_tokens = 8000 - title_tokens - 10
                        
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
                    app_logger.debug(f"高质量文章向量化成功: {article['title'][:50]}... (评分: {article['score']:.2f})")
                
                # 避免API限制
                await asyncio.sleep(0.1)
                
            except Exception as e:
                app_logger.error(f"向量化文章 {article['id']} 失败: {e}")
        
        app_logger.info(f"完成向量化 {vectorized_count} 篇高质量文章")
        return vectorized_count

    async def ai_format_article(self, article: Dict) -> Optional[str]:
        """使用AI对文章进行排版美化"""
        try:
            content = article['content']
            if not content or len(content.strip()) < 50:
                app_logger.warning(f"文章内容太短，跳过排版: {article['title'][:50]}...")
                return None
            
            # 构建排版请求
            message = [
                {"role": "user", "content": GEN_HTML_PROMPT.format(content=content)}
            ]
            
            # 调用AI排版
            formatted_content = ai_chat(message, model="google/gemini-2.5-flash-lite-preview-06-17")
            
            # 简单验证生成的HTML
            if formatted_content and len(formatted_content) > 100:
                app_logger.debug(f"文章排版成功: {article['title'][:50]}...")
                return formatted_content
            else:
                app_logger.warning(f"AI排版返回内容异常: {article['title'][:50]}...")
                return None
                
        except Exception as e:
            app_logger.error(f"AI排版文章 {article['id']} 失败: {e}")
            return None

# 全局任务管理器实例
task_manager = BackgroundTaskManager()

@asynccontextmanager
async def background_task_lifespan():
    """FastAPI应用生命周期管理"""
    # 启动时启动后台任务
    await task_manager.start_scheduler()
    yield
    # 关闭时停止后台任务
    await task_manager.stop_scheduler() 