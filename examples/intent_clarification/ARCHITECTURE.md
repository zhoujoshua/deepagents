# 意图识别与问题澄清Agent架构设计

## 1. 整体架构图

```
用户问题
    ↓
┌───────────────────────────────────────────────────────┐
│              主控制Agent (Orchestrator)                 │
│  - 流程控制                                            │
│  - 状态管理                                            │
│  - 用户交互                                            │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│          意图识别中间件 (IntentClassificationMiddleware)│
│  - 识别用户意图                                        │
│  - 判断是否需要澄清                                     │
│  - 路由到对应的子agent                                 │
└───────────────────────────────────────────────────────┘
    ↓
    ├─需要澄清→┌────────────────────────────────────┐
    │          │   问题澄清子Agent                   │
    │          │   (ClarificationSubAgent)          │
    │          │  - 识别缺失信息                     │
    │          │  - 调用知识库工具                   │
    │          │  - 生成澄清问题                     │
    │          │  - 多轮对话循环                     │
    │          └────────────────────────────────────┘
    │               ↕
    │          ┌────────────────────────────────────┐
    │          │   知识库召回工具                    │
    │          │   (KnowledgeRetriever)            │
    │          │  - 检索相关schema信息               │
    │          │  - 检索业务规则                     │
    │          │  - 检索历史案例                     │
    │          └────────────────────────────────────┘
    │               ↓
    │          ┌────────────────────────────────────┐
    │          │   用户确认                          │
    │          │  - 展示澄清后的问题                 │
    │          │  - 等待用户确认                     │
    │          └────────────────────────────────────┘
    │               ↓
    └─意图明确→┌────────────────────────────────────┐
               │   SQL生成子Agent                    │
               │   (SQLGeneratorSubAgent)          │
               │  - 将问题转换为SQL                  │
               │  - 验证SQL正确性                    │
               │  - 返回结果                         │
               └────────────────────────────────────┘
```

## 2. 核心组件设计

### 2.1 主控制Agent (Orchestrator Agent)

**职责**：
- 接收用户输入
- 协调各子agent的调用
- 管理对话状态和上下文
- 处理用户确认流程

**工具集**：
- `task` - 调用子agent（由SubAgentMiddleware提供）
- `save_to_file` - 保存中间结果（由FilesystemMiddleware提供）
- `read_file` - 读取历史信息（由FilesystemMiddleware提供）

**状态字段**：
```python
{
    "original_question": str,      # 原始问题
    "intent": str,                 # 识别出的意图类型
    "needs_clarification": bool,   # 是否需要澄清
    "clarified_question": str,     # 澄清后的问题
    "clarification_context": dict, # 澄清过程中的上下文
    "user_confirmed": bool,        # 用户是否确认
    "final_result": Any,           # 最终结果
}
```

### 2.2 意图识别中间件 (IntentClassificationMiddleware)

**设计模式**: AgentMiddleware

**职责**：
- 在agent执行前注入意图识别逻辑
- 扩展系统提示词，添加意图分类指令
- 提供意图类型枚举

**支持的意图类型**：
```python
class IntentType(Enum):
    QUERY_DATA = "query_data"          # 数据查询
    ANALYZE_DATA = "analyze_data"      # 数据分析
    GENERATE_REPORT = "generate_report" # 生成报告
    EXPLAIN_CONCEPT = "explain_concept" # 解释概念
    UNKNOWN = "unknown"                # 未知意图
```

**实现方式**：
- 修改系统提示词，注入意图识别逻辑
- 添加结构化输出格式要求
- 提供意图到子agent的路由映射

### 2.3 问题澄清子Agent (ClarificationSubAgent)

**系统提示词**：
```
你是一个专业的问题澄清助手。你的任务是识别用户问题中缺失或不明确的信息，
并通过多轮对话收集这些信息。

工作流程：
1. 分析用户问题，识别所有需要澄清的要素
2. 使用knowledge_retriever工具获取相关的schema、业务规则等背景信息
3. 基于背景信息，判断哪些要素是必需的但缺失的
4. 一次提出1-3个澄清问题（不要一次问太多）
5. 根据用户回答，更新已知信息
6. 重复2-5步，直到所有必需信息都已收集
7. 输出完整的、明确的问题描述

输出格式：
- 如果还需要澄清：{"status": "needs_more_info", "questions": [...]}
- 如果已经清晰：{"status": "clear", "clarified_question": "..."}
```

