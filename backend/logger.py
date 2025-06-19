import sys
from pathlib import Path
from loguru import logger

def setup_logger():
    """设置日志配置"""
    # 移除默认handler
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 文件输出 - 使用安全的默认路径
    try:
        from config import settings
        log_file = settings.LOG_FILE
        log_level = settings.LOG_LEVEL
    except Exception:
        # 如果配置加载失败，使用默认值
        current_dir = Path(__file__).parent
        log_dir = current_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = str(log_dir / "personaflow.log")
        log_level = "INFO"
    
    # 确保日志文件路径不为空
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        )
    
    return logger

# 全局logger实例
app_logger = setup_logger() 