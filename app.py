import json
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import os

# 配置
FILTERED_CONTENT_FILE = 'filtered_content.json'
MIN_DISPLAY_SCORE = 6.0

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

def format_datetime(iso_string: str) -> str:
    """格式化时间显示"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%m-%d %H:%M')
    except:
        return iso_string

def get_score_indicator(score: float) -> str:
    """根据分数返回简洁指示器"""
    if score >= 9.0:
        return "●●●"  # 必读
    elif score >= 8.0:
        return "●●○"  # 推荐
    elif score >= 7.0:
        return "●○○"  # 不错
    else:
        return "○○○"  # 一般

def display_article(article: Dict, index: int):
    """显示文章卡片 - 简洁优雅版本"""
    score = article.get('ai_score', 0)
    title = article.get('title', '无标题')
    url = article.get('url', '#')
    ai_summary = article.get('ai_summary', '')
    source_title = article.get('source_title', '未知来源')
    scored_at = article.get('scored_at', '')
    
    # 主卡片容器
    with st.container():
        # 使用更优雅的分割线
        st.markdown('<hr style="margin: 2rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, #e0e0e0, transparent);">', unsafe_allow_html=True)
        
        # 文章标题区域
        col1, col2 = st.columns([5, 1])
        with col1:
            # 可点击的标题
            st.markdown(f'<h3 style="margin-bottom: 0.5rem; line-height: 1.4;"><a href="{url}" target="_blank" style="text-decoration: none; color: #1f1f1f; border-bottom: 2px solid transparent; transition: border-color 0.2s;" onmouseover="this.style.borderColor=\'#ff6b6b\'" onmouseout="this.style.borderColor=\'transparent\'">{title}</a></h3>', unsafe_allow_html=True)
        
        with col2:
            # 分数显示 - 更优雅
            st.markdown(f'<div style="text-align: right; font-size: 0.9rem; color: #666;">{get_score_indicator(score)}<br><span style="font-weight: 600; color: #333;">{score:.1f}</span></div>', unsafe_allow_html=True)
        
        # AI摘要 - 如果存在
        if ai_summary:
            st.markdown(f'<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 3px solid #667eea; margin: 1rem 0; font-style: italic; color: #444;">{ai_summary}</div>', unsafe_allow_html=True)
        
        # 底部信息栏 - 极简
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f'<small style="color: #888;">{source_title}</small>', unsafe_allow_html=True)
        with col2:
            if scored_at:
                st.markdown(f'<small style="color: #aaa; text-align: right; display: block;">{format_datetime(scored_at)}</small>', unsafe_allow_html=True)

def main():
    # 页面配置 - 更简洁
    st.set_page_config(
        page_title="优质信息流", 
        layout="wide",
        page_icon="◉",
        initial_sidebar_state="collapsed"
    )
    
    # 自定义CSS - 优雅字体和间距
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
        max-width: 800px;
        margin: 0 auto;
    }
    .stButton > button {
        background: transparent;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 0.25rem 1rem;
        font-size: 0.8rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: #667eea;
        color: #667eea;
    }
    h1 {
        font-weight: 300;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f0f0f0;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题 - 极简
    st.markdown('<h1 style="text-align: center; color: #333; font-weight: 300;">优质信息流</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #888; margin-bottom: 2rem;">AI 筛选的高质量内容</p>', unsafe_allow_html=True)
    
    # 加载数据
    filtered_data = load_filtered_content()
    
    if not filtered_data:
        # 空状态 - 优雅处理
        st.markdown('<div style="text-align: center; padding: 4rem 2rem; color: #999;"><h3 style="font-weight: 300;">暂无内容</h3><p>请运行 <code>python main.py</code> 获取最新内容</p></div>', unsafe_allow_html=True)
        return
    
    articles = filtered_data.get('articles', [])
    if not articles:
        st.markdown('<div style="text-align: center; padding: 4rem 2rem; color: #999;"><h3 style="font-weight: 300;">暂无文章</h3></div>', unsafe_allow_html=True)
        return
    
    # 顶部状态栏 - 极简指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><strong>{len(articles)}</strong><br><small>文章</small></div>', unsafe_allow_html=True)
    with col2:
        avg_score = sum(a.get('ai_score', 0) for a in articles) / len(articles)
        st.markdown(f'<div class="metric-card"><strong>{avg_score:.1f}</strong><br><small>平均分</small></div>', unsafe_allow_html=True)
    with col3:
        max_score = max(a.get('ai_score', 0) for a in articles)
        st.markdown(f'<div class="metric-card"><strong>{max_score:.1f}</strong><br><small>最高分</small></div>', unsafe_allow_html=True)
    with col4:
        if st.button("刷新", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 简单排序控制
    col1, col2 = st.columns([3, 1])
    with col2:
        sort_by_score = st.checkbox("按分数排序", value=True)
    
    # 排序文章
    if sort_by_score:
        articles.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    else:
        articles.sort(key=lambda x: x.get('scored_at', ''), reverse=True)
    
    # 只显示高分文章
    high_quality_articles = [a for a in articles if a.get('ai_score', 0) >= MIN_DISPLAY_SCORE]
    
    # 显示文章
    st.markdown('<div style="margin-top: 2rem;">', unsafe_allow_html=True)
    for i, article in enumerate(high_quality_articles):
        display_article(article, i)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 底部签名
    st.markdown('<div style="text-align: center; margin-top: 4rem; padding: 2rem; color: #ccc; font-size: 0.8rem;">Designed for focus</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()