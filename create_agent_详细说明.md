# create_agent() 详细说明

## 一、函数来源

**是的，`create_agent()` 是 LangChain 的内置函数**，从 LangChain 1.0+ 版本开始提供。

```python
from langchain.agents import create_agent
```

**依赖版本要求：**
- `langchain >= 1.0.2, < 2.0.0`
- `langchain-core >= 1.0.0, < 2.0.0`

**官方文档：**
- API Reference: https://reference.langchain.com/python/langchain/agents/
- 使用指南: https://docs.langchain.com/oss/python/langchain/agents

---

## 二、完整函数签名

```python
def create_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    # 提示词和行为
    system_prompt: str | None = None,

    # 中间件系统
    middleware: Sequence[AgentMiddleware[StateT_co, ContextT]] = (),

    # 结构化输出
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | None = None,

    # 状态和上下文模式
    state_schema: type[AgentState[ResponseT]] | None = None,
    context_schema: type[ContextT] | None = None,

    # 持久化
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,

    # 中断控制
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,

    # 调试和配置
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph[
    AgentState[ResponseT],
    ContextT,
    _InputAgentState,
    _OutputAgentState[ResponseT]
]
```

---

## 三、参数详解

### 核心参数

#### 1. **model** (必需)
**类型：** `str | BaseChatModel`

**说明：** 用于 Agent 推理的语言模型。

**示例：**
```python
# 方式1: 使用字符串（通过 init_chat_model 初始化）
create_agent(model="claude-sonnet-4-5-20250929")
create_agent(model="openai:gpt-4o")
create_agent(model="anthropic:claude-3-opus-20240229")

# 方式2: 使用 LangChain 模型对象
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model_name="claude-sonnet-4-5-20250929", max_tokens=20000)
create_agent(model=model)

# 方式3: 使用 init_chat_model
from langchain.chat_models import init_chat_model
model = init_chat_model("openai:gpt-4o", temperature=0.7)
create_agent(model=model)
```

#### 2. **tools** (可选)
**类型：** `Sequence[BaseTool | Callable | dict[str, Any]] | None`

**说明：** Agent 可调用的工具列表。

**支持的格式：**
```python
# 格式1: 使用 @tool 装饰器定义的工具
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"It's sunny in {city}"

# 格式2: 普通 Python 函数（自动推断参数）
def search_web(query: str, max_results: int = 5) -> list:
    """Search the web."""
    return [...]

# 格式3: BaseTool 子类
from langchain_core.tools import BaseTool

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "A custom tool"

    def _run(self, query: str) -> str:
        return "result"

# 格式4: 字典配置
{
    "name": "my_tool",
    "description": "Tool description",
    "func": lambda x: x
}

# 使用示例
create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather, search_web, CustomTool()]
)
```

#### 3. **system_prompt** (可选)
**类型：** `str | None`

**说明：** Agent 的系统提示词，定义角色和行为。

**示例：**
```python
system_prompt = """You are an expert researcher.

Your responsibilities:
1. Conduct thorough research using available tools
2. Synthesize information into clear reports
3. Cite sources appropriately

When researching:
- Break down complex topics into sub-questions
- Use web search to gather current information
- Cross-reference multiple sources
"""

create_agent(
    model="claude-sonnet-4-5-20250929",
    system_prompt=system_prompt
)
```

### 高级参数

#### 4. **middleware** (可选)
**类型：** `Sequence[AgentMiddleware]`

**说明：** 中间件列表，用于拦截和修改模型调用、工具调用等。

**中间件类型：**
- `TodoListMiddleware`: 任务规划
- `FilesystemMiddleware`: 文件系统操作
- `SubAgentMiddleware`: 子代理管理
- `SummarizationMiddleware`: 消息摘要
- `AnthropicPromptCachingMiddleware`: 提示词缓存
- `HumanInTheLoopMiddleware`: 人机交互

**示例：**
```python
from langchain.agents.middleware import TodoListMiddleware, HumanInTheLoopMiddleware

create_agent(
    model="claude-sonnet-4-5-20250929",
    middleware=[
        TodoListMiddleware(),  # 启用任务规划
        HumanInTheLoopMiddleware(interrupt_on={"shell": True})  # 需要批准 shell 命令
    ]
)
```

#### 5. **response_format** (可选)
**类型：** `ResponseFormat[ResponseT] | type[ResponseT] | None`

**说明：** 强制 Agent 以结构化格式输出。

