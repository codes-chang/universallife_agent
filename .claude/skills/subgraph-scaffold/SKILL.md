---
name: subgraph-scaffold
description: Creates a complete new subgraph directory under app/subgraphs/. Use when adding a new domain, creating a new subgraph, adding routing for a new intent, or extending the agent with a new domain. Triggers on "add a new subgraph", "create a new domain", "add X capability", "support X intent".
---

# Subgraph Scaffold

Creates a complete new subgraph with all files and wiring into the main graph.

## Before You Begin

Read these files:
1. `app/subgraphs/base.py` - BaseSubgraph class
2. `app/subgraphs/trip/` - Complete subgraph reference
3. `app/subgraphs/outfit/graph.py` - generate_candidate_memories pattern
4. `app/core/state.py` - State TypedDicts
5. `app/graph/main_graph.py` - Subgraph routing
6. `app/graph/router.py` - SUPPORTED_INTENTS
7. `app/graph/reviewer.py` - HARD_RULES

## Step 1: Gather Requirements

Ask for:
1. **Domain name** - Single lowercase word (e.g., `health`, `food`)
2. **Description** - What it handles (1-2 sentences in Chinese)
3. **Query types** - Supported query types

## Step 2: Generate 6 Files in `app/subgraphs/{domain}/`

### `__init__.py` - Empty file

### `state.py` - TypedDict state extending BaseSubgraphState

```python
from typing import TypedDict, Optional
from ..base import BaseSubgraphState

class {Pascal}SubgraphState(TypedDict):
    task_input: str
    domain: str
    plan: Optional[str]
    tool_calls: list
    intermediate_result: Optional[str]
    final_result: Optional[str]
    critique: Optional[str]
    iteration_count: int
    max_iterations: int
    # domain-specific fields
    {field}: Optional[{type}]
```

### `prompts.py` - Domain prompt templates

### `tools.py` - Domain tool functions using httpx.AsyncClient

### `nodes.py` - Three async functions: build_plan_node, execute_tools_node, synthesize_result_node

### `graph.py` - Subgraph class extending BaseSubgraph + singleton

```python
class {Pascal}Subgraph(BaseSubgraph):
    def __init__(self):
        super().__init__("{domain}")

    async def execute_domain_tools(self, state) -> str:
        ...

_{domain}_subgraph = None

def get_{domain}_subgraph() -> {Pascal}Subgraph:
    global _{domain}_subgraph
    if _{domain}_subgraph is None:
        _{domain}_subgraph = {Pascal}Subgraph()
    return _{domain}_subgraph
```

## Step 3: Update 4 Existing Files

1. **`app/core/state.py`** - Add state class + update RouterResult Literal
2. **`app/graph/main_graph.py`** - Add import + elif branch in execute_subgraph
3. **`app/graph/router.py`** - Add to SUPPORTED_INTENTS
4. **`app/graph/reviewer.py`** - Add domain HARD_RULES

## Step 4: Verify

- All 6 files exist
- Domain string consistent across routing/reviewer/state
- SUPPORTED_INTENTS and RouterResult Literal include new domain
- Singleton getter imported in main_graph.py
