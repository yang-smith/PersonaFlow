#!/usr/bin/env python3
"""
PersonaFlow API 服务启动脚本
"""

import uvicorn
import asyncio
from pathlib import Path

from config import settings
from logger import app_logger

async def startup_checks():
    """启动前检查"""
    app_logger.info("正在进行启动前检查...")
    
    # 检查配置
    if not settings.OPENAI_API_KEY:
        app_logger.warning("未设置 OPENAI_API_KEY，某些功能可能无法正常工作")
    
    # 检查数据库
    try:
        from models import DatabaseManager
        db = DatabaseManager()
        stats = db.get_database_stats()
        app_logger.info(f"数据库连接成功，统计信息: {stats}")
    except Exception as e:
        app_logger.error(f"数据库连接失败: {e}")
        return False
    
    app_logger.info("启动前检查完成")
    return True

def main():
    """主函数"""
    app_logger.info("启动 PersonaFlow API 服务...")
    
    # 运行启动检查
    if not asyncio.run(startup_checks()):
        app_logger.error("启动前检查失败，退出")
        return
    
    app_logger.info(f"API 文档地址: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    app_logger.info(f"ReDoc 文档地址: http://{settings.API_HOST}:{settings.API_PORT}/redoc")
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )

if __name__ == "__main__":
    main() 