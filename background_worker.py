import os
import sqlite3
import openai
import feedparser
import chromadb
from chromadb.config import Settings
from apscheduler.schedulers.blocking import BlockingScheduler
import pickle

DB_PATH = 'db.sqlite3'
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'articles'

openai.api_key = os.environ['OPENAI_API_KEY']

# 读取RSS源
def load_rss_sources():
    with open('rss_sources.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def fetch_and_store():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rss_sources = load_rss_sources()
    for rss_url in rss_sources:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            url = entry.get('link', '')
            title = entry.get('title', '')
            content = entry.get('summary', '')
            # 入库（去重）
            c.execute('SELECT 1 FROM articles WHERE url=?', (url,))
            if c.fetchone() is None:
                c.execute('INSERT INTO articles (url, title, content, rss_source) VALUES (?, ?, ?, ?)',
                          (url, title, content, rss_url))
    conn.commit()
    # 向量化未处理的文章
    c.execute('SELECT id, title, content FROM articles WHERE vectorized_status=0')
    rows = c.fetchall()
    if rows:
        client = chromadb.Client(Settings(persist_directory=CHROMA_PATH))
        collection = client.get_collection(COLLECTION_NAME)
        for row in rows:
            article_id, title, content = row
            text = (title or '') + '\n' + (content or '')
            response = openai.embeddings.create(
                input=text,
                model='text-embedding-3-small'
            )
            vector = response.data[0].embedding
            # 存入ChromaDB
            collection.add(
                embeddings=[vector],
                ids=[str(article_id)],
                metadatas=[{"title": title}]
            )
            # 更新vectorized_status
            c.execute('UPDATE articles SET vectorized_status=1 WHERE id=?', (article_id,))
        conn.commit()
    conn.close()

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(fetch_and_store, 'interval', hours=1)
    print('后台抓取任务已启动，每小时执行一次。按Ctrl+C退出。')
    fetch_and_store()  # 启动时先执行一次
    scheduler.start() 