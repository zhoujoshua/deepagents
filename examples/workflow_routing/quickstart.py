"""Quick start example for WorkflowRoutingMiddleware.

This is the simplest possible workflow example to get you started.
"""

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from deepagents.middleware.workflow_routing import (
    NodeType,
    WorkflowAgent,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRoutingMiddleware,
)


def main():
    """Run a simple sequential workflow."""

    # Step 1: Define agents
    agents = {
        "greeter": WorkflowAgent(
            name="greeter",
            description="Greets the user",
            system_prompt="You are a friendly greeter. Say hello warmly.",
            tools=[],
        ),
        "helper": WorkflowAgent(
            name="helper",
            description="Offers help",
            system_prompt="You are a helpful assistant. Offer to assist the user.",
            tools=[],
        ),
    }

    # Step 2: Define workflow
    workflow = WorkflowDefinition(
        start_node="greet",
        nodes=[
            WorkflowNode(
                id="greet",
                type=NodeType.AGENT,
                agent="greeter",
                next_node="help",
            ),
            WorkflowNode(
                id="help",
                type=NodeType.AGENT,
                agent="helper",
            ),
        ],
    )

    # Step 3: Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model="openai:gpt-4o-mini",
        agents=agents,
        workflows={"welcome": workflow},
    )

    # Step 4: Create main agent with middleware
    agent = create_agent(
        "openai:gpt-4o-mini",
        system_prompt="You coordinate workflows. Use execute_workflow with workflow_id='welcome'.",
        tools=[],
        middleware=[middleware],
    )

    # Step 5: Execute
    print("Running simple workflow...\n")

    result = agent.invoke({
        "messages": [HumanMessage(content="Hello!")],
    })

    # Display results
    print("Workflow Results:")
    print("=" * 80)
    for step in result.get("workflow_results", []):
        print(f"\n[{step['agent']}]")
        print(step['result'])


if __name__ == "__main__":
    main()
