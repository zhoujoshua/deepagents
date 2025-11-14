"""Integration tests for WorkflowRoutingMiddleware."""

import pytest
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from deepagents.middleware.workflow_routing import (
    ConditionOperator,
    ConditionRule,
    ConditionalBranch,
    NodeType,
    WorkflowAgent,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRoutingMiddleware,
    _evaluate_condition,
    _evaluate_branch,
)


def test_evaluate_condition_equals():
    """Test equality condition evaluation."""
    state = {"status": "approved", "count": 5}

    rule: ConditionRule = {
        "field": "status",
        "operator": ConditionOperator.EQUALS,
        "value": "approved",
    }
    assert _evaluate_condition(rule, state) is True

    rule["value"] = "rejected"
    assert _evaluate_condition(rule, state) is False


def test_evaluate_condition_comparison():
    """Test comparison operators."""
    state = {"count": 10, "score": 85.5}

    # Greater than
    rule: ConditionRule = {
        "field": "count",
        "operator": ConditionOperator.GREATER_THAN,
        "value": 5,
    }
    assert _evaluate_condition(rule, state) is True

    # Less than
    rule = {
        "field": "count",
        "operator": ConditionOperator.LESS_THAN,
        "value": 20,
    }
    assert _evaluate_condition(rule, state) is True

    # Greater equal
    rule = {
        "field": "count",
        "operator": ConditionOperator.GREATER_EQUAL,
        "value": 10,
    }
    assert _evaluate_condition(rule, state) is True


def test_evaluate_condition_contains():
    """Test contains operators."""
    state = {"tags": ["python", "ai", "ml"], "description": "A machine learning project"}

    rule: ConditionRule = {
        "field": "tags",
        "operator": ConditionOperator.CONTAINS,
        "value": "ai",
    }
    assert _evaluate_condition(rule, state) is True

    rule = {
        "field": "description",
        "operator": ConditionOperator.CONTAINS,
        "value": "machine",
    }
    assert _evaluate_condition(rule, state) is True


def test_evaluate_condition_exists():
    """Test exists operators."""
    state = {"name": "test", "value": None}

    rule: ConditionRule = {
        "field": "name",
        "operator": ConditionOperator.EXISTS,
    }
    assert _evaluate_condition(rule, state) is True

    rule = {
        "field": "missing",
        "operator": ConditionOperator.EXISTS,
    }
    assert _evaluate_condition(rule, state) is False

    rule = {
        "field": "missing",
        "operator": ConditionOperator.NOT_EXISTS,
    }
    assert _evaluate_condition(rule, state) is True


def test_evaluate_condition_nested_field():
    """Test nested field access."""
    state = {"user": {"name": "Alice", "role": "admin"}}

    rule: ConditionRule = {
        "field": "user.role",
        "operator": ConditionOperator.EQUALS,
        "value": "admin",
    }
    assert _evaluate_condition(rule, state) is True


def test_evaluate_branch_and_logic():
    """Test branch evaluation with AND logic."""
    state = {"status": "approved", "count": 10}

    branch: ConditionalBranch = {
        "conditions": [
            {"field": "status", "operator": ConditionOperator.EQUALS, "value": "approved"},
            {"field": "count", "operator": ConditionOperator.GREATER_THAN, "value": 5},
        ],
        "logic": "AND",
        "next_node": "process",
    }
    assert _evaluate_branch(branch, state) is True

    # One condition fails
    state["count"] = 3
    assert _evaluate_branch(branch, state) is False


def test_evaluate_branch_or_logic():
    """Test branch evaluation with OR logic."""
    state = {"status": "pending", "count": 3}

    branch: ConditionalBranch = {
        "conditions": [
            {"field": "status", "operator": ConditionOperator.EQUALS, "value": "approved"},
            {"field": "count", "operator": ConditionOperator.GREATER_THAN, "value": 5},
        ],
        "logic": "OR",
        "next_node": "process",
    }
    # Neither condition is true
    assert _evaluate_branch(branch, state) is False

    # One condition becomes true
    state["status"] = "approved"
    assert _evaluate_branch(branch, state) is True


