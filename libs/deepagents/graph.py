"""Deepagents come with planning, filesystem, and subagents."""

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig, TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ResponseFormat
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from deepagents.backends.protocol import BackendFactory, BackendProtocol
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware

BASE_AGENT_PROMPT = "In order to complete the objective that the user asks of you, you have access to a number of standard tools."


def get_default_model() -> ChatAnthropic:
    """Get the default model for deep agents.

    Returns:
        ChatAnthropic instance configured with Claude Sonnet 4.
    """
    return ChatAnthropic(
        model_name="claude-sonnet-4-5-20250929",
        max_tokens=20000,
    )


def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    disable_default_middleware: bool | set[str] | list[str] = False,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph:
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    six file editing tools: write_file, ls, read_file, edit_file, glob_search, grep_search,
    and a tool to call subagents.

    Args:
        model: The model to use. Defaults to Claude Sonnet 4.
        tools: The tools the agent should have access to.
        system_prompt: The additional instructions the agent should have. Will go in
            the system prompt.
        middleware: Additional middleware to apply after standard middleware.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the
                  sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `model` (either a LanguageModelLike instance or dict
                  settings)
                - (optional) `middleware` (list of AgentMiddleware)
        response_format: A structured output response format to use for the agent.
        context_schema: The schema of the deep agent.
        checkpointer: Optional checkpointer for persisting agent state between runs.
        store: Optional store for persistent storage (required if backend uses StoreBackend).
        backend: Optional backend for file storage. Pass either a Backend instance or a
            callable factory like `lambda rt: StateBackend(rt)`.
        interrupt_on: Optional Dict[str, bool | InterruptOnConfig] mapping tool names to
            interrupt configs.
        disable_default_middleware: Controls which default middleware to disable.
            - False (default): Enable all default middleware
            - True: Disable all default middleware
            - set/list of strings: Disable specific middleware by name
              Available names: "todo_list", "filesystem", "subagents",
              "summarization", "prompt_caching", "patch_tool_calls"
        debug: Whether to enable debug mode. Passed through to create_agent.
        name: The name of the agent. Passed through to create_agent.
        cache: The cache to use for the agent. Passed through to create_agent.

    Returns:
        A configured deep agent.
    """
    if model is None:
        model = get_default_model()

    # Convert disable_default_middleware to a set for easier checking
    if disable_default_middleware is True:
        disabled = {"todo_list", "filesystem", "subagents", "summarization", "prompt_caching", "patch_tool_calls"}
    elif disable_default_middleware is False:
        disabled = set()
    else:
        disabled = set(disable_default_middleware)

    # Build middleware list conditionally
    deepagent_middleware = []

    if "todo_list" not in disabled:
        deepagent_middleware.append(TodoListMiddleware())

    if "filesystem" not in disabled:
        deepagent_middleware.append(FilesystemMiddleware(backend=backend))

    if "subagents" not in disabled:
        # Build subagent default middleware based on disabled set
        subagent_default_middleware = []
        if "todo_list" not in disabled:
            subagent_default_middleware.append(TodoListMiddleware())
        if "filesystem" not in disabled:
            subagent_default_middleware.append(FilesystemMiddleware(backend=backend))
        if "summarization" not in disabled:
            subagent_default_middleware.append(
                SummarizationMiddleware(
                    model=model,
                    max_tokens_before_summary=170000,
                    messages_to_keep=6,
                )
            )
        if "prompt_caching" not in disabled:
            subagent_default_middleware.append(
                AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore")
            )
        if "patch_tool_calls" not in disabled:
            subagent_default_middleware.append(PatchToolCallsMiddleware())

        deepagent_middleware.append(
            SubAgentMiddleware(
                default_model=model,
                default_tools=tools,
                subagents=subagents if subagents is not None else [],
                default_middleware=subagent_default_middleware,
                default_interrupt_on=interrupt_on,
                general_purpose_agent=True,
            )
        )

    if "summarization" not in disabled:
        deepagent_middleware.append(
            SummarizationMiddleware(
                model=model,
                max_tokens_before_summary=170000,
                messages_to_keep=6,
            )
        )

    if "prompt_caching" not in disabled:
        deepagent_middleware.append(
            AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore")
        )

    if "patch_tool_calls" not in disabled:
        deepagent_middleware.append(PatchToolCallsMiddleware())
    if middleware:
        deepagent_middleware.extend(middleware)
    if interrupt_on is not None:
        deepagent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    return create_agent(
        model,
        system_prompt=system_prompt + "\n\n" + BASE_AGENT_PROMPT if system_prompt else BASE_AGENT_PROMPT,
        tools=tools,
        middleware=deepagent_middleware,
        response_format=response_format,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        debug=debug,
        name=name,
        cache=cache,
    ).with_config({"recursion_limit": 1000})
