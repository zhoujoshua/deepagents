"""
Agent定义模块

定义所有子agent的配置。
"""

from typing import Any
from deepagents.middleware import FilesystemMiddleware
from .prompts import CLARIFICATION_AGENT_PROMPT, SQL_GENERATOR_AGENT_PROMPT
from .tools import knowledge_retriever
from .middleware import ClarificationTrackingMiddleware, ContextSummaryMiddleware


# ==================== 问题澄清子Agent ====================

clarification_subagent: dict[str, Any] = {
    "name": "clarification-agent",
    "description": """用于澄清模糊或不完整的用户问题。

适用场景：
- 问题缺少时间范围
- 关键对象不明确
- 指标定义模糊
- 聚合维度不清晰
- 条件不完整

这个agent会通过多轮对话，逐步收集必要信息，最终生成一个完整、明确的问题描述。

输入：
- 用户的原始问题
- 意图识别结果（从/workspace/intent.json读取）

输出：
- 澄清后的完整问题
- 收集到的所有信息
- 状态标记（needs_more_info 或 clear）
""",
    "system_prompt": CLARIFICATION_AGENT_PROMPT,
    "tools": [
        knowledge_retriever,
        # FilesystemMiddleware会自动提供文件操作工具
    ],
    "middleware": [
        FilesystemMiddleware(),  # 访问共享文件系统
        ClarificationTrackingMiddleware(max_clarification_rounds=5),  # 跟踪轮次
        ContextSummaryMiddleware(summarize_every_n_rounds=3),  # 定期总结
    ],
    # 可以使用更便宜的模型进行澄清
    # "model": "claude-sonnet-4-20250514",
}


# ==================== SQL生成子Agent ====================

sql_generator_subagent: dict[str, Any] = {
    "name": "sql-generator",
    "description": """用于将明确的自然语言问题转换为SQL查询。

前置条件：
- 问题必须已经澄清完毕
- 需要的信息都已收集完整

功能：
1. 理解问题需求
2. 获取相关数据库schema
3. 获取业务规则
4. 参考历史案例
5. 生成SQL查询
6. 验证SQL正确性
7. 提供详细解释

输入：
- 澄清后的问题（从/workspace/clarified_question.txt读取）
- 澄清上下文（从/workspace/clarification_context.json读取）

输出：
- SQL查询语句
- SQL解释说明
- 涉及的表
- 复杂度评估
- 注意事项
""",
    "system_prompt": SQL_GENERATOR_AGENT_PROMPT,
    "tools": [
        knowledge_retriever,
        # FilesystemMiddleware会自动提供文件操作工具
    ],
    "middleware": [
        FilesystemMiddleware(),  # 访问共享文件系统
    ],
    # SQL生成可能需要更强的模型
    # "model": "claude-sonnet-4-5-20250929",
}


# ==================== 数据分析子Agent（示例扩展）====================

data_analyzer_subagent: dict[str, Any] = {
    "name": "data-analyzer",
    "description": """用于数据分析任务。

适用场景：
- 趋势分析
- 对比分析
- 占比分析
- 相关性分析

功能：
1. 生成数据查询（SQL或API调用）
2. 分析数据
3. 生成可视化建议
4. 提供洞察和结论

输入：
- 分析需求描述
- 数据范围和维度

输出：
- 分析步骤
- 查询语句
- 分析结果
- 可视化建议
""",
    "system_prompt": """
你是一个专业的数据分析助手。

你的任务是：
1. 理解分析需求
2. 设计分析方案
3. 生成数据查询
4. 分析数据并提取洞察
5. 提供可视化建议

请使用knowledge_retriever获取必要的背景信息，
使用文件系统工具保存中间结果。
""",
    "tools": [
        knowledge_retriever,
    ],
    "middleware": [
        FilesystemMiddleware(),
    ],
}


# ==================== Agent集合 ====================

ALL_SUBAGENTS = [
    clarification_subagent,
    sql_generator_subagent,
    data_analyzer_subagent,
]


# ==================== 意图到Agent的路由映射 ====================

INTENT_TO_AGENT_MAP = {
    "query_data": "sql-generator",
    "analyze_data": "data-analyzer",
    "generate_report": "report-generator",  # 可以后续添加
    "explain_concept": None,  # 主agent可以直接处理
    "unknown": None,  # 返回错误信息
}


def get_agent_for_intent(intent: str) -> str | None:
    """
    根据意图类型获取对应的处理agent名称

    Args:
        intent: 意图类型

    Returns:
        agent名称，如果没有对应的agent则返回None
    """
    return INTENT_TO_AGENT_MAP.get(intent)


# ==================== 导出 ====================

__all__ = [
    "clarification_subagent",
    "sql_generator_subagent",
    "data_analyzer_subagent",
    "ALL_SUBAGENTS",
    "INTENT_TO_AGENT_MAP",
    "get_agent_for_intent",
]
