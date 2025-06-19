import os
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

class Settings:
    def __init__(self):
        # API配置
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", "8000"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # 数据库配置 - 使用绝对路径
        self.DATABASE_PATH: str = os.getenv("DATABASE_PATH", None)
        if not self.DATABASE_PATH:
            # 使用当前目录下的数据库文件
            current_dir = Path(__file__).parent
            self.DATABASE_PATH = str(current_dir / "personaflow.db")
        
        # 确保数据库目录存在
        db_path = Path(self.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # LLM配置
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # 后台任务配置
        self.FETCH_INTERVAL_HOURS: int = int(os.getenv("FETCH_INTERVAL_HOURS", "12"))
        self.SCORE_THRESHOLD: float = float(os.getenv("SCORE_THRESHOLD", "0.7"))
        self.SIMILARITY_WEIGHT: float = float(os.getenv("SIMILARITY_WEIGHT", "0.5"))
        self.AI_QUALITY_WEIGHT: float = float(os.getenv("AI_QUALITY_WEIGHT", "0.5"))
        self.USER_VECTOR_LEARNING_RATE: float = float(os.getenv("USER_VECTOR_LEARNING_RATE", "0.1"))
        
        # 日志配置
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE: str = os.getenv("LOG_FILE", None)
        
        # 如果没有设置日志文件路径，使用默认路径
        if not self.LOG_FILE:
            current_dir = Path(__file__).parent
            log_dir = current_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            self.LOG_FILE = str(log_dir / "personaflow.log")

settings = Settings() 