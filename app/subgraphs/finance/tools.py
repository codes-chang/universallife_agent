"""Finance 子图工具定义"""

from ...tools.base import ToolResult
from ...core.config import settings


async def get_stock_quote(symbol: str) -> ToolResult:
    """获取股票报价"""
    from ...services.finance_service import get_finance_service

    service = get_finance_service()
    result = await service.get_stock_quote(symbol)

    return ToolResult(
        success=True,
        data=result,
        source=result.get("source", "yahoo-finance")
    )


async def compare_prices(product_name: str) -> ToolResult:
    """比较商品价格"""
    from ...services.finance_service import get_finance_service

    service = get_finance_service()
    result = await service.compare_prices(product_name)

    return ToolResult(
        success=True,
        data=result,
        source=result.get("source", "mock")
    )
