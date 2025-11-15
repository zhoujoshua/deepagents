"""
意图识别与问题澄清Agent

这是主控制agent的实现，负责协调整个流程。
"""

from deepagents import create_deep_agent
from deepagents.middleware import (
    TodoListMiddleware,
    FilesystemMiddleware,
    SubAgentMiddleware,
    SummarizationMiddleware,
)

from .prompts import ORCHESTRATOR_PROMPT
from .agents import ALL_SUBAGENTS
from .middleware import IntentClassificationMiddleware
from .tools import knowledge_retriever


def create_intent_clarification_agent(
    model: str = "claude-sonnet-4-5-20250929",
    enable_todo: bool = True,
    enable_summarization: bool = True,
    max_clarification_rounds: int = 5,
    **kwargs,
):
    """
    创建意图识别与问题澄清Agent

    这个agent能够：
    1. 识别用户问题的意图
    2. 判断是否需要澄清
    3. 通过多轮对话澄清问题
    4. 调用知识库获取背景信息
    5. 用户确认后，调用相应的处理agent
    6. 返回最终结果

    Args:
        model: 使用的模型名称
        enable_todo: 是否启用任务规划（默认True）
        enable_summarization: 是否启用上下文总结（默认True）
        max_clarification_rounds: 最大澄清轮次（默认5）
        **kwargs: 传递给create_deep_agent的其他参数

    Returns:
        CompiledStateGraph: 编译后的agent

    Example:
        >>> agent = create_intent_clarification_agent()
        >>> result = agent.invoke({
        ...     "messages": [("user", "查询销售额")]
        ... })
    """

    # 构建中间件栈
    middleware = []

    # 1. 意图识别中间件（首次运行时注入）
    middleware.append(IntentClassificationMiddleware())

    # 2. 任务规划中间件（可选）
    if enable_todo:
        middleware.append(TodoListMiddleware())

    # 3. 文件系统中间件（用于保存和共享状态）
    middleware.append(FilesystemMiddleware())

    # 4. 子Agent中间件（管理所有子agent）
    middleware.append(
        SubAgentMiddleware(
            subagents=ALL_SUBAGENTS,
            # 子agent默认使用和主agent相同的模型
            default_model=model,
            # 子agent可以访问知识库工具
            default_tools=[knowledge_retriever],
        )
    )

    # 5. 上下文总结中间件（可选，避免token溢出）
    if enable_summarization:
        middleware.append(SummarizationMiddleware())

    # 创建agent
    agent = create_deep_agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        middleware=middleware,
        tools=[
            knowledge_retriever,  # 主agent也可以直接调用知识库
        ],
        **kwargs,
    )

    return agent


# ==================== 便捷的流式调用接口 ====================


def run_clarification_flow(
    question: str,
    model: str = "claude-sonnet-4-5-20250929",
    stream: bool = True,
    thread_id: str | None = None,
):
    """
    运行完整的问题澄清流程

    这是一个高层接口，简化了agent的调用。

    Args:
        question: 用户的原始问题
        model: 使用的模型
        stream: 是否使用流式输出（默认True）
        thread_id: 会话ID，用于持久化状态（可选）

    Yields:
        如果stream=True，yield每个输出chunk
        如果stream=False，返回最终结果

    Example:
        >>> for chunk in run_clarification_flow("查询销售额"):
        ...     print(chunk)
    """

    # 创建agent
    agent = create_intent_clarification_agent(model=model)

    # 构建配置
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # 构建输入
    input_data = {"messages": [("user", question)]}

    # 运行
    if stream:
        for chunk in agent.stream(input_data, config):
            yield chunk
    else:
        return agent.invoke(input_data, config)


# ==================== 命令行接口 ====================


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python intent_clarification_agent.py <问题>")
        print('例如: python intent_clarification_agent.py "查询销售额"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"问题: {question}\n")
    print("=" * 60)
    print()

    # 运行agent
    for chunk in run_clarification_flow(question, stream=True):
        # 打印agent的输出
        if "messages" in chunk:
            for message in chunk["messages"]:
                if hasattr(message, "content"):
                    print(message.content)
        print()


if __name__ == "__main__":
    main()


# ==================== 导出 ====================

__all__ = [
    "create_intent_clarification_agent",
    "run_clarification_flow",
]
