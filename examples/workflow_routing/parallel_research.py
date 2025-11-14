"""Parallel research workflow with concurrent agent execution.

This example demonstrates parallel agent execution where multiple research
agents work independently and concurrently, then results are synthesized.

Workflow:
1. Parallel Research:
   - Technical Research (implementation details, architecture)
   - Market Research (competitors, trends, adoption)
   - Risk Research (security, scalability, challenges)
2. Synthesize → Combine all research into comprehensive report
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


def create_parallel_research_workflow():
    """Create a parallel research workflow."""

    agents = {
        "technical_researcher": WorkflowAgent(
            name="technical_researcher",
            description="Researches technical aspects",
            system_prompt="""You are a technical research specialist.
Focus on technical aspects:
- Architecture and implementation details
- Technical specifications and requirements
- Integration and compatibility considerations
- Performance characteristics
- Technical best practices

Provide a technical research report.""",
            tools=[],
        ),
        "market_researcher": WorkflowAgent(
            name="market_researcher",
            description="Researches market aspects",
            system_prompt="""You are a market research specialist.
Focus on market aspects:
- Current market landscape and competitors
- Adoption trends and statistics
- Target audience and use cases
- Pricing models and cost considerations
- Market opportunities and positioning

Provide a market research report.""",
            tools=[],
        ),
        "risk_researcher": WorkflowAgent(
            name="risk_researcher",
            description="Researches risks and challenges",
            system_prompt="""You are a risk assessment specialist.
Focus on risks and challenges:
- Security concerns and vulnerabilities
- Scalability limitations
- Potential failure modes
- Compliance and regulatory issues
- Mitigation strategies

Provide a risk assessment report.""",
            tools=[],
        ),
        "synthesizer": WorkflowAgent(
            name="synthesizer",
            description="Synthesizes research findings",
            system_prompt="""You are a research synthesis specialist.
You will receive research from multiple specialists (technical, market, risk).

Create a comprehensive synthesis that:
- Combines insights from all research areas
- Identifies patterns and connections
- Provides balanced assessment
- Highlights key opportunities and risks
- Makes actionable recommendations

Structure your synthesis clearly with sections for each perspective.""",
            tools=[],
        ),
    }

    # Define parallel workflow
    workflow = WorkflowDefinition(
        start_node="parallel_research",
        nodes=[
            # Parallel research phase
            WorkflowNode(
                id="parallel_research",
                type=NodeType.PARALLEL,
                children=["technical", "market", "risk"],
                next_node="synthesize",
            ),
            WorkflowNode(
                id="technical",
                type=NodeType.AGENT,
                agent="technical_researcher",
            ),
            WorkflowNode(
                id="market",
                type=NodeType.AGENT,
                agent="market_researcher",
            ),
            WorkflowNode(
                id="risk",
                type=NodeType.AGENT,
                agent="risk_researcher",
            ),
            # Synthesis phase
            WorkflowNode(
                id="synthesize",
                type=NodeType.AGENT,
                agent="synthesizer",
            ),
        ],
    )

    return agents, workflow


def main():
    """Run the parallel research example."""
    agents, workflow = create_parallel_research_workflow()

    # Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model="openai:gpt-4o-mini",
        agents=agents,
        workflows={"parallel_research": workflow},
    )

    # Create main agent
    research_agent = create_agent(
        "openai:gpt-4o-mini",
        system_prompt="""You are a research coordinator.
When given a research request, use the execute_workflow tool with workflow_id='parallel_research'
to conduct comprehensive research from multiple perspectives in parallel.""",
        tools=[],
        middleware=[middleware],
    )

    # Example research topic
    topic = "Kubernetes for microservices deployment"

    print(f"Conducting parallel research on: {topic}\n")
    print("=" * 80)
    print("🔄 Running parallel research agents...\n")

    result = research_agent.invoke({
        "messages": [HumanMessage(content=f"Research topic: {topic}")],
    })

    # Display workflow execution
    if "workflow_results" in result:
        research_icons = {
            "technical_researcher": "🔧",
            "market_researcher": "📊",
            "risk_researcher": "⚠️",
            "synthesizer": "🎯",
        }

        research_results = []
        synthesis_result = None

        # Separate research and synthesis
        for step in result["workflow_results"]:
            if step["agent"] == "synthesizer":
                synthesis_result = step["result"]
            else:
                research_results.append(step)

        # Display individual research results
        print("📚 RESEARCH FINDINGS\n")
        for step in research_results:
            icon = research_icons.get(step["agent"], "📄")
            agent_name = step["agent"].replace("_", " ").title()
            print(f"{icon} {agent_name}")
            print("-" * 80)
            content = step["result"]
            preview = content[:400] + "..." if len(content) > 400 else content
            print(preview)
            print()

        # Display synthesis
        if synthesis_result:
            print("\n" + "=" * 80)
            print("🎯 COMPREHENSIVE SYNTHESIS")
            print("=" * 80)
            print(synthesis_result)


if __name__ == "__main__":
    main()
