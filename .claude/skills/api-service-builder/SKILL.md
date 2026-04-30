---
name: api-service-builder
description: Scaffolds a new API service class in app/services/. Use when creating a new external API integration, adding a service that calls a third-party API, or scaffolding any new service class. Triggers on "add a new API service", "create a service for X API", "integrate X API", "new service class".
---

# API Service Builder

Generates a complete API service class following the project's exact conventions.

## Before You Begin

Read these files to understand the patterns:
1. `app/services/weather_service.py` - api_key auth with formatting methods
2. `app/services/search_service.py` - api_key auth in POST body
3. `app/services/academic_service.py` - token-based auth
4. `app/services/finance_service.py` - no auth + LLM integration
5. `app/core/config.py` - Where settings live
6. `.env.example` - Where env vars are documented

## Step 1: Gather Requirements

Ask the user for:
1. **Service name** - PascalCase (e.g., `NewsService`)
2. **API base URL** - The API endpoint
3. **Auth type** - `api_key` / `bearer` / `none`
4. **Key methods** - Method names, HTTP verbs, endpoints, parameters, return data

## Step 2: Generate Service File

Create `app/services/{snake_case}.py` with this structure:

```python
"""{Description} - using {Provider} API"""

import httpx
from typing import Optional, Dict, Any
from ..core.config import settings
from ..core.logging import logger


class {Name}Service:
    """{Description}"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.{setting_name}
        self.base_url = "{url}"

    async def {method}(self, {params}) -> Dict[str, Any]:
        """{Chinese docstring}"""
        if not self.api_key:
            raise ValueError("{SETTING} 未配置")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.{get|post}(url, ...)
            result = response.json()
            return {"key": "value", "source": "{provider}"}

    def format_{method}(self, data: Dict[str, Any]) -> str:
        """格式化结果为文本"""
        ...


_{name}_service: Optional[{Name}Service] = None

def get_{name}_service() -> {Name}Service:
    global _{name}_service
    if _{name}_service is None:
        _{name}_service = {Name}Service()
    return _{name}_service
```

Mandatory conventions:
- All methods async with `httpx.AsyncClient(timeout=30.0)`
- Raise `ValueError` for missing config, `RuntimeError` for API failures
- NEVER add mock fallback
- Return dicts with `"source"` key
- Chinese docstrings
- Singleton pattern with `get_*_service()`

## Step 3: Update config.py

Add setting to `Settings` class:
```python
{setting_name}: str = ""
```

## Step 4: Update .env.example

```
{SETTING_NAME}=your_key_here
```

## Step 5: Verify

- Imports resolve (relative `..core`)
- Config setting matches service
- No mock data anywhere
