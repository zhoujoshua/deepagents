"""Middleware for workflow-based routing between agents with conditional branching."""

from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from typing import Any, Literal, NotRequired, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain.tools import BaseTool, ToolRuntime
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import StructuredTool
from langgraph.types import Command


class NodeType(str, Enum):
    """Type of workflow node."""

    AGENT = "agent"
    """Execute an agent."""
    CONDITION = "condition"
    """Conditional branching based on state."""
    PARALLEL = "parallel"
    """Execute multiple agents in parallel."""
    SEQUENTIAL = "sequential"
    """Execute agents in sequence."""


class ConditionOperator(str, Enum):
    """Operators for condition evaluation."""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MATCHES_REGEX = "matches"


class ConditionRule(TypedDict):
    """A single condition rule."""

    field: str
    """State field to evaluate."""

    operator: ConditionOperator
    """Comparison operator."""

    value: NotRequired[Any]
    """Value to compare against (not needed for exists/not_exists)."""


class ConditionalBranch(TypedDict):
    """A conditional branch with rules and target node."""

    conditions: list[ConditionRule]
    """List of conditions (all must be true - AND logic)."""

    logic: NotRequired[Literal["AND", "OR"]]
    """Logic operator for combining conditions. Default is AND."""

    next_node: str
    """Node ID to execute if conditions are met."""


class WorkflowAgent(TypedDict):
    """Specification for an agent in a workflow."""

    name: str
    """The name of the agent."""

    description: str
    """The description of the agent."""

    system_prompt: str
    """The system prompt to use for the agent."""

    tools: Sequence[BaseTool | Callable | dict[str, Any]]
    """The tools to use for the agent."""

    model: NotRequired[str | BaseChatModel]
    """The model for the agent. Defaults to `default_model`."""

    middleware: NotRequired[list[AgentMiddleware]]
    """Additional middleware to append after `default_middleware`."""

    interrupt_on: NotRequired[dict[str, bool | InterruptOnConfig]]
    """The tool configs to use for the agent."""


class WorkflowNode(TypedDict):
    """A node in the workflow graph."""

    id: str
    """Unique identifier for this node."""

    type: NodeType
    """Type of node (agent, condition, parallel, sequential)."""

    agent: NotRequired[str]
    """Agent name to execute (for AGENT type nodes)."""

    branches: NotRequired[list[ConditionalBranch]]
    """Conditional branches (for CONDITION type nodes)."""

    children: NotRequired[list[str]]
    """Child node IDs (for PARALLEL/SEQUENTIAL type nodes)."""

    next_node: NotRequired[str]
    """Default next node ID (for AGENT and SEQUENTIAL nodes)."""

    default_branch: NotRequired[str]
    """Default branch if no conditions match (for CONDITION nodes)."""


class WorkflowDefinition(TypedDict):
    """Complete workflow definition."""

    start_node: str
    """ID of the starting node."""

    nodes: list[WorkflowNode]
    """All nodes in the workflow."""


# State keys that should be excluded when passing state to workflow agents
_EXCLUDED_STATE_KEYS = ("messages", "todos")

WORKFLOW_TOOL_DESCRIPTION = """Execute a workflow that routes between multiple agents based on conditions and branching logic.

This tool enables complex multi-agent orchestration with:
- **Conditional Routing**: Branch to different agents based on state conditions
- **Sequential Execution**: Chain agents together in a specific order
- **Parallel Execution**: Run multiple agents concurrently
- **Decision Trees**: Build complex routing logic with nested conditions

Available workflows:
{available_workflows}

## Usage notes:
1. Specify the workflow_id to execute
2. Provide a clear description of what you want the workflow to accomplish
3. The workflow will automatically route between agents based on the defined logic
4. Results from each agent are accumulated and returned at the end
"""

WORKFLOW_SYSTEM_PROMPT = """## `execute_workflow` (workflow orchestrator)

You have access to an `execute_workflow` tool that orchestrates complex multi-agent workflows with conditional routing, sequential execution, and parallel processing.

Use this when:
- Tasks require multiple specialized agents working together
- Routing logic depends on intermediate results or state conditions
- You need to parallelize independent sub-tasks across different agents
- Complex decision trees guide the execution flow

The workflow will automatically handle agent coordination, state management, and result aggregation."""


