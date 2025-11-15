# 意图识别与问题澄清Agent

一个基于[DeepAgents](https://github.com/langchain-ai/deepagents)框架的智能问答系统，能够自动识别用户意图、通过多轮对话澄清模糊问题，并调用专业子agent处理具体任务。

## 特性

- **自动意图识别**：识别用户问题的意图类型（数据查询、数据分析等）
- **智能问题澄清**：通过多轮对话收集缺失信息，将模糊问题转化为明确需求
- **知识库集成**：集成数据库schema、业务规则、历史案例等知识
- **模块化Prompt管理**：通过中间件模式分离不同阶段的prompt，避免单一prompt过长
- **可扩展架构**：轻松添加新的意图类型和处理agent
- **人机协作**：支持用户确认流程，确保理解准确

## 架构设计

系统采用**主控制agent + 多个专业子agent**的架构：

```
用户问题
    ↓
主控制Agent (流程控制)
    ↓
意图识别中间件
    ↓
    ├─需要澄清→ 问题澄清子Agent ←→ 知识库召回工具
    │                ↓
    │           用户确认
    │                ↓
    └─意图明确→ SQL生成子Agent / 数据分析子Agent / ...
                     ↓
                  返回结果
```

详细架构文档请参考：[ARCHITECTURE.md](./ARCHITECTURE.md)

## 快速开始

### 安装依赖

```bash
cd /path/to/deepagents
pip install -e libs/deepagents
```

### 基本使用

```python
from examples.intent_clarification import create_intent_clarification_agent

# 创建agent
agent = create_intent_clarification_agent()

# 提问
result = agent.invoke({
    "messages": [("user", "查询销售额")]
})

# 查看响应
print(result["messages"][-1].content)
```

### 流式输出

```python
from examples.intent_clarification import run_clarification_flow

# 流式输出更友好
for chunk in run_clarification_flow("查询最近的活跃用户", stream=True):
    if "messages" in chunk:
        for message in chunk["messages"]:
            print(message.content)
```

### 命令行使用

```bash
cd examples/intent_clarification
python intent_clarification_agent.py "查询销售额"
```

## 核心组件

### 1. 主控制Agent

负责整体流程协调，不处理具体任务。

**职责**：
- 接收用户问题
- 协调意图识别
- 调用子agent
- 管理用户确认

**Prompt文件**：`prompts.py::ORCHESTRATOR_PROMPT`

### 2. 意图识别中间件

自动识别用户意图，判断是否需要澄清。

**支持的意图类型**：
- `query_data`：数据查询（需要生成SQL）
- `analyze_data`：数据分析
- `generate_report`：生成报告
- `explain_concept`：解释概念
- `unknown`：未知意图

**实现文件**：`middleware.py::IntentClassificationMiddleware`

### 3. 问题澄清子Agent

通过多轮对话澄清模糊问题。

**工作流程**：
1. 分析问题，识别缺失信息
2. 调用知识库获取背景
3. 生成澄清问题（一次1-3个）
4. 处理用户回答
5. 重复直到信息完整
6. 输出澄清后的问题

**配置文件**：`agents.py::clarification_subagent`

### 4. 知识库召回工具

提供数据库schema、业务规则、历史案例等信息。

**知识类型**：
- `schema`：数据库表结构、字段定义
- `business_rule`：业务规则、指标定义
- `example`：历史案例、SQL示例
- `all`：所有类型

**使用示例**：

```python
from examples.intent_clarification.tools import knowledge_retriever

# 检索schema信息
result = knowledge_retriever("订单表有哪些字段", "schema")
print(result)

# 检索业务规则
result = knowledge_retriever("如何计算销售额", "business_rule")
print(result)

# 检索历史案例
result = knowledge_retriever("查询活跃用户的SQL", "example")
print(result)
```

**自定义知识库**：

```python
from examples.intent_clarification.tools import KnowledgeBase, set_knowledge_base

class MyKnowledgeBase(KnowledgeBase):
    def retrieve_schema(self, query: str):
        # 从你的数据库获取schema
        return {...}

    def retrieve_business_rule(self, query: str):
        # 从你的规则库获取
        return {...}

    def retrieve_example(self, query: str):
        # 从你的案例库获取
        return {...}

# 设置为全局知识库
set_knowledge_base(MyKnowledgeBase())
```

### 5. SQL生成子Agent

将明确的问题转换为SQL查询。

**功能**：
- 理解问题需求
- 获取相关schema
- 参考业务规则和历史案例
- 生成符合规范的SQL
- 提供详细解释

**配置文件**：`agents.py::sql_generator_subagent`

## 配置选项

```python
agent = create_intent_clarification_agent(
    model="claude-sonnet-4-5-20250929",  # 模型选择
    enable_todo=True,                     # 启用任务规划
    enable_summarization=True,            # 启用上下文总结
    max_clarification_rounds=5,           # 最大澄清轮次
    debug=False,                          # 调试模式
)
```

## 示例场景

### 场景1：缺少时间范围

```
用户：查询销售额
Agent：您想查询哪个时间范围的销售额？
       A. 最近7天
       B. 本月
       C. 上个月
       D. 自定义日期范围
用户：本月的
Agent：好的，我为您查询2024年11月的销售额...
      [调用SQL生成agent]
```

### 场景2：指标不明确

```
用户：统计活跃用户
Agent：请问如何定义"活跃用户"？
       A. 最近登录的用户
       B. 最近下单的用户
       C. 最近登录或下单的用户
用户：最近登录或下单的
Agent：好的，请问"最近"是指多长时间？
       A. 最近7天
       B. 最近30天
       C. 自定义
用户：最近7天
Agent：明白了，我为您统计最近7天内有登录或下单行为的用户数量...
      [调用SQL生成agent]
```

### 场景3：已经明确的问题

```
用户：查询2024年10月所有已完成订单的总销售金额，按商品类别分组
Agent：我理解您的需求：
      - 时间范围：2024年10月（2024-10-01至2024-10-31）
      - 订单状态：已完成
      - 统计指标：总销售金额
      - 分组维度：商品类别

      请确认是否正确？
用户：是的
Agent：[调用SQL生成agent，生成SQL并返回]
```

## 文件结构

```
intent_clarification/
├── ARCHITECTURE.md              # 详细架构设计文档
├── README.md                    # 本文件
├── __init__.py                  # 模块导出
├── prompts.py                   # 所有prompt定义
├── tools.py                     # 知识库工具实现
├── middleware.py                # 自定义中间件
├── agents.py                    # 子agent配置
├── intent_clarification_agent.py # 主agent实现
└── example_usage.py             # 使用示例
```

## 扩展指南

### 添加新的意图类型

1. 在`agents.py`中定义新的子agent：

```python
my_custom_subagent = {
    "name": "my-custom-agent",
    "description": "处理自定义任务",
    "system_prompt": "你是...",
    "tools": [...],
    "middleware": [...],
}
```

2. 在`agents.py`中更新路由映射：

```python
INTENT_TO_AGENT_MAP = {
    "query_data": "sql-generator",
    "my_custom_intent": "my-custom-agent",  # 新增
}
```

3. 在`prompts.py`中更新意图识别prompt，添加新意图的说明

### 接入真实知识库

#### 接入向量数据库（如Chroma）

```python
from examples.intent_clarification.tools import VectorKnowledgeBase, set_knowledge_base
import chromadb

client = chromadb.Client()
# 初始化向量数据库...

kb = VectorKnowledgeBase(collection_name="my_knowledge")
set_knowledge_base(kb)
```

#### 接入SQL元数据

```python
from examples.intent_clarification.tools import KnowledgeBase, set_knowledge_base
import sqlalchemy

class SQLMetadataKnowledgeBase(KnowledgeBase):
    def __init__(self, connection_string):
        self.engine = sqlalchemy.create_engine(connection_string)

    def retrieve_schema(self, query: str):
        # 从information_schema查询表结构
        inspector = sqlalchemy.inspect(self.engine)
        tables = inspector.get_table_names()
        # ... 返回schema信息
        return {...}

    # 实现其他方法...

kb = SQLMetadataKnowledgeBase("postgresql://...")
set_knowledge_base(kb)
```

### 自定义澄清逻辑

修改`prompts.py::CLARIFICATION_AGENT_PROMPT`，调整澄清策略：

```python
CLARIFICATION_AGENT_PROMPT = """
你是一个专业的问题澄清助手...

[自定义的澄清规则]

输出格式：
[自定义的输出格式]
"""
```

## 性能优化

### 1. 使用更便宜的模型进行澄清

```python
clarification_subagent = {
    ...
    "model": "claude-sonnet-4-20250514",  # 澄清任务用便宜模型
}

sql_generator_subagent = {
    ...
    "model": "claude-sonnet-4-5-20250929",  # SQL生成用强模型
}
```

### 2. 启用Prompt缓存

DeepAgents默认启用`AnthropicPromptCachingMiddleware`，会自动缓存稳定的prompt部分。

将不变的知识（如schema）放在prompt前部，可以大幅降低成本。

### 3. 并行调用

在主agent中可以并行调用多个子agent：

```python
# 在orchestrator prompt中指示
"""
你可以同时调用多个子agent来提高效率。
例如，同时查询用户数据和订单数据。
"""
```

## 常见问题

### Q: 澄清轮次过多怎么办？

A: 设置`max_clarification_rounds`限制最大轮次，并在prompt中指导agent更高效地提问：

```python
agent = create_intent_clarification_agent(
    max_clarification_rounds=3  # 最多3轮
)
```

### Q: 如何处理超出系统能力的问题？

A: 在意图识别阶段，将无法处理的问题分类为`unknown`，主agent会返回友好的错误消息。

### Q: 知识库检索效果不好？

A: 可以：
1. 优化检索关键词提取
2. 使用向量数据库提高语义匹配
3. 在prompt中指导agent更好地使用检索结果

### Q: 如何调试agent的执行过程？

A: 启用debug模式，并检查文件系统状态：

```python
agent = create_intent_clarification_agent(debug=True)
result = agent.invoke(...)

# 查看文件系统
for file_path, file_info in result.get("files", {}).items():
    print(f"{file_path}:\n{file_info['content']}\n")
```

## 运行示例

我们提供了多个示例演示不同的使用场景：

```bash
cd examples/intent_clarification

# 查看所有示例
python example_usage.py

# 运行特定示例
python example_usage.py 1  # 基本使用
python example_usage.py 2  # 流式输出
python example_usage.py 3  # 多轮对话
python example_usage.py 4  # 自定义知识库
python example_usage.py 5  # 配置选项
python example_usage.py 6  # 批量处理
python example_usage.py 7  # 错误处理
python example_usage.py 8  # 状态检查
```

## 贡献

欢迎贡献新的子agent、知识库实现或优化建议！

## 许可证

与DeepAgents项目相同的许可证。

## 相关资源

- [DeepAgents文档](https://github.com/langchain-ai/deepagents)
- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [架构设计文档](./ARCHITECTURE.md)
