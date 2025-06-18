import feedparser
import json
from datetime import datetime

def test_rss_sources():
    """测试RSS源的抓取功能"""
    
    # 读取RSS源
    try:
        with open('rss_sources.txt', 'r', encoding='utf-8') as f:
            rss_sources = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ 找不到 rss_sources.txt 文件")
        return
    
    print(f"📡 开始测试 {len(rss_sources)} 个RSS源...")
    print("=" * 50)
    
    total_articles = 0
    all_articles = []  # 存储所有文章的完整信息
    
    for i, rss_url in enumerate(rss_sources, 1):
        print(f"\n🔍 测试源 {i}: {rss_url}")
        
        try:
            # 解析RSS
            feed = feedparser.parse(rss_url)
            
            # 检查是否成功解析
            if feed.bozo:
                print(f"⚠️  RSS解析有警告: {feed.bozo_exception}")
            
            # 获取Feed信息
            feed_title = feed.feed.get('title', '未知标题')
            feed_desc = feed.feed.get('description', '无描述')
            entries_count = len(feed.entries)
            
            print(f"✅ Feed标题: {feed_title}")
            print(f"📝 Feed描述: {feed_desc[:100]}{'...' if len(feed_desc) > 100 else ''}")
            print(f"📰 文章数量: {entries_count}")
            
            total_articles += entries_count
            
            # 显示前3篇文章的详细信息（控制台预览）
            print(f"📋 前3篇文章预览:")
            for j, entry in enumerate(feed.entries[:3], 1):
                title = entry.get('title', '无标题')
                link = entry.get('link', '无链接')
                summary = entry.get('summary', '无摘要')
                published = entry.get('published', '无发布时间')
                
                print(f"  {j}. 标题: {title}")
                print(f"     链接: {link}")
                print(f"     摘要: {summary[:150]}{'...' if len(summary) > 150 else ''}")
                print(f"     发布: {published}")
                print()
            
            # 保存所有文章的完整信息
            for entry in feed.entries:
                article = {
                    'rss_source': rss_url,
                    'rss_title': feed_title,
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'content': entry.get('content', [{}])[0].get('value', '') if entry.get('content') else '',
                    'published': entry.get('published', ''),
                    'published_parsed': str(entry.get('published_parsed', '')),
                    'author': entry.get('author', ''),
                    'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
                    'id': entry.get('id', ''),
                    'guid': entry.get('guid', '')
                }
                all_articles.append(article)
            
        except Exception as e:
            print(f"❌ 抓取失败: {str(e)}")
    
    print("=" * 50)
    print(f"🎯 测试完成！总共获取到 {total_articles} 篇文章")
    
    # 保存完整测试结果到JSON文件
    test_result = {
        'test_time': datetime.now().isoformat(),
        'total_sources': len(rss_sources),
        'total_articles': total_articles,
        'sources': rss_sources,
        'articles': all_articles
    }
    
    with open('rss_test_result.json', 'w', encoding='utf-8') as f:
        json.dump(test_result, f, ensure_ascii=False, indent=2)
    
    print(f"📄 完整测试结果已保存到 rss_test_result.json")
    
    # 额外保存一个纯文本格式的文章列表，便于阅读
    with open('rss_articles.txt', 'w', encoding='utf-8') as f:
        f.write(f"RSS文章抓取结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, article in enumerate(all_articles, 1):
            f.write(f"文章 {i}:\n")
            f.write(f"来源: {article['rss_title']} ({article['rss_source']})\n")
            f.write(f"标题: {article['title']}\n")
            f.write(f"链接: {article['link']}\n")
            f.write(f"发布时间: {article['published']}\n")
            f.write(f"作者: {article['author']}\n")
            f.write(f"标签: {', '.join(article['tags'])}\n")
            f.write(f"摘要: {article['summary']}\n")
            if article['content']:
                f.write(f"正文: {article['content']}\n")
            f.write("-" * 80 + "\n\n")
    
    print(f"📝 文章内容已保存到 rss_articles.txt")
    print(f"💾 共保存了 {len(all_articles)} 篇文章的完整信息")

if __name__ == '__main__':
    test_rss_sources() 