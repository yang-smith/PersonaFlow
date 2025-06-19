import json
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import os
import sqlite3  
import time

from models import DatabaseManager
from llm_client import ai_chat, get_embedding
import numpy as np


# 配置
MIN_DISPLAY_SCORE = 0.7

# 初始化数据库
@st.cache_resource
def get_db():
    return DatabaseManager()

def init_session_state():
    """初始化session state"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'feed'
    if 'user_feedback' not in st.session_state:
        st.session_state.user_feedback = []
    if 'current_article_index' not in st.session_state:
        st.session_state.current_article_index = 0
    if 'articles_list' not in st.session_state:
        st.session_state.articles_list = []
    if 'reading_mode' not in st.session_state:
        st.session_state.reading_mode = False

def load_filtered_content() -> Optional[Dict]:
    """加载筛选后的内容"""
    try:
        if not os.path.exists(FILTERED_CONTENT_FILE):
            return None
        
        with open(FILTERED_CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载内容失败: {e}")
        return None

def format_datetime(dt_string: str) -> str:
    """格式化时间显示"""
    if not dt_string:
        return "未知时间"
    
    try:
        if 'T' in dt_string:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%m-%d %H:%M')
    except:
        return str(dt_string)

def get_score_indicator(score: float) -> str:
    """根据分数返回指示器"""
    if score >= 0.9:
        return "🔥"
    elif score >= 0.8:
        return "⭐"
    elif score >= 0.7:
        return "👍"
    else:
        return "📄"

def update_user_intent_vector(liked_articles: List[int], disliked_articles: List[int]):
    """更新用户意图向量"""
    db = get_db()
    
    # 获取喜欢和不喜欢文章的向量
    liked_vectors = []
    disliked_vectors = []
    
    for article_id in liked_articles:
        embedding = db.get_article_embedding(article_id)
        if embedding:
            liked_vectors.append(embedding)
    
    for article_id in disliked_articles:
        embedding = db.get_article_embedding(article_id)
        if embedding:
            disliked_vectors.append(embedding)
    
    if not liked_vectors and not disliked_vectors:
        return False
    
    # 计算新的用户意图向量
    if liked_vectors:
        liked_mean = np.mean(liked_vectors, axis=0)
    else:
        liked_mean = np.zeros(len(disliked_vectors[0]))
    
    if disliked_vectors:
        disliked_mean = np.mean(disliked_vectors, axis=0)
        user_vector = liked_mean - 0.3 * disliked_mean
    else:
        user_vector = liked_mean
    
    # 归一化向量
    norm = np.linalg.norm(user_vector)
    if norm > 0:
        user_vector = user_vector / norm
    
    return db.save_user_intent_vector(user_vector.tolist())

def handle_user_feedback(article_id: int, feed_id: int, action: str):
    """处理用户反馈并移动到下一篇文章"""
    db = get_db()
    
    # 更新文章交互状态
    interaction_status = {
        'like': 1,
        'dislike': 2, 
        'skip': 3,
        'read': 0
    }.get(action, 0)
    
    db.update_article_interaction_status(article_id, interaction_status)
    db.update_feed_status(feed_id, 'read')
    
    # 显示操作反馈
    feedback_messages = {
        'like': "❤️ 已收藏到喜欢",
        'dislike': "👎 已标记为不喜欢", 
        'skip': "⏭️ 已跳过",
        'read': "✓ 已标记为已读"
    }
    st.toast(feedback_messages.get(action, "操作完成"), icon="✨")
    
    # 收集用户反馈
    if action in ['like', 'dislike']:
        feedback = {
            'article_id': article_id,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.user_feedback.append(feedback)
        
        # 更新用户意图向量
        if len(st.session_state.user_feedback) >= 3:
            liked = [f['article_id'] for f in st.session_state.user_feedback if f['action'] == 'like']
            disliked = [f['article_id'] for f in st.session_state.user_feedback if f['action'] == 'dislike']
            
            if update_user_intent_vector(liked, disliked):
                st.toast("🎯 偏好模型已更新", icon="🌟")
                st.session_state.user_feedback = []
    
    # 添加短暂延迟以显示反馈，然后移动到下一篇文章
    time.sleep(0.5)  # 让用户看到操作反馈
    next_article()

def next_article():
    """移动到下一篇文章"""
    if st.session_state.current_article_index < len(st.session_state.articles_list) - 1:
        st.session_state.current_article_index += 1
    else:
        # 到达末尾，重新加载文章
        st.session_state.current_article_index = 0
        load_articles()
    
    # 关闭阅读模式
    st.session_state.reading_mode = False
    st.rerun()

def previous_article():
    """移动到上一篇文章"""
    if st.session_state.current_article_index > 0:
        st.session_state.current_article_index -= 1
        st.session_state.reading_mode = False
        st.rerun()

def load_articles():
    """加载文章列表"""
    db = get_db()
    st.session_state.articles_list = db.get_unread_feed()

def show_end_page():
    """显示终结页"""
    st.markdown("""
    <style>
    @keyframes steam {
        0% { transform: translateY(0px) scale(1); opacity: 0.8; }
        100% { transform: translateY(-8px) scale(1.02); opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 80vh;
        text-align: center;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 20px;
        margin: 2rem 0;
        padding: 4rem 2rem;
    ">
        <div style="
            font-size: 4rem;
            margin-bottom: 2rem;
            animation: steam 2s ease-in-out infinite alternate;
        ">🍃</div>
        
        <h2 style="
            color: #4a5568;
            font-weight: 300;
            font-size: 2rem;
            margin-bottom: 1rem;
            line-height: 1.4;
        ">林间拾穗已毕</h2>
        
        <h3 style="
            color: #4a5568;
            font-weight: 300;
            font-size: 1.5rem;
            margin-bottom: 2rem;
            line-height: 1.4;
        ">愿君满载而归</h3>
        
        <p style="
            color: #718096;
            font-size: 1.1rem;
            margin-bottom: 3rem;
            max-width: 400px;
            line-height: 1.6;
        ">今日的精选内容已全部阅读完毕<br>请静心回味所得，或稍后再来探寻</p>
        
        <div style="
            background: white;
            padding: 2rem 2.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        ">
            <p style="
                color: #2d3748;
                margin: 0;
                font-style: italic;
                font-size: 1.05rem;
            ">"知识如茶，需要慢慢品味"</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 刷新按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 检查新内容", use_container_width=True, type="primary"):
            load_articles()
            if st.session_state.articles_list:
                st.session_state.current_article_index = 0
                st.rerun()
            else:
                st.info("暂时还没有新的内容，请稍后再试")

def display_single_article_card(article: Dict, article_index: int):
    """显示单张文章卡片 - 优雅简约设计"""
    
    # 添加双击支持的CSS和JavaScript
    st.markdown("""
    <style>
    .article-card {
        background: #fefefe;
        border-radius: 16px;
        padding: 2.5rem;
        margin: 2rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
        transition: all 0.3s ease;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
        cursor: pointer;
        user-select: none;
    }
    .article-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.08);
    }
    .article-title {
        font-size: 1.8rem;
        font-weight: 300;
        line-height: 1.4;
        color: #2c3e50;
        margin-bottom: 1.5rem;
        letter-spacing: -0.02em;
        text-align: center;
    }
    .article-summary {
        background: #f8fafe;
        padding: 1.8rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        font-style: italic;
        color: #4a5568;
        margin: 2rem 0;
        line-height: 1.7;
        font-size: 1.05rem;
    }
    .article-meta {
        color: #8e8e93;
        font-size: 0.9rem;
        margin: 1.5rem 0;
        text-align: center;
    }
    .score-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        font-weight: 500;
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .gesture-hint {
        text-align: center;
        color: #a0a0a0;
        font-size: 0.85rem;
        margin-top: 1rem;
        font-style: italic;
    }
    </style>
    
    <script>
    function setupCardInteractions() {
        const card = document.querySelector('.article-card');
        if (card) {
            let touchStartX = 0;
            let touchStartY = 0;
            let lastTap = 0;
            
            // 双击检测
            card.addEventListener('click', function(e) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTap;
                if (tapLength < 500 && tapLength > 0) {
                    // 双击事件
                    document.querySelector('[data-testid="stButton"][key*="like"]').click();
                }
                lastTap = currentTime;
            });
            
            // 触摸滑动检测
            card.addEventListener('touchstart', function(e) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            });
            
            card.addEventListener('touchend', function(e) {
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;
                const deltaX = touchEndX - touchStartX;
                const deltaY = touchEndY - touchStartY;
                
                // 只处理水平滑动
                if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                    if (deltaX > 0) {
                        // 向右滑动 - 跳过
                        document.querySelector('[data-testid="stButton"][key*="skip"]').click();
                    } else {
                        // 向左滑动 - 已读
                        document.querySelector('[data-testid="stButton"][key*="read"]').click();
                    }
                }
            });
        }
    }
    
    // 页面加载后设置交互
    setTimeout(setupCardInteractions, 100);
    </script>
    """, unsafe_allow_html=True)
    
    feed_id = article['id']
    
    with st.container():
        st.markdown('<div class="article-card" id="main-card">', unsafe_allow_html=True)
        
        # 分数徽章 - 居中显示
        score = article['final_score']
        st.markdown(f'<div style="text-align: center;"><span class="score-badge">★ {score:.2f}</span></div>', unsafe_allow_html=True)
        
        # 标题 - 点击进入阅读模式
        st.markdown(f'<h2 class="article-title">{article["title"]}</h2>', unsafe_allow_html=True)
        
        # AI推荐语 (如果有的话)
        if article.get('ai_rationale'):
            st.markdown(f'<div class="article-summary">🤖 {article["ai_rationale"]}</div>', unsafe_allow_html=True)
        
        # AI摘要
        if article.get('ai_summary'):
            st.markdown(f'<div class="article-summary">💭 {article["ai_summary"]}</div>', unsafe_allow_html=True)
        
        # 文章元信息
        db = get_db()
        article_detail = db.get_article_by_id(article['article_id'])
        published_at = article_detail.get('published_at') if article_detail else None
        
        st.markdown(f'''
        <div class="article-meta">
            📖 {article.get("source_name", "未知来源")} • 🕒 {format_datetime(published_at)}
        </div>
        ''', unsafe_allow_html=True)
        
        # 手势提示
        st.markdown('<div class="gesture-hint">双击卡片表示喜欢 • 左滑已读 • 右滑跳过 • 点击标题深度阅读</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 交互按钮区域 - 简洁布局
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("❤️ 喜欢", key=f"like_{feed_id}", use_container_width=True, type="primary"):
                handle_user_feedback(article['article_id'], feed_id, 'like')
        
        with col2:
            if st.button("👎 不喜欢", key=f"dislike_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'dislike')
        
        with col3:
            if st.button("⏭️ 跳过", key=f"skip_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'skip')
        
        with col4:
            if st.button("✓ 已读", key=f"read_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'read')
        
        # 深度阅读按钮
        if st.button("📖 深度阅读", key=f"read_mode_{feed_id}", use_container_width=True, type="secondary"):
            st.session_state.reading_mode = True
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_reading_mode(article: Dict):
    """沉浸式阅读模式"""
    
    # 阅读模式的CSS
    st.markdown("""
    <style>
    .reading-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 3rem;
        background: #fafafa;
        min-height: 80vh;
        border-radius: 16px;
    }
    .reading-title {
        font-size: 2.2rem;
        font-weight: 400;
        line-height: 1.3;
        color: #1a1a1a;
        margin-bottom: 2rem;
        text-align: center;
    }
    .reading-content {
        font-size: 1.1rem;
        line-height: 1.8;
        color: #333;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .reading-meta {
        text-align: center;
        color: #666;
        margin: 2rem 0;
        padding: 1rem;
        border-top: 1px solid #eee;
        border-bottom: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 获取完整文章内容
    db = get_db()
    article_detail = db.get_article_by_id(article['article_id'])
    
    with st.container():
        # 返回按钮
        if st.button("← 返回", key="back_to_card"):
            st.session_state.reading_mode = False
            st.rerun()
        
        st.markdown('<div class="reading-container">', unsafe_allow_html=True)
        
        # 标题
        st.markdown(f'<h1 class="reading-title">{article["title"]}</h1>', unsafe_allow_html=True)
        
        # 元信息
        published_at = article_detail.get('published_at') if article_detail else None
        st.markdown(f'''
        <div class="reading-meta">
            <strong>{article.get("source_name", "未知来源")}</strong> • {format_datetime(published_at)}<br>
            推荐分数: ★ {article["final_score"]:.2f}
        </div>
        ''', unsafe_allow_html=True)
        
        # AI摘要
        if article.get('ai_summary'):
            st.info(f"**AI摘要**: {article['ai_summary']}")
        
        # 文章内容
        content = article_detail.get('content', '内容加载失败') if article_detail else '内容加载失败'
        st.markdown(f'<div class="reading-content">{content}</div>', unsafe_allow_html=True)
        
        # 原文链接
        st.markdown(f"**[查看原文]({article['url']})**", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 底部操作按钮
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        feed_id = article['id']
        with col1:
            if st.button("❤️ 喜欢这篇", key=f"reading_like_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'like')
        
        with col2:
            if st.button("👎 不喜欢", key=f"reading_dislike_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'dislike')
        
        with col3:
            if st.button("⏭️ 跳过", key=f"reading_skip_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'skip')
        
        with col4:
            if st.button("✓ 标记已读", key=f"reading_read_{feed_id}", use_container_width=True):
                handle_user_feedback(article['article_id'], feed_id, 'read')

def show_feed_page():
    """显示Feed页面 - 一次一张卡片"""
    
    # 加载文章列表
    if not st.session_state.articles_list:
        load_articles()
    
    articles = st.session_state.articles_list
    
    if not articles:
        show_end_page()
        return
    
    # 确保索引有效
    if st.session_state.current_article_index >= len(articles):
        show_end_page()
        return
    
    current_article = articles[st.session_state.current_article_index]
    
    # 根据模式显示内容
    if st.session_state.reading_mode:
        show_reading_mode(current_article)
    else:
        # 页面标题 - 更加简洁
        st.markdown("""
        <div style="text-align: center; margin-bottom: 3rem;">
            <h1 style="color: #2c3e50; font-weight: 300; font-size: 2rem; margin-bottom: 0.5rem;">📖 专注阅读</h1>
            <p style="color: #7f8c8d; font-size: 1rem; margin: 0;">静心品读，收获智慧</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 显示当前文章卡片
        display_single_article_card(current_article, st.session_state.current_article_index)

def delete_source(source_id: int) -> bool:
    """删除RSS源"""
    try:
        db = get_db()
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            # 先删除相关的文章和feed记录
            cursor.execute('''
                DELETE FROM feed WHERE article_id IN (
                    SELECT id FROM articles WHERE source_id = ?
                )
            ''', (source_id,))
            cursor.execute('DELETE FROM articles WHERE source_id = ?', (source_id,))
            cursor.execute('DELETE FROM source WHERE id = ?', (source_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"删除RSS源失败: {e}")
        return False

def show_source_management():
    """显示RSS源管理"""
    st.subheader("RSS源管理")
    
    db = get_db()
    
    with st.expander("➕ 添加新的RSS源"):
        with st.form("add_source"):
            col1, col2 = st.columns(2)
            with col1:
                source_name = st.text_input("源名称", placeholder="例如: 阮一峰的网络日志")
                source_url = st.text_input("RSS URL", placeholder="https://example.com/rss")
            with col2:
                source_type = st.selectbox("源类型", ["RSS", "WEB"])
                
            submitted = st.form_submit_button("添加源")
            
            if submitted and source_name and source_url:
                source_id = db.add_source(source_url, source_name, source_type)
                if source_id:
                    st.success(f"✅ 源 '{source_name}' 添加成功！")
                    st.rerun()
                else:
                    st.error("❌ 添加失败，URL可能已存在")
    
    st.subheader("当前RSS源")
    sources = db.get_all_sources()
    
    if not sources:
        st.info("还没有添加任何RSS源")
        return
    
    for source in sources:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.write(f"**{source['name']}**")
                st.caption(source['url'])
            
            with col2:
                st.caption(f"类型: {source['type']}")
            
            with col3:
                last_fetch = source['last_fetched_at']
                if last_fetch:
                    st.caption(f"最后抓取: {format_datetime(last_fetch)}")
                else:
                    st.caption("从未抓取")
            
            with col4:
                # 删除按钮 - 添加确认机制
                if st.button("🗑️", key=f"delete_{source['id']}", help="删除此源"):
                    # 使用session state来跟踪确认状态
                    confirm_key = f"confirm_delete_{source['id']}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
                    
                    if not st.session_state[confirm_key]:
                        st.session_state[confirm_key] = True
                        st.rerun()
                
                # 显示确认对话框
                confirm_key = f"confirm_delete_{source['id']}"
                if confirm_key in st.session_state and st.session_state[confirm_key]:
                    st.warning(f"确定要删除源 '{source['name']}' 吗？")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("确认删除", key=f"confirm_yes_{source['id']}", type="primary"):
                            if delete_source(source['id']):
                                st.success(f"✅ 源 '{source['name']}' 已删除")
                                # 清理确认状态
                                del st.session_state[confirm_key]
                                # 清空当前文章列表，因为可能包含被删除源的文章
                                st.session_state.articles_list = []
                                st.session_state.current_article_index = 0
                                st.rerun()
                            else:
                                st.error("❌ 删除失败")
                    with col_no:
                        if st.button("取消", key=f"confirm_no_{source['id']}"):
                            del st.session_state[confirm_key]
                            st.rerun()
            
            st.divider()

def show_settings_page():
    """显示设置页面"""
    st.title("⚙️ 设置")
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["RSS源管理", "AI人设设置", "系统状态", "数据管理"])
    
    with tab1:
        show_source_management()
    
    with tab2:
        show_persona_settings()
    
    with tab3:
        show_system_status()
    
    with tab4:
        show_data_management()

def show_data_management():
    """显示数据管理页面"""
    st.subheader("数据管理")
    
    db = get_db()
    stats = db.get_database_stats()
    
    st.write("**当前数据统计：**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文章总数", stats['total_articles'])
    with col2:
        st.metric("推荐队列", stats['unread_feed'])
    with col3:
        st.metric("已交互文章", stats['interacted_articles'])
    
    st.divider()
    
    st.warning("⚠️ **危险操作区域** - 以下操作不可逆，请谨慎使用！")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清空推荐队列", use_container_width=True, type="secondary"):
            if clear_feed_queue():
                st.success("✅ 推荐队列已清空")
                st.session_state.articles_list = []
                st.session_state.current_article_index = 0
                st.rerun()
            else:
                st.error("❌ 清空推荐队列失败")
    
    with col2:
        if st.button("💣 清空所有文章", use_container_width=True, type="secondary"):
            if clear_all_articles():
                st.success("✅ 所有文章数据已清空")
                st.session_state.articles_list = []
                st.session_state.current_article_index = 0
                st.rerun()
            else:
                st.error("❌ 清空文章数据失败")
    
    st.divider()
    st.write("**重置整个系统：**")
    
    confirm_text = st.text_input("输入 'RESET' 来确认重置整个系统（包括文章、推荐队列、用户偏好）：")
    
    if st.button("🔄 重置整个系统", disabled=(confirm_text != "RESET"), type="primary"):
        if reset_entire_system():
            st.success("✅ 系统已完全重置")
            st.session_state.articles_list = []
            st.session_state.current_article_index = 0
            st.rerun()
        else:
            st.error("❌ 系统重置失败")

def clear_feed_queue() -> bool:
    """清空推荐队列"""
    try:
        db = get_db()
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feed')
            conn.commit()
        return True
    except Exception as e:
        print(f"清空推荐队列失败: {e}")
        return False

def clear_all_articles() -> bool:
    """清空所有文章和推荐队列"""
    try:
        db = get_db()
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feed')
            cursor.execute('DELETE FROM articles')
            conn.commit()
        return True
    except Exception as e:
        print(f"清空文章数据失败: {e}")
        return False

def reset_entire_system() -> bool:
    """重置整个系统"""
    try:
        db = get_db()
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feed')
            cursor.execute('DELETE FROM articles') 
            cursor.execute('DELETE FROM user')
            conn.commit()
        return True
    except Exception as e:
        print(f"系统重置失败: {e}")
        return False

def show_persona_settings():
    """显示AI人设设置"""
    st.subheader("AI评分人设")
    
    try:
        with open('prompt.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        start = content.find('SYSTEM_PROMPT = """') + len('SYSTEM_PROMPT = """')
        end = content.find('"""', start)
        current_prompt = content[start:end].strip()
        
    except Exception as e:
        current_prompt = "无法读取当前设置"
        st.error(f"读取prompt.py失败: {e}")
    
    st.write("**当前AI人设：**")
    st.text_area("", value=current_prompt, height=200, disabled=True)
    
    st.write("**编辑AI人设：**")
    with st.form("edit_persona"):
        new_prompt = st.text_area(
            "输入新的AI人设描述",
            value=current_prompt,
            height=300,
            help="这将影响AI如何评分和筛选文章"
        )
        
        submitted = st.form_submit_button("保存设置")
        
        if submitted:
            try:
                new_content = content.replace(
                    f'SYSTEM_PROMPT = """\n{current_prompt}\n"""',
                    f'SYSTEM_PROMPT = """\n{new_prompt}\n"""'
                )
                
                with open('prompt.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                st.success("✅ AI人设已更新！")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 保存失败: {e}")

def show_system_status():
    """显示系统状态"""
    st.subheader("系统状态")
    
    db = get_db()
    stats = db.get_database_stats()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("RSS源数量", stats['total_sources'])
        st.metric("总文章数", stats['total_articles'])
        st.metric("已向量化文章", stats['vectorized_articles'])
    
    with col2:
        st.metric("已AI评分文章", stats['scored_articles'])
        st.metric("已交互文章", stats['interacted_articles'])
        st.metric("推荐队列未读", stats['unread_feed'])
    
    st.subheader("用户配置")
    if stats['has_user_profile']:
        st.success("✅ 用户偏好向量已建立")
    else:
        st.warning("⚠️ 用户偏好向量未建立，请先对一些文章进行喜欢/不喜欢操作")
    
    st.subheader("手动操作")
    if st.button("🔄 手动运行后台抓取任务", help="立即运行一次后台抓取和处理"):
        with st.spinner("正在运行后台任务..."):
            try:
                from background_worker import BackgroundWorker
                worker = BackgroundWorker()
                worker.run_fetch_and_process()
                st.success("✅ 后台任务运行完成！")
                # 重新加载文章列表
                st.session_state.articles_list = []
                load_articles()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 后台任务运行失败: {e}")

def main():
    """主函数"""
    st.set_page_config(
        page_title="PersonaFlow - 专注阅读", 
        layout="wide",
        page_icon="📖",
        initial_sidebar_state="collapsed"
    )
    
    init_session_state()
    
    # 简化的侧边栏
    with st.sidebar:
        st.markdown("## 📖 PersonaFlow")
        st.markdown("*专注阅读，精准推荐*")
        
        st.divider()
        
        if st.button("📚 专注阅读", use_container_width=True, type="primary" if st.session_state.current_page == 'feed' else "secondary"):
            st.session_state.current_page = 'feed'
            st.rerun()
        
        if st.button("⚙️ 系统设置", use_container_width=True, type="primary" if st.session_state.current_page == 'settings' else "secondary"):
            st.session_state.current_page = 'settings'
            st.rerun()
        
        st.divider()
        
        # 显示简要统计
        try:
            db = get_db()
            stats = db.get_database_stats()
            st.caption(f"📊 {stats['total_articles']} 篇文章")
            st.caption(f"🎯 {stats['unread_feed']} 篇待读")
        except:
            pass
    
    # 主要内容区域
    if st.session_state.current_page == 'feed':
        show_feed_page()
    elif st.session_state.current_page == 'settings':
        show_settings_page()

if __name__ == "__main__":
    main()