**工具集**：
- `knowledge_retriever` - 召回知识库信息
- `update_context` - 更新澄清上下文
- `read_file` - 读取已保存的上下文

**多轮循环机制**：
- 使用LangGraph的状态机制自然实现
- 每次返回`needs_more_info`状态时，主agent会再次调用
- 直到返回`clear`状态，退出循环

### 2.4 知识库召回工具 (KnowledgeRetriever)

**工具定义**：
```python
@tool
def knowledge_retriever(
    query: str,
    knowledge_type: Literal["schema", "business_rule", "example", "all"]
) -> str:
    """
    从知识库中检索相关信息

    Args:
        query: 查询文本
        knowledge_type: 知识类型
            - schema: 数据库schema信息
            - business_rule: 业务规则
            - example: 历史案例
            - all: 所有类型

    Returns:
        检索到的相关信息
    """
```

**实现方式**：
- 可以接入向量数据库（如Chroma、Pinecone）
- 可以接入关系数据库的schema元数据
- 可以接入文档检索系统
- 支持混合检索策略

### 2.5 SQL生成子Agent (SQLGeneratorSubAgent)

**系统提示词**：
```
你是一个专业的SQL生成助手。基于用户的明确问题和提供的数据库schema，
生成正确的SQL查询。

要求：
1. 理解问题的完整语义
2. 使用knowledge_retriever获取相关表的schema信息
3. 生成符合数据库方言的SQL（如PostgreSQL、MySQL等）
4. 添加必要的注释说明查询逻辑
5. 验证SQL的语法正确性
6. 返回SQL及其解释

输出格式：
{
    "sql": "SELECT ...",
    "explanation": "这个查询...",
    "tables_used": ["table1", "table2"],
    "estimated_complexity": "simple|medium|complex"
}
```

**工具集**：
- `knowledge_retriever` - 获取schema信息
- `validate_sql` - SQL语法验证（可选）

## 3. 数据流设计

### 3.1 状态流转

```
INITIAL (初始)
    ↓ (接收用户问题)
INTENT_CLASSIFICATION (意图识别)
    ↓
    ├─→ NEEDS_CLARIFICATION (需要澄清)
    │       ↓ (循环)
    │   CLARIFYING (澄清中)
    │       ↓ (召回知识库)
    │   KNOWLEDGE_RETRIEVAL (知识检索)
    │       ↓ (生成问题)
    │   ASKING_USER (询问用户)
    │       ↓ (用户回答)
    │   [循环直到clear]
    │       ↓
    └─→ CLEAR (意图明确)
            ↓
        AWAITING_CONFIRMATION (等待确认)
            ↓ (用户确认)
        PROCESSING (处理中)
            ↓
        COMPLETED (完成)
```

### 3.2 上下文传递

**文件系统作为共享存储**：
```
/workspace/
  ├── question.txt              # 原始问题
  ├── intent.json               # 意图识别结果
  ├── clarification_context.json # 澄清上下文
  │   ├── missing_info: []      # 缺失信息列表
  │   ├── collected_info: {}    # 已收集信息
  │   └── knowledge_base: {}    # 召回的知识
  ├── clarified_question.txt    # 澄清后的问题
  └── result.json               # 最终结果
```

**为什么使用文件系统**：
- DeepAgents的设计理念：使用文件系统作为上下文卸载机制
- 避免状态对象过大导致token浪费
- 便于debugging和审计
- 子agent之间可以通过文件共享信息

## 4. 中间件组合策略

```python
# 主agent中间件栈
middleware = [
    IntentClassificationMiddleware(),  # 意图识别
    TodoListMiddleware(),              # 任务规划
    FilesystemMiddleware(),            # 文件系统
    SubAgentMiddleware(                # 子agent管理
        subagents=[
            clarification_subagent,
            sql_generator_subagent,
        ]
    ),
    SummarizationMiddleware(),         # 上下文总结
]

# 澄清子agent中间件栈
clarification_middleware = [
    FilesystemMiddleware(),            # 访问共享文件
    # 不需要SubAgentMiddleware，因为它是叶子agent
]

# SQL生成子agent中间件栈
sql_generator_middleware = [
    FilesystemMiddleware(),            # 访问共享文件
]
```

