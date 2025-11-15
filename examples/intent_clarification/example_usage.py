"""
使用示例

演示如何使用意图识别与问题澄清Agent。
"""

import asyncio
from intent_clarification_agent import (
    create_intent_clarification_agent,
    run_clarification_flow,
)
from tools import set_knowledge_base, MockKnowledgeBase


# ==================== 示例1: 基本使用 ====================


def example_basic():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    print()

    # 设置知识库（使用Mock实现）
    set_knowledge_base(MockKnowledgeBase())

    # 创建agent
    agent = create_intent_clarification_agent()

    # 调用agent
    question = "查询销售额"
    print(f"用户问题: {question}\n")

    result = agent.invoke({"messages": [("user", question)]})

    # 打印结果
    print("\n结果:")
    print(result)


# ==================== 示例2: 流式输出 ====================


def example_streaming():
    """流式输出示例"""
    print("\n\n")
    print("=" * 60)
    print("示例2: 流式输出")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    question = "最近有多少活跃用户"
    print(f"用户问题: {question}\n")
    print("Agent响应:")
    print("-" * 60)

    for chunk in run_clarification_flow(question, stream=True):
        if "messages" in chunk:
            for message in chunk["messages"]:
                if hasattr(message, "content") and message.content:
                    print(message.content)
                    print()


# ==================== 示例3: 多轮对话 ====================


def example_multi_turn():
    """多轮对话示例（模拟人工交互）"""
    print("\n\n")
    print("=" * 60)
    print("示例3: 多轮对话（需要人工参与）")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    # 创建agent，使用thread_id来保持会话状态
    agent = create_intent_clarification_agent()
    thread_id = "example-session-123"
    config = {"configurable": {"thread_id": thread_id}}

    # 第一轮：用户提问
    print("用户: 查询销售额")
    print()

    result = agent.invoke(
        {"messages": [("user", "查询销售额")]},
        config=config,
    )

    # 打印agent的响应（会问澄清问题）
    print("Agent:", result["messages"][-1].content)
    print()

    # 第二轮：用户回答
    print("用户: 本月的")
    print()

    result = agent.invoke(
        {"messages": [("user", "本月的")]},
        config=config,
    )

    print("Agent:", result["messages"][-1].content)
    print()

    # 可以继续更多轮...


# ==================== 示例4: 自定义知识库 ====================


def example_custom_knowledge_base():
    """使用自定义知识库示例"""
    print("\n\n")
    print("=" * 60)
    print("示例4: 自定义知识库")
    print("=" * 60)
    print()

    from tools import KnowledgeBase

    class CustomKnowledgeBase(KnowledgeBase):
        """自定义知识库实现"""

        def retrieve_schema(self, query: str):
            # 从你的数据库或API获取schema
            return {
                "custom_table": {
                    "table_name": "custom_table",
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "data", "type": "TEXT"},
                    ],
                }
            }

        def retrieve_business_rule(self, query: str):
            # 从你的业务规则库获取
            return {
                "custom_rule": {
                    "rule": "自定义规则",
                    "description": "这是一个自定义的业务规则",
                }
            }

        def retrieve_example(self, query: str):
            # 从你的案例库获取
            return {
                "custom_example": {
                    "question": "示例问题",
                    "sql": "SELECT * FROM custom_table",
                }
            }

    # 设置自定义知识库
    set_knowledge_base(CustomKnowledgeBase())

    agent = create_intent_clarification_agent()
    result = agent.invoke({"messages": [("user", "查询自定义表的数据")]})

    print("使用自定义知识库的结果:")
    print(result["messages"][-1].content)


# ==================== 示例5: 配置选项 ====================


def example_configuration():
    """配置选项示例"""
    print("\n\n")
    print("=" * 60)
    print("示例5: 配置选项")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    # 创建agent时可以配置各种选项
    agent = create_intent_clarification_agent(
        model="claude-sonnet-4-20250514",  # 使用不同的模型
        enable_todo=False,  # 禁用任务规划
        enable_summarization=False,  # 禁用上下文总结
        max_clarification_rounds=3,  # 最多3轮澄清
        debug=True,  # 启用调试模式
    )

    result = agent.invoke({"messages": [("user", "统计商品销量")]})

    print("配置后的agent响应:")
    print(result["messages"][-1].content)