**示例：**
```python
from pydantic import BaseModel

class ResearchReport(BaseModel):
    title: str
    summary: str
    key_findings: list[str]
    sources: list[str]

create_agent(
    model="claude-sonnet-4-5-20250929",
    response_format=ResearchReport
)

# Agent 的最终输出将是 ResearchReport 实例
result = agent.invoke({"messages": [...]})
print(result["response"].title)  # 结构化访问
```

#### 6. **state_schema** (可选)
**类型：** `type[AgentState[ResponseT]] | None`

**说明：** 自定义 Agent 状态模式。

**示例：**
```python
from typing_extensions import TypedDict
from langchain.agents.middleware.types import AgentState

class CustomAgentState(AgentState):
    research_context: str  # 自定义状态字段
    iteration_count: int

create_agent(
    model="claude-sonnet-4-5-20250929",
    state_schema=CustomAgentState
)
```

#### 7. **checkpointer** (可选)
**类型：** `Checkpointer | None`

**说明：** 用于持久化 Agent 状态的 checkpointer。

**示例：**
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# 内存 checkpointer（会话内持久）
checkpointer = MemorySaver()

# SQLite checkpointer（跨会话持久）
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

create_agent(
    model="claude-sonnet-4-5-20250929",
    checkpointer=checkpointer
)

# 使用 thread_id 持久化对话
agent.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

#### 8. **store** (可选)
**类型：** `BaseStore | None`

**说明：** 长期记忆存储，用于跨线程持久化数据。

**示例：**
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

create_agent(
    model="claude-sonnet-4-5-20250929",
    store=store
)

# Agent 可以使用 store 保存长期记忆
# 例如：用户偏好、历史研究结果等
```

#### 9. **interrupt_on** (可选)
**类型：** `dict[str, bool | InterruptOnConfig] | None`

**说明：** 配置哪些工具调用需要人工批准。

**示例：**
```python
from langchain.agents.middleware import InterruptOnConfig

interrupt_config = {
    # 简单配置：布尔值
    "web_search": True,  # 所有 web_search 调用需批准

    # 高级配置：InterruptOnConfig
    "shell": InterruptOnConfig({
        "allowed_decisions": ["approve", "reject", "edit"],
        "description": lambda tool_call, state, runtime: (
            f"Command: {tool_call['args']['command']}\n"
            f"⚠️ This will execute on your system"
        )
    })
}

create_agent(
    model="claude-sonnet-4-5-20250929",
    interrupt_on=interrupt_config
)
```

#### 10. **debug** (可选)
**类型：** `bool`

**说明：** 启用调试模式，打印详细日志。

```python
create_agent(
    model="claude-sonnet-4-5-20250929",
    debug=True  # 打印每个步骤的详细信息
)
```

#### 11. **name** (可选)
**类型：** `str | None`

**说明：** Agent 的名称，用于日志和跟踪。

```python
create_agent(
    model="claude-sonnet-4-5-20250929",
    name="research-agent"
)
```

#### 12. **cache** (可选)
**类型：** `BaseCache | None`

**说明：** 缓存 LLM 调用结果以节省成本。

```python
from langchain.cache import InMemoryCache

create_agent(
    model="claude-sonnet-4-5-20250929",
    cache=InMemoryCache()
)
```

---

## 四、返回值

**类型：** `CompiledStateGraph`

**说明：** 返回一个编译好的 LangGraph 状态图，可以像普通 Runnable 一样调用。

### 返回对象的方法

```python
agent = create_agent(...)

# 1. 同步调用
result = agent.invoke({"messages": [{"role": "user", "content": "Hello"}]})
print(result["messages"][-1].content)

# 2. 异步调用
result = await agent.ainvoke({"messages": [...]})

# 3. 流式调用
for chunk in agent.stream({"messages": [...]}):
    print(chunk)

# 4. 流式异步调用
async for chunk in agent.astream({"messages": [...]}):
    print(chunk)

# 5. 批量调用
results = agent.batch([
    {"messages": [{"role": "user", "content": "Query 1"}]},
    {"messages": [{"role": "user", "content": "Query 2"}]},
])

