"""Finance 子图节点实现"""

import re
from ...services.llm_service import get_llm
from ...services.finance_service import get_finance_service
from ...core.logging import logger
from .state import FinanceSubgraphState


async def build_plan_node(state: FinanceSubgraphState) -> FinanceSubgraphState:
    """规划节点 - 分析金融需求"""
    logger.info("[Finance] 正在分析需求...")

    task_input = state.get("task_input", "")

    # 分析查询类型
    if "股票" in task_input or "stock" in task_input.lower():
        state["query_type"] = "stock"

        # 提取股票代码
        # 匹配如 AAPL, 600519, TSLA 等格式
        pattern = r'\b([A-Z]{2,5}|\d{6})\b'
        matches = re.findall(pattern, task_input)
        if matches:
            state["symbol"] = matches[0]
        else:
            # 尝试从中文公司名推断
            if "苹果" in task_input:
                state["symbol"] = "AAPL"
            elif "特斯拉" in task_input:
                state["symbol"] = "TSLA"
            elif "茅台" in task_input:
                state["symbol"] = "600519.SS"
            else:
                state["symbol"] = "AAPL"  # 默认

        state["plan"] = f"查询 {state['symbol']} 的股票信息"

    elif "价格" in task_input or "比价" in task_input or "买" in task_input:
        state["query_type"] = "price_compare"

        # 提取商品名称
        product = task_input.replace("价格", "").replace("比价", "").replace("买", "").strip()
        state["product_name"] = product if product else "示例商品"

        state["plan"] = f"比较 '{state['product_name']}' 的价格"

    else:
        state["query_type"] = "unknown"
        state["plan"] = "分析金融需求"

    return state


async def execute_tools_node(state: FinanceSubgraphState) -> FinanceSubgraphState:
    """工具执行节点 - 执行金融查询"""
    logger.info(f"[Finance] 正在执行 {state.get('query_type')} 查询...")

    query_type = state.get("query_type", "")

    try:
        finance_service = get_finance_service()

        if query_type == "stock":
            symbol = state.get("symbol", "AAPL")
            stock_data = await finance_service.get_stock_quote(symbol)
            state["price_data"] = stock_data

            formatted = finance_service.format_stock_info(stock_data)
            state["intermediate_result"] = formatted

        elif query_type == "price_compare":
            product = state.get("product_name", "")
            price_data = await finance_service.compare_prices(product)
            state["price_data"] = price_data

            formatted = format_price_comparison(price_data)
            state["intermediate_result"] = formatted

        else:
            state["intermediate_result"] = "请明确您的查询类型（股票查询或价格比较）"

    except Exception as e:
        logger.error(f"[Finance] 查询失败: {e}")
        state["intermediate_result"] = f"查询失败: {str(e)}"

    return state


async def synthesize_result_node(state: FinanceSubgraphState) -> FinanceSubgraphState:
    """结果合成节点 - 整理金融信息"""
    logger.info("[Finance] 正在整理结果...")

    intermediate = state.get("intermediate_result", "")
    if intermediate and len(intermediate) > 20:
        state["final_result"] = intermediate
    else:
        state["final_result"] = "金融信息查询完成，请查看详细结果。"

    # 添加数据来源和时间戳
    if state.get("price_data"):
        source = state["price_data"].get("source", "unknown")
        timestamp = state["price_data"].get("timestamp", "")
        state["final_result"] += f"\n\n数据来源: {source}"
        if timestamp:
            state["final_result"] += f"\n更新时间: {timestamp}"

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
        url = p.get("url", "")

        is_best = (platform == best_platform)
        icon = "🏆" if is_best else "  "
        parts.append(f"{icon} {platform}: ¥{price} {stock}")

    parts.append("")
    parts.append(f"💰 最低价: ¥{best_price} ({best_platform})")
    parts.append(f"⏰ 数据来源: {data.get('source', 'unknown')}")
    parts.append(f"📅 时间: {data.get('timestamp', '')}")

    return "\n".join(parts)
