# Domain Tagging — Developer Guide

Quick start for annotating code with `@biz`/`@sys` tags and building the domain registry.

---

## What Is Domain Tagging?

Domain tagging connects your business code to your business vocabulary. You annotate classes and functions with `@biz` tags, and the pipeline makes the code's meaning explicit and queryable.

The result: agents and developers can navigate from a business concept ("evaluate kit completion") directly to the code that implements it — instead of grepping the entire codebase.

---

## The Quick Path: 5 Steps

### 1. Open a business-relevant function or class

Any symbol that implements, enforces, queries, or produces a dictionary concept.

```python
def evaluate_kit_completion(folder_docs, active_kits):
    pass
```

### 2. Make sure it has a docstring with a description

```python
def evaluate_kit_completion(folder_docs, active_kits):
    """Evaluate a folder's documents against active KitTypes using OR logic."""
    pass
```

### 3. Check the dictionary

Does `KitType` (or whatever concept this symbol represents) exist in `dictionaries/dictionary-business.md`?

- **Yes?** Go to step 4.
- **No?** Create it first. Add the definition, code equivalent, aliases, and edges. See [Dictionary Entry Schema](domain-tagging-constitution.md#rule-6--dictionary-entry-schema).

### 4. Add the tag as the last line of the docstring

Format: `@biz: <Term> | type: <type>`

```python
def evaluate_kit_completion(folder_docs, active_kits):
    """Evaluate a folder's documents against active KitTypes using OR logic.

    @biz: KitType | type: rule
    """
    pass
```

### 5. Run the pipeline

```bash
python -m tools.ontology.cli extract
python -m tools.ontology.cli validate --strict
```

Done. The registry is updated and validated.

---

## Choosing the Right Type

The `type` field classifies what role this symbol plays in the domain.

| Type | Use when... | Example |
|------|-----------|---------|
| `entity` | Persistent object with an identity | `class KitType(Base)` |
| `value-object` | Immutable data, defined by content | `@dataclass(frozen=True) class KitMatchResult` |
| `enum` | Fixed set of named values | `class FilterResult(Enum)` |
| `rule` | Boolean guard that must pass before an operation | `def evaluate_kit_completion()` |
| `query` | Read-only, no side effects | `def count_kits_by_type()` |
| `operation` | Action that changes state | `def register_template()` |
| `calculation` | Pure function deriving a value | `def calculate_match_score()` |
| `workflow` | Multi-step process coordinating operations | `def process_upload_pipeline()` |
| `interface` | API boundary | Class with `@property` methods |
| `event` | Notification that something happened | (Usually in dictionary, not tagged on code) |
| `mapping` | Data transformation between two shapes | (Usually in dictionary, not tagged on code) |
| `policy` | Decision logic selecting between behaviors | `def select_filter_strategy()` |
| `state-machine` | Formal entity lifecycle | (Advanced — usually not tagged on code) |

**Not sure?** Ask yourself:
- Does it *change state*? → `operation`
- Does it *return a read-only result*? → `query`
- Does it *check a condition*? → `rule`
- Is it an *object with identity*? → `entity`
- Is it *immutable data*? → `value-object`

---

## Building Your First Dictionary

The dictionary is a Markdown file with a simple structure. Each concept is an H3 heading with metadata bullets underneath.

### Minimal example

Create `dictionaries/dictionary-business.md`:

```markdown
# Business Dictionary

## Core Concepts

### Order

A customer request to purchase one or more products. Tracks items,
pricing, and fulfillment status through its lifecycle.

- **Code equivalent:** `Order`

### OrderStatus

The lifecycle state of an order — from placement through fulfillment
or cancellation.

- **Code equivalent:** `OrderStatus`
- **Edges:** `governs` → Order
```

That's enough to start tagging. Two terms, two entries, each with a description and code equivalent.

### Growing the dictionary

As you tag more code, the dictionary grows. Add optional fields when they help:

```markdown
### EligibilityFilter

A stateless, side-effect-free business rule that determines whether a
record may pass a specific eligibility check.

- **Code equivalent:** `EligibilityFilter`
- **Aliases in codebase:** `eligibility_criteria`, `filter_criteria`
- **Aliases in conversation:** `filtro de elegibilidade`, `filter gate`
- **Edges:** `enforces` → Remessa, `produces` → FilterResult
- **Distinct from:** FilterResult — the outcome of applying a filter, not the filter itself
```

### When a concept has no code

Some terms are abstract — financial concepts, domain-level ideas that exist
in conversation but not as a class or function. Mark them:

```markdown
### CreditRights

The underlying financial asset — the receivable itself. Broader than
any single model or table.

- **Code equivalent:** —
- **Unanchorable:** `true`
```

The pipeline sees `Unanchorable: true` and counts it as "unanchored by design"
rather than "missing tags" in the coverage report.

---

## Common Mistakes

### Tag as a comment instead of in the docstring

```python
# @biz: KitType | type: rule    ← drifts when code is reordered
def evaluate_kit_completion():
    pass
```

**Fix:** Put it inside the docstring.

### Term doesn't exist in the dictionary

```python
def process_stuff():
    """@biz: StuffProcessor | type: operation"""    ← not in the dictionary
```

**Fix:** Add `StuffProcessor` to the dictionary first. Then tag.

### Forcing the wrong term

```python
def cross_check_fields(extracted_data, installment_rows):
    """@biz: DocumentTemplate | type: rule"""    ← this is about CrossCheck, not DocumentTemplate
```

**Fix:** Create a new dictionary entry for the actual concept. Then tag with that.

### Tagging infrastructure

```python
def log_event_safe(event_name, payload):
    """@biz: EventLog | type: operation"""    ← infrastructure, not business logic
```

**Fix:** Don't tag utilities, logging, serialization, or framework plumbing.

### Inventing types outside the taxonomy

```python
def calculate_fee():
    """@biz: Fee | type: helper"""    ← 'helper' is not a valid type
```

**Fix:** Use one of the 13 types. If none fit, the concept needs clarification.

### Tag without a description

```python
def approve_remessa():
    """@biz: Remessa | type: operation"""    ← no description of what it does
```

**Fix:** Describe what the function does, then add the tag.

---

## Running the Pipeline

```bash
# Full extraction — lint, scan, build registry
python -m tools.ontology.cli extract

# Strict validation — fails on orphan anchors
python -m tools.ontology.cli validate --strict

# Coverage report
python -m tools.ontology.cli report

# Custom paths
python -m tools.ontology.cli extract \
    --biz-dict dictionaries/dictionary-business.md \
    --sys-dict dictionaries/dictionary-sys.md \
    --scan-root src/ \
    --output generated/ontology-registry.json
```

---

## In Code Review

- [ ] Every business symbol has a tag?
- [ ] Tag terms exist in the dictionary?
- [ ] Descriptions are present above the tag?
- [ ] Types are valid (one of 13)?
- [ ] No infrastructure tagged?

---

## Further Reading

- **[Constitution](domain-tagging-constitution.md)** — the full rules
- **[Quick Reference](quick-reference.md)** — compact checklist for tagging