@pytest.mark.vcr()
def test_sequential_workflow(model_name: str):
    """Test sequential workflow execution."""
    # Define two simple agents
    agents = {
        "agent1": WorkflowAgent(
            name="agent1",
            description="First agent",
            system_prompt="You are agent 1. Respond with 'Agent 1 completed'.",
            tools=[],
        ),
        "agent2": WorkflowAgent(
            name="agent2",
            description="Second agent",
            system_prompt="You are agent 2. Respond with 'Agent 2 completed'.",
            tools=[],
        ),
    }

    # Define sequential workflow
    workflow = WorkflowDefinition(
        start_node="step1",
        nodes=[
            WorkflowNode(
                id="step1",
                type=NodeType.AGENT,
                agent="agent1",
                next_node="step2",
            ),
            WorkflowNode(
                id="step2",
                type=NodeType.AGENT,
                agent="agent2",
            ),
        ],
    )

    # Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model=model_name,
        agents=agents,
        workflows={"sequential": workflow},
    )

    # Create main agent with workflow middleware
    main_agent = create_agent(
        model_name,
        system_prompt="You are a workflow coordinator.",
        tools=[],
        middleware=[middleware],
    )

    # Execute workflow
    result = main_agent.invoke({
        "messages": [HumanMessage(content="Execute the sequential workflow")],
    })

    # Verify both agents executed
    assert "workflow_results" in result
    assert len(result["workflow_results"]) == 2
    assert result["workflow_results"][0]["agent"] == "agent1"
    assert result["workflow_results"][1]["agent"] == "agent2"


@pytest.mark.vcr()
def test_conditional_workflow(model_name: str):
    """Test conditional workflow routing."""
    agents = {
        "classifier": WorkflowAgent(
            name="classifier",
            description="Classifies input",
            system_prompt="Classify the input and set status field to 'urgent' or 'normal'.",
            tools=[],
        ),
        "urgent_handler": WorkflowAgent(
            name="urgent_handler",
            description="Handles urgent requests",
            system_prompt="You handle urgent requests. Respond with 'Urgent handled'.",
            tools=[],
        ),
        "normal_handler": WorkflowAgent(
            name="normal_handler",
            description="Handles normal requests",
            system_prompt="You handle normal requests. Respond with 'Normal handled'.",
            tools=[],
        ),
    }

    workflow = WorkflowDefinition(
        start_node="classify",
        nodes=[
            WorkflowNode(
                id="classify",
                type=NodeType.AGENT,
                agent="classifier",
                next_node="route",
            ),
            WorkflowNode(
                id="route",
                type=NodeType.CONDITION,
                branches=[
                    ConditionalBranch(
                        conditions=[
                            {"field": "status", "operator": ConditionOperator.EQUALS, "value": "urgent"}
                        ],
                        next_node="urgent",
                    ),
                ],
                default_branch="normal",
            ),
            WorkflowNode(
                id="urgent",
                type=NodeType.AGENT,
                agent="urgent_handler",
            ),
            WorkflowNode(
                id="normal",
                type=NodeType.AGENT,
                agent="normal_handler",
            ),
        ],
    )

    middleware = WorkflowRoutingMiddleware(
        default_model=model_name,
        agents=agents,
        workflows={"conditional": workflow},
    )

    main_agent = create_agent(
        model_name,
        system_prompt="You are a workflow coordinator.",
        tools=[],
        middleware=[middleware],
    )

    # Test with urgent status
    result = main_agent.invoke({
        "messages": [HumanMessage(content="This is urgent!")],
        "status": "urgent",
    })

    workflow_results = result.get("workflow_results", [])
    # Should have classifier and urgent_handler
    agent_names = [r["agent"] for r in workflow_results]
    assert "classifier" in agent_names
    # Due to conditional routing, either urgent or normal handler executed
    assert "urgent_handler" in agent_names or "normal_handler" in agent_names


