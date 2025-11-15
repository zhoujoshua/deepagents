"""
意图识别与问题澄清Agent

一个基于DeepAgents框架的多agent协作系统，用于智能识别用户意图、
澄清模糊问题，并调用专业agent处理具体任务。

主要特性：
- 自动意图识别
- 多轮对话澄清
- 知识库集成
- 模块化prompt管理
- 可扩展的子agent架构

快速开始：

    from intent_clarification import create_intent_clarification_agent

    agent = create_intent_clarification_agent()
    result = agent.invoke({"messages": [("user", "查询销售额")]})
"""

from .intent_clarification_agent import (
    create_intent_clarification_agent,
    run_clarification_flow,
)
from .tools import (
    KnowledgeBase,
    MockKnowledgeBase,
    VectorKnowledgeBase,
    set_knowledge_base,
    get_knowledge_base,
    knowledge_retriever,
)
from .agents import (
    clarification_subagent,
    sql_generator_subagent,
    data_analyzer_subagent,
    ALL_SUBAGENTS,
    get_agent_for_intent,
)
from .middleware import (
    IntentClassificationMiddleware,
    ClarificationTrackingMiddleware,
    ContextSummaryMiddleware,
)

__version__ = "0.1.0"

__all__ = [
    # Main API
    "create_intent_clarification_agent",
    "run_clarification_flow",
    # Knowledge Base
    "KnowledgeBase",
    "MockKnowledgeBase",
    "VectorKnowledgeBase",
    "set_knowledge_base",
    "get_knowledge_base",
    "knowledge_retriever",
    # Agents
    "clarification_subagent",
    "sql_generator_subagent",
    "data_analyzer_subagent",
    "ALL_SUBAGENTS",
    "get_agent_for_intent",
    # Middleware
    "IntentClassificationMiddleware",
    "ClarificationTrackingMiddleware",
    "ContextSummaryMiddleware",
]
