你是一个资深 AI Agent 系统架构师、Python 工程师、LangGraph 重构专家。
请你对我当前的项目进行一次面向生产可维护性的高质量重构，目标是在尽量保留现有能力的前提下，为系统引入分层记忆机制，包括：

短期记忆：Redis
长期记忆：Milvus
按需检索与注入机制
主图 / 子图的记忆读写边界
记忆候选生成、筛选、持久化闭环
一、项目背景

我的项目是一个基于 LangGraph 的全能型多智能体生活助手（Universal Life Agent）。

当前架构核心特点：

使用 主图 - 子图（Main Graph - Domain Subgraphs） 架构
主图负责：
全局状态管理
用户原始请求
意图路由
历史路由尝试
最终结果整合
用户反馈处理
子图负责垂直领域任务执行，例如：
outfit（穿搭）
finance（金融/购物）
academic（学术/办公）
search（全网检索）
路由层使用大模型做意图识别，输出：
primary_intent
confidence
系统已有 reviewer / reflection loop：
结果审查
critique 回流
plan 迭代修正
工具层偏向 MCP / API 动态调用
二、这次重构的核心目标

请你帮助我对现有代码进行结构化重构，并加入完整的记忆体系。目标不是简单加几个 memory function，而是做成清晰、可扩展、低耦合的架构。

请重点完成以下目标：

目标 1：建立三层记忆体系

请在系统中清晰区分以下三类：

1）工作记忆（Working Memory）
当前 LangGraph state 内的运行时信息
仅用于当前执行过程
不做长期存储
2）短期记忆（Short-term Memory, Redis）

用于保存：

最近若干轮会话摘要
当前会话上下文
当前任务检查点
子图执行中间结果
最近用户反馈标签
近期偏好 / 临时约束
中断恢复信息
3）长期记忆（Long-term Memory, Milvus）

用于保存：

用户长期偏好
用户画像
跨会话重要任务经历
对用户有效的成功策略
高价值领域知识沉淀
经过筛选后的结构化 memory items
目标 2：明确主图和子图的记忆职责边界

请按下面原则重构：

主图负责
记忆治理
是否触发记忆检索
聚合 Redis 与 Milvus 结果
生成 memory bundle
控制注入时机
控制长期记忆写入
避免全局 state 被污染
子图负责
消费主图下发的 memory bundle
在执行后生成 candidate memories
不直接无约束写入长期记忆
仅输出候选记忆给上层判断
目标 3：加入两个专门的记忆节点

请为系统设计并实现两个新节点：

A. memory_manager_node

职责：

判断当前是否需要检索记忆
判断检索 Redis / Milvus / Both / None
基于当前用户请求、意图、历史反馈、领域信息构建检索 query
聚合、排序、去重、压缩记忆
输出结构化 memory_bundle
B. memory_judge_node

职责：

接收子图输出的 candidate memories
判断是否存储
判断写入 Redis / Milvus / Both / None
给出记忆类型与 metadata
控制长期记忆质量，避免垃圾写入
三、希望实现的记忆设计原则

请严格遵循以下原则：

1）不要把长期记忆默认注入所有 prompt

必须做按需注入。

只有在这些情况才考虑检索长期记忆：

用户请求依赖历史偏好
路由置信度低
多步规划任务
reviewer 指出缺少上下文
用户显式提到“上次 / 之前 / 延续 / 记得”
强个性化任务（推荐、规划、购物、穿搭、学术建议等）
2）不要把所有对话直接写进 Milvus

长期记忆必须经过：

抽取
结构化
去噪
打分
分类
决策后再写入
3）默认先写 Redis，再判断是否升格到 Milvus

只有满足以下条件之一，才考虑入长期记忆：

多次重复出现
用户显式要求记住
明显属于长期偏好
是高价值成功经验
reviewer / judge 判定高 importance + high confidence
4）记忆必须支持领域隔离

比如：

outfit 记忆不要污染 academic prompt
finance 记忆不要无差别注入全局
需要支持 global / domain 两级记忆视图
5）注入内容必须压缩

不要把检索结果原文大段塞进 prompt。
需要压缩成结构化 bundle，例如：

全局偏好若干条
当前领域相关经验若干条
最近短期上下文若干条
四、希望你输出的重构结果

请你不要只给建议，而是尽可能直接改代码。如果需要，请分步骤执行，但每一步都要尽量落地。

请按以下顺序完成：

第一步：先审查现有代码结构

请先完整理解代码库，并输出：

当前项目目录结构概览
主图入口文件位置
子图定义位置
state schema 定义位置
router / planner / reviewer 节点位置
tool 调用层位置
当前最适合插入 memory 层的模块位置
当前代码中可能存在的耦合问题、状态污染问题、重复逻辑问题