def _evaluate_condition(rule: ConditionRule, state: dict[str, Any]) -> bool:
    """Evaluate a single condition rule against the state.

    Args:
        rule: The condition rule to evaluate.
        state: The current state.

    Returns:
        True if the condition is met, False otherwise.
    """
    import re

    field = rule["field"]
    operator = rule["operator"]
    expected_value = rule.get("value")

    # Handle nested field access (e.g., "user.name")
    field_value = state
    for key in field.split("."):
        if isinstance(field_value, dict) and key in field_value:
            field_value = field_value[key]
        else:
            field_value = None
            break

    # Evaluate based on operator
    if operator == ConditionOperator.EXISTS:
        return field_value is not None

    if operator == ConditionOperator.NOT_EXISTS:
        return field_value is None

    if field_value is None:
        return False

    if operator == ConditionOperator.EQUALS:
        return field_value == expected_value

    if operator == ConditionOperator.NOT_EQUALS:
        return field_value != expected_value

    if operator == ConditionOperator.GREATER_THAN:
        return field_value > expected_value

    if operator == ConditionOperator.LESS_THAN:
        return field_value < expected_value

    if operator == ConditionOperator.GREATER_EQUAL:
        return field_value >= expected_value

    if operator == ConditionOperator.LESS_EQUAL:
        return field_value <= expected_value

    if operator == ConditionOperator.CONTAINS:
        return expected_value in field_value

    if operator == ConditionOperator.NOT_CONTAINS:
        return expected_value not in field_value

    if operator == ConditionOperator.IN:
        return field_value in expected_value

    if operator == ConditionOperator.NOT_IN:
        return field_value not in expected_value

    if operator == ConditionOperator.MATCHES_REGEX:
        return bool(re.match(expected_value, str(field_value)))

    return False


def _evaluate_branch(branch: ConditionalBranch, state: dict[str, Any]) -> bool:
    """Evaluate a conditional branch against the state.

    Args:
        branch: The branch to evaluate.
        state: The current state.

    Returns:
        True if the branch conditions are met, False otherwise.
    """
    logic = branch.get("logic", "AND")
    conditions = branch["conditions"]

    if logic == "OR":
        return any(_evaluate_condition(rule, state) for rule in conditions)
    else:  # AND
        return all(_evaluate_condition(rule, state) for rule in conditions)


