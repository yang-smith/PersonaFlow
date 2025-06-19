#!/usr/bin/env python3
"""
开发工具脚本
"""

import click
import asyncio
import os
import sys
import logging
from pathlib import Path

# 确保能够导入项目模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 设置简单的日志记录器，避免复杂的依赖
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
simple_logger = logging.getLogger(__name__)

from models import DatabaseManager
from background_tasks import BackgroundTaskManager
from config import settings

@click.group()
def cli():
    """PersonaFlow 开发工具"""
    pass

@cli.command()
def init_db():
    """初始化数据库"""
    try:
        db = DatabaseManager()
        simple_logger.info("数据库初始化完成")
        stats = db.get_database_stats()
        simple_logger.info(f"数据库统计: {stats}")
    except Exception as e:
        simple_logger.error(f"数据库初始化失败: {e}")

@cli.command()
def reset_db():
    """重置数据库"""
    if click.confirm('确定要重置数据库吗？这将删除所有数据！'):
        try:
            if os.path.exists(settings.DATABASE_PATH):
                os.remove(settings.DATABASE_PATH)
                simple_logger.info("数据库文件已删除")
            
            # 重新初始化
            db = DatabaseManager()
            simple_logger.info("数据库重置完成")
        except Exception as e:
            simple_logger.error(f"数据库重置失败: {e}")

@cli.command()
@click.argument('url')
@click.argument('name')
@click.option('--type', 'source_type', default='RSS', help='源类型 (RSS/WEB)')
def add_source(url, name, source_type):
    """添加RSS源"""
    try:
        db = DatabaseManager()
        source_id = db.add_source(url, name, source_type)
        if source_id:
            simple_logger.info(f"源添加成功，ID: {source_id}")
        else:
            simple_logger.warning("源已存在或添加失败")
    except Exception as e:
        simple_logger.error(f"添加源失败: {e}")

@cli.command()
def list_sources():
    """列出所有RSS源"""
    try:
        db = DatabaseManager()
        sources = db.get_all_sources()
        
        if not sources:
            click.echo("没有配置任何源")
            return
        
        click.echo("\n=== RSS/WEB 源列表 ===")
        for source in sources:
            last_fetched = source['last_fetched_at'] or '从未'
            click.echo(f"ID: {source['id']}, 名称: {source['name']}")
            click.echo(f"    URL: {source['url']}")
            click.echo(f"    类型: {source['type']}, 最后抓取: {last_fetched}")
            click.echo()
            
    except Exception as e:
        simple_logger.error(f"获取源列表失败: {e}")

@cli.command()
def stats():
    """显示数据库统计信息"""
    try:
        db = DatabaseManager()
        stats = db.get_database_stats()
        
        click.echo("\n=== PersonaFlow 数据库统计 ===")
        click.echo(f"RSS源数量: {stats['total_sources']}")
        click.echo(f"总文章数: {stats['total_articles']}")
        click.echo(f"已向量化文章: {stats['vectorized_articles']}")
        click.echo(f"已AI评分文章: {stats['scored_articles']}")
        click.echo(f"已交互文章: {stats['interacted_articles']}")
        click.echo(f"未读推荐: {stats['unread_feed']}")
        click.echo(f"用户配置: {'是' if stats['has_user_profile'] else '否'}")
        click.echo()
        
    except Exception as e:
        simple_logger.error(f"获取统计信息失败: {e}")

@cli.command()
def update_now():
    """立即执行完整的文章更新流程"""
    async def run_update():
        try:
            click.echo("开始执行完整的文章更新流程...")
            
            task_manager = BackgroundTaskManager()
            await task_manager.run_full_update_cycle()
            
            click.echo("文章更新流程完成！")
            
        except Exception as e:
            simple_logger.error(f"更新流程失败: {e}")
            click.echo(f"更新失败: {e}")
    
    # 运行异步函数
    asyncio.run(run_update())

