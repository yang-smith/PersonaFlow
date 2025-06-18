"""AI辅助信息筛选主程序"""

import asyncio
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import re

from reader.reader import read_url, ReaderError
from llm_client import ai_chat
from prompt import SYSTEM_PROMPT, BASE_PROMPT


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('content_filter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ContentFilter:
    """内容筛选器主类"""
    
    def __init__(
        self,
        sources_file: str = "rss_sources.txt",
        output_file: str = "filtered_content.json",
        min_score: float = 6.0,
        model: str = "google/gemini-2.5-flash-lite-preview-06-17",
    ):
        """初始化内容筛选器
        
        Args:
            sources_file: RSS源文件路径
            output_file: 输出文件路径
            min_score: 最低分数阈值
            model: AI模型名称
        """
        self.sources_file = sources_file
        self.output_file = output_file
        self.min_score = min_score
        self.model = model
        
    def load_sources(self) -> List[str]:
        """从文件加载RSS源"""
        try:
            with open(self.sources_file, 'r', encoding='utf-8') as f:
                sources = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"加载了 {len(sources)} 个RSS源")
            return sources
        except FileNotFoundError:
            logger.error(f"RSS源文件 {self.sources_file} 不存在")
            return []
        except Exception as e:
            logger.error(f"加载RSS源时出错: {e}")
            return []
    
    async def fetch_rss_content(self, url: str) -> Optional[Dict]:
        """获取RSS内容"""
        try:
            logger.info(f"正在获取RSS内容: {url}")
            result = await read_url(url, format_output=False)
            
            if result['type'] != 'rss_feed':
                logger.warning(f"URL {url} 不是RSS feed")
                return None
                
            logger.info(f"成功获取RSS: {result['title']}, 文章数: {result['processed_entries']}")
            return result
            
        except ReaderError as e:
            logger.error(f"获取RSS内容失败 {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"处理RSS时发生意外错误 {url}: {e}")
            return None
    
    def score_article(self, article: Dict) -> Optional[Dict]:
        """为单篇文章评分"""
        try:
            # 准备文章内容用于评分
            content_for_scoring = article['content']
            # 构建完整的提示
            full_prompt = BASE_PROMPT.format(content=content_for_scoring)
            message = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ]

            # 调用AI进行评分
            response = ai_chat(
                message=message,
                model=self.model,
            )
            
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
            
            try:
                score = float(score_match.group(1))
                rationale = rationale_match.group(1)
                summary = summary_match.group(1)
            except (ValueError, IndexError) as e:
                logger.error(f"解析提取的分数或理由失败: {e}")
                return None
            
            # 添加评分信息到文章
            scored_article = article.copy()
            scored_article['ai_score'] = score
            scored_article['ai_rationale'] = rationale
            scored_article['ai_summary'] = summary
            scored_article['scored_at'] = datetime.now().isoformat()
            
            logger.info(f"文章评分完成: {scored_article['title'][:50]}... - 分数: {scored_article['ai_score']}")
            return scored_article
            
        except Exception as e:
            logger.error(f"评分文章时出错: {e}")
            return None

    
    async def process_rss_feed(self, url: str) -> List[Dict]:
        """处理单个RSS源"""
        rss_content = await self.fetch_rss_content(url)
        if not rss_content:
            return []
        
        scored_articles = []
        for article in rss_content['articles']:
            try:
                scored_article = self.score_article(article)
                if scored_article:
                    scored_articles.append(scored_article)
            except Exception as e:
                logger.error(f"处理文章时出错 '{article.get('title', 'N/A')}': {e}")
        
        # 添加RSS源信息
        for article in scored_articles:
            article['source_url'] = url
            article['source_title'] = rss_content['title']
        
        return scored_articles
    
    def filter_by_score(self, articles: List[Dict]) -> List[Dict]:
        """根据分数筛选文章"""
        filtered = [article for article in articles if article.get('ai_score', 0) >= self.min_score]
        logger.info(f"筛选后的文章数: {len(filtered)} / {len(articles)}")
        return filtered
    
    def save_results(self, articles: List[Dict]) -> None:
        """保存结果到文件"""
        try:
            # 按分数降序排序
            sorted_articles = sorted(articles, key=lambda x: x.get('ai_score', 0), reverse=True)
            
            result = {
                'filtered_at': datetime.now().isoformat(),
                'total_articles': len(sorted_articles),
                'min_score_threshold': self.min_score,
                'articles': sorted_articles
            }
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到 {self.output_file}")
            
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
    
    def print_summary(self, articles: List[Dict]) -> None:
        """打印筛选摘要"""
        if not articles:
            print("没有找到符合条件的文章")
            return
        
        print(f"\n=== 筛选摘要 ===")
        print(f"共找到 {len(articles)} 篇高质量文章 (分数 >= {self.min_score})")
        print(f"最高分: {max(article.get('ai_score', 0) for article in articles):.1f}")
        print(f"平均分: {sum(article.get('ai_score', 0) for article in articles) / len(articles):.1f}")
        
        print(f"\n=== Top 5 文章 ===")
        for i, article in enumerate(sorted(articles, key=lambda x: x.get('ai_score', 0), reverse=True)[:5], 1):
            print(f"{i}. [{article.get('ai_score', 0):.1f}] {article.get('title', 'Unknown Title')}")
            print(f"   来源: {article.get('source_title', 'Unknown Source')}")
            print(f"   理由: {article.get('ai_rationale', 'No rationale')}")
            print()
    
    async def run(self) -> None:
        """运行主程序"""
        logger.info("开始运行内容筛选程序")
        
        # 加载RSS源
        sources = self.load_sources()
        if not sources:
            logger.error("没有可用的RSS源")
            return
        
        # 处理所有RSS源
        all_articles = []
        for url in sources:
            articles = await self.process_rss_feed(url)
            all_articles.extend(articles)
        
        logger.info(f"总共处理了 {len(all_articles)} 篇文章")
        
        # 筛选高质量文章
        filtered_articles = self.filter_by_score(all_articles)
        
        # 保存结果
        self.save_results(filtered_articles)
        
        # 打印摘要
        self.print_summary(filtered_articles)
        
        logger.info("程序运行完成")


async def main():
    """主函数"""
    # 创建内容筛选器实例
    filter_instance = ContentFilter(
        sources_file="rss_sources.txt",
        output_file="filtered_content.json",
        min_score=6.0,  # 只保留6分以上的文章
        model="google/gemini-2.5-flash-lite-preview-06-17",
    )
    
    # 运行筛选程序
    await filter_instance.run()


if __name__ == "__main__":
    asyncio.run(main()) 