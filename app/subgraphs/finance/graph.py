"""Finance 子图 - 金融购物"""

from langgraph.graph import StateGraph, START, END
from .state import FinanceSubgraphState
from . import nodes
from ..base import BaseSubgraph


class FinanceSubgraph(BaseSubgraph):
    """金融子图

    提供股票查询、价格比较等功能。
    """

    def __init__(self):
        super().__init__("finance")

    def get_state_class(self) -> type:
        return FinanceSubgraphState

    def get_system_prompt(self) -> str:
        return """你是专业的金融信息助手。帮助用户获取股票、基金、价格等信息。

注意事项：
- 所有价格必须注明来源和时间
- 不提供投资建议
- 说明数据的时效性
- 股票价格有波动，请以实际交易为准
"""

    async def execute_domain_tools(self, state: FinanceSubgraphState) -> str:
        """执行金融工具"""
        from ...services.finance_service import get_finance_service

        query_type = state.get("query_type", "")
        symbol = state.get("symbol", "")

        finance_service = get_finance_service()

        if query_type == "stock":
            stock_data = await finance_service.get_stock_quote(symbol)
            return finance_service.format_stock_info(stock_data)
        elif query_type == "price_compare":
            product = state.get("product_name", "")
            price_data = await finance_service.compare_prices(product)
            return format_price_comparison(price_data)
        else:
            return "请明确您的查询类型（股票查询或价格比较）"


def format_price_comparison(data: dict) -> str:
    """格式化价格比较结果"""
    product = data.get("product", "商品")
    prices = data.get("prices", [])
    best_price = data.get("best_price", 0)
    best_platform = data.get("best_platform", "")

    parts = [
        f"🛒 {product} 价格比较",
        ""
    ]

    for p in prices:
        platform = p.get("platform", "")
        price = p.get("price", 0)
        stock = p.get("stock", "")
        is_best = (platform == best_platform)
        icon = "🏆" if is_best else "  "
        parts.append(f"{icon} {platform}: ¥{price} {stock}")

    parts.append("")
    parts.append(f"💰 最低价: ¥{best_price} ({best_platform})")
    parts.append(f"⏰ 数据来源: {data.get('source', 'unknown')}")

    return "\n".join(parts)


def create_finance_subgraph() -> StateGraph:
    """创建金融子图工作流"""
    workflow = StateGraph(FinanceSubgraphState)

    workflow.add_node("build_plan", nodes.build_plan_node)
    workflow.add_node("execute_tools", nodes.execute_tools_node)
    workflow.add_node("synthesize_result", nodes.synthesize_result_node)

    workflow.add_edge(START, "build_plan")
    workflow.add_edge("build_plan", "execute_tools")
    workflow.add_edge("execute_tools", "synthesize_result")
    workflow.add_edge("synthesize_result", END)

    return workflow.compile()


_finance_subgraph = None


def get_finance_subgraph() -> FinanceSubgraph:
    """获取金融子图实例"""
    global _finance_subgraph
    if _finance_subgraph is None:
        _finance_subgraph = FinanceSubgraph()
    return _finance_subgraph
