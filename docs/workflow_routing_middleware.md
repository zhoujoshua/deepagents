# WorkflowRoutingMiddleware

`WorkflowRoutingMiddleware` 是一个强大的中间件，用于在多个 agent 之间实现复杂的工作流路由和编排。它支持条件分支、顺序执行、并行执行以及决策树逻辑。

## 核心特性

### 1. **条件路由 (Conditional Routing)**
根据状态字段自动选择不同的执行路径。

- 支持多种比较操作符（等于、大于、小于、包含等）
- 支持嵌套字段访问（如 `user.role`）
- 支持 AND/OR 逻辑组合多个条件

### 2. **顺序编排 (Sequential Orchestration)**
按固定顺序执行多个 agent，每个 agent 的输出可供后续 agent 使用。

- 适用于管道式处理
- 状态在 agent 之间累积
- 保持执行顺序的确定性

### 3. **并行执行 (Parallel Execution)**
同时执行多个独立的 agent，提高效率。

- 自动并发管理
- 等待所有并行任务完成
- 结果自动聚合

### 4. **决策树 (Decision Trees)**
构建复杂的多级条件路由逻辑。

- 支持嵌套条件节点
- 默认分支处理
- 防止循环引用

## 安装

```python
from deepagents.middleware.workflow_routing import (
    WorkflowRoutingMiddleware,
    WorkflowAgent,
    WorkflowDefinition,
    WorkflowNode,
    NodeType,
    ConditionOperator,
    ConditionalBranch,
)
```

## 基本用法

### 定义 Agent

```python
agents = {
    "agent1": WorkflowAgent(
        name="agent1",
        description="First agent",
        system_prompt="You are agent 1.",
        tools=[],
    ),
    "agent2": WorkflowAgent(
        name="agent2",
        description="Second agent",
        system_prompt="You are agent 2.",
        tools=[],
    ),
}
```

### 定义 Workflow

```python
workflow = WorkflowDefinition(
    start_node="start",
    nodes=[
        WorkflowNode(
            id="start",
            type=NodeType.AGENT,
            agent="agent1",
            next_node="next",
        ),
        WorkflowNode(
            id="next",
            type=NodeType.AGENT,
            agent="agent2",
        ),
    ],
)
```

### 创建 Middleware

```python
middleware = WorkflowRoutingMiddleware(
    default_model="openai:gpt-4o-mini",
    agents=agents,
    workflows={"my_workflow": workflow},
)
```

### 使用 Middleware

```python
from langchain.agents import create_agent

main_agent = create_agent(
    "openai:gpt-4o-mini",
    system_prompt="You coordinate workflows.",
    tools=[],
    middleware=[middleware],
)

result = main_agent.invoke({
    "messages": [HumanMessage(content="Execute the workflow")],
})
```

## 节点类型

### AGENT 节点

执行单个 agent。

```python
WorkflowNode(
    id="process",
    type=NodeType.AGENT,
    agent="processor",
    next_node="next_step",
)
```

### CONDITION 节点

基于条件进行分支。

```python
WorkflowNode(
    id="route",
    type=NodeType.CONDITION,
    branches=[
        ConditionalBranch(
            conditions=[
                {"field": "status", "operator": ConditionOperator.EQUALS, "value": "urgent"}
            ],
            next_node="urgent_handler",
        ),
        ConditionalBranch(
            conditions=[
                {"field": "status", "operator": ConditionOperator.EQUALS, "value": "normal"}
            ],
            next_node="normal_handler",
        ),
    ],
    default_branch="normal_handler",
)
```

### SEQUENTIAL 节点

按顺序执行子节点。

```python
WorkflowNode(
    id="sequence",
    type=NodeType.SEQUENTIAL,
    children=["step1", "step2", "step3"],
    next_node="after_sequence",
)
```

### PARALLEL 节点

并行执行子节点。

```python
WorkflowNode(
    id="parallel",
    type=NodeType.PARALLEL,
    children=["task1", "task2", "task3"],
    next_node="after_parallel",
)
```

## 条件操作符

### 比较操作符

- `EQUALS` (`eq`): 相等
- `NOT_EQUALS` (`ne`): 不相等
- `GREATER_THAN` (`gt`): 大于
- `LESS_THAN` (`lt`): 小于
- `GREATER_EQUAL` (`gte`): 大于等于
- `LESS_EQUAL` (`lte`): 小于等于