## 5. Prompt管理策略

**问题**：如果把所有prompt写在一起太长

**解决方案**：

### 5.1 按职责分离Prompt

```python
# prompts/orchestrator.py
ORCHESTRATOR_PROMPT = """
你是一个智能问答系统的协调者。你的职责是：
1. 接收用户问题
2. 判断是否需要澄清（通过intent字段）
3. 如果需要澄清，调用clarification-agent
4. 如果已明确，向用户展示理解并请求确认
5. 用户确认后，调用对应的处理agent
"""

# prompts/intent_classification.py
INTENT_CLASSIFICATION_PROMPT = """
分析用户问题的意图，并判断是否需要澄清。

需要澄清的情况：
- 缺少必要的时间范围
- 缺少关键业务对象
- 指标定义不明确
- 聚合维度不清晰

输出格式：
{
    "intent": "query_data|analyze_data|...",
    "needs_clarification": true|false,
    "reason": "为什么需要/不需要澄清"
}
"""

# prompts/clarification.py
CLARIFICATION_PROMPT = """
你是一个专业的问题澄清助手...
[详细的澄清逻辑]
"""

# prompts/sql_generator.py
SQL_GENERATOR_PROMPT = """
你是一个专业的SQL生成助手...
[详细的SQL生成逻辑]
"""
```

### 5.2 动态Prompt组装

```python
def build_orchestrator_prompt(intent: str | None = None) -> str:
    """根据当前状态动态组装prompt"""
    base = ORCHESTRATOR_PROMPT

    if intent == "query_data":
        base += "\n\n" + DATA_QUERY_SPECIFIC_INSTRUCTIONS
    elif intent == "analyze_data":
        base += "\n\n" + DATA_ANALYSIS_SPECIFIC_INSTRUCTIONS

    return base
```

### 5.3 使用中间件动态修改Prompt

```python
class IntentClassificationMiddleware(AgentMiddleware):
    def __call__(self, state, config):
        # 如果是首次进入，注入意图识别prompt
        if not state.get("intent"):
            # 临时修改系统prompt
            original_prompt = config.get("configurable", {}).get("system_prompt", "")
            enhanced_prompt = original_prompt + "\n\n" + INTENT_CLASSIFICATION_PROMPT

            # 更新配置
            config["configurable"]["system_prompt"] = enhanced_prompt

        return state
```

## 6. 关键技术点

### 6.1 多轮澄清的循环控制

**方法1：使用LangGraph的条件边**
```python
def should_continue_clarification(state) -> str:
    """判断是否需要继续澄清"""
    clarification_result = state.get("clarification_result", {})
    if clarification_result.get("status") == "clear":
        return "continue_to_confirmation"
    else:
        return "ask_user_again"

# 在graph中定义
graph.add_conditional_edges(
    "clarification",
    should_continue_clarification,
    {
        "ask_user_again": "wait_user_input",
        "continue_to_confirmation": "confirmation",
    }
)
```

**方法2：使用子agent的返回值**
```python
# 主agent的逻辑
while True:
    result = task(
        agent="clarification-agent",
        input=current_question,
        context=clarification_context
    )

    if result["status"] == "clear":
        clarified_question = result["clarified_question"]
        break
    else:
        # 向用户提问
        user_response = ask_user(result["questions"])
        # 更新上下文
        clarification_context["user_responses"].append(user_response)
```

### 6.2 知识库召回的优化

**策略1：缓存热门schema**
```python
# 在StateBackend中缓存
@cache_to_state("/knowledge_cache/schemas/")
def get_table_schema(table_name: str) -> dict:
    # 首次从数据库获取，后续从state读取
    pass
```

**策略2：渐进式召回**
```python
# 第一轮：只召回高层概览
knowledge = retrieve(query, depth="overview")

# 如果需要更多细节
if needs_more_detail:
    knowledge = retrieve(query, depth="detailed")
```

### 6.3 用户确认的人机交互

**使用HumanInTheLoopMiddleware**
```python
from deepagents.middleware import HumanInTheLoopMiddleware

middleware = [
    # ... other middleware
    HumanInTheLoopMiddleware(
        # 在confirmation节点等待用户输入
        interrupt_on={"confirmation": True}
    ),
]
```

