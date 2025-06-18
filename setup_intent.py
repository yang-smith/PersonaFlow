import os
import sqlite3
import openai
import chromadb
from chromadb.config import Settings

import pickle

DB_PATH = 'db.sqlite3'
CHROMA_PATH = './chroma_db'
COLLECTION_NAME = 'articles'

# 1. 读取 my_charter.txt
with open('my_charter.txt', 'r', encoding='utf-8') as f:
    charter_text = f.read()

# 2. 获取 embedding
openai.api_key = os.environ['OPENAI_API_KEY']
response = openai.embeddings.create(
    input=charter_text,
    model='text-embedding-3-small'
)
intent_vector = response.data[0].embedding

# 3. 初始化 SQLite
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    content TEXT,
    rss_source TEXT,
    vectorized_status INTEGER DEFAULT 0,
    interacted_status INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY,
    intent_vector BLOB
)''')
# 只保留一条用户记录
c.execute('DELETE FROM user_profile WHERE id=1')
c.execute('INSERT INTO user_profile (id, intent_vector) VALUES (?, ?)', (1, pickle.dumps(intent_vector)))
conn.commit()
conn.close()

# 4. 初始化 ChromaDB
client = chromadb.Client(Settings(
    persist_directory=CHROMA_PATH
))
if COLLECTION_NAME not in [col.name for col in client.list_collections()]:
    client.create_collection(COLLECTION_NAME)
print('初始化完成！') 