"""Complex decision workflow with mixed node types.

This example demonstrates a sophisticated workflow that combines:
- Sequential execution for preprocessing
- Parallel execution for multi-perspective analysis
- Conditional routing based on analysis results
- Final synthesis and recommendations

Use Case: Investment Decision Analysis
1. Preprocess → Clean and structure the investment data
2. Parallel Analysis:
   - Financial Analysis
   - Technical Analysis
   - Sentiment Analysis
3. Risk Assessment → Based on analysis, determine risk level
4. Conditional Routing:
   - High Risk → Conservative recommendations
   - Medium Risk → Balanced recommendations
   - Low Risk → Aggressive recommendations
5. Final Report → Comprehensive investment recommendation
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


def create_investment_analysis_workflow():
    """Create a complex investment analysis workflow."""

    agents = {
        "preprocessor": WorkflowAgent(
            name="preprocessor",
            description="Preprocesses investment data",
            system_prompt="""You are a data preprocessing specialist.
Clean and structure the investment opportunity data:
- Extract key metrics (revenue, growth rate, valuation, etc.)
- Identify the industry and sector
- Note any data quality issues
- Standardize format for analysis

Provide structured, clean data for analysts.""",
            tools=[],
        ),
        "financial_analyst": WorkflowAgent(
            name="financial_analyst",
            description="Performs financial analysis",
            system_prompt="""You are a financial analyst.
Analyze financial aspects:
- Revenue and profit trends
- Valuation metrics (P/E, P/S, etc.)
- Cash flow and burn rate
- Financial health indicators
- Growth projections

Rate financial attractiveness: high/medium/low""",
            tools=[],
        ),
        "technical_analyst": WorkflowAgent(
            name="technical_analyst",
            description="Performs technical analysis",
            system_prompt="""You are a technical analyst.
Analyze technical aspects:
- Product/technology quality and innovation
- Technical moat and defensibility
- Scalability potential
- Technical team and execution capability
- Technology trends alignment

Rate technical strength: high/medium/low""",
            tools=[],
        ),
        "sentiment_analyst": WorkflowAgent(
            name="sentiment_analyst",
            description="Performs sentiment analysis",
            system_prompt="""You are a market sentiment analyst.
Analyze market sentiment:
- Media coverage and public perception
- Customer satisfaction and reviews
- Social media sentiment
- Industry expert opinions
- Competitive positioning

Rate market sentiment: positive/neutral/negative""",
            tools=[],
        ),
        "risk_assessor": WorkflowAgent(
            name="risk_assessor",
            description="Assesses overall risk",
            system_prompt="""You are a risk assessment specialist.
Based on financial, technical, and sentiment analysis, assess overall risk.

Consider:
- Consistency across analyses
- Red flags in any area
- Market conditions
- Uncertainty factors

Set risk_level field to: high/medium/low
Provide detailed risk assessment.""",
            tools=[],
        ),
        "conservative_advisor": WorkflowAgent(
            name="conservative_advisor",
            description="Provides conservative recommendations",
            system_prompt="""You are a conservative investment advisor.
For this HIGH RISK opportunity:
- Recommend cautious approach
- Suggest smaller position sizes
- Emphasize risk mitigation
- Propose wait-and-see alternatives
- Set clear exit criteria

Provide conservative investment recommendation.""",
            tools=[],
        ),
        "balanced_advisor": WorkflowAgent(
            name="balanced_advisor",
            description="Provides balanced recommendations",
            system_prompt="""You are a balanced investment advisor.
For this MEDIUM RISK opportunity:
- Recommend measured approach
- Suggest moderate position sizes
- Balance risk and reward
- Propose phased entry strategy
- Set monitoring milestones

Provide balanced investment recommendation.""",
            tools=[],
        ),
        "aggressive_advisor": WorkflowAgent(
            name="aggressive_advisor",
            description="Provides aggressive recommendations",
            system_prompt="""You are an aggressive growth advisor.
For this LOW RISK opportunity:
- Recommend confident approach
- Suggest larger position sizes
- Emphasize upside potential
- Propose accelerated timeline
- Set ambitious targets

Provide aggressive investment recommendation.""",
            tools=[],
        ),
        "report_generator": WorkflowAgent(
            name="report_generator",
            description="Generates final report",
            system_prompt="""You are an investment report specialist.
Create a comprehensive investment report that includes:
- Executive summary
- Analysis highlights (financial, technical, sentiment)
- Risk assessment
- Investment recommendation
- Action items