# 6. 带配置调用（传递 thread_id 等）
result = agent.invoke(
    {"messages": [...]},
    config={
        "configurable": {"thread_id": "session-123"},
        "recursion_limit": 50
    }
)
```

---

## 五、create_agent 与 create_deep_agent 的关系

### Deep Agents 的实现

```python
# libs/deepagents/graph.py:131-143
def create_deep_agent(...) -> CompiledStateGraph:
    """Deep Agents 是对 create_agent 的封装"""

    # 1. 准备中间件栈
    deepagent_middleware = [
        TodoListMiddleware(),
        FilesystemMiddleware(backend=backend),
        SubAgentMiddleware(...),
        SummarizationMiddleware(...),
        AnthropicPromptCachingMiddleware(...),
        PatchToolCallsMiddleware(),
    ]

    # 2. 调用 LangChain 的 create_agent
    return create_agent(
        model,
        system_prompt=system_prompt + "\n\n" + BASE_AGENT_PROMPT,
        tools=tools,
        middleware=deepagent_middleware,  # 核心：注入深度能力
        response_format=response_format,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        debug=debug,
        name=name,
        cache=cache,
    ).with_config({"recursion_limit": 1000})
```

### 关系总结

```
create_agent (LangChain 内置)
    ↓ 是基础
create_deep_agent (Deep Agents 封装)
    ↓ 预配置以下能力
    - 任务规划 (TodoListMiddleware)
    - 文件系统 (FilesystemMiddleware)
    - 子代理 (SubAgentMiddleware)
    - 消息摘要 (SummarizationMiddleware)
    - 提示词缓存 (AnthropicPromptCachingMiddleware)
```

---

## 六、工作原理

### Agent 执行循环

```python
# create_agent 创建的是一个工具调用循环
1. 接收用户消息
   ↓
2. 通过中间件 (wrap_model_call)
   - 注入系统提示词
   - 注入工具定义
   ↓
3. LLM 推理
   - 决定是否调用工具
   - 生成工具参数
   ↓
4. 如果有工具调用:
   a. 通过中间件 (wrap_tool_call)
   b. 执行工具
   c. 获取结果
   d. 回到步骤 2（继续循环）
   ↓
5. 如果没有工具调用:
   - 返回最终回复
   - 结束循环
```

### 状态更新机制

```python
# Agent 状态结构
{
    "messages": [
        HumanMessage(content="用户输入"),
        AIMessage(content="...", tool_calls=[...]),
        ToolMessage(content="工具结果", tool_call_id="..."),
        AIMessage(content="最终回复"),
    ],
    # 中间件可添加的自定义状态
    "files": {...},        # FilesystemMiddleware
    "todos": [...],        # TodoListMiddleware
    "custom_field": ...,   # 自定义中间件
}
```

---

## 七、实战示例

### 示例 1: 最简单的 Agent

```python
from langchain.agents import create_agent

def calculator(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[calculator],
    system_prompt="You are a math assistant."
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What is 25 * 4 + 10?"}]
})
print(result["messages"][-1].content)  # "The result is 110."
```

### 示例 2: 带中间件的 Agent

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[web_search, calculator],
    middleware=[TodoListMiddleware()],  # 启用任务规划
    system_prompt="You are a research assistant with planning capabilities."
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Research the top 3 AI companies and calculate their total market cap"
    }]
})

# Agent 会：
# 1. 使用 write_todos 创建计划
# 2. 依次 web_search 每家公司
# 3. 使用 calculator 求和
# 4. 返回结果
```

### 示例 3: 持久化对话

```python
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("agent_memory.db")

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather, set_reminder],
    checkpointer=checkpointer,
    system_prompt="You are a personal assistant with memory."
)

# 第一次对话
agent.invoke(
    {"messages": [{"role": "user", "content": "My name is Alice"}]},
    config={"configurable": {"thread_id": "alice-session"}}
)

# 第二次对话（稍后）
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    config={"configurable": {"thread_id": "alice-session"}}
)
# Agent 回复: "Your name is Alice."（记住了之前的对话）
```

### 示例 4: 人工审批工具调用

```python
from langchain.agents import create_agent
from langchain.agents.middleware import InterruptOnConfig

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[delete_file, send_email],
    interrupt_on={
        "delete_file": True,  # 删除文件需批准
        "send_email": InterruptOnConfig({
            "allowed_decisions": ["approve", "reject", "edit"],
            "description": lambda tc, s, r: (
                f"To: {tc['args']['to']}\n"
                f"Subject: {tc['args']['subject']}\n"
                f"⚠️ This will send a real email"
            )
        })
    },
    checkpointer=MemorySaver()  # 必需，用于暂停/恢复
)

# 第一步：Agent 请求调用工具
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Send summary to boss@company.com"}]},
    config={"configurable": {"thread_id": "session-1"}}
)

# 此时 Agent 会暂停，等待批准
# result["next"] == ["__interrupt__"]

# 第二步：用户批准
result = agent.invoke(
    Command(resume={"approve": True}),  # 或 {"reject": True}
    config={"configurable": {"thread_id": "session-1"}}
)
# 继续执行
```

