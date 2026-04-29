"""子图基类定义"""

import asyncio
from typing import TypedDict, Any, Optional, Callable
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ..core.state import BaseSubgraphState, ToolCall
from ..core.logging import logger
from ..services.llm_service import get_llm


class BaseSubgraph:
    """子图基类

    所有领域子图应继承此类并实现相关方法。
    """

    def __init__(self, name: str):
        self.name = name
        self.graph = None
        self._build_graph()

    def _build_graph(self):
        """构建子图工作流"""
        # 暂时不使用 LangGraph，使用顺序执行
        self.graph = None

    def get_state_class(self):
        """获取状态类（子类应覆盖）"""
        return BaseSubgraphState

    def get_system_prompt(self) -> str:
        """获取系统 Prompt（子类应覆盖）"""
        return f"你是{self.name}领域的专家助手。"

    async def build_plan_node(self, state: BaseSubgraphState) -> BaseSubgraphState:
        """规划节点 - 分析任务并制定执行计划"""
        logger.info(f"[{self.name}] 正在制定计划...")

        task_input = state.get("task_input", "")
        domain = state.get("domain", self.name)
        memory_input = state.get("memory_input", {})

        try:
            llm = get_llm()

            # 构建记忆上下文
            memory_context = self._format_memory_context(memory_input)

            prompt = f"""分析以下任务并制定执行计划：

任务: {task_input}
领域: {domain}

{memory_context}

请列出：
1. 任务理解
2. 需要的信息
3. 执行步骤
4. 预期结果

请以简洁的方式输出计划。
"""

            messages = [
                SystemMessage(content=self.get_system_prompt()),
                HumanMessage(content=prompt)
            ]

            response = await llm.ainvoke(messages)
            plan = response.content if hasattr(response, 'content') else str(response)

            state["plan"] = plan
            logger.info(f"[{self.name}] 计划制定完成")

        except Exception as e:
            logger.error(f"[{self.name}] 计划制定失败: {e}")
            state["plan"] = f"直接执行任务: {task_input}"

        # 初始化候选记忆
        if "candidate_memories" not in state:
            state["candidate_memories"] = []

        return state

    def _format_memory_context(self, memory_input: dict) -> str:
        """格式化记忆上下文"""
        if not memory_input:
            return ""

        parts = []

        if memory_input.get("has_user_preferences"):
            prefs = memory_input.get("user_preferences", [])
            if prefs:
                parts.append("# 用户偏好")
                parts.extend(f"- {p.get('content', '')}" for p in prefs[:3])

        if memory_input.get("has_domain_memories"):
            memories = memory_input.get("domain_memories", [])
            if memories:
                parts.append("# 相关经验")
                parts.extend(f"- {m.get('content', '')}" for m in memories[:3])

        if memory_input.get("has_constraints"):
            constraints = memory_input.get("constraints", [])
            if constraints:
                parts.append("# 用户约束")
                parts.extend(f"- {c}" for c in constraints)

        return "\n".join(parts) if parts else ""

    async def execute_tools_node(self, state: BaseSubgraphState) -> BaseSubgraphState:
        """工具执行节点 - 根据计划调用相应工具"""
        logger.info(f"[{self.name}] 正在执行工具...")

        try:
            # 子类应覆盖此方法实现具体工具调用
            result = await self.execute_domain_tools(state)
            state["intermediate_result"] = result

            # 记录工具调用
            tool_call: ToolCall = {
                "tool_name": f"{self.name}_tools",
                "parameters": {"task": state.get("task_input", "")},
                "result": result,
                "error": None,
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            state["tool_calls"] = state.get("tool_calls", [])
            state["tool_calls"].append(tool_call)

        except Exception as e:
            logger.error(f"[{self.name}] 工具执行失败: {e}")
            state["intermediate_result"] = f"执行失败: {str(e)}"

        return state

    async def execute_domain_tools(self, state: BaseSubgraphState) -> str:
        """执行领域特定工具（子类应覆盖）"""
        return f"这是 {self.name} 子图的工具执行结果"

    async def synthesize_result_node(self, state: BaseSubgraphState) -> BaseSubgraphState:
        """结果合成节点 - 将工具执行结果合成为最终答案"""
        logger.info(f"[{self.name}] 正在合成结果...")

        try:
            llm = get_llm()
            task_input = state.get("task_input", "")
            intermediate = state.get("intermediate_result", "")

            prompt = f"""基于以下信息生成最终回复：

用户任务: {task_input}

执行结果:
{intermediate}

请生成一个完整、友好、有用的回复。
"""

            messages = [
                SystemMessage(content=self.get_system_prompt()),
                HumanMessage(content=prompt)
            ]

            response = await llm.ainvoke(messages)
            final_result = response.content if hasattr(response, 'content') else str(response)

            state["final_result"] = final_result
            logger.info(f"[{self.name}] 结果合成完成")

        except Exception as e:
            logger.error(f"[{self.name}] 结果合成失败: {e}")
            state["final_result"] = state.get("intermediate_result", "处理完成")

        return state

    async def run(self, task_input: str, memory_input: dict = None, **kwargs) -> dict:
        """运行子图

        Args:
            task_input: 任务输入
            memory_input: 记忆输入（由主图提供）
            **kwargs: 额外参数

        Returns:
            执行结果字典
        """
        # 构建初始状态
        initial_state = self.get_state_class()({
            "task_input": task_input,
            "domain": self.name,
            "memory_input": memory_input or {},
            "plan": None,
            "tool_calls": [],
            "intermediate_result": None,
            "final_result": None,
            "critique": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "candidate_memories": [],  # 初始化候选记忆列表
            **kwargs
        })

        # 如果 graph 构建失败，直接按顺序执行节点
        if self.graph is None:
            logger.warning(f"[{self.name}] 使用简化的顺序执行模式")
            try:
                initial_state = await self.build_plan_node(initial_state)
                initial_state = await self.execute_tools_node(initial_state)
                initial_state = await self.synthesize_result_node(initial_state)
                # 生成候选记忆
                initial_state = await self.generate_candidate_memories(initial_state)
                final_state = initial_state
            except Exception as e:
                logger.error(f"[{self.name}] 执行失败: {e}")
                final_state = initial_state
                final_state["final_result"] = f"处理失败: {str(e)}"
        else:
            # 使用 graph 执行工作流
            final_state = initial_state
            async for output in self.graph.astream(final_state):
                for node_name, node_output in output.items():
                    final_state = node_output

        return {
            "domain": self.name,
            "result": final_state.get("final_result", ""),
            "plan": final_state.get("plan", ""),
            "intermediate": final_state.get("intermediate_result", ""),
            "tool_calls": final_state.get("tool_calls", []),
            "candidate_memories": final_state.get("candidate_memories", [])
        }

    async def generate_candidate_memories(self, state: BaseSubgraphState) -> BaseSubgraphState:
        """生成候选记忆（子类可覆盖）

        默认实现：基于任务执行结果生成候选记忆
        """
        # 子类可以覆盖此方法，生成特定的候选记忆
        # 这里只是一个基本实现
        return state


def create_simple_subgraph(name: str, handler_func: callable) -> BaseSubgraph:
    """创建简单子图的辅助函数

    Args:
        name: 子图名称
        handler_func: 处理函数，接收 task_input，返回结果

    Returns:
        子图实例
    """

    class SimpleSubgraph(BaseSubgraph):
        async def execute_domain_tools(self, state: BaseSubgraphState) -> str:
            task_input = state.get("task_input", "")
            return await handler_func(task_input, state)

    return SimpleSubgraph(name)