class WorkflowExecutor:
    """Executes a workflow definition with state management."""

    def __init__(
        self,
        workflow: WorkflowDefinition,
        agents: dict[str, Runnable],
        state: dict[str, Any],
    ):
        """Initialize the workflow executor.

        Args:
            workflow: The workflow definition to execute.
            agents: Dictionary mapping agent names to runnable instances.
            state: Initial state for the workflow.
        """
        self.workflow = workflow
        self.agents = agents
        self.state = state
        self.nodes = {node["id"]: node for node in workflow["nodes"]}
        self.execution_log: list[dict[str, Any]] = []

    def execute(self) -> dict[str, Any]:
        """Execute the workflow from the start node.

        Returns:
            Final state after workflow execution.
        """
        current_node_id = self.workflow["start_node"]
        visited_nodes = set()

        while current_node_id:
            # Prevent infinite loops
            if current_node_id in visited_nodes:
                self.execution_log.append({
                    "node_id": current_node_id,
                    "type": "error",
                    "error": "Circular reference detected",
                })
                break
            visited_nodes.add(current_node_id)

            node = self.nodes.get(current_node_id)
            if not node:
                self.execution_log.append({
                    "node_id": current_node_id,
                    "type": "error",
                    "error": f"Node {current_node_id} not found",
                })
                break

            # Execute the node
            current_node_id = self._execute_node(node)

        return self.state

    async def aexecute(self) -> dict[str, Any]:
        """Execute the workflow asynchronously.

        Returns:
            Final state after workflow execution.
        """
        current_node_id = self.workflow["start_node"]
        visited_nodes = set()

        while current_node_id:
            if current_node_id in visited_nodes:
                self.execution_log.append({
                    "node_id": current_node_id,
                    "type": "error",
                    "error": "Circular reference detected",
                })
                break
            visited_nodes.add(current_node_id)

            node = self.nodes.get(current_node_id)
            if not node:
                self.execution_log.append({
                    "node_id": current_node_id,
                    "type": "error",
                    "error": f"Node {current_node_id} not found",
                })
                break

            current_node_id = await self._aexecute_node(node)

        return self.state

    def _execute_node(self, node: WorkflowNode) -> str | None:
        """Execute a single node in the workflow.

        Args:
            node: The node to execute.

        Returns:
            ID of the next node to execute, or None to end execution.
        """
        node_type = node["type"]

        if node_type == NodeType.AGENT:
            return self._execute_agent_node(node)
        elif node_type == NodeType.CONDITION:
            return self._execute_condition_node(node)
        elif node_type == NodeType.SEQUENTIAL:
            return self._execute_sequential_node(node)
        elif node_type == NodeType.PARALLEL:
            return self._execute_parallel_node(node)

        return None

    async def _aexecute_node(self, node: WorkflowNode) -> str | None:
        """Execute a single node asynchronously.

        Args:
            node: The node to execute.

        Returns:
            ID of the next node to execute, or None to end execution.
        """
        node_type = node["type"]

        if node_type == NodeType.AGENT:
            return await self._aexecute_agent_node(node)
        elif node_type == NodeType.CONDITION:
            return self._execute_condition_node(node)
        elif node_type == NodeType.SEQUENTIAL:
            return await self._aexecute_sequential_node(node)
        elif node_type == NodeType.PARALLEL:
            return await self._aexecute_parallel_node(node)

        return None

    def _execute_agent_node(self, node: WorkflowNode) -> str | None:
        """Execute an agent node.

        Args:
            node: The agent node to execute.

        Returns:
            ID of the next node to execute.
        """
        agent_name = node.get("agent")
        if not agent_name or agent_name not in self.agents:
            self.execution_log.append({
                "node_id": node["id"],
                "type": "error",
                "error": f"Agent {agent_name} not found",
            })
            return None

        agent = self.agents[agent_name]

        # Prepare agent state (exclude messages and todos)
        agent_state = {k: v for k, v in self.state.items() if k not in _EXCLUDED_STATE_KEYS}

        # Get the task description from the last message if available
        messages = self.state.get("messages", [])
        task_description = messages[-1].content if messages and hasattr(messages[-1], "content") else ""

        agent_state["messages"] = [HumanMessage(content=task_description)]

        # Execute the agent
        result = agent.invoke(agent_state)

        # Update state with agent result (excluding messages and todos)
        state_update = {k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS}
        self.state.update(state_update)

        # Store the agent's response message
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            # Update workflow execution result
            if "workflow_results" not in self.state:
                self.state["workflow_results"] = []
            self.state["workflow_results"].append({
                "agent": agent_name,
                "node_id": node["id"],
                "result": last_message.content if hasattr(last_message, "content") else str(last_message),
            })

        self.execution_log.append({
            "node_id": node["id"],
            "type": "agent",
            "agent": agent_name,
        })

        return node.get("next_node")

    async def _aexecute_agent_node(self, node: WorkflowNode) -> str | None:
        """Execute an agent node asynchronously.

        Args:
            node: The agent node to execute.

        Returns:
            ID of the next node to execute.
        """
        agent_name = node.get("agent")
        if not agent_name or agent_name not in self.agents:
            self.execution_log.append({
                "node_id": node["id"],
                "type": "error",
                "error": f"Agent {agent_name} not found",
            })
            return None

        agent = self.agents[agent_name]

        agent_state = {k: v for k, v in self.state.items() if k not in _EXCLUDED_STATE_KEYS}

        messages = self.state.get("messages", [])
        task_description = messages[-1].content if messages and hasattr(messages[-1], "content") else ""

        agent_state["messages"] = [HumanMessage(content=task_description)]

        result = await agent.ainvoke(agent_state)

        state_update = {k: v for k, v in result.items() if k not in _EXCLUDED_STATE_KEYS}
        self.state.update(state_update)

        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if "workflow_results" not in self.state:
                self.state["workflow_results"] = []
            self.state["workflow_results"].append({
                "agent": agent_name,
                "node_id": node["id"],
                "result": last_message.content if hasattr(last_message, "content") else str(last_message),
            })

        self.execution_log.append({
            "node_id": node["id"],
            "type": "agent",
            "agent": agent_name,
        })

        return node.get("next_node")

    def _execute_condition_node(self, node: WorkflowNode) -> str | None:
        """Execute a condition node.

        Args:
            node: The condition node to execute.

        Returns:
            ID of the next node based on condition evaluation.
        """
        branches = node.get("branches", [])

        for branch in branches:
            if _evaluate_branch(branch, self.state):
                self.execution_log.append({
                    "node_id": node["id"],
                    "type": "condition",
                    "branch_taken": branch["next_node"],
                })
                return branch["next_node"]

        # No condition matched, use default branch
        default_branch = node.get("default_branch")
        self.execution_log.append({
            "node_id": node["id"],
            "type": "condition",
            "branch_taken": default_branch or "none",
        })
        return default_branch

    def _execute_sequential_node(self, node: WorkflowNode) -> str | None:
        """Execute a sequential node (executes children in order).

        Args:
            node: The sequential node to execute.

        Returns:
            ID of the next node after all children complete.
        """
        children = node.get("children", [])

        for child_id in children:
            child_node = self.nodes.get(child_id)
            if child_node:
                # Execute child and continue to next child
                self._execute_node(child_node)

        self.execution_log.append({
            "node_id": node["id"],
            "type": "sequential",
            "children_executed": len(children),
        })

        return node.get("next_node")

    async def _aexecute_sequential_node(self, node: WorkflowNode) -> str | None:
        """Execute a sequential node asynchronously.

        Args:
            node: The sequential node to execute.

        Returns:
            ID of the next node after all children complete.
        """
        children = node.get("children", [])

        for child_id in children:
            child_node = self.nodes.get(child_id)
            if child_node:
                await self._aexecute_node(child_node)

        self.execution_log.append({
            "node_id": node["id"],
            "type": "sequential",
            "children_executed": len(children),
        })

        return node.get("next_node")

    def _execute_parallel_node(self, node: WorkflowNode) -> str | None:
        """Execute a parallel node (executes children concurrently).

        Args:
            node: The parallel node to execute.

        Returns:
            ID of the next node after all children complete.
        """
        import concurrent.futures

        children = node.get("children", [])

        def execute_child(child_id: str) -> None:
            child_node = self.nodes.get(child_id)
            if child_node:
                self._execute_node(child_node)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(execute_child, child_id) for child_id in children]
            concurrent.futures.wait(futures)

        self.execution_log.append({
            "node_id": node["id"],
            "type": "parallel",
            "children_executed": len(children),
        })

        return node.get("next_node")

    async def _aexecute_parallel_node(self, node: WorkflowNode) -> str | None:
        """Execute a parallel node asynchronously.

        Args:
            node: The parallel node to execute.

        Returns:
            ID of the next node after all children complete.
        """
        import asyncio

        children = node.get("children", [])

        async def execute_child(child_id: str) -> None:
            child_node = self.nodes.get(child_id)
            if child_node:
                await self._aexecute_node(child_node)

        await asyncio.gather(*[execute_child(child_id) for child_id in children])

        self.execution_log.append({
            "node_id": node["id"],
            "type": "parallel",
            "children_executed": len(children),
        })

        return node.get("next_node")