@cli.command()
def vectorize_now():
    """立即对所有未向量化的文章进行向量化"""
    async def run_vectorize():
        try:
            click.echo("开始向量化未处理的文章...")
            
            task_manager = BackgroundTaskManager()
            count = await task_manager.vectorize_articles()
            
            click.echo(f"向量化完成，处理了 {count} 篇文章")
            
        except Exception as e:
            simple_logger.error(f"向量化失败: {e}")
            click.echo(f"向量化失败: {e}")
    
    asyncio.run(run_vectorize())

@cli.command()
def score_now():
    """立即对所有未评分的文章进行AI评分"""
    async def run_score():
        try:
            click.echo("开始AI评分未处理的文章...")
            
            task_manager = BackgroundTaskManager()
            count = await task_manager.ai_score_articles()
            
            click.echo(f"AI评分完成，处理了 {count} 篇文章")
            
        except Exception as e:
            simple_logger.error(f"AI评分失败: {e}")
            click.echo(f"AI评分失败: {e}")
    
    asyncio.run(run_score())

@cli.command()
def fetch_now():
    """立即从所有RSS源抓取最新文章"""
    async def run_fetch():
        try:
            click.echo("开始从RSS源抓取文章...")
            
            task_manager = BackgroundTaskManager()
            db = task_manager.db
            sources = db.get_all_sources()
            
            if not sources:
                click.echo("没有配置任何RSS源")
                return
            
            total_new = 0
            for source in sources:
                if source['type'] == 'RSS':
                    try:
                        articles = await task_manager.fetch_rss_articles(source)
                        new_ids = await task_manager.store_articles(source['id'], articles)
                        total_new += len(new_ids)
                        db.update_source_last_fetched(source['id'])
                        click.echo(f"从 {source['name']} 获取 {len(new_ids)} 篇新文章")
                    except Exception as e:
                        click.echo(f"抓取 {source['name']} 失败: {e}")
            
            click.echo(f"抓取完成，总共获取 {total_new} 篇新文章")
            
        except Exception as e:
            simple_logger.error(f"抓取失败: {e}")
            click.echo(f"抓取失败: {e}")
    
    asyncio.run(run_fetch())

@cli.command()
def queue_now():
    """立即计算推荐分数并更新推荐队列"""
    async def run_queue():
        try:
            click.echo("开始计算推荐分数...")
            
            task_manager = BackgroundTaskManager()
            count = await task_manager.calculate_final_scores_and_enqueue()
            
            click.echo(f"推荐计算完成，入队 {count} 篇文章")
            
        except Exception as e:
            simple_logger.error(f"推荐计算失败: {e}")
            click.echo(f"推荐计算失败: {e}")
    
    asyncio.run(run_queue())

@cli.command()
@click.option('--limit', default=10, help='显示数量限制')
def show_feed(limit):
    """显示当前推荐队列"""
    try:
        db = DatabaseManager()
        feed_items = db.get_unread_feed()
        
        if not feed_items:
            click.echo("推荐队列为空")
            return
        
        click.echo(f"\n=== 推荐队列 (前{min(limit, len(feed_items))}篇) ===")
        for i, item in enumerate(feed_items[:limit]):
            click.echo(f"{i+1}. {item['title']}")
            click.echo(f"   分数: {item['final_score']:.3f}")
            click.echo(f"   来源: {item['source_name']}")
            click.echo(f"   摘要: {item['ai_summary'][:100]}..." if item['ai_summary'] else "   摘要: 无")
            click.echo()
            
    except Exception as e:
        simple_logger.error(f"获取推荐队列失败: {e}")

