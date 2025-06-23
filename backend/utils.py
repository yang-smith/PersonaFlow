import re
import hashlib
from typing import List, Optional
from datetime import datetime
import numpy as np

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 处理图片标签，提取alt文本或src信息
    text = re.sub(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*>', r'[图片: \1]', text)
    text = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*>', r'[图片: \1]', text)
    text = re.sub(r'<img[^>]*>', '[图片]', text)
    
    # 处理链接标签，保留链接文本
    text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'\2 (\1)', text)
    text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', text)
    
    # 处理视频标签
    text = re.sub(r'<video[^>]*>', '[视频]', text)
    text = re.sub(r'</video>', '', text)
    
    # 处理音频标签
    text = re.sub(r'<audio[^>]*>', '[音频]', text)
    text = re.sub(r'</audio>', '', text)
    
    # 处理换行标签
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    
    # 处理标题标签，保留层级信息
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n\2\n', text)
    
    # 处理列表标签
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text)
    text = re.sub(r'</?[uo]l[^>]*>', '', text)
    
    # 处理引用标签
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'"\1"', text, flags=re.DOTALL)
    
    # 处理代码标签
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text)
    text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\1```', text, flags=re.DOTALL)
    
    # 移除剩余的HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 处理HTML实体
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    
    # 移除多余的空白字符
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # 最多保留两个连续换行
    text = re.sub(r'[ \t]+', ' ', text)  # 合并空格和制表符
    
    # 移除首尾空白
    text = text.strip()
    
    return text

def generate_url_hash(url: str) -> str:
    """生成URL的哈希值"""
    return hashlib.md5(url.encode()).hexdigest()

def safe_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def normalize_vector(vector: List[float]) -> List[float]:
    """向量归一化"""
    if not vector:
        return vector
    
    np_vector = np.array(vector)
    norm = np.linalg.norm(np_vector)
    
    if norm == 0:
        return vector
    
    return (np_vector / norm).tolist()

def cosine_similarity_score(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    if not vec1 or not vec2:
        return 0.0
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        
        v1 = np.array(vec1).reshape(1, -1)
        v2 = np.array(vec2).reshape(1, -1)
        
        similarity = cosine_similarity(v1, v2)[0][0]
        return (similarity + 1) / 2  # 转换到 [0, 1] 范围
    except Exception:
        return 0.0

def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """格式化时间戳"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S") 