def _create_workflow_tool(
    *,
    workflows: dict[str, WorkflowDefinition],
    agents: dict[str, Runnable],
    workflow_description: str | None = None,
) -> BaseTool:
    """Create a workflow execution tool.

    Args:
        workflows: Dictionary mapping workflow IDs to workflow definitions.
        agents: Dictionary mapping agent names to runnable instances.
        workflow_description: Custom description for the workflow tool.

    Returns:
        A StructuredTool that can execute workflows.
    """
    workflow_list = "\n".join([f"- {wf_id}: {wf['start_node']} -> ..." for wf_id, wf in workflows.items()])

    if workflow_description is None:
        workflow_description = WORKFLOW_TOOL_DESCRIPTION.format(available_workflows=workflow_list)
    elif "{available_workflows}" in workflow_description:
        workflow_description = workflow_description.format(available_workflows=workflow_list)

    def execute_workflow(
        workflow_id: str,
        description: str,
        runtime: ToolRuntime,
    ) -> str | Command:
        """Execute a workflow by ID."""
        if workflow_id not in workflows:
            msg = f"Workflow {workflow_id} not found. Available workflows: {list(workflows.keys())}"
            raise ValueError(msg)

        workflow = workflows[workflow_id]

        # Prepare initial state from runtime state
        initial_state = {k: v for k, v in runtime.state.items() if k not in _EXCLUDED_STATE_KEYS}
        initial_state["messages"] = [HumanMessage(content=description)]

        executor = WorkflowExecutor(workflow, agents, initial_state)
        result_state = executor.execute()

        # Format results
        workflow_results = result_state.get("workflow_results", [])
        result_text = f"Workflow '{workflow_id}' completed.\n\n"

        for i, result in enumerate(workflow_results, 1):
            result_text += f"{i}. Agent '{result['agent']}' (node: {result['node_id']}):\n{result['result']}\n\n"

        # Return Command with state update
        if not runtime.tool_call_id:
            return result_text

        state_update = {k: v for k, v in result_state.items() if k not in _EXCLUDED_STATE_KEYS and k != "workflow_results"}

        return Command(
            update={
                **state_update,
                "messages": [ToolMessage(result_text, tool_call_id=runtime.tool_call_id)],
            }
        )

    async def aexecute_workflow(
        workflow_id: str,
        description: str,
        runtime: ToolRuntime,
    ) -> str | Command:
        """Execute a workflow by ID asynchronously."""
        if workflow_id not in workflows:
            msg = f"Workflow {workflow_id} not found. Available workflows: {list(workflows.keys())}"
            raise ValueError(msg)

        workflow = workflows[workflow_id]

        initial_state = {k: v for k, v in runtime.state.items() if k not in _EXCLUDED_STATE_KEYS}
        initial_state["messages"] = [HumanMessage(content=description)]

        executor = WorkflowExecutor(workflow, agents, initial_state)
        result_state = await executor.aexecute()

        workflow_results = result_state.get("workflow_results", [])
        result_text = f"Workflow '{workflow_id}' completed.\n\n"

        for i, result in enumerate(workflow_results, 1):
            result_text += f"{i}. Agent '{result['agent']}' (node: {result['node_id']}):\n{result['result']}\n\n"

        if not runtime.tool_call_id:
            return result_text

        state_update = {k: v for k, v in result_state.items() if k not in _EXCLUDED_STATE_KEYS and k != "workflow_results"}

        return Command(
            update={
                **state_update,
                "messages": [ToolMessage(result_text, tool_call_id=runtime.tool_call_id)],
            }
        )

    return StructuredTool.from_function(
        name="execute_workflow",
        func=execute_workflow,
        coroutine=aexecute_workflow,
        description=workflow_description,
    )


