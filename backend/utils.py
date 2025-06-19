import re
import hashlib
from typing import List, Optional
from datetime import datetime
import numpy as np

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
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