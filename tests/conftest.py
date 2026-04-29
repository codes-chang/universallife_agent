"""Pytest 配置文件"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM 服务（用于单元测试）"""
    from langchain_core.messages import AIMessage

    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=AIMessage(content='{"result": "mock response"}'))
    mock.astream = AsyncMock()
    mock.with_structured_output = MagicMock(return_value=mock)
    mock.bind_tools = MagicMock(return_value=mock)
    mock.model_name = "mock-model"

    from app.services import llm_service
    monkeypatch.setattr(llm_service, "_llm_instance", mock)

    yield mock

    llm_service.reset_llm()


@pytest.fixture
def sample_queries():
    """示例查询"""
    return {
        "outfit": "明天上海下雨，帮我搭配一套适合通勤的穿搭",
        "search": "搜索 LangChain 最新教程",
        "finance": "查询 AAPL 股票价格",
        "academic": "查找 langgraph GitHub 仓库",
        "trip": "规划北京 3 天旅行"
    }


@pytest.fixture
async def main_graph_runner():
    """主图运行器 fixture"""
    from app.graph.main_graph import get_main_graph_runner
    return get_main_graph_runner()


@pytest.fixture
def mock_weather_data():
    """Mock 天气数据"""
    return {
        "city": "上海",
        "province": "上海",
        "report_time": "2026-03-24 12:00:00",
        "casts": [
            {
                "date": "2026-03-25",
                "day_weather": "小雨",
                "night_weather": "小雨",
                "day_temp": "15",
                "night_temp": "10"
            }
        ]
    }


@pytest.fixture
def mock_search_results():
    """Mock 搜索结果"""
    return {
        "query": "LangChain",
        "results": [
            {
                "title": "LangChain - Building with LLMs",
                "url": "https://example.com/langchain",
                "snippet": "LangChain is a framework for building LLM applications...",
                "score": 0.95
            }
        ]
    }


@pytest.fixture
def mock_stock_data():
    """Mock 股票数据"""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 178.50,
        "change": 2.30,
        "change_percent": 1.30,
        "timestamp": "2026-03-24T12:00:00",
        "source": "yahoo-finance"
    }


@pytest.fixture
def mock_github_results():
    """Mock GitHub 搜索结果"""
    return {
        "query": "langgraph",
        "results": [
            {
                "name": "langgraph",
                "full_name": "langchain-ai/langgraph",
                "description": "LangGraph is a library for building stateful, multi-actor applications with LLMs",
                "stars": 15000,
                "language": "Python",
                "url": "https://github.com/langchain-ai/langgraph"
            }
        ]
    }


# 测试配置
def test_pytest_config():
    """测试 pytest 配置是否正确"""
    assert True