**或者自定义中断逻辑**
```python
# 在主agent的prompt中
"""
当你完成问题澄清后：
1. 将澄清后的问题写入 clarified_question.txt
2. 生成确认消息展示给用户
3. 使用 request_user_confirmation 工具等待用户响应
4. 只有在用户明确同意后才继续
"""
```

## 7. 扩展性设计

### 7.1 支持更多处理类型

除了SQL生成，可以轻松添加：
```python
subagents = [
    clarification_subagent,
    sql_generator_subagent,
    python_analyzer_subagent,      # Python数据分析
    report_generator_subagent,     # 报告生成
    chart_creator_subagent,        # 图表创建
]

# 在意图识别中路由
intent_to_agent = {
    "query_data": "sql-generator",
    "analyze_data": "python-analyzer",
    "generate_report": "report-generator",
}
```

### 7.2 可插拔的知识库

```python
class KnowledgeBase(Protocol):
    def retrieve(self, query: str, type: str) -> str:
        ...

# 实现1：向量数据库
class VectorKnowledgeBase:
    def __init__(self, chroma_client):
        self.client = chroma_client

    def retrieve(self, query, type):
        return self.client.query(query, filter={"type": type})

# 实现2：SQL元数据
class SQLMetadataKnowledgeBase:
    def __init__(self, db_connection):
        self.conn = db_connection

    def retrieve(self, query, type):
        if type == "schema":
            return self.get_schema_info(query)
        # ...

# 使用
knowledge_base = VectorKnowledgeBase(chroma_client)
# 或
knowledge_base = SQLMetadataKnowledgeBase(db_conn)
```

## 8. 性能优化建议

### 8.1 并行化

```python
# 意图识别后，可以并行预热知识库
async def parallel_warmup(intent, question):
    tasks = [
        retrieve_schema_async(question),
        retrieve_business_rules_async(intent),
        retrieve_examples_async(question),
    ]
    return await asyncio.gather(*tasks)
```

### 8.2 Prompt缓存

```python
# 使用AnthropicPromptCachingMiddleware
# 把稳定的schema信息放在prompt前部，启用缓存
CACHED_SCHEMA_INFO = """
# 数据库Schema（此部分会被缓存）
[大量schema信息]
"""

system_prompt = CACHED_SCHEMA_INFO + "\n\n" + DYNAMIC_INSTRUCTIONS
```

### 8.3 流式输出

```python
# 澄清问题时，流式输出让用户更快看到反馈
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    streaming=True,  # 启用流式
)

# 在调用时
for chunk in agent.stream({"messages": [("user", question)]}):
    print(chunk)
```

## 9. 监控和调试

### 9.1 日志记录

```python
# 在每个关键步骤写入日志文件
@tool
def log_step(step_name: str, data: dict) -> str:
    """记录执行步骤"""
    log_entry = {
        "timestamp": datetime.now(),
        "step": step_name,
        "data": data,
    }
    # 写入 /logs/execution.jsonl
    return "Logged"
```

### 9.2 状态可视化

```python
# 保存LangGraph的执行轨迹
config = {
    "configurable": {
        "thread_id": "user-123-session-456"
    }
}

# 之后可以回放
checkpointer.get_tuple(config)
```

## 10. 总结

这个架构的核心优势：

1. **模块化**：每个组件职责单一，易于理解和维护
2. **可扩展**：轻松添加新的意图类型和处理agent
3. **Prompt管理**：通过中间件和子agent分离，避免单一prompt过长
4. **状态清晰**：使用文件系统作为共享存储，状态流转明确
5. **符合现有架构**：完全基于DeepAgents的设计理念和组件
6. **人机协作**：支持多轮澄清和用户确认
7. **性能优化**：支持缓存、并行、流式等优化手段

建议的实现顺序：
1. 先实现知识库召回工具（可以先用mock数据）
2. 实现问题澄清子agent和简单的主控制agent
3. 测试多轮澄清流程
4. 实现意图识别中间件
5. 实现SQL生成子agent
6. 集成所有组件
7. 添加用户确认和人机交互
8. 性能优化和监控
