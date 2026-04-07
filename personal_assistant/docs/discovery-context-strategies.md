---
tags:
  - personal-assistant
  - agent
  - experiment
  - context-strategy
node_type: discovery
is_session: false
layer: application, ontology
nature: exploratory, technical
status: draft
veracidade: medium
convicção: medium
version: 0.2.0
last_updated: 2026-04-07
---

# Discovery: Context Injection Strategies for the Agent

## Problem

The personal assistant uses Gemini Flash to answer questions about the system.
Before calling the LLM, the backend must decide **how much domain context to
inject** into the system prompt.

Too little → the agent hallucinates or gives generic answers.
Too much → token cost grows, signal dilutes, latency increases.

The right injection strategy is unknown. This discovery proposes an experiment
to find it empirically.

---

## The Context Stack

The agent has three potential sources of domain knowledge:

```
┌───────────────────────────────────────────────────────┐
│  1. Semantic Index (static registry JSON)             │
│     Terms, definitions, edges, code anchors           │
│     ~49 terms today — grows as codebase grows         │
└───────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────┐
│  2. EventLog (live database)                          │
│     Full lifecycle history per entity                 │
│     Answers: what happened to contract X?             │
└───────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────┐
│  3. GitNexus (code knowledge graph)                   │
│     Call graphs, symbol definitions, cross-references │
│     Answers: how does X actually work in code?        │
└───────────────────────────────────────────────────────┘
```

Phase 1 of the experiment uses only **source 1** (static registry). The
EventLog and GitNexus are out of scope until the registry strategies are
benchmarked.

---

## The Strategies

Four strategies, ordered from zero complexity to moderate.

---

### S0 — Control (no registry)

No domain knowledge injected. Only role instructions.

```
system:
  "You are a domain expert for a FIDC credit rights platform
   operating in Brazil. Answer questions clearly and concisely."
```

**Why this matters:** this is the floor. It tells us what Gemini already
knows about FIDC, credit rights, and related concepts from its training
data — without any project-specific context. If S0 performs comparably to
S1, the entire registry traversal question is moot.

**Expected strength:** general financial/legal concepts.
**Expected failure:** project-specific terms (Cedente as defined here,
RemessaStatus lifecycle, KitType logic).

---

### S1 — Full registry dump

Inject the entire semantic index JSON into every system prompt.

```
system:
  role_instructions +
  "## Domain Knowledge\n" +
  registry_json   # all terms, edges, aliases, anchors
```

**Token estimate:** ~8–12K tokens for current registry size (49 terms,
44 anchors). Grows linearly as the registry grows.

**Why this matters:** this is the ceiling. Everything available is always
present. No retrieval logic can fail, no relevant term can be missing.
If S1 doesn't outperform S0 significantly, the registry itself is the
problem — not the injection strategy.

**Expected strength:** any question touching a defined term.
**Expected failure:** when registry grows large and dilutes signal;
when operational data (EventLog) is needed and absent.

---

### S2 — Term name matching with session memory

Extract words from the user's message **and from all previous turns in the
session**. Match against term names and aliases in the registry. Inject
only matched terms and their direct edge neighbors (1 hop).

**What "inject term X" means precisely:**
- Include: `name`, `definition`, `aliases`, `category`, `edge list`
- Exclude: the definitions and edges of 1-hop neighbors (those get only `name` + `definition`)
- This prevents exponential expansion while keeping the semantic neighborhood readable.

```python
question = "O que é Cedente e como se relaciona com Parcelas?"

# Step 1: tokenize current question + all previous messages in this session
session_tokens = ["cedente", "parcelas", ...]

# Step 2: match against term names + aliases (accumulates across turns)
session_seeds = session.accumulated_terms | {"Cedente", "Parcela"}

# Step 3: load seeds + 1-hop edge targets (definition only, no further edges)
inject = {
  "Cedente":        { ...definition, aliases, edges: [Remessa] },
  "Parcela":        { ...definition, aliases, edges: [AquisicaoManual, ContratoCCB, Remessa] },
  "Remessa":        { name, definition },          # ← 1-hop neighbor: name + definition only
  "AquisicaoManual": { name, definition },         # ← 1-hop neighbor
  "ContratoCCB":    { name, definition },          # ← 1-hop neighbor
}
```

**Session memory:** `session.accumulated_terms` grows with each turn. A
follow-up like "e como ela se relaciona com Remessa?" on turn 2 — where
"ela" refers to Cedente from turn 1 — still resolves correctly because
Cedente is already in the session seed set.

**Token estimate:** ~500–2K tokens depending on question specificity.

**Expected strength:** direct and follow-up questions about named concepts.
**Expected failure:** first-turn implicit references that name no term at
all ("o ativo que o fundo compra"), synonyms not in the alias list,
multi-domain questions that span many unconnected terms.

---

### S3 — Category-level injection

Detect which domain category the question belongs to. Inject all terms
from that category. If no category is detected, fall back to **S1** (full dump).

The registry organizes terms into categories (Core/Shared, Aquisição,
Documents & OCR). Category detection runs on keywords present in the
question.

