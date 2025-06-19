from typing import Dict, Any
from datetime import datetime
import psutil
import os
from pathlib import Path

from models import DatabaseManager
from config import settings

def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    # CPU和内存使用情况
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # 磁盘使用情况
    disk = psutil.disk_usage('/')
    
    # 数据库文件大小
    db_path = Path(settings.DATABASE_PATH)
    db_size = db_path.stat().st_size if db_path.exists() else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            }
        },
        "database": {
            "size_bytes": db_size,
            "size_mb": round(db_size / 1024 / 1024, 2)
        }
    }

def check_dependencies() -> Dict[str, bool]:
    """检查依赖项状态"""
    checks = {}
    
    # 检查数据库连接
    try:
        db = DatabaseManager()
        db.get_database_stats()
        checks["database"] = True
    except Exception:
        checks["database"] = False
    
    # 检查LLM服务
    try:
        from llm_client import get_embedding
        # 尝试获取一个简单的向量
        get_embedding("test")
        checks["llm_service"] = True
    except Exception:
        checks["llm_service"] = False
    
    # 检查必要的目录
    checks["data_directory"] = Path(settings.DATABASE_PATH).parent.exists()
    checks["log_directory"] = Path(settings.LOG_FILE).parent.exists()
    
    return checks 