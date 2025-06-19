from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    RSS = "RSS"
    WEB = "WEB"

class InteractionStatus(int, Enum):
    UNINTERACTED = 0
    LIKED = 1
    DISLIKED = 2
    SKIPPED = 3

class FeedStatus(str, Enum):
    UNREAD = "unread"
    LIKED = "liked"
    SKIPPED = "skipped"

# Request/Response Models
class SourceCreate(BaseModel):
    url: str = Field(..., description="源URL")
    name: str = Field(..., description="源名称")
    type: SourceType = Field(default=SourceType.RSS, description="源类型")

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SourceType] = None

class SourceResponse(BaseModel):
    id: int
    url: str
    name: str
    type: str
    last_fetched_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ArticleResponse(BaseModel):
    id: int
    source_id: int
    url: str
    title: str
    content: Optional[str]
    ai_summary: Optional[str]
    ai_quality_score: Optional[float]
    ai_rationale: Optional[str]
    published_at: Optional[datetime]
    interaction_status: int
    source_name: Optional[str] = None
    final_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class FeedActionRequest(BaseModel):
    article_id: int = Field(..., description="文章ID")
    action: Literal["like", "skip"] = Field(..., description="操作类型: like 或 skip")

class FeedActionResponse(BaseModel):
    status: str = "success"
    message: str = "Action recorded"

class PromptRequest(BaseModel):
    prompt: str = Field(..., description="AI System Prompt")

class PromptResponse(BaseModel):
    prompt: str

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None 