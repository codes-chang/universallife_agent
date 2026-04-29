"""Pydantic 数据模型定义"""

from typing import Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============ 请求模型 ============

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1)
    session_id: Optional[str] = Field(default=None, description="会话ID")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "明天上海下雨，帮我搭配一套适合通勤的穿搭",
                "session_id": "user-123"
            }
        }


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    message: str = Field(..., description="用户反馈消息", min_length=1)
    session_id: Optional[str] = Field(default=None, description="会话ID")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "你理解错了，我不是要穿搭，我是要买防雨通勤鞋",
                "session_id": "user-123"
            }
        }


# ============ 响应模型 ============

class RouterResultModel(BaseModel):
    """路由结果模型"""
    primary_intent: str
    secondary_intents: List[str]
    confidence: float
    reasoning: str
    constraints: dict[str, Any]


class ReviewResultModel(BaseModel):
    """审查结果模型"""
    passed: bool
    score: float
    violations: List[str]
    critique: str
    suggestions: List[str]


class ExecutionTraceItem(BaseModel):
    """执行轨迹项"""
    step: str
    domain: Optional[str] = None
    timestamp: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str = "running"
    details: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    message: str
    router_result: Optional[RouterResultModel] = None
    active_domain: Optional[str] = None
    subgraph_output: Optional[dict[str, Any]] = None
    review_result: Optional[ReviewResultModel] = None
    final_answer: Optional[str] = None
    execution_trace: List[ExecutionTraceItem] = []
    session_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "处理成功",
                "router_result": {
                    "primary_intent": "outfit",
                    "secondary_intents": ["weather"],
                    "confidence": 0.95,
                    "reasoning": "用户询问关于穿搭的建议",
                    "constraints": {"location": "上海", "weather": "雨"}
                },
                "active_domain": "outfit",
                "final_answer": "根据明天上海的雨天天气，建议您..."
            }
        }


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    message: str
    detected_negative: bool = False
    rerouted: bool = False
    new_intent: Optional[str] = None
    response: Optional[str] = None


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


# ============ 健康检查 ============

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    components: dict[str, str]


# ============ 穿搭相关模型 ============

class OutfitItem(BaseModel):
    """穿搭单品"""
    category: str = Field(..., description="类别: 上装/下装/鞋/配饰")
    name: str = Field(..., description="名称")
    reason: str = Field(..., description="推荐理由")
    color_suggestions: List[str] = Field(default_factory=list, description="颜色建议")


class OutfitRecommendation(BaseModel):
    """穿搭推荐方案"""
    location: str
    weather: str
    temperature: str
    occasion: str
    items: List[OutfitItem]
    additional_advice: str


# ============ 搜索相关模型 ============

class SearchResult(BaseModel):
    """搜索结果"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str


# ============ 金融相关模型 ============

class StockInfo(BaseModel):
    """股票信息"""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    timestamp: str
    source: str


class PriceComparison(BaseModel):
    """价格比较"""
    product_name: str
    prices: List[dict[str, Any]]
    best_price: float
    best_source: str
    timestamp: str


# ============ 学术相关模型 ============

class GitHubRepo(BaseModel):
    """GitHub 仓库信息"""
    name: str
    description: str
    stars: int
    language: str
    url: str
    updated_at: str


class ArxivPaper(BaseModel):
    """arXiv 论文信息"""
    title: str
    authors: List[str]
    summary: str
    published: str
    arxiv_url: str
    pdf_url: str
