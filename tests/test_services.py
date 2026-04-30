"""服务层测试 - 使用 unittest.mock 模拟 HTTP 调用"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ======================================================================
# WeatherService Tests
# ======================================================================

class TestWeatherService:
    """天气服务测试"""

    @pytest.mark.asyncio
    async def test_get_weather_success(self):
        """测试天气查询成功"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "1",
            "forecasts": [
                {
                    "city": "上海",
                    "province": "上海",
                    "reporttime": "2026-03-24 12:00:00",
                    "casts": [
                        {
                            "date": "2026-03-25",
                            "week": "3",
                            "dayweather": "小雨",
                            "nightweather": "小雨",
                            "daytemp": "15",
                            "nighttemp": "10",
                            "daywinddirection": "东",
                            "daywindpower": "3",
                            "nightwinddirection": "东北",
                            "nightwindpower": "2"
                        }
                    ]
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.get_weather("上海", days=3)

        assert result["city"] == "上海"
        assert result["province"] == "上海"
        assert len(result["casts"]) == 1
        assert result["casts"][0]["day_weather"] == "小雨"
        assert result["casts"][0]["day_temp"] == "15"
        assert result["casts"][0]["night_temp"] == "10"

    @pytest.mark.asyncio
    async def test_get_weather_no_api_key(self):
        """测试未配置 API Key 时抛出 ValueError"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="")

        with pytest.raises(ValueError, match="AMAP_API_KEY"):
            await service.get_weather("上海")

    @pytest.mark.asyncio
    async def test_get_weather_api_error(self):
        """测试高德 API 返回错误时抛出 RuntimeError"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "0",
            "info": "INVALID_USER_KEY"
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="高德天气 API"):
                await service.get_weather("上海")

    @pytest.mark.asyncio
    async def test_get_weather_city_not_found(self):
        """测试城市未找到时抛出 RuntimeError"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "1",
            "forecasts": []
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="未找到城市"):
                await service.get_weather("不存在的城市")

    def test_get_weather_summary(self):
        """测试天气摘要格式化"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        weather_data = {
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

        summary = service.get_weather_summary(weather_data)

        assert "上海" in summary
        assert "小雨" in summary
        assert "15" in summary
        assert "10" in summary

    def test_get_weather_summary_empty(self):
        """测试空天气数据返回默认信息"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        assert service.get_weather_summary(None) == "暂无天气信息"
        assert service.get_weather_summary({}) == "暂无天气信息"

    def test_check_rain(self):
        """测试雨天检测"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        rainy_data = {
            "casts": [
                {"day_weather": "小雨", "night_weather": "多云"}
            ]
        }
        assert service.check_rain(rainy_data) is True

        sunny_data = {
            "casts": [
                {"day_weather": "晴", "night_weather": "多云"}
            ]
        }
        assert service.check_rain(sunny_data) is False

        night_rain_data = {
            "casts": [
                {"day_weather": "多云", "night_weather": "大雨"}
            ]
        }
        assert service.check_rain(night_rain_data) is True

        assert service.check_rain(None) is False
        assert service.check_rain({}) is False

    def test_get_temperature(self):
        """测试温度范围获取"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        data = {
            "casts": [
                {"day_temp": "20", "night_temp": "12"},
                {"day_temp": "25", "night_temp": "15"},
                {"day_temp": "18", "night_temp": "10"}
            ]
        }

        max_temp, min_temp = service.get_temperature(data)
        assert max_temp == 25
        assert min_temp == 10

    def test_get_temperature_empty(self):
        """测试空数据时返回默认温度"""
        from app.services.weather_service import WeatherService

        service = WeatherService(api_key="test_key")

        max_temp, min_temp = service.get_temperature(None)
        assert max_temp == 25
        assert min_temp == 15

        max_temp, min_temp = service.get_temperature({})
        assert max_temp == 25
        assert min_temp == 15


# ======================================================================
# SearchService Tests
# ======================================================================

class TestSearchService:
    """搜索服务测试"""

    @pytest.mark.asyncio
    async def test_search_success(self):
        """测试搜索成功"""
        from app.services.search_service import SearchService

        service = SearchService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "answer": "LangChain is a framework for building LLM applications.",
            "results": [
                {
                    "title": "LangChain Documentation",
                    "url": "https://docs.langchain.com",
                    "content": "LangChain is a framework...",
                    "score": 0.95,
                    "published_date": "2026-01-15"
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.search_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.search("LangChain tutorial")

        assert result["query"] == "LangChain tutorial"
        assert result["answer"] == "LangChain is a framework for building LLM applications."
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "LangChain Documentation"
        assert result["results"][0]["snippet"] == "LangChain is a framework..."
        assert result["source"] == "tavily"

    @pytest.mark.asyncio
    async def test_search_no_api_key(self):
        """测试未配置 API Key 时抛出 ValueError"""
        from app.services.search_service import SearchService

        service = SearchService(api_key="")

        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            await service.search("test query")

    def test_format_search_results(self):
        """测试搜索结果格式化"""
        from app.services.search_service import SearchService

        service = SearchService(api_key="test_key")

        search_data = {
            "answer": "LangChain is a framework",
            "results": [
                {
                    "title": "LangChain Docs",
                    "url": "https://docs.langchain.com",
                    "snippet": "LangChain is a framework for building LLM apps",
                    "score": 0.95,
                    "published_date": "2026-01-15"
                }
            ]
        }

        formatted = service.format_search_results(search_data)
        assert "摘要" in formatted
        assert "LangChain" in formatted
        assert "搜索结果" in formatted

    def test_format_search_results_empty(self):
        """测试空搜索结果"""
        from app.services.search_service import SearchService

        service = SearchService(api_key="test_key")

        assert service.format_search_results(None) == "无搜索结果"
        assert service.format_search_results({}) == "无搜索结果"


# ======================================================================
# FinanceService Tests
# ======================================================================

class TestFinanceService:
    """金融服务测试"""

    @pytest.mark.asyncio
    async def test_get_stock_quote_success(self):
        """测试股票报价查询成功"""
        from app.services.finance_service import FinanceService

        service = FinanceService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "AAPL",
                            "regularMarketPrice": 178.50,
                            "previousClose": 176.20,
                            "regularMarketDayHigh": 180.00,
                            "regularMarketDayLow": 175.50,
                            "regularMarketVolume": 50000000,
                            "marketState": "REGULAR",
                            "exchangeName": "NMS"
                        },
                        "indicators": {
                            "quote": [
                                {"close": [178.50]}
                            ]
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.finance_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.get_stock_quote("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["price"] == 178.50
        assert result["change"] == pytest.approx(2.30, abs=0.01)
        assert result["source"] == "yahoo-finance"

    @pytest.mark.asyncio
    async def test_get_stock_quote_not_found(self):
        """测试股票代码未找到"""
        from app.services.finance_service import FinanceService

        service = FinanceService()

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.finance_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="未找到"):
                await service.get_stock_quote("INVALID")

    @pytest.mark.asyncio
    async def test_get_stock_quote_no_data(self):
        """测试返回空数据"""
        from app.services.finance_service import FinanceService

        service = FinanceService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chart": {
                "result": []
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.finance_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="未获取到"):
                await service.get_stock_quote("AAPL")

    def test_format_stock_info(self):
        """测试股票信息格式化"""
        from app.services.finance_service import FinanceService

        service = FinanceService()

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 178.50,
            "change": 2.30,
            "change_percent": 1.30,
            "high": 180.00,
            "low": 175.50,
            "volume": 50000000,
            "timestamp": "2026-03-24T12:00:00",
            "source": "yahoo-finance"
        }

        formatted = service.format_stock_info(stock_data)

        assert "AAPL" in formatted
        assert "178.50" in formatted
        assert "+" in formatted  # positive change


# ======================================================================
# AcademicService Tests
# ======================================================================

class TestAcademicService:
    """学术服务测试"""

    @pytest.mark.asyncio
    async def test_search_github_success(self):
        """测试 GitHub 搜索成功"""
        from app.services.academic_service import AcademicService

        service = AcademicService(github_token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 1,
            "items": [
                {
                    "id": 12345,
                    "name": "langgraph",
                    "full_name": "langchain-ai/langgraph",
                    "description": "LangGraph is a library for building stateful applications",
                    "language": "Python",
                    "stargazers_count": 15000,
                    "forks_count": 2000,
                    "html_url": "https://github.com/langchain-ai/langgraph",
                    "updated_at": "2026-03-20T10:00:00Z"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.academic_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.search_github("langgraph")

        assert result["query"] == "langgraph"
        assert result["total_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "langgraph"
        assert result["results"][0]["stars"] == 15000
        assert result["source"] == "github"

    @pytest.mark.asyncio
    async def test_search_github_rate_limit(self):
        """测试 GitHub API 速率限制"""
        from app.services.academic_service import AcademicService

        service = AcademicService(github_token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.academic_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="速率限制"):
                await service.search_github("test")

    @pytest.mark.asyncio
    async def test_search_arxiv_success(self):
        """测试 arXiv 搜索"""
        from app.services.academic_service import AcademicService

        service = AcademicService()

        # Mock arxiv module
        mock_paper = MagicMock()
        mock_paper.title = "Attention Is All You Need"
        mock_paper.authors = [MagicMock(name="Author1")]
        mock_paper.authors[0].name = "Ashish Vaswani"
        mock_paper.summary = "We propose a new simple network architecture, the Transformer."
        mock_paper.published = MagicMock()
        mock_paper.published.isoformat = MagicMock(return_value="2017-06-12T00:00:00")
        mock_paper.entry_id = "https://arxiv.org/abs/1706.03762"
        mock_paper.pdf_url = "https://arxiv.org/pdf/1706.03762"
        mock_paper.primary_category = "cs.CL"

        mock_search_result = MagicMock()
        mock_search_result.results = MagicMock(return_value=[mock_paper])

        mock_arxiv_module = MagicMock()
        mock_arxiv_module.Search = MagicMock(return_value=mock_search_result)
        mock_arxiv_module.SortCriterion = MagicMock(Relevance="relevance")

        with patch.dict("sys.modules", {"arxiv": mock_arxiv_module}):
            result = await service.search_arxiv("transformer attention")

        assert result["query"] == "transformer attention"
        assert result["total_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Attention Is All You Need"
        assert result["source"] == "arxiv"

    @pytest.mark.asyncio
    async def test_get_github_repo_not_found(self):
        """测试 GitHub 仓库不存在"""
        from app.services.academic_service import AcademicService

        service = AcademicService(github_token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.academic_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="不存在"):
                await service.get_github_repo("nonexistent", "repo")

    def test_format_github_results(self):
        """测试 GitHub 搜索结果格式化"""
        from app.services.academic_service import AcademicService

        service = AcademicService()

        data = {
            "total_count": 1,
            "results": [
                {
                    "full_name": "langchain-ai/langgraph",
                    "description": "LangGraph library",
                    "language": "Python",
                    "stars": 15000,
                    "url": "https://github.com/langchain-ai/langgraph"
                }
            ]
        }

        formatted = service.format_github_results(data)
        assert "langchain-ai/langgraph" in formatted
        assert "Python" in formatted
        assert "15000" in formatted

    def test_format_github_results_empty(self):
        """测试空 GitHub 搜索结果"""
        from app.services.academic_service import AcademicService

        service = AcademicService()

        assert service.format_github_results({"results": []}) == "未找到相关仓库"

    def test_format_arxiv_results(self):
        """测试 arXiv 搜索结果格式化"""
        from app.services.academic_service import AcademicService

        service = AcademicService()

        data = {
            "total_count": 1,
            "results": [
                {
                    "title": "Attention Is All You Need",
                    "authors": ["Ashish Vaswani"],
                    "summary": "We propose a new simple network architecture.",
                    "arxiv_url": "https://arxiv.org/abs/1706.03762"
                }
            ]
        }

        formatted = service.format_arxiv_results(data)
        assert "Attention Is All You Need" in formatted
        assert "Vaswani" in formatted