如果现有架构不利于引入记忆，请明确指出。

第二步：给出重构方案

请输出一个面向落地代码的重构计划，至少包括：

新的模块划分
新增文件建议
需要修改的旧文件
新的数据流
主图与子图状态边界
Redis 与 Milvus 的接入层设计
记忆检索 / 存储 / 注入的生命周期
风险点与兼容策略
第三步：直接实施代码重构

请你直接修改代码，实现以下能力：

A. 新增记忆模块

建议新增类似目录（可调整，但要合理）：

memory/
interfaces.py
models.py
redis_store.py
milvus_store.py
retriever.py
writer.py
compressor.py
judge.py
manager.py
B. 新增统一数据模型

至少定义清晰的数据结构，例如：

MemoryItem
MemoryCandidate
MemoryBundle
MemoryDecision
SessionCheckpoint
RecentContext
UserPreferenceMemory
EpisodeMemory
ProcedureMemory

可以使用 pydantic / dataclass，但要统一、可维护。

C. Redis 存储层

请实现短期记忆能力，包括：

session timeline
recent feedback
checkpoint
subgraph last result
recent preferences
TTL 策略
读写接口封装
错误处理与 graceful fallback
D. Milvus 存储层

请实现长期记忆能力，包括：

collection 初始化
upsert / search / filter
metadata 结构
user_id / domain / memory_type 过滤
时间与 importance / confidence 等字段
向量检索接口封装
可替换 embedding provider 的设计
E. 记忆检索编排

实现 memory_manager_node：

根据当前请求判断是否查记忆
生成 query
先查 Redis，再按需查 Milvus
做 merge / rerank / dedupe / compress
输出给后续节点的 memory_bundle
F. 记忆候选写入与审查

实现 memory_judge_node：

接收 candidate memories
打分：
relevance
durability
user_specificity
novelty
confidence
选择 target：
none / redis / milvus / both
对长期记忆严格筛选
G. 修改主图

请把记忆流程接入主图：

router 前后是否需要辅助记忆
plan 前注入 memory bundle
review 时利用 memory bundle 做一致性校验
任务结束后进入 memory candidate -> judge -> persist 闭环
H. 修改子图

请修改至少核心子图的接口，使其支持：

接收 memory_bundle
输出 candidate_memories
不直接操作长期记忆层
五、实现时必须遵守的工程要求

请严格遵守：

1）尽量少破坏现有业务逻辑

优先做非侵入式重构，能保留的能力尽量保留。

2）优先提升可维护性

代码要具备：

清晰分层
低耦合
好扩展
容易加新 domain subgraph
3）加入类型标注与必要注释

特别是：

state
memory model
node 输入输出
storage interface
4）补齐配置管理

如果需要新增配置，请统一整理到配置层，例如：

Redis URL
Milvus host / port / token
embedding model name
memory TTL
retrieval top_k
rerank weights
score threshold
5）有降级能力

当 Redis / Milvus 不可用时：

系统不要整体崩溃
允许 memory disabled fallback
必要时记录 warning
6）不要写死第三方实现

embedding、vector store、kv store 最好做抽象，方便未来替换。

六、我希望最终至少看到这些交付物

请尽量直接在代码里完成，并在最后总结以下内容：

1）架构说明

简述重构后的记忆架构。

2）改动清单

列出：

新增文件
修改文件
删除文件（如有）
3）关键数据流

说明：

用户请求进入后，何时查 Redis
何时查 Milvus
何时注入 memory bundle
何时生成 candidate memories
何时写回 Redis / Milvus
4）状态结构说明

给出主图 state / 子图 state 中新增字段。

5）后续建议

指出还可以继续优化但这次未做的点。

七、实现偏好

我的偏好如下，请尽量遵守：

偏向 Pythonic、工程化、清晰分层
偏向显式 schema，不喜欢过度隐式魔法
希望结构化输出，命名统一
希望“主图治理、子图消费”的边界明确
希望先有 MVP 可跑通，再保留扩展空间
如果你发现当前代码存在明显设计问题，请直接重构，不要只做表面 patch
八、如果代码库信息不足时的工作方式

如果你发现某些模块不存在、命名不同或实际结构与预期不同，请你：

先基于真实代码结构做适配
不要机械照搬我上面的命名
保持设计思想一致即可
优先让改造结果能真正融入现有项目
九、输出风格要求

请按下面风格工作：

先快速审视代码结构
再给出 concise 但明确的重构计划
然后开始直接改代码
改完后给我：
改动摘要
核心设计说明
如何继续扩展

不要只停留在概念建议层，请尽量推进到实际代码修改。
请不要反复征求我确认。先基于当前代码库做最佳重构实现，遇到不确定之处做合理工程假设，并在最后明确说明假设。