# ==================== 示例6: 批量处理 ====================


async def example_batch_processing():
    """批量处理多个问题"""
    print("\n\n")
    print("=" * 60)
    print("示例6: 批量处理")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    questions = [
        "查询销售额",
        "统计活跃用户",
        "哪些商品卖得最好",
        "用户留存率如何",
    ]

    agent = create_intent_clarification_agent()

    # 并行处理多个问题
    async def process_question(q):
        return agent.invoke({"messages": [("user", q)]})

    tasks = [process_question(q) for q in questions]
    results = await asyncio.gather(*tasks)

    for question, result in zip(questions, results):
        print(f"\n问题: {question}")
        print(f"响应: {result['messages'][-1].content[:100]}...")
        print("-" * 60)


# ==================== 示例7: 错误处理 ====================


def example_error_handling():
    """错误处理示例"""
    print("\n\n")
    print("=" * 60)
    print("示例7: 错误处理")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    agent = create_intent_clarification_agent()

    try:
        # 故意传入不合法的输入
        result = agent.invoke({"messages": []})  # 空消息列表
    except Exception as e:
        print(f"捕获到错误: {type(e).__name__}: {e}")

    try:
        # 传入非常复杂或模糊的问题
        complex_question = "帮我分析一下整体业务情况并给出优化建议"
        result = agent.invoke({"messages": [("user", complex_question)]})
        print(f"\n复杂问题的处理:")
        print(result["messages"][-1].content)
    except Exception as e:
        print(f"处理复杂问题时出错: {e}")


# ==================== 示例8: 状态检查 ====================


def example_state_inspection():
    """状态检查示例"""
    print("\n\n")
    print("=" * 60)
    print("示例8: 状态检查")
    print("=" * 60)
    print()

    set_knowledge_base(MockKnowledgeBase())

    agent = create_intent_clarification_agent()

    result = agent.invoke({"messages": [("user", "查询销售额")]})

    # 检查文件系统状态
    print("\n文件系统状态:")
    if "files" in result:
        for file_path, file_info in result["files"].items():
            print(f"\n文件: {file_path}")
            print(f"大小: {len(file_info.get('content', ''))} 字节")
            if file_path.endswith(".json"):
                import json

                try:
                    content = json.loads(file_info.get("content", "{}"))
                    print(f"内容: {json.dumps(content, indent=2, ensure_ascii=False)}")
                except:
                    print(f"内容: {file_info.get('content', '')[:100]}...")

    # 检查消息历史
    print("\n\n消息历史:")
    for i, message in enumerate(result["messages"]):
        print(f"\n消息 {i+1}:")
        print(f"  角色: {message.type if hasattr(message, 'type') else 'unknown'}")
        print(f"  内容: {str(message.content)[:100]}...")


# ==================== 主函数 ====================


def main():
    """运行所有示例"""
    import sys

    examples = {
        "1": ("基本使用", example_basic),
        "2": ("流式输出", example_streaming),
        "3": ("多轮对话", example_multi_turn),
        "4": ("自定义知识库", example_custom_knowledge_base),
        "5": ("配置选项", example_configuration),
        "6": ("批量处理", lambda: asyncio.run(example_batch_processing())),
        "7": ("错误处理", example_error_handling),
        "8": ("状态检查", example_state_inspection),
    }

    if len(sys.argv) > 1:
        # 运行指定的示例
        example_num = sys.argv[1]
        if example_num in examples:
            name, func = examples[example_num]
            print(f"\n运行示例: {name}\n")
            func()
        else:
            print(f"未知的示例编号: {example_num}")
            print(f"可用的示例: {', '.join(examples.keys())}")
    else:
        # 显示所有可用示例
        print("可用的示例:")
        print()
        for num, (name, _) in examples.items():
            print(f"  {num}. {name}")
        print()
        print("用法: python example_usage.py <示例编号>")
        print('例如: python example_usage.py 1')
        print()
        print("或者不带参数运行所有示例（可能需要较长时间）")

        # 可选：运行所有示例
        # for name, func in examples.values():
        #     func()


if __name__ == "__main__":
    main()
