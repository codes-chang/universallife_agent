---
name: memory-enabled-subgraph
description: Adds candidate memory generation to an existing subgraph. Use when adding memory capabilities, enabling preference learning, extracting user preferences from a domain, or making a subgraph memory-aware. Triggers on "add memory to subgraph", "enable memory for X", "extract preferences", "make X remember preferences".
---

# Memory-Enabled Subgraph

Adds `generate_candidate_memories()` override to an existing subgraph.

## Before You Begin

Read these files:
1. `app/subgraphs/outfit/graph.py` - Canonical reference
2. `app/subgraphs/trip/graph.py` - Another complete example
3. `app/memory/models.py` - MemoryCandidate, MemoryType, MemoryScope

## Step 1: Gather Requirements

Ask for:
1. **Domain name** - Existing subgraph to add memory to
2. **Preference fields** - Category-to-keyword mapping. Example for food:
   - Diet type: vegan, vegetarian, keto, low-carb
   - Cuisine: Chinese, Japanese, Italian
   - Spice level: mild, medium, spicy

## Step 2: Generate the Method

Add to the subgraph class in `app/subgraphs/{domain}/graph.py`:

```python
from ...memory.models import MemoryCandidate, MemoryType, MemoryScope

async def generate_candidate_memories(self, state) -> dict:
    candidates = []
    task_input = state.get("task_input", "")

    preference_keywords = {
        "{category}": [{keywords}],
    }

    for pref_type, keywords in preference_keywords.items():
        for keyword in keywords:
            if keyword in task_input:
                candidate = MemoryCandidate(
                    content=f"用户{domain}偏好: {pref_type}: {keyword}",
                    memory_type=MemoryType.USER_PREFERENCE,
                    scope=MemoryScope.DOMAIN,
                    domain="{domain}",
                    importance=0.7,
                    confidence=0.75,
                    source="subgraph:{domain}",
                    metadata={"preference_type": "{domain}_style", "original_query": task_input}
                )
                candidates.append(candidate.model_dump())

    final_result = state.get("final_result", "")
    if final_result and "失败" not in final_result:
        experience = MemoryCandidate(
            content=f"成功完成{domain}任务: {task_input[:50]}...",
            memory_type=MemoryType.TASK_EPISODE,
            scope=MemoryScope.DOMAIN,
            domain="{domain}",
            importance=0.5,
            confidence=0.6,
            source="subgraph:{domain}",
            metadata={"task_type": "{domain}_task"}
        )
        candidates.append(experience.model_dump())

    state["candidate_memories"] = candidates
    if candidates:
        logger.info(f"[{Pascal}Subgraph] 生成 {len(candidates)} 个候选记忆")
    return state
```

Key conventions:
- `MemoryType.USER_PREFERENCE` for preferences, `MemoryType.TASK_EPISODE` for success records
- `MemoryScope.DOMAIN` for all subgraph memories
- importance: 0.7 preferences, 0.5 episodes
- Call `.model_dump()` before appending
- Only create TASK_EPISODE if result exists and doesn't contain "失败"

## Step 3: Verify

- Imports correct at top of file
- Domain string matches subgraph name
- Method is async on the class
