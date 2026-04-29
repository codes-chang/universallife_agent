"""金融服务 - Yahoo Finance API + 价格比较"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import settings
from ..core.logging import logger
from ..tools.mocks import MockToolRegistry


class FinanceService:
    """金融服务

    提供股票查询、价格比较等功能。
    Yahoo Finance API 无需认证，可直接使用。
    """

    def __init__(self, mock_mode: bool = None):
        if mock_mode is None:
            self.mock_mode = settings.mock_mode
        else:
            self.mock_mode = mock_mode

        self.yahoo_base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    async def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票报价

        Args:
            symbol: 股票代码 (如 AAPL, TSLA)

        Returns:
            股票数据字典
        """
        if self.mock_mode:
            return await self._mock_stock_quote(symbol)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Yahoo Finance API
                url = f"{self.yahoo_base_url}/{symbol}"
                params = {
                    "interval": "1d",
                    "range": "1d"
                }

                response = await client.get(url, params=params)
                result = response.json()

                chart = result.get("chart", {})
                result_data = chart.get("result", [])
                if not result_data:
                    return await self._mock_stock_quote(symbol)

                meta = result_data[0].get("meta", {})
                regular_time = result_data[0].get("regularTime", {})
                indicators = result_data[0].get("indicators", {})
                quote = indicators.get("quote", [{}])[0]

                current_price = quote.get("close", [meta.get("regularMarketPrice", 0)])[-1]
                previous_close = meta.get("previousClose", current_price)

                return {
                    "symbol": symbol.upper(),
                    "name": meta.get("symbol", symbol),
                    "price": current_price,
                    "change": current_price - previous_close,
                    "change_percent": ((current_price - previous_close) / previous_close * 100) if previous_close else 0,
                    "high": meta.get("regularMarketDayHigh", 0),
                    "low": meta.get("regularMarketDayLow", 0),
                    "volume": meta.get("regularMarketVolume", 0),
                    "market_state": meta.get("marketState", "UNKNOWN"),
                    "exchange": meta.get("exchangeName", "UNKNOWN"),
                    "timestamp": datetime.now().isoformat(),
                    "source": "yahoo-finance"
                }

        except Exception as e:
            logger.error(f"股票查询异常: {e}")
            return await self._mock_stock_quote(symbol)

    async def _mock_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Mock 股票数据"""
        mock_data = MockToolRegistry.get_finance_mock(symbol)
        return {**mock_data, "timestamp": datetime.now().isoformat()}

    async def compare_prices(self, product_name: str) -> Dict[str, Any]:
        """
        比较商品价格

        Args:
            product_name: 商品名称

        Returns:
            价格比较数据
        """
        # 目前使用 Mock，后续可接入真实比价 API
        return await self._mock_price_compare(product_name)

    async def _mock_price_compare(self, product_name: str) -> Dict[str, Any]:
        """Mock 价格比较"""
        return {
            "product": product_name,
            "prices": [
                {
                    "platform": "京东",
                    "price": 299.00,
                    "url": "https://jd.com/example",
                    "stock": "有货"
                },
                {
                    "platform": "淘宝",
                    "price": 289.00,
                    "url": "https://taobao.com/example",
                    "stock": "有货"
                },
                {
                    "platform": "拼多多",
                    "price": 279.00,
                    "url": "https://pinduoduo.com/example",
                    "stock": "有货"
                }
            ],
            "best_price": 279.00,
            "best_platform": "拼多多",
            "timestamp": datetime.now().isoformat(),
            "source": "mock",
            "note": "当前使用 Mock 数据，暂未接入真实比价 API"
        }

    def format_stock_info(self, stock_data: Dict[str, Any]) -> str:
        """格式化股票信息为文本"""
        symbol = stock_data.get("symbol", "N/A")
        name = stock_data.get("name", symbol)
        price = stock_data.get("price", 0)
        change = stock_data.get("change", 0)
        change_percent = stock_data.get("change_percent", 0)
        high = stock_data.get("high", 0)
        low = stock_data.get("low", 0)
        volume = stock_data.get("volume", 0)
        timestamp = stock_data.get("timestamp", "")

        # 格式化成交量
        if volume > 100000000:
            volume_str = f"{volume / 100000000:.2f}亿"
        elif volume > 10000:
            volume_str = f"{volume / 10000:.2f}万"
        else:
            volume_str = str(volume)

        # 涨跌标识
        change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        change_str = f"+{change:.2f}" if change > 0 else f"{change:.2f}"
        change_percent_str = f"+{change_percent:.2f}%" if change_percent > 0 else f"{change_percent:.2f}%"

        return f"""📊 {name} ({symbol})
   当前价格: ${price:.2f}
   涨跌: {change_symbol} {change_str} ({change_percent_str})
   今日最高: ${high:.2f}
   今日最低: ${low:.2f}
   成交量: {volume_str}
   更新时间: {timestamp}
   数据来源: {stock_data.get("source", "unknown")}"""


# ============ 全局实例 ============

_finance_service: Optional[FinanceService] = None


def get_finance_service() -> FinanceService:
    """获取金融服务实例"""
    global _finance_service
    if _finance_service is None:
        _finance_service = FinanceService()
    return _finance_service