@pytest.mark.vcr()
def test_parallel_workflow(model_name: str):
    """Test parallel workflow execution."""
    agents = {
        "agent1": WorkflowAgent(
            name="agent1",
            description="Agent 1",
            system_prompt="You are agent 1. Respond quickly.",
            tools=[],
        ),
        "agent2": WorkflowAgent(
            name="agent2",
            description="Agent 2",
            system_prompt="You are agent 2. Respond quickly.",
            tools=[],
        ),
        "agent3": WorkflowAgent(
            name="agent3",
            description="Agent 3",
            system_prompt="You are agent 3. Respond quickly.",
            tools=[],
        ),
    }

    workflow = WorkflowDefinition(
        start_node="parallel_step",
        nodes=[
            WorkflowNode(
                id="parallel_step",
                type=NodeType.PARALLEL,
                children=["task1", "task2", "task3"],
            ),
            WorkflowNode(
                id="task1",
                type=NodeType.AGENT,
                agent="agent1",
            ),
            WorkflowNode(
                id="task2",
                type=NodeType.AGENT,
                agent="agent2",
            ),
            WorkflowNode(
                id="task3",
                type=NodeType.AGENT,
                agent="agent3",
            ),
        ],
    )

    middleware = WorkflowRoutingMiddleware(
        default_model=model_name,
        agents=agents,
        workflows={"parallel": workflow},
    )

    main_agent = create_agent(
        model_name,
        system_prompt="You are a workflow coordinator.",
        tools=[],
        middleware=[middleware],
    )

    result = main_agent.invoke({
        "messages": [HumanMessage(content="Execute parallel tasks")],
    })

    # All three agents should have executed
    workflow_results = result.get("workflow_results", [])
    assert len(workflow_results) == 3
    agent_names = {r["agent"] for r in workflow_results}
    assert agent_names == {"agent1", "agent2", "agent3"}


@pytest.mark.vcr()
def test_complex_workflow(model_name: str):
    """Test complex workflow with mixed node types."""
    agents = {
        "preprocessor": WorkflowAgent(
            name="preprocessor",
            description="Preprocesses input",
            system_prompt="Preprocess the input data.",
            tools=[],
        ),
        "analyzer1": WorkflowAgent(
            name="analyzer1",
            description="Analyzer 1",
            system_prompt="Analyze data from perspective 1.",
            tools=[],
        ),
        "analyzer2": WorkflowAgent(
            name="analyzer2",
            description="Analyzer 2",
            system_prompt="Analyze data from perspective 2.",
            tools=[],
        ),
        "synthesizer": WorkflowAgent(
            name="synthesizer",
            description="Synthesizes results",
            system_prompt="Synthesize analysis results.",
            tools=[],
        ),
    }

    workflow = WorkflowDefinition(
        start_node="preprocess",
        nodes=[
            # Step 1: Preprocess
            WorkflowNode(
                id="preprocess",
                type=NodeType.AGENT,
                agent="preprocessor",
                next_node="analyze_parallel",
            ),
            # Step 2: Parallel analysis
            WorkflowNode(
                id="analyze_parallel",
                type=NodeType.PARALLEL,
                children=["analyze1", "analyze2"],
                next_node="synthesize",
            ),
            WorkflowNode(
                id="analyze1",
                type=NodeType.AGENT,
                agent="analyzer1",
            ),
            WorkflowNode(
                id="analyze2",
                type=NodeType.AGENT,
                agent="analyzer2",
            ),
            # Step 3: Synthesize
            WorkflowNode(
                id="synthesize",
                type=NodeType.AGENT,
                agent="synthesizer",
            ),
        ],
    )

    middleware = WorkflowRoutingMiddleware(
        default_model=model_name,
        agents=agents,
        workflows={"complex": workflow},
    )

    main_agent = create_agent(
        model_name,
        system_prompt="You are a workflow coordinator.",
        tools=[],
        middleware=[middleware],
    )

    result = main_agent.invoke({
        "messages": [HumanMessage(content="Process this data")],
    })

    workflow_results = result.get("workflow_results", [])
    # Should have preprocessor, both analyzers, and synthesizer
    agent_names = [r["agent"] for r in workflow_results]
    assert "preprocessor" in agent_names
    assert "analyzer1" in agent_names
    assert "analyzer2" in agent_names
    assert "synthesizer" in agent_names
