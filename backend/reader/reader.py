import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import feedparser
import re
import aiohttp

from logger import app_logger
from utils import clean_text
from exceptions import RSSFetchException

class ArticleReader:
    """文章内容读取器"""
    
    async def fetch_article_content_via_jina(self, url: str) -> Optional[str]:
        """使用 Jina AI Reader 服务获取文章的 Markdown 内容"""
        try:
            jina_url = f"https://r.jina.ai/{url}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(jina_url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 使用正则表达式提取 Markdown Content 后面的内容
                        markdown_pattern = r'Markdown Content:\s*\n(.*)'
                        match = re.search(markdown_pattern, content, re.DOTALL)
                        
                        if match:
                            markdown_content = match.group(1).strip()
                            app_logger.debug(f"成功通过 Jina 获取文章内容: {url}")
                            return markdown_content
                        else:
                            app_logger.warning(f"无法从 Jina 响应中提取 Markdown 内容: {url}")
                            return None
                    else:
                        app_logger.warning(f"Jina 服务返回错误状态码 {response.status}: {url}")
                        return None
                        
        except Exception as e:
            app_logger.error(f"通过 Jina 获取文章内容失败 {url}: {e}")
            return None
    
    async def fetch_rss_articles(self, source: Dict, num_articles: int = 10) -> List[Dict]:
        """从RSS源获取文章"""
        articles = []

        try:
            app_logger.info(f"正在抓取RSS源: {source['name']}")

            # 使用 asyncio.wait_for 添加5秒超时限制
            feed = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, feedparser.parse, source['url']),
                timeout=10.0
            )
            
            if feed.bozo and feed.bozo_exception:
                app_logger.warning(f"RSS源 {source['name']} 解析警告: {feed.bozo_exception}")
            
            # 限制最多获取20个最新条目
            entries = feed.entries[:num_articles]
            
            for entry in entries:
                url = entry.get('link', '')
                title = entry.get('title', '')
                content = entry.get('summary', '') or entry.get('description', '')
                
                # 清理标题
                title = clean_text(title)
                
                
                # 判断RSS内容是否足够（少于200字符认为是摘要）
                if len(content) < 200:
                    app_logger.debug(f"RSS内容太少({len(content)}字符)，尝试通过Jina获取完整内容: {url}")
                    # 尝试通过 Jina 获取完整的文章内容
                    full_content = await self.fetch_article_content_via_jina(url)
                    if full_content:
                        content = full_content
                        app_logger.debug(f"成功通过Jina获取到完整内容: {title[:50]}...")
                    else:
                        app_logger.debug(f"Jina获取失败，使用RSS摘要: {title[:50]}...")
                else:
                    app_logger.debug(f"RSS内容充足({len(content)}字符)，直接使用: {title[:50]}...")
                
                # 尝试获取发布时间
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except (ValueError, TypeError):
                        pass
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        published_at = datetime(*entry.updated_parsed[:6])
                    except (ValueError, TypeError):
                        pass
                
                if url and title:
                    articles.append({
                        'url': url,
                        'title': title,
                        'content': content,
                        'published_at': published_at
                    })
                    
                # 添加延迟避免过于频繁的请求
                await asyncio.sleep(1)
                    
            app_logger.info(f"从 {source['name']} 获取到 {len(articles)} 篇文章")
            
        except Exception as e:
            app_logger.error(f"抓取RSS源 {source['name']} 失败: {e}")
            raise RSSFetchException(f"抓取RSS源失败: {e}")
            
        return articles

# 全局读取器实例
article_reader = ArticleReader()
