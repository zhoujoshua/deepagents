"""Customer support workflow with conditional routing.

This example demonstrates how to use WorkflowRoutingMiddleware to build
a customer support system that routes requests based on priority and type.

Workflow:
1. Classify the request (priority: urgent/normal, type: technical/billing)
2. Route to appropriate handler based on classification
3. Generate response
"""

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from deepagents.middleware.workflow_routing import (
    ConditionOperator,
    ConditionalBranch,
    NodeType,
    WorkflowAgent,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRoutingMiddleware,
)


def create_customer_support_workflow():
    """Create a customer support workflow with conditional routing."""

    # Define specialized agents
    agents = {
        "classifier": WorkflowAgent(
            name="classifier",
            description="Classifies customer requests",
            system_prompt="""You are a customer request classifier.
Analyze the customer request and determine:
1. Priority: "urgent" or "normal"
2. Type: "technical" or "billing"

Set these fields in your response:
- priority: urgent/normal
- request_type: technical/billing

Example classifications:
- "My service is down" → urgent, technical
- "I have a question about my bill" → normal, billing
- "I can't access my account" → urgent, technical
- "What payment methods do you accept?" → normal, billing
""",
            tools=[],
        ),
        "urgent_technical": WorkflowAgent(
            name="urgent_technical",
            description="Handles urgent technical issues",
            system_prompt="""You are a senior technical support specialist handling urgent issues.
Provide immediate, actionable solutions. Escalate to engineering if needed.
Be concise and prioritize quick resolution.""",
            tools=[],
        ),
        "normal_technical": WorkflowAgent(
            name="normal_technical",
            description="Handles normal technical questions",
            system_prompt="""You are a technical support specialist.
Provide detailed explanations and troubleshooting steps.
Be thorough and educational in your responses.""",
            tools=[],
        ),
        "urgent_billing": WorkflowAgent(
            name="urgent_billing",
            description="Handles urgent billing issues",
            system_prompt="""You are a billing specialist handling urgent matters.
Address payment issues, service interruptions, and billing disputes immediately.
Offer immediate solutions and escalation paths.""",
            tools=[],
        ),
        "normal_billing": WorkflowAgent(
            name="normal_billing",
            description="Handles normal billing questions",
            system_prompt="""You are a billing support specialist.
Answer questions about invoices, payment methods, and billing cycles.
Provide clear explanations and helpful resources.""",
            tools=[],
        ),
    }

    # Define workflow with conditional routing
    workflow = WorkflowDefinition(
        start_node="classify",
        nodes=[
            # Step 1: Classify the request
            WorkflowNode(
                id="classify",
                type=NodeType.AGENT,
                agent="classifier",
                next_node="route_by_priority",
            ),
            # Step 2: Route by priority
            WorkflowNode(
                id="route_by_priority",
                type=NodeType.CONDITION,
                branches=[
                    ConditionalBranch(
                        conditions=[
                            {"field": "priority", "operator": ConditionOperator.EQUALS, "value": "urgent"}
                        ],
                        next_node="route_urgent",
                    ),
                ],
                default_branch="route_normal",
            ),
            # Route urgent requests by type
            WorkflowNode(
                id="route_urgent",
                type=NodeType.CONDITION,
                branches=[
                    ConditionalBranch(
                        conditions=[
                            {"field": "request_type", "operator": ConditionOperator.EQUALS, "value": "technical"}
                        ],
                        next_node="handle_urgent_technical",
                    ),
                    ConditionalBranch(
                        conditions=[
                            {"field": "request_type", "operator": ConditionOperator.EQUALS, "value": "billing"}
                        ],
                        next_node="handle_urgent_billing",
                    ),
                ],
                default_branch="handle_urgent_technical",
            ),
            # Route normal requests by type
            WorkflowNode(
                id="route_normal",
                type=NodeType.CONDITION,
                branches=[
                    ConditionalBranch(
                        conditions=[
                            {"field": "request_type", "operator": ConditionOperator.EQUALS, "value": "technical"}
                        ],
                        next_node="handle_normal_technical",
                    ),
                    ConditionalBranch(
                        conditions=[
                            {"field": "request_type", "operator": ConditionOperator.EQUALS, "value": "billing"}
                        ],
                        next_node="handle_normal_billing",
                    ),
                ],
                default_branch="handle_normal_technical",
            ),
            # Handler nodes
            WorkflowNode(
                id="handle_urgent_technical",
                type=NodeType.AGENT,
                agent="urgent_technical",
            ),
            WorkflowNode(
                id="handle_normal_technical",
                type=NodeType.AGENT,
                agent="normal_technical",
            ),
            WorkflowNode(
                id="handle_urgent_billing",
                type=NodeType.AGENT,
                agent="urgent_billing",
            ),
            WorkflowNode(
                id="handle_normal_billing",
                type=NodeType.AGENT,
                agent="normal_billing",
            ),
        ],
    )

    return agents, workflow


def main():
    """Run the customer support workflow example."""
    agents, workflow = create_customer_support_workflow()

    # Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model="openai:gpt-4o-mini",
        agents=agents,
        workflows={"customer_support": workflow},
    )

    # Create main agent
    support_agent = create_agent(
        "openai:gpt-4o-mini",
        system_prompt="""You are a customer support coordinator.
When a customer contacts support, use the execute_workflow tool to process their request.
The workflow will automatically classify and route to the appropriate specialist.""",
        tools=[],
        middleware=[middleware],
    )

    # Example requests
    test_requests = [
        "My service has been down for 2 hours! I need help immediately!",
        "I have a question about the charge on my last invoice.",
        "I can't log into my account and I have an important meeting in 10 minutes!",
        "What payment methods do you accept for monthly subscriptions?",
    ]

    for i, request in enumerate(test_requests, 1):
        print(f"\n{'=' * 80}")
        print(f"Request {i}: {request}")
        print('=' * 80)

        result = support_agent.invoke({
            "messages": [HumanMessage(content=request)],
        })

        # Display results
        if "workflow_results" in result:
            print("\nWorkflow Execution:")
            for step in result["workflow_results"]:
                print(f"\n  [{step['agent']}]")
                print(f"  {step['result'][:200]}...")

        # Display final response
        if result["messages"]:
            final_msg = result["messages"][-1]
            print(f"\n\nFinal Response:\n{final_msg.content}")


if __name__ == "__main__":
    main()
