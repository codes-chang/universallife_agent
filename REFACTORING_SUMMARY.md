# Universal Life Agent 记忆系统重构总结

## 一、架构说明

重构后的系统引入了完整的分层记忆机制：

### 1.1 三层记忆体系

| 层级 | 存储介质 | 生命周期 | 用途 |
|------|---------|---------|------|
| 工作记忆 | LangGraph State | 当前请求 | 运行时状态，不持久化 |
| 短期记忆 | Redis | 会话级别（TTL） | 最近对话、临时偏好、检查点 |
| 长期记忆 | Milvus | 跨会话 | 用户偏好、任务经历、领域知识 |

### 1.2 主图与子图的记忆职责

**主图负责：**
- 记忆治理：判断是否需要检索记忆
- 记忆检索：协调 Redis 和 Milvus
- 记忆压缩：生成 memory_bundle
- 记忆审查：决定候选记忆是否存储
- 边界控制：避免全局状态污染

**子图负责：**
- 消费主图下发的 memory_bundle
- 在执行后生成 candidate_memories
- 不直接操作长期记忆存储
- 仅输出候选记忆给主图 judge

### 1.3 记忆流程数据流

```
用户请求
    ↓
normalize_input
    ↓
memory_manager (检索 Redis/Milvus)
    ↓ 生成 memory_bundle
route_intent (使用记忆上下文)
    ↓
prepare_memory (为子图准备记忆)
    ↓
branch_to_subgraph (子图消费记忆)
    ↓ 生成 candidate_memories
memory_judge (审查候选记忆)
    ↓ 决定存储到 Redis/Milvus/None
reviewer → finalize_response
```

## 二、改动清单

### 2.1 新增文件

| 文件 | 说明 |
|------|------|
| `app/memory/__init__.py` | 记忆模块入口 |
| `app/memory/models.py` | 数据模型定义 |
| `app/memory/interfaces.py` | 抽象接口定义 |
| `app/memory/embeddings.py` | Embedding 提供者 |
| `app/memory/compressor.py` | 记忆压缩器 |
| `app/memory/redis_store.py` | Redis 短期存储实现 |
| `app/memory/milvus_store.py` | Milvus 长期存储实现 |
| `app/memory/manager.py` | 记忆管理器 + memory_manager_node |
| `app/memory/judge.py` | 记忆审查器 + memory_judge_node |

### 2.2 修改文件

| 文件 | 改动说明 |
|------|---------|
| `app/core/state.py` | 添加 MemoryBundle、记忆相关状态字段 |
| `app/core/config.py` | 添加 Redis/Milvus/Embedding 配置 |
| `app/graph/main_graph.py` | 集成记忆节点到工作流 |
| `app/graph/router.py` | 使用记忆上下文进行路由 |
| `app/subgraphs/base.py` | 支持 memory_input 和 candidate_memories |
| `app/subgraphs/outfit/graph.py` | 示例：生成候选记忆 |
| `requirements.txt` | 添加 redis/pymilvus 等依赖 |
| `.env.example` | 添加记忆系统环境变量 |

## 三、关键数据流

### 3.1 何时查 Redis

**场景：**
- 需要最近对话历史
- 需要最近用户反馈
- 需要缓存的子图结果
- 需要临时用户偏好

**实现位置：** `memory_manager._retrieve_short_term()`

### 3.2 何时查 Milvus

**场景：**
- 触发记忆检索条件（关键词、低置信度等）
- 需要用户长期偏好
- 需要历史任务经历
- 需要领域知识记忆

**实现位置：** `memory_manager._retrieve_long_term()`

### 3.3 何时注入 memory_bundle

**时机：**
- 在 `route_intent` 之前通过 `memory_manager_node` 生成
- 在 `prepare_memory_for_subgraph` 中转换为子图输入格式
- 子图在 `build_plan` 时可以访问记忆上下文

### 3.4 何时生成 candidate_memories