---

## 八、与其他框架对比

| 特性 | create_agent | LangGraph 手动构建 | AutoGPT/BabyAGI |
|-----|-------------|-------------------|-----------------|
| **易用性** | ⭐⭐⭐⭐⭐ 一行代码 | ⭐⭐⭐ 需要定义节点和边 | ⭐⭐⭐⭐ 预定义流程 |
| **灵活性** | ⭐⭐⭐⭐ 中间件系统 | ⭐⭐⭐⭐⭐ 完全自定义 | ⭐⭐ 有限配置 |
| **工具调用** | ⭐⭐⭐⭐⭐ 原生支持 | ⭐⭐⭐⭐⭐ 原生支持 | ⭐⭐⭐ 需适配 |
| **状态管理** | ⭐⭐⭐⭐⭐ 自动 | ⭐⭐⭐⭐⭐ 手动精确控制 | ⭐⭐⭐ 内置简单状态 |
| **持久化** | ⭐⭐⭐⭐⭐ Checkpointer | ⭐⭐⭐⭐⭐ Checkpointer | ⭐⭐ 自行实现 |
| **调试** | ⭐⭐⭐⭐ LangSmith | ⭐⭐⭐⭐ LangSmith | ⭐⭐⭐ 日志 |

**推荐使用场景：**
- `create_agent`: 80% 的 Agent 需求（快速原型、生产应用）
- `LangGraph 手动`: 复杂自定义流程（多阶段、条件分支）
- `AutoGPT`: 自主任务执行（不需要精确控制）

---

## 九、常见问题 FAQ

### Q1: create_agent 和 initialize_agent 有什么区别？

**A:** `initialize_agent` 是 LangChain 0.x 的旧 API，已弃用。

```python
# 旧 API (已弃用)
from langchain.agents import initialize_agent, AgentType
agent = initialize_agent(
    tools, llm, agent=AgentType.OPENAI_FUNCTIONS
)

# 新 API (推荐)
from langchain.agents import create_agent
agent = create_agent(model=llm, tools=tools)
```

**主要区别：**
- `create_agent` 返回 LangGraph (更强大、更灵活)
- 支持中间件、结构化输出、持久化
- 统一的 invoke/stream 接口

### Q2: 如何限制 Agent 的执行步数？

**A:** 使用 `recursion_limit` 配置：

```python
agent = create_agent(...)

result = agent.invoke(
    {"messages": [...]},
    config={"recursion_limit": 10}  # 最多 10 轮工具调用
)
```

### Q3: 如何获取中间步骤？

**A:** 使用 `stream` 方法：

```python
for chunk in agent.stream({"messages": [...]}):
    if "tools" in chunk:
        print(f"工具调用: {chunk['tools']}")
    if "agent" in chunk:
        print(f"Agent 输出: {chunk['agent']}")
```

### Q4: 如何自定义停止条件？

**A:** 创建自定义中间件：

```python
class CustomStoppingMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        response = handler(request)
        # 检查是否满足停止条件
        if should_stop(response):
            return ModelResponse(messages=[...], stop=True)
        return response

agent = create_agent(
    model=...,
    middleware=[CustomStoppingMiddleware()]
)
```

---

## 十、总结

### create_agent 的核心价值

1. **抽象层次恰当**
   - 比手动 LangGraph 简单
   - 比固定框架灵活

2. **生产就绪**
   - 内置错误处理
   - 支持持久化
   - 可观测性（LangSmith）

3. **可扩展性强**
   - 中间件系统
   - 自定义状态
   - 工具生态

4. **官方支持**
   - LangChain 核心团队维护
   - 文档完善
   - 持续更新

### Deep Agents 的增强

`create_deep_agent` 在 `create_agent` 基础上添加了：
- 📋 任务规划能力
- 📁 文件系统操作
- 🤖 子代理隔离
- 🧠 智能摘要
- ⚡ 提示词缓存

**选择建议：**
- 简单 Agent → 直接用 `create_agent`
- 复杂任务、需要规划 → 用 `create_deep_agent`
- 极度自定义流程 → 手写 LangGraph

---

**参考资源：**
- LangChain Agents 文档: https://docs.langchain.com/oss/python/langchain/agents
- API Reference: https://reference.langchain.com/python/langchain/agents/
- Deep Agents 文档: https://docs.langchain.com/oss/python/deepagents/overview
