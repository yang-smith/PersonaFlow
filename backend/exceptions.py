class PersonaFlowException(Exception):
    """PersonaFlow 基础异常类"""
    pass

class DatabaseException(PersonaFlowException):
    """数据库操作异常"""
    pass

class LLMException(PersonaFlowException):
    """LLM服务异常"""
    pass

class RSSFetchException(PersonaFlowException):
    """RSS抓取异常"""
    pass

class VectorException(PersonaFlowException):
    """向量操作异常"""
    pass 