**时机：**
- 子图执行完成后，在 `generate_candidate_memories()` 中生成
- 基于：用户偏好提取、任务成功经验、失败教训
- 返回给主图的 `memory_judge_node` 进行审查

### 3.5 何时写回 Redis/Milvus

**决策逻辑（在 memory_judge_node 中）：**

| 目标 | 条件 |
|------|------|
| NONE | 分数 < 0.4 或重要性/置信度过低 |
| Redis | 0.4 <= 分数 < 0.7 或会话类记忆 |
| Milvus | 分数 >= 0.7 且重要性/置信度都高 |
| BOTH | auto_upgrade=true 且重要性 > 0.8 |

## 四、状态结构说明

### 4.1 主图新增字段

```python
# 记忆束 - 由 memory_manager 生成
memory_bundle: Optional[MemoryBundle]

# 记忆上下文 - 用于注入 prompt 的格式化记忆
memory_context: Optional[str]

# 子图记忆输入 - 传递给子图的记忆数据
subgraph_memory_input: Optional[dict[str, Any]]

# 记忆决策 - 由 memory_judge 生成的存储决策
memory_decisions: list[dict[str, Any]]

# 候选记忆 - 由子图生成，等待 judge 审查
candidate_memories: list[Any]
```

### 4.2 子图新增字段

```python
# 记忆输入（由主图提供）
memory_input: Optional[dict[str, Any]]

# 候选记忆（输出给主图 judge）
candidate_memories: list[dict[str, Any]]
```

## 五、配置说明

### 5.1 核心配置项

```bash
# 记忆系统开关
MEMORY_ENABLED=true
MEMORY_FALLBACK_ON_ERROR=true

# Embedding 配置
EMBEDDING_PROVIDER=mock  # mock/openai/sentence-transformer

# Redis 配置
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
REDIS_TTL_SESSION=3600

# Milvus 配置
MILVUS_ENABLED=false
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 记忆检索配置
MEMORY_RETRIEVE_THRESHOLD=0.3
MEMORY_MAX_RESULTS=10
MEMORY_MIN_SCORE=0.6

# 记忆存储配置
MEMORY_STORE_IMPORTANCE_THRESHOLD=0.7
MEMORY_STORE_CONFIDENCE_THRESHOLD=0.6
```

### 5.2 降级策略

1. **Redis/Milvus 不可用**：自动使用 Mock 存储
2. **Embedding 不可用**：使用基于哈希的伪向量
3. **记忆检索失败**：系统继续运行，只是没有记忆

## 六、后续建议

### 6.1 未完成但可以继续优化

1. **向量检索优化**：
   - 实现真正的 Milvus 向量检索（当前 Mock 模式）
   - 添加 rerank 机制提升检索质量

2. **记忆挖掘增强**：
   - 使用 LLM 自动抽取用户偏好
   - 实现记忆的重要性自动评估

3. **记忆更新机制**：
   - 支持记忆的更新和合并
   - 实现记忆的遗忘和淘汰策略

4. **子图全覆盖**：
   - 为所有子图（search/finance/academic/trip）添加候选记忆生成
   - 根据领域特点定制记忆抽取逻辑

### 6.2 扩展方向

1. **多用户隔离**：
   - 增强用户 ID 管理
   - 支持多租户场景

2. **记忆共享**：
   - 支持跨用户的通用知识记忆
   - 实现"社区记忆"功能

3. **记忆可视化**：
   - 添加记忆管理 API
   - 实现记忆浏览和编辑界面

4. **A/B 测试**：
   - 支持不同记忆策略的对比
   - 记忆效果评估指标

## 七、工程假设说明

1. **session_id 作为 user_id**：当前简化使用 session_id 作为用户标识
2. **默认 Mock 模式**：Redis/Milvus 默认关闭，使用 Mock 存储
3. **记忆阈值固定**：当前使用固定阈值，可扩展为动态调整
4. **向量维度**：默认 1536（与 OpenAI embedding 一致）

---

**重构完成时间**：2026-03-25
**核心原则**：主图治理、子图消费、按需检索、质量优先
