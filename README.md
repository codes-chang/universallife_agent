# Universal Life Agent

基于 LangGraph 的全场景通用智能助手系统。支持多领域任务处理、语义路由、多步规划、工具调用、结果审查与自我修正。

## 项目简介

Universal Life Agent 是一个企业级的智能助手框架，通过"主图 + 垂直子图"架构支持多个业务领域：

- **Outfit** - 穿搭建议（基于天气、场合、风格）
- **Search** - 全网搜索（Tavily API）
- **Finance** - 金融购物（股票查询、价格比较）
- **Academic** - 学术办公（GitHub、arXiv）
- **Trip** - 旅行规划（景点、酒店、行程）

## 核心特性

### 智能路由
- LLM 驱动的语义意图识别
- 置信度评分与自动重路由
- 负反馈检测与意图纠错
- 路由历史记录与避错

### 审查机制
- 各领域的硬规则校验
- 审查不通过时触发回流
- 最多 3 次自我修正迭代
- 优雅降级处理

### 工具集成
- 统一的工具接口（BaseTool）
- MCP（Model Context Protocol）适配器
- 真实 API 优先，Mock 自动回退
- 工具可用性自动检测

### 可扩展架构
- 模块化子图设计
- 独立的领域状态管理
- 统一的服务层抽象
- 清晰的代码组织

## 项目结构

```
universal_life_agent/
├── app/
│   ├── main.py                           # FastAPI 应用入口
│   ├── api/
│   │   └── routes.py                     # API 路由
│   ├── core/
│   │   ├── config.py                     # 配置管理
│   │   ├── state.py                      # 状态模型
│   │   ├── models.py                     # Pydantic 数据模型
│   │   ├── prompts.py                    # Prompt 模板
│   │   └── logging.py                    # 日志配置
│   ├── graph/
│   │   ├── main_graph.py                 # 主图编排
│   │   ├── router.py                     # 语义路由器
│   │   ├── reviewer.py                   # 审查器
│   │   └── recovery.py                   # 恢复逻辑
│   ├── subgraphs/                        # 领域子图
│   │   ├── base.py                       # 子图基类
│   │   ├── outfit/                       # 穿搭子图
│   │   ├── search/                       # 搜索子图
│   │   ├── finance/                      # 金融子图
│   │   ├── academic/                     # 学术子图
│   │   └── trip/                         # 旅行子图
│   ├── tools/                            # 工具层
│   │   ├── base.py                       # 工具基类
│   │   ├── adapters.py                   # MCP/API 适配器
│   │   ├── registry.py                   # 工具注册中心
│   │   └── mocks.py                      # Mock 工具
│   ├── services/                         # 服务层
│   │   ├── llm_service.py                # LLM 服务
│   │   ├── weather_service.py            # 天气服务
│   │   ├── search_service.py             # 搜索服务
│   │   ├── finance_service.py            # 金融数据服务
│   │   └── academic_service.py           # 学术资源服务
│   └── utils/                            # 工具函数
├── tests/                                # 测试文件
├── .env.example                          # 环境变量模板
├── requirements.txt                       # Python 依赖
├── run.py                                # 启动脚本
└── README.md                             # 项目文档
```

## 安装方法

### 1. 克隆项目

```bash
cd e:\learning\LLM\hello-agents\code\chapter13
git clone <repository-url> universal_life_agent
cd universal_life_agent
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的 API Key：

```env
# LLM 配置（必需）
LLM_API_KEY=your-openai-api-key
LLM_MODEL_ID=gpt-4
LLM_BASE_URL=https://api.openai.com/v1

# 高德地图 API（Outfit/Trip 功能）
AMAP_API_KEY=your_amap_api_key

# Tavily 搜索 API（Search 功能）
TAVILY_API_KEY=your_tavily_api_key

# GitHub Token（Academic 功能）
GITHUB_TOKEN=your_github_token

