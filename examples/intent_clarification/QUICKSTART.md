# 快速开始指南

5分钟快速上手意图识别与问题澄清Agent。

## 1. 安装

```bash
# 确保在deepagents项目根目录
cd /path/to/deepagents

# 安装deepagents库
pip install -e libs/deepagents

# （可选）安装额外依赖
cd examples/intent_clarification
pip install -r requirements.txt
```

## 2. 设置API Key

```bash
# 设置Anthropic API Key
export ANTHROPIC_API_KEY="your-api-key-here"
```

## 3. 第一个示例

创建文件 `my_first_agent.py`：

```python
from examples.intent_clarification import (
    create_intent_clarification_agent,
    set_knowledge_base,
    MockKnowledgeBase,
)

# 设置知识库（使用Mock实现，包含示例数据）
set_knowledge_base(MockKnowledgeBase())

# 创建agent
agent = create_intent_clarification_agent()

# 提问
question = "查询销售额"
result = agent.invoke({"messages": [("user", question)]})

# 查看响应
print(result["messages"][-1].content)
```

运行：

```bash
python my_first_agent.py
```

**预期输出**：Agent会识别出这是一个需要澄清的问题，并询问时间范围等信息。

## 4. 流式输出（更友好的交互）

```python
from examples.intent_clarification import run_clarification_flow

# 流式输出，实时显示agent的思考过程
for chunk in run_clarification_flow("统计活跃用户", stream=True):
    if "messages" in chunk:
        for message in chunk["messages"]:
            if hasattr(message, "content") and message.content:
                print(message.content)
                print("-" * 60)
```

## 5. 多轮对话

```python
from examples.intent_clarification import create_intent_clarification_agent

agent = create_intent_clarification_agent()

# 使用thread_id保持会话状态
thread_id = "my-session-001"
config = {"configurable": {"thread_id": thread_id}}

# 第一轮：提问
print("用户：查询销售额")
result = agent.invoke(
    {"messages": [("user", "查询销售额")]},
    config=config,
)
print(f"Agent：{result['messages'][-1].content}")

# 第二轮：回答agent的澄清问题
print("\n用户：本月的")
result = agent.invoke(
    {"messages": [("user", "本月的")]},
    config=config,
)
print(f"Agent：{result['messages'][-1].content}")

# 继续更多轮...
```

## 6. 自定义知识库

如果你想接入自己的数据库schema或业务规则：

```python
from examples.intent_clarification.tools import KnowledgeBase, set_knowledge_base

class MyKnowledgeBase(KnowledgeBase):
    def retrieve_schema(self, query: str):
        # 从你的数据库获取schema
        # 例如：使用SQLAlchemy的inspector
        return {
            "my_table": {
                "table_name": "my_table",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)"},
                    # ... 更多字段
                ],
            }
        }

    def retrieve_business_rule(self, query: str):
        # 从你的业务规则库获取
        return {
            "my_rule": {
                "rule": "业务规则名称",
                "description": "规则描述",
            }
        }

    def retrieve_example(self, query: str):
        # 从你的案例库获取
        return {
            "example_1": {
                "question": "示例问题",
                "clarified_question": "澄清后的问题",
                "sql": "SELECT ...",
            }
        }

# 设置为全局知识库
set_knowledge_base(MyKnowledgeBase())

# 之后创建的agent都会使用这个知识库
agent = create_intent_clarification_agent()
```

## 7. 配置选项

```python
agent = create_intent_clarification_agent(
    model="claude-sonnet-4-5-20250929",  # 选择模型
    enable_todo=True,                     # 启用任务规划
    enable_summarization=True,            # 启用上下文总结
    max_clarification_rounds=5,           # 最多5轮澄清
    debug=False,                          # 调试模式
)
```

## 8. 运行示例代码

我们提供了丰富的示例：

```bash
cd examples/intent_clarification

# 查看所有示例
python example_usage.py

# 运行特定示例
python example_usage.py 1  # 基本使用
python example_usage.py 2  # 流式输出
python example_usage.py 4  # 自定义知识库

# 或使用命令行工具
python intent_clarification_agent.py "查询销售额"
```

## 9. 运行测试

```bash
cd examples/intent_clarification

# 运行单元测试（不需要API key）
pytest test_basic.py -v

# 跳过集成测试
pytest test_basic.py -v -k "not Integration"
```

## 10. 下一步

- 阅读 [README.md](./README.md) 了解完整功能
- 阅读 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解架构设计
- 查看 `example_usage.py` 学习更多使用模式
- 根据你的需求定制prompts、agents和知识库

## 常见问题

### Q: 如何减少API调用成本？

A: 可以：
1. 对澄清agent使用更便宜的模型（claude-sonnet-4）
2. 启用prompt缓存（默认已启用）
3. 减少max_clarification_rounds
4. 禁用不必要的中间件（如todo、summarization）

### Q: 如何让澄清更高效？

A: 优化`prompts.py`中的`CLARIFICATION_AGENT_PROMPT`，指导agent：
- 一次问更多问题（但不要太多）
- 提供选项让用户快速选择
- 基于上下文做合理假设

### Q: 如何添加新的处理类型（除了SQL）？

A: 参考`agents.py`中的`sql_generator_subagent`，创建新的子agent，并在`INTENT_TO_AGENT_MAP`中添加路由。

### Q: 知识库检索效果不好？

A: 可以：
1. 使用向量数据库（VectorKnowledgeBase）提高语义匹配
2. 优化检索关键词提取
3. 增加更多高质量的案例数据

## 获取帮助

- 查看详细文档：[README.md](./README.md)
- 查看架构设计：[ARCHITECTURE.md](./ARCHITECTURE.md)
- 提交Issue：[DeepAgents GitHub](https://github.com/langchain-ai/deepagents/issues)

祝使用愉快！🚀