### 包含操作符

- `CONTAINS`: 包含（用于字符串或列表）
- `NOT_CONTAINS`: 不包含
- `IN`: 在...中
- `NOT_IN`: 不在...中

### 存在性操作符

- `EXISTS`: 字段存在
- `NOT_EXISTS`: 字段不存在

### 模式匹配

- `MATCHES_REGEX` (`matches`): 正则表达式匹配

## 条件逻辑

### AND 逻辑（默认）

所有条件都必须为真。

```python
ConditionalBranch(
    conditions=[
        {"field": "status", "operator": ConditionOperator.EQUALS, "value": "approved"},
        {"field": "amount", "operator": ConditionOperator.GREATER_THAN, "value": 1000},
    ],
    logic="AND",
    next_node="high_value_approved",
)
```

### OR 逻辑

任一条件为真即可。

```python
ConditionalBranch(
    conditions=[
        {"field": "priority", "operator": ConditionOperator.EQUALS, "value": "urgent"},
        {"field": "vip", "operator": ConditionOperator.EQUALS, "value": True},
    ],
    logic="OR",
    next_node="priority_handler",
)
```

## 嵌套字段访问

支持使用点号访问嵌套字段。

```python
{"field": "user.profile.role", "operator": ConditionOperator.EQUALS, "value": "admin"}
```

对应的状态结构：

```python
state = {
    "user": {
        "profile": {
            "role": "admin"
        }
    }
}
```

## 状态管理

### 状态传递

- Agent 之间共享状态（除了 `messages` 和 `todos`）
- 每个 agent 获得独立的消息历史
- Agent 的输出更新共享状态

### 结果累积

执行结果存储在 `workflow_results` 列表中：

```python
result = {
    "workflow_results": [
        {
            "agent": "agent1",
            "node_id": "step1",
            "result": "Agent 1 output",
        },
        {
            "agent": "agent2",
            "node_id": "step2",
            "result": "Agent 2 output",
        },
    ],
    # ... other state fields
}
```

## 高级用法

### 多 Workflow 管理

可以定义多个 workflow 并通过 ID 选择：

```python
workflows = {
    "simple": simple_workflow,
    "complex": complex_workflow,
    "emergency": emergency_workflow,
}

middleware = WorkflowRoutingMiddleware(
    default_model="openai:gpt-4o-mini",
    agents=agents,
    workflows=workflows,
)

# 使用时指定 workflow_id
result = agent.invoke({
    "messages": [HumanMessage(content="Execute workflow: complex")],
})
```

### 自定义 Agent 配置

为不同 agent 指定不同的模型和工具：

```python
agents = {
    "lightweight": WorkflowAgent(
        name="lightweight",
        description="Fast agent",
        system_prompt="Quick responses.",
        tools=[],
        model="openai:gpt-4o-mini",  # 轻量模型
    ),
    "powerful": WorkflowAgent(
        name="powerful",
        description="Complex reasoning",
        system_prompt="Deep analysis.",
        tools=[custom_tool],
        model="openai:gpt-4o",  # 强大模型
    ),
}
```

### 中间件组合

与其他中间件一起使用：

```python
from deepagents.middleware import FilesystemMiddleware

middleware = WorkflowRoutingMiddleware(
    default_model="openai:gpt-4o-mini",
    agents=agents,
    workflows=workflows,
    default_middleware=[
        FilesystemMiddleware(backend=backend),
    ],
)
```

### 自定义系统提示

```python
custom_prompt = """
# Custom Workflow Instructions

You have access to the execute_workflow tool...
"""

middleware = WorkflowRoutingMiddleware(
    default_model="openai:gpt-4o-mini",
    agents=agents,
    workflows=workflows,
    system_prompt=custom_prompt,
)
```

## 最佳实践

### 1. 节点命名

使用描述性的节点 ID：

```python
# 好的命名
WorkflowNode(id="classify_request", ...)
WorkflowNode(id="route_by_priority", ...)
WorkflowNode(id="handle_urgent_technical", ...)

# 避免的命名
WorkflowNode(id="node1", ...)
WorkflowNode(id="step", ...)
```

### 2. 防止循环

