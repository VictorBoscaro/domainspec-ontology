---
node_type: guide
name: Semantic Index Usage Guide
description: Step-by-step guide to using the domain-code-mapping system in your codebase
version: 2.0.0
last_updated: 2026-04-13
---

# Semantic Index Usage Guide

This guide walks you through actually **using** the semantic index system in your codebase. For the philosophical foundations, see [`README.md`](README.md).

---

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Step 1: Write Your Dictionaries](#step-1-write-your-dictionaries)
3. [Step 2: Tag Your Code](#step-2-tag-your-code)
4. [Step 3: Extract & Validate](#step-3-extract--validate)
5. [Step 4: Query Your Domain](#step-4-query-your-domain)
6. [Step 5: Embed & Deploy](#step-5-embed--deploy)
7. [Common Workflows](#common-workflows)

---

## Installation & Setup

### 1. Install the Package

```bash
# From the repo root
pip install -e .
```

This makes the `semantic_index` module available and the CLI commands available globally.

### 2. Set Up Postgres (One Time)

The system needs a Postgres database with `pgvector` extension for embeddings.

```bash
# Start a local Postgres with pgvector
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Or use your existing Postgres + manually create the extension
psql -d your_db -c "CREATE EXTENSION IF NOT EXISTS pgvector"
```

### 3. Bootstrap the Schema

```bash
# Set environment variables
export POSTGRES_PASSWORD=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=postgres
export POSTGRES_USER=postgres

# Create tables
python -m semantic_index.setup
```

You should see:
```
Connecting to localhost:5432/postgres...
  Connected.
Creating pgvector extension...
Creating embedding_term table...
Creating embedding_anchor table...
  OK
```

---

## Step 1: Write Your Dictionaries

Business and system dictionaries live in **Markdown files in `docs/vault/`**.

### Dictionary Structure

Create `docs/vault/dictionary-business.md`:

```markdown
---
version: 1.0.0
---

# Business Dictionary

## Concepts

### KitType

A collection of document templates grouped by business process.
All templates in a kit must be present for a folder to be considered complete.

- **Code equivalent:** KitType
- **Aliases in codebase:** Kit, TemplateKit
- **Aliases in conversation:** Kit, Template Kit

### DocumentTemplate

A reusable template for documents in a specific format (PDF, XLS, etc.).

- **Code equivalent:** DocumentTemplate
```

And `docs/vault/dictionary-sys.md` for infrastructure concepts:

```markdown
---
version: 1.0.0
---

# System Dictionary

## Concepts

### PostgresConnection

A pooled database connection to the operational database.

- **Code equivalent:** get_postgres_connection
- **Unanchorable:** false
```

### What Each Field Means

| Field | Required | Example | Notes |
|-------|----------|---------|-------|
| **H3 heading** | Yes | `### KitType` | Concept name. Must be unique within dictionary. |
| **Description** | Yes | Free text | Plain language definition of the concept. |
| **Code equivalent** | Yes | `KitType` | The function/class name in code that implements this. |
| **Aliases in codebase** | No | `Kit, TemplateKit` | Symbol names used in code for this concept. |
| **Aliases in conversation** | No | `Kit, Template Kit` | Names used in meetings, Slack, docs. |
| **Unanchorable** | No | `true` | Set for abstract concepts with no taggable code symbol. |

> **Edges live in code, not in dictionaries.** Relationships between concepts are declared with `@edge:` lines in docstrings — right next to the code that establishes the relationship.

### Taxonomy Types

When you tag code, you'll reference one of 13 types. Here's which ones apply where:

**Structural** (what things exist):
- `entity` — Has identity, persists over time (e.g., a User, an Order)
- `value-object` — Immutable, defined by content (e.g., Money, Address)
- `enum` — Fixed set of named values (e.g., OrderStatus)

**Behavioral** (what happens):
- `operation` — Changes state (e.g., ProcessPayment, CreateFolder)
- `query` — Reads data without side effects (e.g., GetUserById)
- `calculation` — Pure function, deterministic (e.g., CalculateTax)
- `rule` — Boolean constraint that must hold (e.g., ValidateKitCompletion)
- `policy` — Selects behavior at runtime (e.g., RoutingPolicy, ScoringPolicy)
- `workflow` — Orchestrates multiple operations (e.g., CheckoutWorkflow)

**Connective** (how parts communicate):
- `interface` — API boundary (e.g., RESTful endpoint)
- `event` — Notification that something happened (e.g., OrderCreated, PaymentCompleted)
- `mapping` — Field-by-field transformation (e.g., DictToModel, APIResponseMapper)

**Lifecycle** (how things change):
- `state-machine` — States, transitions, guards, invariants (e.g., OrderStateMachine)

---

## Step 2: Tag Your Code

Every function or class that implements a concept gets a **`@biz`** or **`@sys` tag** in its docstring.

### Basic Tag Format

```python
def process_payment(order_id: str, amount: float) -> bool:
    """
    Process a payment for an order.

    @biz: Payment | type: operation
    """
    # implementation
```

### Tag Anatomy

```
@biz: ConceptName | type: operation
^     ^            ^      ^
|     |            |      └─ Taxonomy type (required)
|     |            └────────── Pipe separator
|     └────────────────────── Concept name (matches dictionary)
└──────────────────────────── Category: @biz (business) or @sys (system)
```

### Full Example with Edges

Edges are declared in docstrings, not in the dictionary. Use `@edge:` lines alongside your `@biz`/`@sys` tag:

```python
class Order:
    """Represents a customer order."""
    
    @biz: Order | type: entity

def apply_discount(order: Order, discount_code: str) -> Order:
    """
    Apply a discount code to an order.

    @biz: Discount | type: rule
    @edge: enforces -> ApplyDiscount
    @edge: produces -> OrderDiscountApplied
    """
    # implementation
```

### Edge Format

```
@edge: verb -> TargetConcept
```

The edge lives right next to the code that establishes the relationship. The scanner extracts it and includes it in `spec.yaml` alongside the anchor.

**Common verbs:**
`enforces`, `produces`, `contains`, `queries`, `emits`, `orchestrates`, `applies`, `maps`, `performs`, `calculates`, `exposes`, `transitions`

### Common Patterns

**Entity with methods:**
```python
class User:
    """A platform user."""
    
    @biz: User | type: entity

    def authenticate(self, password: str) -> bool:
        """Authenticate against stored password hash."""
        
        @biz: User | type: operation
```

**Multiple roles for one concept:**
```python
# The same concept can appear multiple times with different roles

class KitType:
    """A kit definition."""
    @biz: KitType | type: entity

def evaluate_kit_completion(folder: Folder, kit: KitType) -> bool:
    """Check if folder satisfies all kit requirements."""
    @biz: KitType | type: rule
    # Semantic index understands that both the class and function implement KitType
```

**Events:**
```python
from dataclasses import dataclass

@dataclass
class OrderCreated:
    """Fired when a new order is placed."""
    order_id: str
    timestamp: datetime
    
    @biz: OrderCreated | type: event
```

---

## Step 3: Extract & Validate

The extraction pipeline reads dictionaries and code tags, then builds a **unified spec.yaml**.

### Lint (Fastest)

Checks dictionary syntax without scanning code:

```bash
python -m semantic_index.cli lint
```

Output:
```
  OK: dictionaries pass lint checks
```

### Extract (Recommended)

Reads dictionaries + code tags, builds `domains/spec.yaml`:

```bash
python -m semantic_index.cli extract
```

Output:
```
Extracting terms from dictionaries...
  5 business terms, 3 system terms

Scanning codebase for @biz/@sys tags (root: .)...
  12 anchors found, 0 scan issues

Building unified registry...
  spec.yaml written to domains/spec.yaml
  12 anchors
```

### Validate (CI-Ready)

Full validation with strict mode:

```bash
python -m semantic_index.cli validate
```

This fails if:
- Any tag references a concept that doesn't exist in the dictionary
- Any dictionary concept has zero code tags (and isn't marked `unanchorable: true`)

### Report

Coverage report:

```bash
python -m semantic_index.cli report
```

Output:
```
============================================================
  Ontology Coverage Report
============================================================
  Dictionary versions:      biz=1.0.0  sys=1.0.0
  Total terms:              8
  Total code anchors:       12
  Orphan anchors:           0
  Unanchored terms:         0

  Tagging coverage:         100.0%
============================================================
```

---

## Step 4: Query Your Domain

Once `spec.yaml` exists, you can query it without a database.

### In Python

```python
from semantic_index import load_domain_slice, format_domain_context

# Get all concepts in a domain
concepts = load_domain_slice("aquisicao")

# Format as readable text
text = format_domain_context("aquisicao", concepts)
print(text)
```

Output:
```
DOMAIN: aquisicao (5 concepts)

ENTITIES (2)
  Remessa  domains/aquisicao/models.py:42  → RemessaAquisicao
    A batch of documents uploaded together.
    edges: contains → Document, emits → RemessaCreated

  Document  domains/aquisicao/models.py:89  → Document
    A single file in a remessa.
    edges: contained-in → Remessa

OPERATIONS (1)
  process_remessa  domains/aquisicao/tasks.py:15  → ProcessRemessa
    Process all documents in a remessa.
    edges: produces → DocumentProcessed
```

### Via MCP (Claude Code Integration)

If you set up the MCP server, Claude Code agents can query your domain:

```python
from semantic_index.query.domain_slice import list_domains

# List available domains
domains = list_domains()
# {'aquisicao': 5, 'estoque': 3, 'liquidacao': 2, ...}
```

---

## Step 5: Embed & Deploy

Once `spec.yaml` is committed, deploy runs the embedding pipeline.

### Generate Embeddings

```bash
export GEMINI_API_KEY=your_key_here

python -m semantic_index.cli embed
```

This:
1. Reads `domains/spec.yaml`
2. Composes rich text for each concept and code anchor
3. Calls Gemini Embedding API to get vectors
4. Upserts vectors to `embedding_term` and `embedding_anchor` tables

### Query by Meaning

Once embeddings are stored, ask natural-language questions:

```bash
python -m semantic_index.cli semantic-query "How do we validate documents?"
```

Output:
```
SEMANTIC SEARCH: How do we validate documents?

1. anchor:DocumentValidator → validate_document (score: 0.923) [domain: documents_validation]
   Validates a document against its kit requirements. Checks OCR confidence, 
   extracts required fields...

2. term:DocumentValidation (score: 0.891) [domain: documents_validation]
   The process of ensuring that extracted document content is complete and 
   accurate before marking it ready for downstream processing...

3. anchor:ValidationRule → check_required_fields (score: 0.867) [domain: documents_validation]
   Ensures that all required fields are present in extracted data...
```

---

## Common Workflows

### Adding a New Feature

**1. Document the domain first (write dictionary entry)**

```markdown
### PaymentMethod

A payment instrument (card, bank transfer, etc.) associated with a customer.

- **Code equivalent:** PaymentMethod
- **Edges:**
  - contains → CardDetails or BankDetails
  - enforces → PaymentValidation
```

**2. Implement the code**

```python
class PaymentMethod:
    """Represents a payment instrument."""
    @biz: PaymentMethod | type: entity
```

**3. Extract and validate**

```bash
python -m semantic_index.cli extract
```

**4. Commit `domains/spec.yaml`**

```bash
git add domains/spec.yaml
git commit -m "feat: add PaymentMethod concept"
```

### Finding Code for a Concept

You wrote a dictionary entry but don't remember which function implements it?

```python
from semantic_index import load_domain_slice

concepts = load_domain_slice("aquisicao")
for concept in concepts:
    if concept['term'] == 'RemessaValidation':
        print(f"Found at {concept['file']}:{concept['line']}")
        print(f"Symbol: {concept['symbol']}")
```

### Enforcing Coverage (CI Gate)

In your CI/CD, fail the build if any concept is unanchored:

```bash
python -m semantic_index.cli validate
if [ $? -ne 0 ]; then
  echo "Validation failed: unanchored concepts found"
  exit 1
fi
```

### Updating an Existing Concept

**If you rename a function:**

```python
# OLD
def evaluate_kit_completion(...):
    @biz: KitType | type: rule

# NEW
def check_kit_completeness(...):
    @biz: KitType | type: rule
    # Tag stays the same, function name changes
```

Then re-extract:

```bash
python -m semantic_index.cli extract
# spec.yaml updates with new file location
```

---

## Troubleshooting

### "ERROR: tag references unknown concept 'Foo'"

**Cause**: You used `@biz: Foo | type: operation` but there's no `### Foo` in the dictionary.

**Fix**: Add it to `docs/vault/dictionary-business.md` or `docs/vault/dictionary-sys.md`.

### "WARNING: {N} orphan anchors"

**Cause**: You tagged code but the tag doesn't match any dictionary entry.

**Fix**: Check spelling. Tag names are case-sensitive and must match exactly.

### "FAIL: {N} unanchored terms"

**Cause**: Dictionary has concepts with zero code tags.

**Fix**: Either:
- Tag the concept in code, or
- Mark it `unanchorable: true` if it's abstract

### Postgres Connection Fails

**Make sure**:
- Postgres is running: `docker ps | grep postgres`
- `POSTGRES_PASSWORD` env var is set
- Port matches (default 5432)

```bash
# Test connection
psql -h localhost -U postgres -d postgres -c "SELECT 1"
```

---

## Next Steps

- **For agents/Claude Code**: See `.claude/plugins/superpowers/skills/` for MCP integration
- **For semantic search**: Set `GEMINI_API_KEY` and run `cli embed` 
- **For visualization**: Run `cli visualize` to generate an interactive HTML explorer

---

## API Reference

### CLI Commands

| Command | What It Does |
|---------|-------------|
| `lint` | Check dictionary syntax |
| `extract` | Build spec.yaml from dictionaries + tags |
| `validate` | Full validation (lint + extract + check for orphans) |
| `embed` | Generate Gemini embeddings + upsert to Postgres |
| `report` | Print coverage statistics |
| `visualize` | Generate interactive HTML ontology explorer |

### Python API

```python
from semantic_index import (
    CodeAnchor,
    DictionaryTerm,
    load_domain_slice,
    list_domains,
    semantic_search,
    format_domain_context,
)

# Get all domains
domains = list_domains()  # {'aquisicao': 5, ...}

# Get concepts in a domain
concepts = load_domain_slice("aquisicao")

# Format for display
text = format_domain_context("aquisicao", concepts)
print(text)

# Vector search (requires Postgres + embeddings)
results = semantic_search(
    "how do we handle payment errors?",
    top_k=5,
    types=["rule", "operation"]
)
```

---

**Questions?** See [`README.md`](README.md) for philosophy + architecture.
