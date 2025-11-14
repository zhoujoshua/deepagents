"""Content creation pipeline with sequential workflow.

This example demonstrates a sequential workflow where each agent builds
on the output of the previous agent to create polished content.

Workflow:
1. Research → Gather information on the topic
2. Outline → Create structured outline from research
3. Draft → Write first draft based on outline
4. Review → Critique and suggest improvements
5. Finalize → Produce final polished version
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


def create_content_pipeline():
    """Create a content creation pipeline with sequential agents."""

    agents = {
        "researcher": WorkflowAgent(
            name="researcher",
            description="Researches topics and gathers information",
            system_prompt="""You are a research specialist.
Your job is to gather key information about the topic, including:
- Core concepts and definitions
- Important facts and statistics
- Different perspectives and viewpoints
- Relevant examples and case studies

Provide a concise research summary that will be used by other agents.""",
            tools=[],
        ),
        "outliner": WorkflowAgent(
            name="outliner",
            description="Creates structured outlines",
            system_prompt="""You are an outline specialist.
Based on the research provided, create a clear, logical outline with:
- Main sections and subsections
- Key points to cover in each section
- Logical flow from introduction to conclusion
- Estimated length for each section

Format your outline clearly with hierarchy.""",
            tools=[],
        ),
        "writer": WorkflowAgent(
            name="writer",
            description="Writes content drafts",
            system_prompt="""You are a skilled writer.
Using the outline and research provided, write a complete first draft that:
- Follows the outline structure
- Incorporates research findings naturally
- Uses clear, engaging language
- Maintains consistent tone and style
- Includes transitions between sections

This is a first draft - focus on getting ideas down.""",
            tools=[],
        ),
        "reviewer": WorkflowAgent(
            name="reviewer",
            description="Reviews and critiques content",
            system_prompt="""You are an editor and content reviewer.
Review the draft and provide constructive feedback on:
- Clarity and coherence
- Argument strength and logic
- Evidence and examples
- Language and style
- Structure and flow
- Areas needing expansion or cutting

Be specific and actionable in your suggestions.""",
            tools=[],
        ),
        "finalizer": WorkflowAgent(
            name="finalizer",
            description="Produces final polished version",
            system_prompt="""You are a senior editor.
Taking into account the draft and review feedback, produce the final version that:
- Addresses all review feedback
- Polishes language and style
- Ensures perfect grammar and punctuation
- Optimizes structure and flow
- Adds a compelling title

This is the publication-ready version.""",
            tools=[],
        ),
    }

    # Define sequential workflow
    workflow = WorkflowDefinition(
        start_node="research",
        nodes=[
            WorkflowNode(
                id="research",
                type=NodeType.AGENT,
                agent="researcher",
                next_node="outline",
            ),
            WorkflowNode(
                id="outline",
                type=NodeType.AGENT,
                agent="outliner",
                next_node="draft",
            ),
            WorkflowNode(
                id="draft",
                type=NodeType.AGENT,
                agent="writer",
                next_node="review",
            ),
            WorkflowNode(
                id="review",
                type=NodeType.AGENT,
                agent="reviewer",
                next_node="finalize",
            ),
            WorkflowNode(
                id="finalize",
                type=NodeType.AGENT,
                agent="finalizer",
            ),
        ],
    )

    return agents, workflow


def main():
    """Run the content pipeline example."""
    agents, workflow = create_content_pipeline()

    # Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model="openai:gpt-4o-mini",
        agents=agents,
        workflows={"content_pipeline": workflow},
    )

    # Create main agent
    content_agent = create_agent(
        "openai:gpt-4o-mini",
        system_prompt="""You are a content production coordinator.
When given a content request, use the execute_workflow tool with workflow_id='content_pipeline'
to create high-quality content through our multi-stage pipeline.""",
        tools=[],
        middleware=[middleware],
    )

    # Example content request
    topic = "The Impact of AI on Software Development"

    print(f"Creating content on: {topic}\n")
    print("=" * 80)

    result = content_agent.invoke({
        "messages": [HumanMessage(content=f"Create an article about: {topic}")],
    })

    # Display workflow execution
    if "workflow_results" in result:
        print("\n📝 Content Creation Pipeline\n")

        stage_names = {
            "researcher": "🔍 Research",
            "outliner": "📋 Outline",
            "writer": "✍️  Draft",
            "reviewer": "👁️  Review",
            "finalizer": "✨ Final",
        }

        for i, step in enumerate(result["workflow_results"], 1):
            stage_name = stage_names.get(step["agent"], step["agent"])
            print(f"\n{'-' * 80}")
            print(f"Stage {i}: {stage_name}")
            print('-' * 80)

            content = step["result"]
            # Display preview (first 500 chars)
            preview = content[:500] + "..." if len(content) > 500 else content
            print(preview)

        # Display final result in full
        final_result = result["workflow_results"][-1]["result"]
        print(f"\n\n{'=' * 80}")
        print("📄 FINAL ARTICLE")
        print('=' * 80)
        print(final_result)


if __name__ == "__main__":
    main()