Make it professional and actionable.""",
            tools=[],
        ),
    }

    # Define complex workflow
    workflow = WorkflowDefinition(
        start_node="preprocess",
        nodes=[
            # Step 1: Preprocess data
            WorkflowNode(
                id="preprocess",
                type=NodeType.AGENT,
                agent="preprocessor",
                next_node="parallel_analysis",
            ),
            # Step 2: Parallel analysis
            WorkflowNode(
                id="parallel_analysis",
                type=NodeType.PARALLEL,
                children=["financial", "technical", "sentiment"],
                next_node="risk_assessment",
            ),
            WorkflowNode(
                id="financial",
                type=NodeType.AGENT,
                agent="financial_analyst",
            ),
            WorkflowNode(
                id="technical",
                type=NodeType.AGENT,
                agent="technical_analyst",
            ),
            WorkflowNode(
                id="sentiment",
                type=NodeType.AGENT,
                agent="sentiment_analyst",
            ),
            # Step 3: Risk assessment
            WorkflowNode(
                id="risk_assessment",
                type=NodeType.AGENT,
                agent="risk_assessor",
                next_node="route_by_risk",
            ),
            # Step 4: Conditional routing by risk level
            WorkflowNode(
                id="route_by_risk",
                type=NodeType.CONDITION,
                branches=[
                    ConditionalBranch(
                        conditions=[
                            {"field": "risk_level", "operator": ConditionOperator.EQUALS, "value": "high"}
                        ],
                        next_node="conservative_recommendation",
                    ),
                    ConditionalBranch(
                        conditions=[
                            {"field": "risk_level", "operator": ConditionOperator.EQUALS, "value": "medium"}
                        ],
                        next_node="balanced_recommendation",
                    ),
                    ConditionalBranch(
                        conditions=[
                            {"field": "risk_level", "operator": ConditionOperator.EQUALS, "value": "low"}
                        ],
                        next_node="aggressive_recommendation",
                    ),
                ],
                default_branch="balanced_recommendation",
            ),
            # Step 5: Risk-appropriate recommendations
            WorkflowNode(
                id="conservative_recommendation",
                type=NodeType.AGENT,
                agent="conservative_advisor",
                next_node="final_report",
            ),
            WorkflowNode(
                id="balanced_recommendation",
                type=NodeType.AGENT,
                agent="balanced_advisor",
                next_node="final_report",
            ),
            WorkflowNode(
                id="aggressive_recommendation",
                type=NodeType.AGENT,
                agent="aggressive_advisor",
                next_node="final_report",
            ),
            # Step 6: Generate final report
            WorkflowNode(
                id="final_report",
                type=NodeType.AGENT,
                agent="report_generator",
            ),
        ],
    )

    return agents, workflow


def main():
    """Run the complex decision workflow example."""
    agents, workflow = create_investment_analysis_workflow()

    # Create middleware
    middleware = WorkflowRoutingMiddleware(
        default_model="openai:gpt-4o-mini",
        agents=agents,
        workflows={"investment_analysis": workflow},
    )

    # Create main agent
    analysis_agent = create_agent(
        "openai:gpt-4o-mini",
        system_prompt="""You are an investment analysis coordinator.
When given an investment opportunity, use the execute_workflow tool with
workflow_id='investment_analysis' to conduct comprehensive analysis.""",
        tools=[],
        middleware=[middleware],
    )

    # Example investment opportunity
    opportunity = """
    Company: AI Startup "DataFlow"
    Industry: Enterprise AI/ML Infrastructure
    Revenue: $5M ARR, growing 200% YoY
    Valuation: $50M (10x revenue)
    Team: 25 employees, strong technical leadership
    Product: ML model deployment and monitoring platform
    Customers: 50+ enterprises including 3 Fortune 500 companies
    Competition: Established players but niche positioning
    """

    print("📊 Investment Analysis Workflow")
    print("=" * 80)
    print(f"\nOpportunity:\n{opportunity}\n")
    print("🔄 Running comprehensive analysis...\n")

    result = analysis_agent.invoke({
        "messages": [HumanMessage(content=f"Analyze this investment opportunity:\n{opportunity}")],
    })

    # Display workflow execution
    if "workflow_results" in result:
        stage_icons = {
            "preprocessor": "🔧",
            "financial_analyst": "💰",
            "technical_analyst": "⚙️",
            "sentiment_analyst": "📈",
            "risk_assessor": "⚖️",
            "conservative_advisor": "🛡️",
            "balanced_advisor": "⚖️",
            "aggressive_advisor": "🚀",
            "report_generator": "📄",
        }

        print("\n" + "=" * 80)
        print("WORKFLOW EXECUTION")
        print("=" * 80)

        # Group results by phase
        preprocessing = []
        analysis = []
        risk = []
        recommendation = []
        report = []

        for step in result["workflow_results"]:
            agent = step["agent"]
            if agent == "preprocessor":
                preprocessing.append(step)
            elif agent in ["financial_analyst", "technical_analyst", "sentiment_analyst"]:
                analysis.append(step)
            elif agent == "risk_assessor":
                risk.append(step)
            elif "advisor" in agent:
                recommendation.append(step)
            elif agent == "report_generator":
                report.append(step)

        # Display each phase
        phases = [
            ("1️⃣ Preprocessing", preprocessing),
            ("2️⃣ Parallel Analysis", analysis),
            ("3️⃣ Risk Assessment", risk),
            ("4️⃣ Recommendation", recommendation),
            ("5️⃣ Final Report", report),
        ]

        for phase_name, steps in phases:
            if steps:
                print(f"\n{phase_name}")
                print("-" * 80)
                for step in steps:
                    icon = stage_icons.get(step["agent"], "•")
                    agent_name = step["agent"].replace("_", " ").title()
                    content = step["result"]
                    preview = content[:300] + "..." if len(content) > 300 else content
                    print(f"\n{icon} {agent_name}")
                    print(preview)

        # Display full final report
        if report:
            print("\n\n" + "=" * 80)
            print("📄 FINAL INVESTMENT REPORT")
            print("=" * 80)
            print(report[0]["result"])


if __name__ == "__main__":
    main()
