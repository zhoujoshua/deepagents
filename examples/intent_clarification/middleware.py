"""
自定义中间件实现

提供意图识别等功能的中间件。
"""

from typing import Any
from langchain_core.runnables import RunnableConfig
from deepagents.middleware.base import AgentMiddleware
from .prompts import INTENT_CLASSIFICATION_PROMPT


class IntentClassificationMiddleware(AgentMiddleware):
    """
    意图识别中间件

    在agent首次处理用户问题时，注入意图识别的prompt和逻辑。
    """

    def __init__(self, auto_classify: bool = True):
        """
        Args:
            auto_classify: 是否自动进行意图识别（默认True）
        """
        self.auto_classify = auto_classify

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        """
        中间件执行逻辑

        如果状态中还没有intent字段，说明是首次进入，需要进行意图识别。
        此时修改系统prompt，注入意图识别的指令。
        """
        # 检查是否已经识别过意图
        messages = state.get("messages", [])

        # 检查文件系统中是否已有intent.json
        files = state.get("files", {})
        has_intent = "/workspace/intent.json" in files

        if not has_intent and self.auto_classify and messages:
            # 首次进入，需要意图识别
            # 修改系统prompt，注入意图识别指令
            original_system_prompt = config.get("configurable", {}).get(
                "system_prompt", ""
            )

            # 在原有prompt后添加意图识别指令
            enhanced_prompt = f"""{original_system_prompt}

# 首次任务：意图识别

在开始处理用户问题之前，你需要先进行意图识别和澄清判断。

{INTENT_CLASSIFICATION_PROMPT}

请立即进行意图识别，并将结果保存到 /workspace/intent.json 文件中。
"""

            # 更新配置
            if "configurable" not in config:
                config["configurable"] = {}
            config["configurable"]["system_prompt"] = enhanced_prompt

        return state


class ClarificationTrackingMiddleware(AgentMiddleware):
    """
    澄清过程跟踪中间件

    跟踪澄清过程的轮次，防止无限循环。
    """

    def __init__(self, max_clarification_rounds: int = 5):
        """
        Args:
            max_clarification_rounds: 最大澄清轮次（默认5轮）
        """
        self.max_rounds = max_clarification_rounds

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        """
        检查澄清轮次，如果超过最大轮次，添加警告。
        """
        # 从clarification_context.json中读取轮次
        files = state.get("files", {})
        clarification_context_file = "/workspace/clarification_context.json"

        if clarification_context_file in files:
            import json

            try:
                context = json.loads(files[clarification_context_file].get("content", "{}"))
                rounds = context.get("rounds", 0)

                if rounds >= self.max_rounds:
                    # 添加系统消息，建议结束澄清
                    state["_clarification_warning"] = (
                        f"警告：已进行{rounds}轮澄清，接近最大轮次限制（{self.max_rounds}）。"
                        "请尽快总结现有信息，生成澄清后的问题。"
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        return state


class ContextSummaryMiddleware(AgentMiddleware):
    """
    上下文总结中间件

    定期总结澄清上下文，避免token浪费。
    """

    def __init__(self, summarize_every_n_rounds: int = 3):
        """
        Args:
            summarize_every_n_rounds: 每N轮进行一次总结
        """
        self.summarize_interval = summarize_every_n_rounds

    def __call__(
        self, state: dict[str, Any], config: RunnableConfig
    ) -> dict[str, Any]:
        """
        检查是否需要总结，如果需要，在prompt中添加总结指令。
        """
        files = state.get("files", {})
        clarification_context_file = "/workspace/clarification_context.json"

        if clarification_context_file in files:
            import json

            try:
                context = json.loads(files[clarification_context_file].get("content", "{}"))
                rounds = context.get("rounds", 0)

                if rounds > 0 and rounds % self.summarize_interval == 0:
                    # 添加总结提示
                    original_system_prompt = config.get("configurable", {}).get(
                        "system_prompt", ""
                    )

                    summary_prompt = f"""{original_system_prompt}

# 上下文总结提示

你已经进行了{rounds}轮澄清对话。请在继续之前，总结当前已收集的信息：

1. 回顾 /workspace/clarification_context.json 中的所有信息
2. 识别哪些信息已经清晰，哪些还需要继续澄清
3. 评估是否已经收集了足够的信息可以生成澄清后的问题
4. 如果可以，生成澄清后的问题并标记状态为 "clear"
5. 如果不行，精简地继续提问（只问最关键的）
"""

                    if "configurable" not in config:
                        config["configurable"] = {}
                    config["configurable"]["system_prompt"] = summary_prompt

            except (json.JSONDecodeError, KeyError):
                pass

        return state


# ==================== 导出 ====================

__all__ = [
    "IntentClassificationMiddleware",
    "ClarificationTrackingMiddleware",
    "ContextSummaryMiddleware",
]