```python
question = "Como funciona a aprovação de uma remessa?"

# Step 1: detect category via keyword presence
keywords_to_category = {
  "remessa":    "Aquisição",
  "aprovação":  "Aquisição",
  "parcela":    "Aquisição",
  "kit":        "Documents & OCR",
  "documento":  "Documents & OCR",
  "cedente":    "Core / Shared",
  "fidc":       "Core / Shared",
}
detected = "Aquisição"

# Step 2: inject all terms in that category
inject = all_terms_where(category="Aquisição")  # ~12 terms, ~3K tokens

# Fallback: if no category detected → inject full registry (S1 behavior)
if not detected:
    inject = full_registry
```

If multiple categories are detected, inject all of them.

**Token estimate:** ~2–5K tokens for a single category; S1-equivalent on fallback.

**Expected strength:** domain-scoped questions where the user is clearly
talking about one area (acquisition flow, document validation, etc.).
**Expected failure:** cross-domain questions; questions about shared
concepts that appear in multiple categories.

---

## Experiment Design

### Assignment: random per session

Each **session** is randomly assigned one of the four strategies. The
strategy is fixed for the entire session — every turn in that session uses
the same strategy.

**Session definition:** a session ends when the user closes the chat or when
10 minutes pass without sending a message. Whichever comes first.

```python
import random

STRATEGIES = ["S0", "S1", "S2", "S3"]

def assign_strategy_for_session() -> str:
    return random.choice(STRATEGIES)
```

Strategy is assigned when the session is created and stored on
`AgentSession.strategy`. All turns in the session inherit it.

This eliminates within-session inconsistency (S0 on turn 1, S1 on turn 2)
and keeps the conversation coherent.

### What to log per turn

```
AgentTurnLog
├── session_id           FK → AgentSession
├── turn_number          int
├── user_message         text
├── strategy_used        str  ← "S0" | "S1" | "S2" | "S3"
├── context_tokens       int  ← usage_metadata.prompt_token_count (Gemini API)
├── completion_tokens    int  ← usage_metadata.candidates_token_count
├── latency_ms           int
├── response_text        text
├── is_helpful           bool null   ← true (👍) | false (👎) | null (no vote)
├── feedback_note        text null   ← optional free text
└── created_at           datetime
```

`context_tokens` is the primary cost metric.
`is_helpful` is the primary quality metric (thumbs voting — boolean,
null when the user does not vote).

The absence of a vote is valid data. Do not impute.

### Feedback UI

After every agent answer, a minimal feedback bar is shown:

```
Was this useful?   👍  👎   [optional note]   [Send]
```

- 👍 → `is_helpful = true`
- 👎 → `is_helpful = false`
- No action → `is_helpful = null`

### Results view

A read-only page aggregates the experiment log:

| Strategy | Avg context tokens | Voted turns | Helpful rate | Avg latency |
|----------|--------------------|-------------|--------------|-------------|
| S0       | ~200               | —           | —            | —           |
| S1       | ~10,000            | —           | —            | —           |
| S2       | ~1,200             | —           | —            | —           |
| S3       | ~3,500             | —           | —            | —           |

`Helpful rate = voted turns where is_helpful = true / total voted turns`

This table is the decision instrument. When enough voted turns accumulate,
it tells us: which strategy gives the best quality-to-cost ratio?

---

## Hypotheses to validate

**H1:** S1 outperforms S0 on quality for project-specific questions.
→ If false: the registry adds no value. Stop here and investigate dictionary quality.

**H2:** S2 achieves comparable quality to S1 at a fraction of the token cost.
→ If true: S2 becomes the default. S1 is retired for conceptual questions.

**H3:** S3 performs better than S2 for broad domain questions ("how does
acquisition work in general?") and worse for narrow ones ("what is KitType?").
→ If true: strategy selection can be made adaptive based on question type.

**H4:** No strategy handles operational questions ("what happened to contract X?")
without EventLog data.
→ Expected true for all four. This is the trigger for Phase 2 (EventLog injection).

---

## Success Criteria for Phase 1

The experiment is complete when:

- [ ] ≥ 80 voted turns have been collected across all strategies
- [ ] At least 20 voted turns per strategy
- [ ] H1 is confirmed or refuted
- [ ] A clear recommendation for Phase 2 default strategy is documented

---

## What Comes Next

**Phase 1.5 — Adaptive strategy (S4):**
After the experiment, if H2 and H3 are both confirmed, replace random
assignment with an adaptive blend: use S2 as the default, fall back to S3
when no term matches, fall back to S1 when S3 coverage is too low. This
adaptive path is the expected production strategy.

**Phase 2 — EventLog injection:**
Add entity detection on the user message. When a recognized identifier is
found (contract number: `CCB-\d+`, remessa ID: `REM-\d+`, or cedente CNPJ),
fetch its EventLog history and inject it alongside the chosen registry
strategy. Answers operational questions ("what happened to contract X?").
Entity patterns come from the registry anchors.

**Phase 3 — GitNexus tool:**
Add a `search_codebase(query)` tool backed by GitNexus. The agent calls
it when registry context is insufficient to answer code-level questions.
Requires investigation of how GitNexus can be called from the Django
backend (subprocess / HTTP / pre-computed snapshot).