确保 workflow 不会形成循环：

```python
# 错误：会导致无限循环
WorkflowNode(id="a", next_node="b"),
WorkflowNode(id="b", next_node="a"),  # 循环！
```

Workflow 执行器会检测循环并停止执行。

### 3. 默认分支

总是为 CONDITION 节点提供默认分支：

```python
WorkflowNode(
    type=NodeType.CONDITION,
    branches=[...],
    default_branch="fallback_handler",  # 重要！
)
```

### 4. 并行任务独立性

确保并行执行的 agent 之间没有依赖：

```python
# 好：独立任务
WorkflowNode(
    type=NodeType.PARALLEL,
    children=["research_topic_a", "research_topic_b"],
)

# 不好：有依赖关系
WorkflowNode(
    type=NodeType.PARALLEL,
    children=["analyze", "synthesize"],  # synthesize 依赖 analyze
)
```

### 5. 状态字段约定

使用清晰的字段命名约定：

```python
# 好的字段名
state = {
    "priority": "urgent",
    "request_type": "technical",
    "risk_level": "high",
}

# 避免的字段名
state = {
    "p": "u",
    "type": "t",
    "rl": "h",
}
```

## 错误处理

### 缺失 Agent

如果引用的 agent 不存在，会记录错误并停止执行：

```python
# 执行日志会包含
{
    "node_id": "missing",
    "type": "error",
    "error": "Agent unknown_agent not found"
}
```

### 缺失 Node

如果引用的节点不存在，会记录错误并停止执行：

```python
{
    "node_id": "unknown",
    "type": "error",
    "error": "Node unknown not found"
}
```

### 循环检测

如果检测到循环引用，会记录错误并停止：

```python
{
    "node_id": "cycle_node",
    "type": "error",
    "error": "Circular reference detected"
}
```

## 性能优化

### 1. 使用并行执行

对于独立任务，使用 PARALLEL 节点而不是 SEQUENTIAL：

```python
# 慢：顺序执行 3 个独立任务
WorkflowNode(type=NodeType.SEQUENTIAL, children=["a", "b", "c"])

# 快：并行执行
WorkflowNode(type=NodeType.PARALLEL, children=["a", "b", "c"])
```

### 2. 选择合适的模型

为简单任务使用轻量模型：

```python
agents = {
    "classifier": WorkflowAgent(
        model="openai:gpt-4o-mini",  # 轻量快速
        ...
    ),
    "deep_analyzer": WorkflowAgent(
        model="openai:gpt-4o",  # 强大但慢
        ...
    ),
}
```

### 3. 最小化状态传递

只在状态中保留必要信息：

```python
# 不好：传递大量数据
state = {
    "full_documents": [...],  # 大量数据
    "all_history": [...],
}

# 好：只传递摘要
state = {
    "document_summary": "...",
    "key_findings": [...],
}
```

## 调试

### 查看执行日志

Workflow 执行器维护执行日志：

```python
executor = WorkflowExecutor(workflow, agents, state)
result = executor.execute()

# 查看执行日志
for log_entry in executor.execution_log:
    print(f"Node: {log_entry['node_id']}, Type: {log_entry['type']}")
```

### 检查 Workflow 结果

```python
workflow_results = result.get("workflow_results", [])
for step in workflow_results:
    print(f"Agent: {step['agent']}")
    print(f"Node: {step['node_id']}")
    print(f"Result: {step['result'][:100]}...")
```

## 示例场景

完整示例请参考 `examples/workflow_routing/` 目录：

1. **客户支持** (`customer_support.py`)
   - 条件路由示例
   - 基于优先级和类型的分支

2. **内容创作管道** (`content_pipeline.py`)
   - 顺序执行示例
   - 多阶段内容生成

3. **并行研究** (`parallel_research.py`)
   - 并行执行示例
   - 多视角研究合成

4. **复杂决策** (`complex_decision.py`)
   - 混合节点类型
   - 投资分析工作流

## API 参考

### WorkflowRoutingMiddleware

```python
class WorkflowRoutingMiddleware(AgentMiddleware):
    def __init__(
        self,
        *,
        default_model: str | BaseChatModel,
        default_tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        default_middleware: list[AgentMiddleware] | None = None,
        default_interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
        agents: dict[str, WorkflowAgent],
        workflows: dict[str, WorkflowDefinition],
        system_prompt: str | None = WORKFLOW_SYSTEM_PROMPT,
        workflow_description: str | None = None,
    ) -> None:
```

