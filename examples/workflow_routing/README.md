# Workflow Routing Examples

This directory contains examples demonstrating the `WorkflowRoutingMiddleware` for complex multi-agent orchestration.

## Examples

### 1. **Customer Support Workflow** (`customer_support.py`)
Demonstrates conditional routing based on request priority and type.

- Classifies customer requests
- Routes to appropriate handlers (urgent/normal, technical/billing)
- Uses decision tree logic

### 2. **Content Creation Pipeline** (`content_pipeline.py`)
Shows sequential workflow with multiple specialized agents.

- Research → Outline → Draft → Review → Finalize
- Each agent builds on the previous agent's work
- State is accumulated through the pipeline

### 3. **Parallel Research Workflow** (`parallel_research.py`)
Illustrates parallel agent execution for independent tasks.

- Multiple research agents work concurrently
- Results are synthesized after all complete
- Maximizes throughput for independent subtasks

### 4. **Complex Decision Workflow** (`complex_decision.py`)
Demonstrates mixed node types (sequential, parallel, conditional).

- Data preprocessing
- Parallel analysis from multiple perspectives
- Conditional routing based on analysis results
- Final synthesis and recommendation

## Running the Examples

Each example can be run independently:

```bash
cd examples/workflow_routing
python customer_support.py
python content_pipeline.py
python parallel_research.py
python complex_decision.py
```

## Key Concepts

### Node Types

- **AGENT**: Execute a single agent
- **CONDITION**: Branch based on state conditions
- **SEQUENTIAL**: Execute children in order
- **PARALLEL**: Execute children concurrently

### Condition Operators

- Comparison: `eq`, `ne`, `gt`, `lt`, `gte`, `lte`
- Containment: `contains`, `not_contains`, `in`, `not_in`
- Existence: `exists`, `not_exists`
- Pattern: `matches` (regex)

### State Management

- Agents share state (except messages and todos)
- Each agent gets isolated message history
- Results accumulate in `workflow_results`
