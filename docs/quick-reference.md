# Domain Tagging — Quick Reference

Compact checklist. Full rules in [domain-tagging-constitution.md](domain-tagging-constitution.md).

---

## When to Tag

- When you modify a **business-relevant** function, class, or method
- When the symbol's name/purpose appears or should appear in the dictionary
- **NOT** infrastructure code (logging, HTTP clients, framework plumbing)
- **NOT** test files or configuration

**Heuristic:** Would someone mention this symbol in a business conversation? Tag it.

---

## Before Tagging — Verify Term Exists

The term must exist in:
- `dictionaries/dictionary-business.md` for `@biz` tags
- `dictionaries/dictionary-sys.md` for `@sys` tags

**If the term doesn't exist:**
1. Stop. Do not force a wrong term.
2. Create the dictionary entry first (definition, code equivalent, aliases, edges).
3. Then tag the code.

---

## Tag Format

Place in the **docstring as the last line**, after the description:

```python
def evaluate_kit_completion(folder_docs, active_kits):
    """Evaluate a folder's documents against active KitTypes (OR logic).

    A kit is confirmed when all required docs are classified and template-matched.

    @biz: KitType | type: rule
    """
```

**Schema:** `@biz: <Term> | type: <type>` or `@sys: <Term> | type: <type>`

---

## Valid Types

### Structural (what exists)
- `entity` — object with unique identity
- `value-object` — immutable, defined by content
- `enum` — fixed finite set

### Behavioral (what happens)
- `operation` — action that changes state
- `query` — read without side effects
- `calculation` — pure function deriving a value
- `rule` — business constraint
- `policy` — decision logic selecting behaviors
- `workflow` — multi-step process

### Connective (how things communicate)
- `interface` — API boundary
- `event` — notification that something happened
- `mapping` — data transformation

### Lifecycle (how things evolve)
- `state-machine` — formal state transitions

---

## Anti-Patterns

```python
# ❌ Tag as comment, not docstring
# @biz: KitType | type: entity
class KitType(Base): ...

# ❌ Term not in dictionary
def process_stuff():
    """@biz: StuffProcessor | type: operation"""

# ❌ Wrong term to avoid multi-term problem
def cross_check_fields():
    """@biz: DocumentTemplate | type: rule"""  # Actually about CrossCheck

# ❌ Tagging infrastructure
def log_event_safe():
    """@biz: EventLog | type: operation"""

# ❌ Invalid taxonomy type
def calculate_fee():
    """@biz: Fee | type: helper"""

# ❌ Tag without description
def approve_remessa():
    """@biz: Remessa | type: operation"""
```

---

## Review Checklist

- [ ] Symbol is business-relevant (not infrastructure)
- [ ] Term exists in the correct dictionary
- [ ] Type is one of the 13 valid taxonomy types
- [ ] Docstring has description above the tag
- [ ] Tag is the last line of the docstring
- [ ] No tags forced under wrong terms