**参数：**

- `default_model`: 默认使用的模型
- `default_tools`: 默认工具列表
- `default_middleware`: 应用于所有 workflow agent 的默认中间件
- `default_interrupt_on`: 工具中断配置
- `agents`: Agent 定义字典
- `workflows`: Workflow 定义字典
- `system_prompt`: 系统提示覆盖
- `workflow_description`: Workflow 工具描述

### WorkflowAgent

```python
class WorkflowAgent(TypedDict):
    name: str
    description: str
    system_prompt: str
    tools: Sequence[BaseTool | Callable | dict[str, Any]]
    model: NotRequired[str | BaseChatModel]
    middleware: NotRequired[list[AgentMiddleware]]
    interrupt_on: NotRequired[dict[str, bool | InterruptOnConfig]]
```

### WorkflowDefinition

```python
class WorkflowDefinition(TypedDict):
    start_node: str
    nodes: list[WorkflowNode]
```

### WorkflowNode

```python
class WorkflowNode(TypedDict):
    id: str
    type: NodeType
    agent: NotRequired[str]
    branches: NotRequired[list[ConditionalBranch]]
    children: NotRequired[list[str]]
    next_node: NotRequired[str]
    default_branch: NotRequired[str]
```

### ConditionalBranch

```python
class ConditionalBranch(TypedDict):
    conditions: list[ConditionRule]
    logic: NotRequired[Literal["AND", "OR"]]
    next_node: str
```

### ConditionRule

```python
class ConditionRule(TypedDict):
    field: str
    operator: ConditionOperator
    value: NotRequired[Any]
```

## 常见问题

### Q: 如何在条件中使用复杂逻辑？

A: 使用多个条件节点嵌套：

```python
# 条件：(A AND B) OR (C AND D)
WorkflowNode(
    id="outer_condition",
    type=NodeType.CONDITION,
    branches=[
        ConditionalBranch(
            conditions=[
                {"field": "a", "operator": ConditionOperator.EQUALS, "value": True},
                {"field": "b", "operator": ConditionOperator.EQUALS, "value": True},
            ],
            logic="AND",
            next_node="result",
        ),
        ConditionalBranch(
            conditions=[
                {"field": "c", "operator": ConditionOperator.EQUALS, "value": True},
                {"field": "d", "operator": ConditionOperator.EQUALS, "value": True},
            ],
            logic="AND",
            next_node="result",
        ),
    ],
    default_branch="fallback",
)
```

### Q: 能否动态创建 workflow？

A: 可以，workflow 定义是普通的 Python 字典，可以在运行时构建：

```python
def create_dynamic_workflow(num_steps: int) -> WorkflowDefinition:
    nodes = []
    for i in range(num_steps):
        nodes.append(WorkflowNode(
            id=f"step_{i}",
            type=NodeType.AGENT,
            agent=f"agent_{i}",
            next_node=f"step_{i+1}" if i < num_steps - 1 else None,
        ))
    return WorkflowDefinition(start_node="step_0", nodes=nodes)
```

### Q: 如何在 workflow 中共享数据？

A: 使用状态字段：

```python
# Agent 1 设置状态
# 在 agent 1 的 system_prompt 中：
"Set the 'analysis_result' field with your findings."

# Agent 2 读取状态
# 在 agent 2 的 system_prompt 中：
"Use the 'analysis_result' field from previous analysis."
```

### Q: 能否在 workflow 中使用工具？

A: 可以，在 WorkflowAgent 定义中指定 tools：

```python
agents = {
    "researcher": WorkflowAgent(
        name="researcher",
        system_prompt="...",
        tools=[web_search_tool, calculator_tool],
    ),
}
```

## 限制

1. **消息历史隔离**：每个 agent 的消息历史是独立的，不会看到其他 agent 的消息
2. **循环限制**：不支持真正的循环（可以用条件节点模拟有限次循环）
3. **同步执行**：虽然有并行节点，但主 workflow 执行是同步的

## 贡献

欢迎贡献！请参考项目的贡献指南。

## 许可证

MIT License