class WorkflowRoutingMiddleware(AgentMiddleware):
    """Middleware for workflow-based routing between agents.

    This middleware enables complex multi-agent orchestration with:
    - Conditional routing based on state
    - Sequential agent execution
    - Parallel agent execution
    - Decision tree logic

    Args:
        default_model: The model to use for workflow agents.
        default_tools: The tools to use for workflow agents.
        default_middleware: Default middleware to apply to all workflow agents.
        default_interrupt_on: The tool configs to use for workflow agents.
        agents: Dictionary mapping agent names to WorkflowAgent specifications.
        workflows: Dictionary mapping workflow IDs to WorkflowDefinition specifications.
        system_prompt: Full system prompt override for the workflow tool.
        workflow_description: Custom description for the workflow tool.

    Example:
        ```python
        from deepagents.middleware import WorkflowRoutingMiddleware

        # Define agents
        agents = {
            "researcher": WorkflowAgent(
                name="researcher",
                description="Research agent",
                system_prompt="You are a research assistant.",
                tools=[],
            ),
            "writer": WorkflowAgent(
                name="writer",
                description="Writing agent",
                system_prompt="You are a writing assistant.",
                tools=[],
            ),
        }

        # Define workflow
        workflow = WorkflowDefinition(
            start_node="research",
            nodes=[
                WorkflowNode(
                    id="research",
                    type=NodeType.AGENT,
                    agent="researcher",
                    next_node="write",
                ),
                WorkflowNode(
                    id="write",
                    type=NodeType.AGENT,
                    agent="writer",
                ),
            ],
        )

        # Create middleware
        middleware = WorkflowRoutingMiddleware(
            default_model="openai:gpt-4o",
            agents=agents,
            workflows={"research_and_write": workflow},
        )
        ```
    """

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
        """Initialize the WorkflowRoutingMiddleware."""
        super().__init__()
        self.system_prompt = system_prompt

        # Create agent instances
        default_subagent_middleware = default_middleware or []
        compiled_agents: dict[str, Runnable] = {}

        for agent_name, agent_spec in agents.items():
            agent_model = agent_spec.get("model", default_model)
            agent_tools = agent_spec.get("tools", default_tools or [])

            agent_middleware = [*default_subagent_middleware]
            if "middleware" in agent_spec:
                agent_middleware.extend(agent_spec["middleware"])

            interrupt_on = agent_spec.get("interrupt_on", default_interrupt_on)
            if interrupt_on:
                agent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

            compiled_agents[agent_name] = create_agent(
                agent_model,
                system_prompt=agent_spec["system_prompt"],
                tools=agent_tools,
                middleware=agent_middleware,
            )

        # Create workflow tool
        workflow_tool = _create_workflow_tool(
            workflows=workflows,
            agents=compiled_agents,
            workflow_description=workflow_description,
        )
        self.tools = [workflow_tool]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Update the system prompt to include instructions on using workflows."""
        if self.system_prompt is not None:
            request.system_prompt = request.system_prompt + "\n\n" + self.system_prompt if request.system_prompt else self.system_prompt
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Update the system prompt to include instructions on using workflows."""
        if self.system_prompt is not None:
            request.system_prompt = request.system_prompt + "\n\n" + self.system_prompt if request.system_prompt else self.system_prompt
        return await handler(request)
