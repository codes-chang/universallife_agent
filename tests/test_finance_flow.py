"""Finance 子图流程测试"""

import pytest
from app.subgraphs.finance.graph import get_finance_subgraph
from app.subgraphs.finance.state import FinanceSubgraphState


@pytest.mark.asyncio
async def test_finance_subgraph_stock():
    """测试金融子图股票查询"""
    subgraph = get_finance_subgraph()

    result = await subgraph.run("查询 AAPL 股票价格")

    assert result["domain"] == "finance"
    assert result["result"] is not None
    assert len(result["result"]) > 0
    # 应该包含股票相关信息
    assert "AAPL" in result["result"] or "Apple" in result["result"] or "价格" in result["result"]


@pytest.mark.asyncio
async def test_finance_subgraph_price_compare():
    """测试金融子图价格比较"""
    subgraph = get_finance_subgraph()

    result = await subgraph.run("比较 iPhone 的价格")

    assert result["domain"] == "finance"
    assert result["result"] is not None


@pytest.mark.asyncio
async def test_finance_nodes():
    """测试金融节点"""
    from app.subgraphs.finance.nodes import build_plan_node, execute_tools_node, synthesize_result_node

    state: FinanceSubgraphState = {
        "task_input": "查询 AAPL 股票价格",
        "domain": "finance",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "query_type": None,
        "symbol": None,
        "price_data": None,
        "product_name": None
    }

    # 测试规划节点
    state = await build_plan_node(state)
    assert state["plan"] is not None
    assert state["query_type"] == "stock"
    assert state["symbol"] == "AAPL"

    # 测试工具执行节点
    state = await execute_tools_node(state)
    assert state["intermediate_result"] is not None

    # 测试结果合成节点
    state = await synthesize_result_node(state)
    assert state["final_result"] is not None


@pytest.mark.asyncio
async def test_finance_format_stock_info():
    """测试股票信息格式化"""
    from app.subgraphs.finance.nodes import format_price_comparison
    from app.services.finance_service import get_finance_service

    service = get_finance_service()
    stock_data = await service.get_stock_quote("AAPL")

    formatted = service.format_stock_info(stock_data)

    assert "AAPL" in formatted
    assert "$" in formatted or "¥" in formatted
    assert "涨" in formatted or "跌" in formatted or "➡️" in formatted
