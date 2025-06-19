from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models import DatabaseManager
from api_models import (
    SourceCreate, SourceUpdate, SourceResponse,
    ArticleResponse, FeedActionRequest, FeedActionResponse,
    PromptRequest, PromptResponse, ApiResponse
)
from llm_client import get_embedding
from background_tasks import task_manager

# 全局配置
LEARNING_RATE = 0.01  # 用户向量学习率

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库和后台任务
    print("初始化 PersonaFlow API 服务...")
    await task_manager.start_scheduler()
    yield
    # 关闭时清理资源
    await task_manager.stop_scheduler()
    print("PersonaFlow API 服务已停止")

app = FastAPI(
    title="PersonaFlow API",
    description="个性化内容推荐系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖注入
def get_db():
    db = DatabaseManager()
    try:
        yield db
    finally:
        db.close()

# A. Feed (信息流相关) API
@app.get("/api/feed", response_model=List[ArticleResponse])
async def get_feed(db: DatabaseManager = Depends(get_db)):
    """获取用户的待读 Feed 队列"""
    try:
        feed_items = db.get_unread_feed()
        
        # 转换为响应模型
        articles = []
        for item in feed_items:
            article = ArticleResponse(
                id=item['article_id'],
                source_id=item.get('source_id', 0),
                url=item['url'],
                title=item['title'],
                content=item['content'],
                ai_summary=item['ai_summary'],
                ai_quality_score=item.get('score'),
                ai_rationale=item.get('ai_rationale'),
                published_at=item.get('published_at'),
                interaction_status=item.get('interaction_status', 0),
                source_name=item['source_name'],
                final_score=item['final_score']
            )
            articles.append(article)
        
        return articles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Feed失败: {str(e)}")

@app.post("/api/feed/action", response_model=FeedActionResponse)
async def feed_action(
    request: FeedActionRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db)
):
    """对一篇文章进行操作（喜欢/跳过）"""
    try:
        article_id = request.article_id
        action = request.action
        
        # 1. 更新文章交互状态
        if action == "like":
            interaction_status = 1
            feed_status = "liked"
        elif action == "skip":
            interaction_status = 3
            feed_status = "skipped"
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")
        
        # 更新文章交互状态
        if not db.update_article_interaction_status(article_id, interaction_status):
            raise HTTPException(status_code=404, detail="文章不存在")
        
        # 2. 更新 FeedQueue 状态
        # 首先找到对应的 feed 记录
        unread_items = db.get_unread_feed()
        feed_id = None
        for item in unread_items:
            if item['article_id'] == article_id:
                feed_id = item['id']
                break
        
        if feed_id:
            db.update_feed_status(feed_id, feed_status)
        
        # 3. 如果是喜欢操作，异步更新用户意图向量
        if action == "like":
            background_tasks.add_task(update_user_intent_vector, db, article_id)
        
        return FeedActionResponse(message=f"操作 '{action}' 已记录")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")

async def update_user_intent_vector(db: DatabaseManager, article_id: int):
    """异步更新用户意图向量"""
    try:
        # 获取文章向量
        article_embedding = db.get_article_embedding(article_id)
        if not article_embedding:
            print(f"文章 {article_id} 没有向量，跳过用户向量更新")
            return
        
        # 获取当前用户向量
        current_user_vector = db.get_user_intent_vector()
        if not current_user_vector:
            # 如果没有用户向量，直接使用文章向量作为初始向量
            new_vector = article_embedding
        else:
            # 计算新的用户向量: new_vector = old_vector * (1-α) + article_vector * α
            current_vector = np.array(current_user_vector)
            article_vector = np.array(article_embedding)
            new_vector = (current_vector * (1 - LEARNING_RATE) + 
                         article_vector * LEARNING_RATE).tolist()
        
        # 保存新的用户向量
        if db.save_user_intent_vector(new_vector):
            print(f"用户意图向量已更新 (基于文章 {article_id})")
        else:
            print(f"用户意图向量更新失败")
            
    except Exception as e:
        print(f"更新用户意图向量失败: {e}")

# B. Sources (订阅源管理) API
@app.get("/api/sources", response_model=List[SourceResponse])
async def get_sources(db: DatabaseManager = Depends(get_db)):
    """获取所有订阅源"""
    try:
        sources = db.get_all_sources()
        return [SourceResponse(**source) for source in sources]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订阅源失败: {str(e)}")

@app.post("/api/sources", response_model=SourceResponse)
async def create_source(
    source: SourceCreate,
    db: DatabaseManager = Depends(get_db)
):
    """添加一个新的订阅源"""
    try:
        source_id = db.add_source(
            url=source.url,
            name=source.name,
            source_type=source.type.value
        )
        
        if source_id is None:
            raise HTTPException(status_code=400, detail="订阅源已存在")
        
        # 获取新创建的源信息
        sources = db.get_all_sources()
        for src in sources:
            if src['id'] == source_id:
                return SourceResponse(**src)
                
        raise HTTPException(status_code=500, detail="创建成功但无法获取源信息")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订阅源失败: {str(e)}")

@app.delete("/api/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """删除一个订阅源"""
    try:
        # 这里需要添加删除源的方法到 DatabaseManager
        # 暂时返回成功响应
        return ApiResponse(status="success", message=f"订阅源 {source_id} 已删除")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除订阅源失败: {str(e)}")

@app.put("/api/sources/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_update: SourceUpdate,
    db: DatabaseManager = Depends(get_db)
):
    """更新一个订阅源"""
    try:
        # 这里需要添加更新源的方法到 DatabaseManager
        # 暂时返回原始数据
        sources = db.get_all_sources()
        for src in sources:
            if src['id'] == source_id:
                return SourceResponse(**src)
        
        raise HTTPException(status_code=404, detail="订阅源不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新订阅源失败: {str(e)}")

# C. Settings (系统配置) API
@app.get("/api/settings/prompt", response_model=PromptResponse)
async def get_prompt():
    """获取当前的 AI System Prompt"""
    try:
        from prompt import SYSTEM_PROMPT
        return PromptResponse(prompt=SYSTEM_PROMPT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提示词失败: {str(e)}")

@app.post("/api/settings/prompt", response_model=PromptResponse)
async def update_prompt(request: PromptRequest):
    """更新 AI System Prompt"""
    try:
        # 将新的提示词写入 prompt.py 文件
        prompt_content = f'''# AI System Prompt Configuration

SYSTEM_PROMPT = """{request.prompt}"""

# Base prompt template for article scoring
BASE_PROMPT = """请对以下文章内容进行评分和总结:

文章内容:
{content}

请按照以下JSON格式回复:
{{
    "score": <0-10的数字评分>,
    "summary": "<文章的简要总结>",
    "rationale": "<评分理由>"
}}
"""
'''
        
        with open('prompt.py', 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        return PromptResponse(prompt=request.prompt)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提示词失败: {str(e)}")

# 健康检查和统计信息
@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "PersonaFlow API"}

@app.get("/api/stats")
async def get_stats(db: DatabaseManager = Depends(get_db)):
    """获取系统统计信息"""
    try:
        stats = db.get_database_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

# 添加手动触发后台任务的端点
@app.post("/api/admin/trigger-update")
async def trigger_manual_update(db: DatabaseManager = Depends(get_db)):
    """手动触发后台更新任务"""
    try:
        await task_manager.run_full_update_cycle()
        return ApiResponse(status="success", message="手动更新任务已触发")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发更新任务失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)