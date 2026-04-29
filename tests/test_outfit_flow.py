"""Outfit 子图流程测试"""

import pytest
from app.subgraphs.outfit.graph import get_outfit_subgraph
from app.subgraphs.outfit.state import OutfitSubgraphState


@pytest.mark.asyncio
async def test_outfit_subgraph_run():
    """测试穿搭子图运行"""
    subgraph = get_outfit_subgraph()

    result = await subgraph.run("明天上海下雨，帮我搭配通勤穿搭")

    assert result["domain"] == "outfit"
    assert result["result"] is not None
    assert len(result["result"]) > 0
    assert "上海" in result["result"] or "穿搭" in result["result"]


@pytest.mark.asyncio
async def test_outfit_with_weather():
    """测试带天气信息的穿搭建议"""
    subgraph = get_outfit_subgraph()

    state: OutfitSubgraphState = {
        "task_input": "明天北京下雪，我要去上班",
        "domain": "outfit",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "location": "北京",
        "weather_condition": None,
        "style_preference": None,
        "occasion": "通勤",
        "gender": None
    }

    result = await subgraph.run("明天北京下雪，我要去上班")

    # 应该包含保暖相关的建议
    result_text = result["result"]
    assert "通勤" in result_text or "工作" in result_text


@pytest.mark.asyncio
async def test_outfit_nodes():
    """测试穿搭节点"""
    from app.subgraphs.outfit.nodes import build_plan_node, execute_tools_node, synthesize_result_node

    state: OutfitSubgraphState = {
        "task_input": "明天上海下雨，帮我搭配通勤穿搭",
        "domain": "outfit",
        "plan": None,
        "tool_calls": [],
        "intermediate_result": None,
        "final_result": None,
        "critique": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "location": None,
        "weather_condition": None,
        "style_preference": None,
        "occasion": None,
        "gender": None
    }

    # 测试规划节点
    state = await build_plan_node(state)
    assert state["plan"] is not None
    assert state["location"] == "上海"

    # 测试工具执行节点
    state = await execute_tools_node(state)
    assert state["intermediate_result"] is not None

    # 测试结果合成节点
    state = await synthesize_result_node(state)
    assert state["final_result"] is not None
    assert len(state["final_result"]) > 0
