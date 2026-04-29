"""Finance 子图 - 金融购物"""

from .state import FinanceSubgraphState
from . import nodes
from ..base import BaseSubgraph
from ...core.logging import logger
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope


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

    async def generate_candidate_memories(self, state: FinanceSubgraphState) -> FinanceSubgraphState:
        """生成金融相关的候选记忆"""
        candidates = []

        task_input = state.get("task_input", "")

        # 提取金融偏好关键词
        preference_keywords = {
            "投资偏好": ["稳健", "激进", "长期", "短期", "价值投资", "成长股"],
            "关注行业": ["科技", "金融", "医疗", "新能源", "消费", "地产"],
            "价格敏感度": ["性价比", "高端", "平价", "折扣", "优惠", "预算"]
        }

        extracted_preferences = []
        for pref_type, keywords in preference_keywords.items():
            for keyword in keywords:
                if keyword in task_input:
                    extracted_preferences.append(f"{pref_type}: {keyword}")

        # 生成偏好候选记忆
        for pref in extracted_preferences:
            candidate = MemoryCandidate(
                content=f"用户金融偏好: {pref}",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.DOMAIN,
                domain="finance",
                importance=0.7,
                confidence=0.75,
                source="subgraph:finance",
                metadata={"preference_type": "finance_style", "original_query": task_input}
            )
            candidates.append(candidate.model_dump())

        # 如果执行成功，生成经验记忆
        final_result = state.get("final_result", "")
        if final_result and "失败" not in final_result:
            experience_candidate = MemoryCandidate(
                content=f"成功完成金融查询任务: {task_input[:50]}...",
                memory_type=MemoryType.TASK_EPISODE,
                scope=MemoryScope.DOMAIN,
                domain="finance",
                importance=0.5,
                confidence=0.6,
                source="subgraph:finance",
                metadata={"task_type": "finance_query"}
            )
            candidates.append(experience_candidate.model_dump())

        # 更新状态
        state["candidate_memories"] = candidates

        if candidates:
            logger.info(f"[FinanceSubgraph] 生成 {len(candidates)} 个候选记忆")

        return state


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


_finance_subgraph = None


def get_finance_subgraph() -> FinanceSubgraph:
    """获取金融子图实例"""
    global _finance_subgraph
    if _finance_subgraph is None:
        _finance_subgraph = FinanceSubgraph()
    return _finance_subgraph