# 开发模式
MOCK_MODE=false
```

## 运行方法

### 启动服务

```bash
python run.py
```

服务将运行在 `http://localhost:8000`

### 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 使用示例

### 聊天接口

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "明天上海下雨，帮我搭配一套适合通勤的穿搭"
  }'
```

**响应示例：**

```json
{
  "success": true,
  "message": "处理完成",
  "router_result": {
    "primary_intent": "outfit",
    "secondary_intents": ["weather"],
    "confidence": 0.95,
    "reasoning": "用户询问穿搭建议",
    "constraints": {"location": "上海", "weather": "雨"}
  },
  "active_domain": "outfit",
  "final_answer": "👔 上海 穿搭建议\n🌤️ 天气: 小雨，15°C\n📍 场景: 通勤\n..."
}
```

### 反馈接口

```bash
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你理解错了，我是要买防雨通勤鞋",
    "session_id": "user-123"
  }'
```

### 其他查询示例

```bash
# 搜索
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "搜索 LangChain 最新教程"}'

# 股票查询
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询 AAPL 股票价格"}'

# GitHub 搜索
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查找 langgraph GitHub 仓库"}'

# 旅行规划
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "规划北京 3 天旅行"}'
```

## 测试方法

### 运行所有测试

```bash
pytest
```

### 运行特定测试

```bash
pytest tests/test_router.py
pytest tests/test_outfit_flow.py -v
pytest tests/test_finance_flow.py -v
```

### 查看测试覆盖率

```bash
pytest --cov=app --cov-report=html
```

## 架构说明

### 主图流程

```
START
  → normalize_input (输入归一化)
  → route_intent (语义路由)
  → branch_to_subgraph (执行子图)
  → reviewer (结果审查)
  → [if pass] → finalize_response → END
  → [if fail] → recovery (恢复处理) → reviewer
```

### 子图流程

```
START
  → build_plan (制定计划)
  → execute_tools (执行工具)
  → synthesize_result (合成结果)
  → END
```

### 路由决策

- **置信度 >= 0.7**: 直接路由
- **置信度 < 0.7**: 触发重路由
- **负反馈检测**: 触发重路由并避开失败意图
- **最大重试 3 次**: 优雅降级

### 审查规则

| 领域 | 规则 |
|------|------|
| Outfit | 必须匹配天气、温度、场合 |
| Search | 必须有来源和时间戳 |
| Finance | 必须说明价格来源和时间 |
| Academic | 必须包含来源链接 |
| Trip | 必须有具体景点和合理行程 |

## 后续扩展建议

### 1. MCP Server 集成

- 接入真实的小红书 MCP（穿搭趋势）
- 接入 LlamaParse MCP（PDF 解析）
- 接入电商比价 MCP（大淘客）

### 2. 更多领域

- **Health**: 健康咨询、运动建议
- **Cooking**: 烹饪食谱、营养搭配
- **Code**: 代码审查、调试助手

### 3. 持久化

- Redis 缓存对话历史
- SQLite 存储用户偏好
- 日志持久化与分析

### 4. 前端更新

- Vue3 对话界面
- 流式输出支持
- 多模态输入（图片）

### 5. 性能优化

- 子图并行执行
- LLM 响应缓存
- 工具调用批处理

## 技术栈

- **Python 3.11+**
- **LangChain** - LLM 应用框架
- **LangGraph** - 工作流编排
- **FastAPI** - API 服务
- **Pydantic** - 数据验证
- **Pytest** - 测试框架

## 依赖服务

| 服务 | 用途 | 是否必需 |
|------|------|----------|
| OpenAI API | LLM 服务 | 是* |
| 高德地图 | 天气/POI | 否（可用 Mock） |
| Tavily | 网络搜索 | 否（可用 Mock） |
| GitHub | 代码搜索 | 否（可用 Mock） |

*注：可使用其他兼容 OpenAI 的 API（如 DeepSeek、GLM 等）

## License

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request
