---
tags: [ontology, extraction, tooling]
node_type: readme
is_session: false
layer: ontology
nature: reference
status: active
version: 1.0.0
last_updated: 2026-04-07
---

# Ontology Tool — Master Navigation

**Name what things are. Connect them to where they live in code.**

---

## Quick Navigation — What's Your Goal?

| Goal | Read This | Time |
|------|-----------|------|
| **Understand what this system does** | [Philosophy](#the-problem) + [How It Works](#how-it-works) (this page) | 5 min |
| **See the full architecture** | `ARCHITECTURE_DIAGRAM.md` (7 Mermaid diagrams) | 10 min |
| **Start writing dictionaries & tagging code** | `docs/USAGE.md` (5-step guide) | 15 min |
| **See all the rules & schema** | `docs/domain-tagging-constitution.md` (required read) | 20 min |
| **Build a query engine to answer questions** | `QUERY_SYSTEM.md` (3 architecture options) | 20 min |
| **Check what's implemented vs. pending** | `IMPLEMENTATION_STATUS.md` (inventory + checklist) | 10 min |
| **Get quick tagging reference** | `docs/quick-reference.md` (one-page checklist) | 3 min |
| **See how everything fits together** | `OVERVIEW.md` (master overview) | 15 min |

---

## The Problem

Every codebase develops its own language. Business people call something "remessa", developers call it `RemessaAquisicao`, the database calls it `remessa_aquisicao`, and the Slack thread calls it "the upload batch". Over time, nobody is sure whether they're all talking about the same thing. New engineers spend weeks learning the vocabulary. Agents hallucinate terms that don't exist. Business rules get implemented twice under different names.

**This tool closes that gap.** The project maintains two dictionaries — business terms and system terms — that define every concept in plain language. Developers tag their code with `@biz` and `@sys` annotations that bind functions and classes to those dictionary terms. The pipeline reads both sides, cross-validates them, and produces a single unified registry: a structured map from "what the business calls it" to "where it lives in code".

That registry feeds into pgvector. Ask "how does kit matching work?" and get back both the dictionary definition of `KitType` and the exact function that implements it — one query, one answer.

---

## Philosophy: Based on Domainspec

This tool builds on [domainspec](https://github.com/vrondelli/domainspec) — a framework whose premise is simple: **think first, code second**.

Most software problems are not caused by bad code. They are caused by building the wrong thing. A business rule gets misunderstood, an edge case goes unnoticed, two systems contradict each other — and the code written before anyone noticed has to be rewritten. domainspec says: document the domain before you touch any implementation. The pipeline is always:

```
Domain Docs → Formal States → Tests → Implementation
```

Each stage depends on the previous. No meaningful tests without formal specs. No correct implementation without tests.

#### The building blocks

domainspec gives you two structural tools for organizing domain knowledge.

**A taxonomy of 13 meta-types** — every concept in your system is classified into exactly one:

| Question | Category | Types |
|----------|----------|-------|
| What things exist? | Structural | Entity, Value Object, Enum |
| What happens? | Behavioral | Operation, Query, Calculation, Rule, Policy, Workflow |
| How do parts communicate? | Connective | Interface, Event, Mapping |
| How do things change over time? | Lifecycle | State Machine |

So `KitType` is an Entity. `evaluate_kit_completion` is a Rule. `PaymentCompleted` is an Event. Every concept gets a type, and the type tells you what kind of documentation it needs.

**A relationship graph with 12 typed edges** — performs, produces, enforces, calculates, transitions, exposes, orchestrates, applies, maps, contains, queries, emits. From any concept, follow the edges to understand everything it touches. An Entity *performs* Operations, which *enforce* Rules, which *produce* Events, which *transition* State Machines.

The other key idea is **test derivation**: if your state machines, rules, and operation contracts are formal enough, tests can be read directly from the documentation. Every transition row becomes a test case. Every rule becomes a pass/fail pair. If you can't derive a test from the docs, the docs have a gap — fill the spec first, then write the test.

#### How this tool maps to domainspec

domainspec is the framework. This tool is the **runtime infrastructure** that makes it work in a real codebase:

| domainspec concept | What we built |
|--------------------|---------------|
| Domain documentation | Business and system dictionaries (`dictionary-business.md`, `dictionary-sys.md`) |
| Concept classification | The `type:` field on `@biz`/`@sys` tags — uses the 13-type taxonomy |
| Relationship graph | Dictionary `edges:` fields — typed edges like `enforces`, `contains` |
| Registry / glossary | Unified registry JSON — all concepts indexed with their code locations |
| Code-to-docs binding | `@biz`/`@sys` docstring tags anchoring dictionary terms to functions and classes |
| Validation pipeline | Cross-validation ensuring every tag references a real dictionary term |
| Semantic search | pgvector embeddings making the whole vocabulary queryable by meaning |

The dictionaries are the domain docs. The tags are the bridge to code. The pipeline keeps them honest. The registry makes it all searchable.

---

---

## Getting Started (Quick Overview)

**→ For the full step-by-step guide, see `docs/USAGE.md`**

Before touching the pipeline, you need to understand the two things you'll actually write by hand: **dictionaries** and **tags**. The pipeline does the rest.

### 1. Write your dictionary

A dictionary is a Markdown file where each H3 heading is a business concept. Start small — two or three terms are enough:

```markdown
# Business Dictionary

## Core Concepts

### Order

A customer request to purchase one or more products.

- **Code equivalent:** `Order`

### OrderStatus

The lifecycle state of an order.

- **Code equivalent:** `OrderStatus`
- **Edges:** `governs` → Order
```

Each entry needs at minimum a description and a code equivalent. As your vocabulary grows, add aliases, edges, and disambiguation. Full schema in [docs/domain-tagging-constitution.md](docs/domain-tagging-constitution.md#rule-6--dictionary-entry-schema).

### 2. Tag your code

Find a business-relevant function. Add a `@biz` tag as the last line of its docstring:

```python
def place_order(cart, customer):
    """Validate cart contents and create a new order for the customer.

    @biz: Order | type: operation
    """
```

The `type` comes from the 13-type taxonomy. Not sure which one? [USAGE.md](docs/USAGE.md#choosing-the-right-type) has a decision guide.

### 3. Run the pipeline

```bash
python -m tools.ontology.cli extract    # lint + scan + build registry
python -m tools.ontology.cli validate --strict   # catch orphan anchors
```

That's it. The registry now maps your vocabulary to your code.

### Learn more

| Document | What it covers |
|----------|---------------|
| [OVERVIEW.md](OVERVIEW.md) | Master overview — how all pieces fit together |
| [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) | Complete pipeline with 7 Mermaid diagrams |
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | What's implemented, what's pending, checklist |
| [QUERY_SYSTEM.md](QUERY_SYSTEM.md) | How to build a query engine to answer questions |
| [Developer Guide](docs/USAGE.md) | 5-step walkthrough, type selection, building dictionaries |
| [Constitution](docs/domain-tagging-constitution.md) | Full rules — when to tag, entry schema, edge vocabulary |
| [Quick Reference](docs/quick-reference.md) | One-page checklist for tagging sessions |

---

## How It Works

Everything below is about the pipeline internals — how the tool reads your dictionaries and tags, cross-validates them, and produces the registry. You don't need this to start using the tool, but it helps to understand what's happening under the hood.

---

## Two Sources, One Registry

Two sources of domain knowledge exist in the project today. Both are human-readable. Neither is machine-queryable.

**Dictionaries** — Markdown files defining every business and system concept in plain language. Each entry has a term name, description, code equivalent, aliases, and relationship edges to other terms. This is the project's vocabulary.

**Docstring tags** — `@biz` and `@sys` annotations in Python docstrings that bind code symbols to dictionary terms. A function tagged `@biz: KitType | type: rule` declares: "this function implements the KitType business rule".

The problem: these two sources are disconnected. A developer tags code with a term that doesn't exist in the dictionary — nobody catches it. An agent querying the dictionary has to parse raw Markdown every time. Neither source feeds into any structured store.

The extraction pipeline connects them. It reads both sides, validates that every code tag references a real term, and produces a single JSON registry merging definitions with their implementations. That registry feeds into pgvector, making the entire vocabulary searchable by meaning.

---

## The Pipeline

Two stages. Clear separation of concerns.

```
Dictionary Markdown → Dictionary Extractor ──┐
                                              ├──► Cross-Validate → Unified Registry → Embeddings → pgvector
Python Codebase    → Tag Scanner ────────────┘
```

### Stage 1 — Pre-Commit Hook (offline, no network)

Runs on every `git commit` when dictionary or Python files change. Fast, local, no API calls.

| Step | What it does | Blocks on failure? |
|------|-------------|-------------------|
| Detect | Check if `dictionary*.md` or `*.py` changed | No — skips if nothing changed |
| Lint | Validate dictionary format against formal schema | Yes — malformed dictionary blocks everything |
| Extract | Dictionary Extractor + Tag Scanner run in parallel | Yes — parse errors block |
| Validate | Check for orphan anchors (tag referencing unknown term) | Yes — orphan anchors block commit |

The hook produces no persistent artifacts. Its output is ephemeral — used for validation only. Nothing is committed.

### Stage 2 — CI/CD (authoritative, online)

Runs on every `git push`. Re-runs the full pipeline from scratch. If the hook was skipped via `--no-verify`, CI catches it.

| Step | What it does |
|------|-------------|
| Re-extract + validate | Full pipeline from scratch — catches skipped hooks |
| Build registry | Generate the unified registry JSON as a CI artifact |
| Embed | Call Gemini Embedding API, upsert 768-dim vectors into pgvector |
| Report | Publish coverage report — unanchored terms, anchor coverage % |

CI is the single source of truth. If CI fails, the build fails.

---

## The Two Extractors

### Dictionary Extractor

Parses `dictionary-business.md` and `dictionary-sys.md` into structured objects. Each H3 heading becomes a term with its full metadata:

```
### EligibilityFilter
    ↓ parses into ↓
{
    term: "EligibilityFilter",
    prefix: "biz",
    category: "Rules & Validation",
    description: "A stateless, side-effect-free business rule...",
    code_equivalent: "EligibilityFilter",
    aliases_code: ["eligibility_criteria", "filter_criteria"],
    aliases_conversation: ["filtro de elegibilidade"],
    edges: [{ type: "enforces", target: "Remessa" }],
    unanchorable: false
}
```

### Tag Scanner

Walks the Python codebase via AST parsing and extracts every `@biz`/`@sys` tag from docstrings:

```python
def evaluate_kit_completion(folder_docs, active_kits):
    """
    Evaluate a folder's documents against active KitTypes using OR logic.

    @biz: KitType | type: rule
    """
```

```
    ↓ extracts into ↓
{
    term: "KitType",
    prefix: "biz",
    type: "rule",
    file: "domains/documents_validation/domain/kit_matching.py",
    symbol: "evaluate_kit_completion",
    kind: "function",
    line: 122
}
```

### Cross-Validation

After both extractors run, the pipeline checks that every code tag references a real dictionary term. A tag referencing an unknown term is an **orphan anchor** — commit blocked.

The reverse is fine. Unanchored terms (dictionary entries with no code tags yet) are tracked but don't block. Tagging is incremental. The coverage report distinguishes between terms that are inherently untaggable (abstract concepts like "Direitos Creditarios") and terms that should be tagged but haven't been yet.

---

## The Registry

One JSON structure. Each dictionary term carries its full definition plus every code anchor that references it:

```json
{
    "meta": {
        "dictionary_biz_version": "0.8.0",
        "dictionary_sys_version": "0.3.0",
        "total_terms": 37,
        "total_anchors": 11,
        "unanchored_terms": 26,
        "unanchored_by_design": 6,
        "unanchored_missing_tags": 20,
        "orphan_anchors": 0
    },
    "terms": {
        "KitType": {
            "prefix": "biz",
            "description": "...",
            "edges": [{ "type": "contains", "target": "DocumentTemplate" }],
            "unanchorable": false,
            "anchors": [
                { "symbol": "evaluate_kit_completion", "taxonomy_type": "rule", "kind": "function", "file": "..." },
                { "symbol": "KitType", "taxonomy_type": "entity", "kind": "class", "file": "..." }
            ]
        }
    }
}
```

Formal Pydantic schema in `models.py`. Every pipeline stage produces and consumes these types. The schema is the contract.

---

## What Gets Embedded

Two granularities. Two kinds of questions answered.

**Dictionary terms (conceptual anchors)** — each term becomes one embedding: name, description, edges, aliases. No taxonomy type — that belongs to the code symbols, not the concept. Ask "what filters eligibility?" and `EligibilityFilter` surfaces.

**Tagged symbols (code anchors)** — each tagged function/class becomes one embedding: symbol name, term, type, file path. Ask "how does kit matching work?" and `evaluate_kit_completion` surfaces.

Both share the `term` key. Find a concept, immediately get its implementations. Find an implementation, immediately get its definition.

---

## Infrastructure

Same Postgres the app already uses. No separate containers, no new services. The only addition is `pgvector` for embedding storage.

### What you need

| Component | Source | Purpose |
|-----------|--------|---------|
| Postgres 15+ | Existing `docker-compose.dev.yml` | Stores everything |
| pgvector extension | Added to existing Postgres via `init-db/` | Native vector columns and cosine similarity search |
| Python 3.10+ | Existing project runtime | Runs the CLI |
| Pydantic v2 | `pip install pydantic` | Data validation for registry schema |
| Gemini API key | `GEMINI_API_KEY` env var | Embedding generation (CI-only, optional locally) |

### Setup

```bash
# 1. Bootstrap the database (pgvector extension + ontology tables)
python tools/semantic-index/setup.py

# 2. Run the extraction pipeline
python -m tools.ontology.cli extract

# 3. Validate dictionaries and tags
python -m tools.ontology.cli validate --strict

# 4. See coverage report
python -m tools.ontology.cli report
```

The setup script:
- Enables `pgvector` extension in the existing Postgres
- Creates `operational_ontology_embeddings` table with `vector(768)` column
- Creates `conceptual_ontology_nodes` and `conceptual_ontology_edges` tables (vault graph index)
- Verifies the connection and prints status

If the project's Docker stack is running (`docker compose -f docker-compose.dev.yml up`), the script connects to `localhost:5433` with the default credentials. No new containers needed.

---

## CLI Reference

All commands run as `python -m tools.ontology.cli <command>`.

| Command | Stage | What it does |
|---------|-------|-------------|
| `extract` | Hook / CI | Lint gate → run both extractors → build unified registry JSON |
| `validate` | Hook / CI | Lint gate → validate dictionaries + check orphan anchors (no output file) |
| `lint` | Hook | Lint dictionary files against formal schema |
| `embed` | Deploy only | Compose embedding texts, call Gemini API, upsert pgvector |
| `report` | CI / local | Print coverage report (terms, anchors, unanchored, orphans) |

### Examples

```bash
# Extract with custom dictionary paths and scan root
python -m tools.ontology.cli extract \
    --biz-dict docs/vault/dictionary-business.md \
    --sys-dict docs/vault/dictionary-sys.md \
    --scan-root . \
    --output generated/ontology-registry.json

# Strict validation (fails on orphan anchors)
python -m tools.ontology.cli validate --strict --scan-root .

# Dry-run embedding (prints texts without calling API)
python -m tools.ontology.cli embed --dry-run

# Coverage report from a registry file
python -m tools.ontology.cli report --registry generated/ontology-registry.json
```

---

## Project Layout

```
tools/semantic-index/
├── README.md                              ← You are here
├── CLAUDE.md                              ← Agent instructions for dictionary + tagging work
├── cli.py                                 ← CLI entry points (lint, extract, validate, embed, report)
├── models.py                              ← Pydantic schemas (the contract)
├── setup.py                               ← Infrastructure bootstrap script
├── docs/
│   ├── domain-tagging-constitution.md     ← The rules: tagging, dictionary schema, edges
│   ├── USAGE.md                           ← Developer guide: 5-step walkthrough, type selection
│   └── quick-reference.md                 ← One-page tagging checklist
├── extractors/
│   ├── tag_scanner.py                     ← AST scanner for @biz/@sys docstring tags
│   ├── dictionary_extractor.py            ← Markdown parser for dictionary files
│   └── dictionary_linter.py               ← Dictionary schema validator (first gate)
├── registry/
│   └── builder.py                         ← Merge + cross-validate + coverage metrics
├── embeddings/
│   └── client.py                          ← Gemini API text composition + pgvector upsert
├── examples/
│   └── example_tagged_module.py           ← Reference: properly tagged Python module
└── tests/
    ├── test_tag_scanner.py                ← Tag scanner unit tests
    ├── test_dictionary_extractor.py       ← Dictionary extractor unit tests
    ├── test_dictionary_linter.py          ← Linter unit tests
    ├── test_builder.py                    ← Registry builder unit tests
    ├── test_embeddings.py                 ← Embedding text composition tests
    └── test_cli_integration.py            ← End-to-end pipeline integration tests
```

---

## Design Decisions

- **Plain Python CLI** — no Django imports, no management commands. Must work in pre-commit hooks, CI runners, and local machines without the app context.

- **Same Postgres, no new services** — ontology data lives next to application data. An agent can JOIN embeddings with business tables in a single query.

- **Two-stage pipeline** — pre-commit hook (offline: lint + extract + validate) and CI (authoritative: re-extract + validate + report). Embedding runs at deploy time, not in CI. Hook is convenience. CI is truth.

- **Registry is a CI artifact** — not committed to the repo. Generated fresh on every push. No merge conflicts, no stale files.

- **Taxonomy type lives on code anchors, not dictionary terms** — the dictionary defines what a concept IS. The code tag defines what role a symbol plays (`| type: rule`). KitType has anchors of type entity, rule, query — the concept itself has no single type.

- **Pydantic for validation** — `models.py` defines the contract. Every pipeline stage reads and writes these types. Extractors, validators, embedders, and consumers all speak the same schema.

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| [Discovery: Extraction Pipeline](../../specs/ontology/docs/data-foundations/discovery-extraction-pipeline.md) | Design document for this pipeline |
| [Implementation Plan: Extraction Pipeline](../../specs/ontology/docs/data-foundations/implementation-plan-extraction-pipeline.md) | Execution roadmap (6 phases) for integrating this pipeline end-to-end |
| [Discovery: Data Foundations](../../specs/ontology/docs/data-foundations/discovery-data-foundations.md) | Prescribes the full data architecture (events, graph, embeddings) |
| [Domain Tagging Discovery](../../specs/ontology/docs/domain-tagging/domain-tagging-discovery.md) | Designs the `@biz`/`@sys` tag convention |
| [Dictionary Business](../../docs/vault/dictionary-business.md) | Primary input: business vocabulary |
| [Dictionary System](../../docs/vault/dictionary-sys.md) | Primary input: system vocabulary |
| [Folder Structure Constitution](../../docs/vault/constitution/folder-structure-constitution.md) | Architectural rules for directory layout |
