import os
import sys
import asyncio
from dotenv import load_dotenv
sys.path.insert(0, '.')
load_dotenv()

print('=== 环境变量 ===')
print('MOCK_MODE:', repr(os.getenv('MOCK_MODE')))
print('Type:', type(os.getenv('MOCK_MODE')))

from app.core.config import settings
print('\n=== Settings ===')
print('settings.mock_mode:', settings.mock_mode)
print('settings.tavily_api_key:', bool(settings.tavily_api_key))

from app.services.search_service import SearchService
print('\n=== SearchService ===')
svc = SearchService()
print('svc.mock_mode:', svc.mock_mode)
print('svc.api_key 设置了:', bool(svc.api_key))
print('svc.api_key 前10字符:', svc.api_key[:10] if svc.api_key else "无")

# 测试搜索
async def test_search():
    result = await svc.search('张雪峰', max_results=1)
    print('\n=== 搜索结果 ===')
    print('source:', result.get('source'))
    if result.get('source') == 'mock':
        print('⚠️  使用了 Mock 搜索！')
    else:
        print('✅ 使用了真实搜索！')
    return result

asyncio.run(test_search())