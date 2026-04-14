# Domain-Code-Mapping

**Bridge domain vocabulary to code via DDD + semantic search.**

> 🚀 **Want to get started?** → Read [`USAGE_GUIDE.md`](USAGE_GUIDE.md) for step-by-step instructions.
>
> 📚 **Want the philosophy?** → Keep reading this README.

---

## Context

Building software for a specific domain is not just writing code. It is building a representation of something real — a business, a process, a set of rules — and making that representation behave as close to reality as possible. To do that well, you need a model of the domain: first a mental model, then a software model. One of the proven strategies is to create a shared language for the business — a language that both business people and developers can use to communicate without translation.

That shared language has always been important, but it has always been expensive to maintain. The language lives in documentation, and the code changes faster than the documentation does. Keeping them aligned in near-real-time was impractical without tooling.

This directory builds on top of the ideas from (https://github.com/vrondelli/domainspec) in the hope of creating a mechanism to extract meaning from code, so the domain can describe itself — its vocabulary, its rules, and where they live.

## The Premise

The idea is that a system should be able to describe itself. Not through generated docs or comments that rot — but through structured annotations that the developers write as part of the code, and dictionary entries that the business maintains as part of the documentation. Both sides declare what they mean, and tooling keeps them honest.

The second premise is that information should never be lost. Every concept that is documented and every tag that is placed in code feeds into a registry — a single, unified graph of domain knowledge. That registry is then embedded semantically, so the system itself becomes queryable. You can ask it what a concept means, where it lives in code, what depends on it, and what would break if you changed it. The knowledge does not live in someone's head or in a Slack thread that scrolls away. It lives in the system, and the system can answer questions about itself.

## The Mechanism

To make those premises concrete, the system needs two things: a way for the business to define what concepts mean, and a way for developers to mark where those concepts live in code.

The business side is a set of Markdown dictionaries — files in `docs/vault/` where each concept gets a heading, a definition in plain language, its relationships to other concepts, and the name it goes by in code. This is not generated documentation. It is written by people who understand the domain, in a structured format that tooling can parse.

```markdown
### KitType

A collection of document templates grouped by business process.
All templates in a kit must be present for a folder to be considered complete.

- **Code equivalent:** KitType
- **Aliases in codebase:** Kit, TemplateKit
```

The developer side is a tag — `@biz` or `@sys` — placed in the docstring of any function, class, or method that implements a domain concept. The tag names the concept and declares what role this particular piece of code plays in it.

```python
class KitType:
    """Represents a collection of document templates.

    @biz: KitType | type: entity
    """

def evaluate_kit_completion(folder, kit):
    """Check if folder satisfies all kit requirements.

    @biz: KitType | type: rule
    """
```

When a developer tags a function with `@biz: KitType | type: rule`, they are saying: this function implements a business rule related to KitType. When the business writes a dictionary entry for KitType, they are saying: this is what KitType means, this is its code equivalent. The two declarations point at each other. If either side changes without the other, the system notices.

Notice that the same concept appears twice in code with different types. The class is an `entity` — it has identity, it persists. The function is a `rule` — it enforces a constraint. This is intentional. A single domain concept often plays more than one role in a codebase, and the type system accounts for that.

The high-level flow looks like this:

```
  Dictionary (Markdown)              Code (@biz/@sys/@edge tags)
  ─────────────────────              ─────────────────────────────
  Term definitions                   Annotations in docstrings
  Aliases                            Taxonomy types (entity, rule, ...)
  Code equivalents                   Edges (@edge: verb -> Target)
                                     File + line locations
          │                                    │
          └──────────── Compare ───────────────┘
                           │
                   Do they agree?
                    │            │
                   Yes           No
                    │            │
              Build registry    Block commit
                    │
             Embed semantically
                    │
             Queryable system
```

If both sides agree, the tooling merges them into a single registry and the system can answer questions about its own domain. If they disagree — a tag without a definition, a definition without code — the commit is blocked until someone fixes the inconsistency.

## The Pipeline

With that mechanism in place, the implementation is a two-stage pipeline.

The first stage runs locally, on every commit. It reads the Markdown dictionaries in `docs/vault/` and extracts the formal concept definitions — term names, descriptions, relationships to other concepts, code equivalents. It also walks the Python source code looking for `@biz` and `@sys` annotations in docstrings, which mark where each concept is actually implemented. Then it compares the two sides. Every annotation in code must point to a concept that exists in the dictionary. Every concept in the dictionary must have at least one location in code. If either side has something the other does not — an annotation without a definition, or a definition without code — the commit is blocked. This runs in about two seconds and needs no network.

The second stage runs in CI, on every push. It repeats the validation to catch anything that slipped past the local hook, then takes the registry further: it composes text representations of each concept and sends them to the Gemini Text Embedding API, which returns 768-dimensional vectors. Those vectors are stored in pgvector. After this stage, the domain is not just validated — it is searchable by meaning. You can ask "how does kit matching work?" and get back the concepts, definitions, and exact code locations that are relevant.

The first stage produces a JSON file — the `OperationalOntologyRegistry` — that contains every concept, its definition, where it lives in code, and how it relates to other concepts. The second stage turns that registry into a semantic index. Together, they keep the domain aligned and make it answerable.

## Taxonomy

Each annotation carries a type. There are 13 of them, organized around four questions that any system needs to answer.

What things exist? An **entity** has unique identity and persists over time. A **value-object** is immutable and defined entirely by its content. An **enum** is a fixed, finite set of named values.

What happens? An **operation** changes state. A **query** reads data without side effects. A **calculation** is a pure function — same input, same output. A **rule** is a boolean constraint that must hold for something to proceed. A **policy** selects between behaviors at runtime. A **workflow** coordinates multiple operations in sequence.

How do parts communicate? An **interface** is an API boundary. An **event** is a notification that something happened. A **mapping** is a field-by-field transformation between two data shapes.

How do things change over time? A **state-machine** defines the states an entity can be in, the transitions between them, the guards that protect those transitions, and the invariants that must always hold.

These types are not decorative. They determine how concepts relate to each other. An entity contains value objects. A rule enforces an operation. An operation produces events. An event transitions a state machine. These relationships are typed and directional — they are called edges, and there are 12 of them.

## Edges

Edges connect concepts into a graph. From any concept, you can follow the edges to understand what it touches and what touches it.

| Edge | Connects | What it tells you |
|------|----------|-------------------|
| contains | Entity → Value Object | What this entity is composed of |
| enforces | Rule → Operation | What must be true for this operation to run |
| produces | Operation → Event | What happens after this operation completes |
| queries | Query → Entity | What data this query reads |
| emits | Entity → Event | What this entity announces when it changes |
| orchestrates | Workflow → Operation[] | What steps this workflow coordinates |
| transitions | Event → State Machine | What state change this event triggers |
| applies | Policy → Operation | What decision logic governs this operation |
| maps | Mapping → Entity/Interface | What transformation happens at this boundary |
| performs | Entity → Operation | What this actor can do |
| calculates | Calculation → Operation | What derived values this operation needs |
| exposes | Interface → Operation/Query | What this API makes available |

Following the chain Entity → Operation → Rules → Events → State Machine gives you a complete picture of any feature. Every connection is explicit — nothing is implied.

## Data Models

All stages of the pipeline — extraction, validation, embedding, querying — share the same Pydantic models. This is a deliberate choice: one type definition across all components means no translation layers and no version drift.

```python
class DictionaryTerm:
    concept_id: str               # "biz:KitType"
    term: str                     # "KitType"
    prefix: str                   # "biz" or "sys"
    description: str              # Formal definition
    code_equivalent: Optional[str]
    aliases_code: list[str]
    taxonomy_types: list[str]     # entity, rule, operation, etc.
    edges: list[Edge]
    unanchorable: bool            # True for abstract concepts without code

class CodeAnchor:
    symbol: str                   # Function or class name
    file: str                     # Relative path
    line: int
    kind: str                     # class, function, method
    taxonomy_type: str            # One of the 13 types
    description: str              # From docstring
```

Concept IDs are namespaced — `biz:KitType`, `sys:PostgresConnection` — so that business concepts and system infrastructure concepts do not collide.

## Database Schema

The semantic index lives in PostgreSQL with pgvector. There are two tables: one for concepts, one for code locations. Both carry 768-dimensional vectors for cosine similarity search.

```sql
CREATE TABLE embedding_term (
    concept_id VARCHAR(255) PRIMARY KEY,
    term VARCHAR(255),
    prefix VARCHAR(10),
    description TEXT,
    composed_text TEXT,
    vector vector(768),
    metadata JSONB,
    updated_at TIMESTAMP
);

CREATE TABLE embedding_anchor (
    id BIGINT PRIMARY KEY,
    concept_id VARCHAR(255) REFERENCES embedding_term,
    symbol VARCHAR(255),
    file VARCHAR(500),
    line INTEGER,
    kind VARCHAR(50),
    taxonomy_type VARCHAR(50),
    composed_text TEXT,
    vector vector(768),
    updated_at TIMESTAMP
);
```

The `composed_text` field is worth noting. It contains the text that was actually sent to the embedding model — a composition of the term name, its description, its edge context, and its anchor details. Embedding quality depends heavily on what text you feed the model, and richer, more composed input produces better retrieval.

## Components

`semantic-index/` is where extraction and validation happen. Inside `extractors/`, there is a dictionary parser that reads Markdown, a code scanner that walks the AST, a linter that checks schema and formatting, and an event validator that cross-checks the event catalog. The `registry/builder.py` merges what the extractors produce, detects orphans, and writes the JSON registry. The `embeddings/` directory handles the Gemini API calls and pgvector upserts. The CLI exposes seven commands: extract, validate, lint, embed, report, visualize, and validate-events.

`personal-assistant/` is the query layer. It takes a natural language question, embeds it, searches pgvector for the closest concepts and anchors, loads their full registry entries, enriches them with edge relationships, and returns a structured answer. The persistence layer uses Django ORM. REST endpoints expose the interface.

`agent-helper/` makes the domain queryable by Claude through MCP tools. When an agent needs to understand what a concept means or where it is implemented, it calls these tools rather than searching through files.

## Design Decisions

It needs to run in pre-commit hooks, in CI, and in offline environments where no services are running. Pydantic handles all the type validation. A developer can run the full extraction and validation cycle on their laptop without starting anything.

The registry is never committed to the repository. It is regenerated on every push. This avoids merge conflicts and ensures that the registry always reflects the actual state of code and documentation at that moment. CI is the authority — the pre-commit hook is a convenience for fast local feedback, not the source of truth.

Orphan detection blocks commits intentionally. This is the enforcement mechanism. If you annotate code with `@biz: SomeConcept` but that concept has no dictionary entry, the commit fails. If you add a dictionary entry but never tag any code, the commit also fails. You are forced to keep both sides in sync. The only escape is to explicitly mark a concept as `unanchorable`, which is reserved for abstract ideas that exist in the domain but have no single code location.

## Getting Started

```bash
# Install the pre-commit hook
python tools/semantic_index/setup.py

# Run extraction and validation (works offline)
python -m semantic_index.cli extract
python -m semantic_index.cli validate

# See where coverage stands
python -m semantic_index.cli report
```

The best way to understand the workflow is to look at what already exists. Open `docs/vault/dictionary-business.md` and read a few entries. Then search the codebase for `@biz` and see how those same concepts show up in code. Once that makes sense, try adding a new dictionary entry and a matching code tag, and commit. The hook will tell you if anything is inconsistent.

For semantic search, you need PostgreSQL with pgvector:

```bash
docker compose up -d postgres
python tools/semantic_index/setup.py
python -m semantic_index.cli embed
```

## CLI Reference

| Command | What it does |
|---------|-------------|
| `extract` | Parse dictionaries and code, build the registry |
| `validate` | Check that both sides match, report orphans |
| `lint` | Check schema and formatting |
| `embed` | Generate embeddings and store them in pgvector |
| `report` | Show coverage statistics |
| `visualize` | Generate an HTML dependency graph |
| `validate-events` | Cross-check the event catalog against operations |

## Current State

The extraction pipeline is operational: 49 terms, over 120 anchors, zero orphans, 78% code coverage. The embedding pipeline, query engine, and REST API are implemented. The HTML dependency explorer is in beta.

## References

- `semantic-index/ARCHITECTURE_DIAGRAM.md` — component walkthrough
- `personal-assistant/README.md` — query API documentation
- `agent-helper/README.md` — Claude integration
- `python -m semantic_index.cli --help` — CLI usage
