"""
改进的中间件实现 - 支持多用户场景

使用状态schema而不是固定文件路径，确保会话隔离。
"""

from typing import Any, TypedDict, Literal
from langchain_core.runnables import RunnableConfig
from deepagents.middleware.base import AgentMiddleware
from .prompts import INTENT_CLASSIFICATION_PROMPT


# ==================== 状态Schema定义 ====================

class IntentClassificationState(TypedDict):
    """意图识别状态"""
    intent: str | None  # 识别出的意图类型
    needs_clarification: bool  # 是否需要澄清
    confidence: float  # 置信度
    missing_info: list[str]  # 缺失的信息


class ClarificationState(TypedDict):
    """澄清状态"""
    status: Literal["pending", "in_progress", "completed"]
    rounds: int  # 已进行的澄清轮次
    collected_info: dict[str, Any]  # 已收集的信息
    still_missing: list[str]  # 仍然缺失的信息


# ==================== 改进的中间件实现 ====================

class IntentClassificationMiddleware(AgentMiddleware):
    """
    意图识别中间件（多用户安全版本）

    使用状态字段而不是固定文件路径，确保多用户场景下的会话隔离。
    """

    def __init__(self, auto_classify: bool = True):
        self.auto_classify = auto_classify

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        # ✅ 使用状态字段检查，而不是文件路径
        intent_state = state.get("intent_classification")
        has_intent = intent_state is not None and intent_state.get("intent") is not None

        if not has_intent and self.auto_classify:
            # 获取thread_id用于日志和调试
            thread_id = config.get("configurable", {}).get("thread_id", "unknown")

            original_system_prompt = config.get("configurable", {}).get(
                "system_prompt", ""
            )

            # 注入意图识别指令
            enhanced_prompt = f"""{original_system_prompt}

# 首次任务：意图识别

在开始处理用户问题之前，你需要先进行意图识别和澄清判断。

{INTENT_CLASSIFICATION_PROMPT}

**重要**：完成意图识别后，请使用 write_file 工具将结果保存到：
- 路径：/intent_classification.json
- 格式：JSON对象，包含 intent, needs_clarification, missing_info 等字段

这个文件会被自动加载到状态中，用于后续流程判断。
"""

            if "configurable" not in config:
                config["configurable"] = {}
            config["configurable"]["system_prompt"] = enhanced_prompt

        return state


class ClarificationTrackingMiddleware(AgentMiddleware):
    """
    澄清过程跟踪中间件（多用户安全版本）

    使用状态字段跟踪澄清进度，防止无限循环。
    """

    def __init__(self, max_clarification_rounds: int = 5):
        self.max_rounds = max_clarification_rounds

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        # ✅ 从状态读取，而不是文件
        clarification_state = state.get("clarification", {})
        rounds = clarification_state.get("rounds", 0)

        if rounds >= self.max_rounds:
            # 在状态中添加警告
            if "warnings" not in state:
                state["warnings"] = []

            state["warnings"].append({
                "type": "max_rounds_reached",
                "message": f"已进行{rounds}轮澄清，接近最大轮次限制（{self.max_rounds}）。",
                "suggestion": "请尽快总结现有信息，生成澄清后的问题。"
            })

        return state


class ContextSummaryMiddleware(AgentMiddleware):
    """
    上下文总结中间件（多用户安全版本）

    定期触发上下文总结，减少token使用。
    """

    def __init__(self, summarize_every_n_rounds: int = 3):
        self.summarize_interval = summarize_every_n_rounds

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        clarification_state = state.get("clarification", {})
        rounds = clarification_state.get("rounds", 0)

        if rounds > 0 and rounds % self.summarize_interval == 0:
            original_system_prompt = config.get("configurable", {}).get(
                "system_prompt", ""
            )

            summary_prompt = f"""{original_system_prompt}

# 上下文总结提示

你已经进行了{rounds}轮澄清对话。请在继续之前，总结当前进度：

1. 回顾已收集的信息（从状态的 clarification 字段读取）
2. 识别哪些信息已经清晰，哪些还需要继续澄清
3. 评估是否已经收集了足够的信息可以生成澄清后的问题
4. 如果可以，生成澄清后的问题并标记状态为 "completed"
5. 如果不行，精简地继续提问（只问最关键的）
"""

            if "configurable" not in config:
                config["configurable"] = {}
            config["configurable"]["system_prompt"] = summary_prompt

        return state


# ==================== 工作空间路径管理器 ====================

class WorkspacePathManager:
    """
    工作空间路径管理器

    为每个会话生成独立的文件路径，确保多用户隔离。
    """

    @staticmethod
    def get_thread_workspace(thread_id: str | None) -> str:
        """
        获取线程专属的工作空间路径

        Args:
            thread_id: 线程ID，如果为None则返回默认路径

        Returns:
            工作空间根路径，例如 /workspace/session-123
        """
        if thread_id:
            return f"/workspace/{thread_id}"
        return "/workspace/default"

    @staticmethod
    def get_intent_file(thread_id: str | None) -> str:
        """获取意图识别结果文件路径"""
        workspace = WorkspacePathManager.get_thread_workspace(thread_id)
        return f"{workspace}/intent.json"

    @staticmethod
    def get_question_file(thread_id: str | None) -> str:
        """获取原始问题文件路径"""
        workspace = WorkspacePathManager.get_thread_workspace(thread_id)
        return f"{workspace}/question.txt"

    @staticmethod
    def get_clarification_context_file(thread_id: str | None) -> str:
        """获取澄清上下文文件路径"""
        workspace = WorkspacePathManager.get_thread_workspace(thread_id)
        return f"{workspace}/clarification_context.json"

    @staticmethod
    def get_clarified_question_file(thread_id: str | None) -> str:
        """获取澄清后的问题文件路径"""
        workspace = WorkspacePathManager.get_thread_workspace(thread_id)
        return f"{workspace}/clarified_question.txt"

    @staticmethod
    def get_result_file(thread_id: str | None) -> str:
        """获取结果文件路径"""
        workspace = WorkspacePathManager.get_thread_workspace(thread_id)
        return f"{workspace}/result.json"


# ==================== 辅助函数 ====================

def get_thread_id_from_config(config: RunnableConfig) -> str | None:
    """从配置中提取thread_id"""
    return config.get("configurable", {}).get("thread_id")


def ensure_thread_workspace(state: dict[str, Any], config: RunnableConfig) -> str:
    """
    确保线程工作空间存在

    Returns:
        工作空间路径
    """
    thread_id = get_thread_id_from_config(config)
    workspace = WorkspacePathManager.get_thread_workspace(thread_id)

    # 可以在这里创建工作空间目录的元数据
    # 实际的文件系统由FilesystemMiddleware管理

    return workspace


# ==================== 导出 ====================

__all__ = [
    "IntentClassificationMiddleware",
    "ClarificationTrackingMiddleware",
    "ContextSummaryMiddleware",
    "IntentClassificationState",
    "ClarificationState",
    "WorkspacePathManager",
    "get_thread_id_from_config",
    "ensure_thread_workspace",
]