@cli.command()
@click.option('--limit', default=20, help='显示数量限制')
@click.option('--min-score', type=float, help='最低分数过滤')
@click.option('--max-score', type=float, help='最高分数过滤')
@click.option('--sort-by', type=click.Choice(['score', 'date', 'title']), default='score', help='排序方式')
@click.option('--order', type=click.Choice(['asc', 'desc']), default='desc', help='排序顺序')
@click.option('--source', help='按源名称过滤')
@click.option('--show-content', is_flag=True, help='显示文章内容摘要')
def show_scores(limit, min_score, max_score, sort_by, order, source, show_content):
    """显示所有文章的AI评分"""
    try:
        # 直接使用 DatabaseManager，它会处理数据库路径
        db = DatabaseManager()
        
        import sqlite3
        
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询
            query = '''
                SELECT a.id, a.title, a.content, a.score, a.ai_summary, a.ai_rationale,
                       a.published_at, a.created_at, a.url, s.name as source_name
                FROM articles a
                LEFT JOIN source s ON a.source_id = s.id
                WHERE a.score IS NOT NULL
            '''
            params = []
            
            # 添加过滤条件
            if min_score is not None:
                query += ' AND a.score >= ?'
                params.append(min_score)
            
            if max_score is not None:
                query += ' AND a.score <= ?'
                params.append(max_score)
            
            if source:
                query += ' AND s.name LIKE ?'
                params.append(f'%{source}%')
            
            # 添加排序
            if sort_by == 'score':
                query += f' ORDER BY a.score {order.upper()}'
            elif sort_by == 'date':
                query += f' ORDER BY a.created_at {order.upper()}'
            elif sort_by == 'title':
                query += f' ORDER BY a.title {order.upper()}'
            
            # 添加限制
            query += f' LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            articles = [dict(row) for row in cursor.fetchall()]
        
        if not articles:
            click.echo("没有找到符合条件的已评分文章")
            return
        
        # 统计信息
        click.echo(f"\n=== AI评分文章列表 (显示前{len(articles)}篇) ===")
        
        if len(articles) > 0:
            scores = [a['score'] for a in articles if a['score'] is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                min_score_val = min(scores)
                max_score_val = max(scores)
                click.echo(f"统计: 平均分 {avg_score:.3f}, 最低分 {min_score_val:.3f}, 最高分 {max_score_val:.3f}")
        
        click.echo()
        
        # 显示文章列表
        for i, article in enumerate(articles, 1):
            score = article['score'] or 0
            
            # 根据分数设置颜色
            if score >= 0.8:
                score_color = 'green'
            elif score >= 0.6:
                score_color = 'yellow'
            elif score >= 0.4:
                score_color = 'cyan'
            else:
                score_color = 'red'
            
            # 修复语法错误
            score_text = f"[{score:.3f}]"
            title_text = article['title'][:80]
            click.echo(f"{i}. {click.style(score_text, fg=score_color)} {title_text}")
            
            click.echo(f"   来源: {article['source_name'] or '未知'}")
            
            if article['published_at']:
                click.echo(f"   发布: {article['published_at']}")
            
            if article['ai_summary']:
                summary = article['ai_summary'][:150] + "..." if len(article['ai_summary']) > 150 else article['ai_summary']
                click.echo(f"   摘要: {summary}")
            
            if article['ai_rationale']:
                rationale = article['ai_rationale'][:200] + "..." if len(article['ai_rationale']) > 200 else article['ai_rationale']
                click.echo(f"   理由: {rationale}")
            
            if show_content and article['content']:
                content = article['content'][:300] + "..." if len(article['content']) > 300 else article['content']
                click.echo(f"   内容: {content}")
            
            click.echo(f"   链接: {article['url']}")
            click.echo()
    
    except Exception as e:
        simple_logger.error(f"获取文章评分失败: {e}")
        click.echo(f"获取文章评分失败: {e}")

@cli.command()
def score_stats():
    """显示AI评分的统计信息"""
    try:
        # 直接使用 DatabaseManager
        db = DatabaseManager()
        
        import sqlite3
        
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本统计
            cursor.execute('SELECT COUNT(*) FROM articles WHERE score IS NOT NULL')
            total_scored = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM articles WHERE score IS NULL')
            unscored = cursor.fetchone()[0]
            
            if total_scored == 0:
                click.echo("没有已评分的文章")
                return
            
            # 分数分布统计
            cursor.execute('''
                SELECT 
                    AVG(score) as avg_score,
                    MIN(score) as min_score,
                    MAX(score) as max_score,
                    COUNT(CASE WHEN score >= 0.8 THEN 1 END) as excellent,
                    COUNT(CASE WHEN score >= 0.6 AND score < 0.8 THEN 1 END) as good,
                    COUNT(CASE WHEN score >= 0.4 AND score < 0.6 THEN 1 END) as average,
                    COUNT(CASE WHEN score < 0.4 THEN 1 END) as poor
                FROM articles 
                WHERE score IS NOT NULL
            ''')
            
            stats = cursor.fetchone()
            
            # 按来源统计
            cursor.execute('''
                SELECT s.name, COUNT(*) as count, AVG(a.score) as avg_score
                FROM articles a
                JOIN source s ON a.source_id = s.id
                WHERE a.score IS NOT NULL
                GROUP BY s.id, s.name
                ORDER BY avg_score DESC
            ''')
            
            source_stats = cursor.fetchall()
            
            # 显示统计信息
            click.echo("\n=== AI评分统计信息 ===")
            click.echo(f"已评分文章: {total_scored}")
            click.echo(f"未评分文章: {unscored}")
            click.echo(f"平均分数: {stats[0]:.3f}")
            click.echo(f"分数范围: {stats[1]:.3f} - {stats[2]:.3f}")
            click.echo()
            
            click.echo("分数分布:")
            click.echo(f"  优秀 (≥0.8): {stats[3]} 篇 ({stats[3]/total_scored*100:.1f}%)")
            click.echo(f"  良好 (0.6-0.8): {stats[4]} 篇 ({stats[4]/total_scored*100:.1f}%)")
            click.echo(f"  一般 (0.4-0.6): {stats[5]} 篇 ({stats[5]/total_scored*100:.1f}%)")
            click.echo(f"  较差 (<0.4): {stats[6]} 篇 ({stats[6]/total_scored*100:.1f}%)")
            click.echo()
            
            if source_stats:
                click.echo("按来源统计:")
                for source_name, count, avg_score in source_stats:
                    click.echo(f"  {source_name}: {count} 篇, 平均分 {avg_score:.3f}")
            
            click.echo()
    
    except Exception as e:
        simple_logger.error(f"获取评分统计失败: {e}")
        click.echo(f"获取评分统计失败: {e}")

@cli.command()
@click.argument('article_id', type=int)
def show_article(article_id):
    """显示指定文章的详细信息"""
    try:
        db = DatabaseManager()
        article = db.get_article_by_id(article_id)
        
        if not article:
            click.echo(f"文章 ID {article_id} 不存在")
            return
        
        # 获取来源信息
        sources = db.get_all_sources()
        source_name = "未知"
        for source in sources:
            if source['id'] == article['source_id']:
                source_name = source['name']
                break
        
        click.echo(f"\n=== 文章详情 (ID: {article_id}) ===")
        click.echo(f"标题: {article['title']}")
        click.echo(f"来源: {source_name}")
        click.echo(f"URL: {article['url']}")
        
        if article['published_at']:
            click.echo(f"发布时间: {article['published_at']}")
        
        click.echo(f"创建时间: {article['created_at']}")
        
        if article['score'] is not None:
            score_color = 'green' if article['score'] >= 0.6 else 'yellow' if article['score'] >= 0.4 else 'red'
            score_text = f"{article['score']:.3f}"
            click.echo(f"AI评分: {click.style(score_text, fg=score_color)}")
        else:
            click.echo("AI评分: 未评分")
        
        if article['ai_summary']:
            click.echo(f"\nAI摘要:\n{article['ai_summary']}")
        
        if article['ai_rationale']:
            click.echo(f"\n评分理由:\n{article['ai_rationale']}")
        
        click.echo(f"\n交互状态: {['未交互', '已喜欢', '已不喜欢', '已跳过'][article['interaction_status']]}")
        
        embedding_status = "已向量化" if db.get_article_embedding(article_id) else "未向量化"
        click.echo(f"向量化状态: {embedding_status}")
        
        if article['content']:
            click.echo(f"\n文章内容:\n{article['content'][:500]}{'...' if len(article['content']) > 500 else ''}")
        
        click.echo()
    
    except Exception as e:
        simple_logger.error(f"获取文章详情失败: {e}")
        click.echo(f"获取文章详情失败: {e}")

if __name__ == '__main__':
    cli() 