# Domain Tagging & Dictionary Constitution

> The enforceable rules for annotating code with `@biz` and `@sys` tags,
> maintaining the dictionary entries that support them, and structuring
> the dictionaries so the extraction pipeline can parse them.

---

## Objective

This constitution governs the **bridge between domain vocabulary and code**.
Two questions:

1. *"When I touch a domain-relevant symbol, what am I obligated to do so that
   the domain graph stays accurate and navigable?"*
2. *"When I add or edit a dictionary term, what structure must I follow so the
   extraction pipeline can parse it?"*

---

## Rule 1 — Every Domain Symbol Must Carry a Tag

A "domain symbol" is any class, function, or method whose name or purpose
appears in either dictionary:
- `dictionaries/dictionary-business.md` — business concepts → `@biz` tags
- `dictionaries/dictionary-sys.md` — system/infrastructure concepts → `@sys` tags

If the symbol implements, enforces, queries, or produces a dictionary concept,
it must be tagged with the corresponding prefix.

**Heuristic:** if someone would mention this symbol in a business conversation
("the cross-check failed", "check the kit_type count"), it is a `@biz`
symbol. If it is a system-level concept in the system dictionary
("the event log", "the filter registry"), it is a `@sys` symbol.

**What does NOT get tagged:**
- Infrastructure utilities not in the system dictionary (logging wrappers, HTTP clients)
- Framework plumbing (Django admin, URL routing, middleware)
- Configuration and constants (unless they represent a business enum)
- Test files

---

## Rule 2 — Tags Live Inside Docstrings

The tag is placed as the **last line** inside the Python docstring,
after the natural language description. Not a comment above the symbol.

```python
def evaluate_kit_completion(
    folder_docs: list[dict],
    active_kits: list["KitType"],
) -> KitMatchResult:
    """Evaluate a folder's documents against active KitTypes (OR logic).

    A kit is confirmed when all required docs are classified and
    template-matched in the folder.

    @biz: KitType | type: rule
    """
```

**Why docstrings, not comments:**
- A docstring is syntactically bound to its symbol — it cannot drift.
- The developer already writes (or should write) a docstring. One extra line.
- Docstrings are accessible via `help()`, IDE tooltips, and documentation
  generators. The tag inherits all of this for free.

**If the symbol has no docstring:** add one. The tag requires a docstring
to exist. This creates positive pressure to document business code.

---

## Rule 3 — The Tag Schema Is Two Fields

```
@biz: <Term> | type: <type>
@sys: <Term> | type: <type>
```

| Field    | Required | What it is |
|----------|----------|------------|
| `prefix` | always   | `@biz` for business concepts, `@sys` for system concepts |
| `Term`   | always   | The dictionary concept this symbol belongs to |
| `type`   | always   | The taxonomic classification from the domainspec taxonomy |

Two fields after the prefix. Nothing else. No file paths, no table names, no
event names. If metadata is derivable from the code itself, it does not go
in the tag.

---

## Rule 4 — The Term Must Exist in the Dictionary

The `Term` in a tag must match an entry in the corresponding dictionary:
- `@biz` tags → `dictionaries/dictionary-business.md`
- `@sys` tags → `dictionaries/dictionary-sys.md`

If no entry exists, the developer must create one before tagging (see Rule 8).

**The dictionary is the authority on meaning. The tag is the authority on
location.** These are complementary — neither replaces the other.

**The dictionary is a superset of taggable concepts.** Not every dictionary term
will have tags in the code. Some concepts are purely conceptual or exist only
at the field level. These terms are marked `Unanchorable: true` in the
dictionary (see Rule 6) and are not expected to have code tags.

---

## Rule 5 — The Type Must Be a Valid Taxonomy Type

The `type` field must be one of the 13 domainspec taxonomy types:

### Structural — What things exist

| Type | Definition |
|------|-----------|
| `entity` | Object with unique identity that persists over time |
| `value-object` | Immutable concept defined entirely by its content, no identity |
| `enum` | Fixed, finite set of named values |

### Behavioral — What happens

| Type | Definition |
|------|-----------|
| `operation` | Business action that changes state |
| `query` | Read that returns data without side effects |
| `calculation` | Pure function that derives a value from inputs |
| `rule` | Business constraint that must hold for an operation to proceed |
| `policy` | Decision logic that selects between behaviors at runtime |
| `workflow` | Multi-step process coordinating multiple operations |

### Connective — How things communicate

| Type | Definition |
|------|-----------|
| `interface` | API boundary exposing operations and queries |
| `event` | Notification that something happened |
| `mapping` | Field-by-field data transformation between two shapes |

### Lifecycle — How things evolve

| Type | Definition |
|------|-----------|
| `state-machine` | Formal specification of how an entity moves through states |

**A single dictionary term can have multiple types across different symbols.**
For example, `FilterResult` can be an `enum` (the TextChoices class) and
a `value-object` (a dataclass). The type belongs to the *symbol*, not the *term*.

---

## Rule 6 — Dictionary Entry Schema

Every dictionary entry must follow a structured format so the extraction
pipeline can parse it.

### Required fields

Every term **must** have these. The dictionary linter blocks commits if any
are missing.

| Field | Format | Example |
|-------|--------|---------|
| **Description** | Prose paragraph(s) immediately after the H3 heading | _"A stateless, side-effect-free business rule that..."_ |
| **Code equivalent:** | Primary code symbol name, or `—` if none | `- **Code equivalent:** \`EligibilityFilter\`` |

### Optional fields

| Field | Format | Example |
|-------|--------|---------|
| **Aliases in codebase:** | Comma-separated identifiers | `eligibility_criteria, filter_criteria` |
| **Aliases in conversation:** | Comma-separated natural language names | `filtro de elegibilidade, filter gate` |
| **Edges:** | Typed relationships using the edge vocabulary (see Rule 12) | `enforces → Remessa, produces → FilterResult` |
| **Distinct from:** | Terms this concept is explicitly not | `Distinct from: FilterResult` |
| **Unanchorable:** | `true` if this term has no taggable code symbol | `- **Unanchorable:** \`true\`` |
| **See also:** | Cross-references to related terms or documents | `See also: CrossCheck` |

### Unanchorable terms

Some dictionary terms represent abstract concepts or field-level value-objects
with no direct code representation. Mark these with `Unanchorable: true`.
The extraction pipeline classifies them as "unanchored by design" rather than
"missing tags" in the coverage report.

### Example entry

```markdown
### EligibilityFilter

A stateless, side-effect-free business rule that determines whether a remessa
or its installments may pass a specific eligibility check for a given fund.
Each filter is a subclass of the abstract EligibilityFilter base class.

- **Code equivalent:** `EligibilityFilter`
- **Aliases in codebase:** `eligibility_criteria`, `filter_criteria`
- **Aliases in conversation:** `filtro de elegibilidade`, `filter gate`
- **Edges:** `enforces` → Remessa, `produces` → FilterResult
- **Distinct from:** FilterResult — the outcome of applying a filter, not the filter itself
```

---

## Rule 7 — Edges Are Redundant

Both sides of a relationship declare the edge. Intentional — it maximizes
information for whoever is reading either entry.

- **EligibilityFilter** declares: `produces` → FilterResult
- **FilterResult** declares: `produced-by` ← EligibilityFilter

Reading any single dictionary entry gives you the full picture of its
connections without chasing the other side.

---

## Rule 8 — Missing Terms Must Be Created Before Tagging

If a developer encounters a function that resists tagging under existing
dictionary terms, the dictionary is missing a concept.

1. Stop. Do not force the tag under a wrong term.
2. Identify what business concept the function actually represents.
3. Add the term to the dictionary with: definition, code equivalent,
   aliases, "distinct from" disambiguation, and edges.
4. Then tag the function with the new term.

**Many apparent multi-term problems are actually missing vocabulary.** When a
function seems to belong to two terms, the right answer is often a new concept.

---

## Rule 9 — Tag on Edit

Tags are added **when a developer touches a business-relevant file**, not
through a big-bang backfill. The most-edited files get tagged first naturally.

When you modify a business-relevant function that has no tag, add one.
This is part of the edit, not a separate task.

**Exception:** if the function resists tagging, flag it. Do not add a wrong
tag just to satisfy this rule.

---

## Rule 10 — Infrastructure Does Not Get Tagged

Only code that represents a **business concept** gets tagged.

| Tagged | Not tagged |
|--------|-----------|
| `EligibilityFilter` (business rule) | `log_event_safe()` (infrastructure) |
| `FilterResult` (business enum) | `BaseRepository` (framework plumbing) |
| `evaluate_kit_completion` (domain logic) | `celery_app.task` (task decorator) |
| `cross_check_fields` (domain rule) | `serialize_response()` (serialization) |

**Heuristic:** if the symbol's name or purpose would appear in the dictionary,
it gets tagged. If it wouldn't, it shouldn't.

---

## Rule 11 — Dictionary Structure

The dictionaries use Markdown heading levels as structural markers. The
extraction pipeline depends on this structure.

- **H1** (`#`) — document title (one per file)
- **H2** (`##`) — category section (groups related terms by domain or concern)
- **H3** (`###`) — term name (one per dictionary entry)

**Terms are always H3 headings.** No other heading level is valid. The
extractor records the H2 section as the term's `category` field.

---

## Rule 12 — Edge Vocabulary

Edges declared in dictionary entries must use verbs from the approved vocabulary.

### Forward edges (A → B)

| Edge | Connects | Answers |
|------|----------|---------|
| `performs` | Entity → Operation | What can this actor do? |
| `produces` | Operation → Event | What happens after this runs? |
| `enforces` | Rule → Operation | What must hold for this to proceed? |
| `calculates` | Calculation → Operation | What values does this derive? |
| `transitions` | Event → State Machine | What state changes does this trigger? |
| `exposes` | Interface → Operation/Query | What does this API surface? |
| `orchestrates` | Workflow → Operation[] | What steps does this coordinate? |
| `applies` | Policy → Operation | What strategies govern this? |
| `maps` | Mapping → Entity/Interface | What transformations exist here? |
| `contains` | Entity → Value Object | What value types does this embed? |
| `queries` | Query → Entity | What data does this read? |
| `emits` | Entity → Event | What events does this announce? |

### Inverse edges (B ← A)

| Forward | Inverse |
|---------|---------|
| `performs` | `performed-by` |
| `produces` | `produced-by` |
| `enforces` | `enforced-by` |
| `calculates` | `calculated-by` |
| `transitions` | `transitioned-by` |
| `exposes` | `exposed-by` |
| `orchestrates` | `orchestrated-by` |
| `applies` | `applied-by` |
| `maps` | `mapped-by` |
| `contains` | `contained-in` |
| `queries` | `queried-by` |
| `emits` | `emitted-by` |

---

## Rule 13 — Automated Enforcement

The extraction pipeline (`tools/ontology/`) automatically enforces several
rules. These checks run in the pre-commit hook and in CI.

| Rule | What the pipeline checks |
|------|-------------------------|
| Rule 4 | Every tag references a term that exists in the dictionary. Orphan anchors block the commit. |
| Rule 5 | Every tag type is one of the 13 valid taxonomy types. |
| Rule 6 | Dictionary terms have required fields. Missing fields block the commit. |
| Rule 11 | Dictionary terms are H3 headings. Structural violations block the commit. |

**Not enforced automatically (human review):**
- Rule 1 — whether a business symbol is missing a tag
- Rule 7 — whether edges are declared on both sides
- Rule 8 — whether missing terms were created before tagging
- Rule 9 — whether the developer tagged on edit
- Rule 10 — whether infrastructure was incorrectly tagged

---

## Anti-Patterns

```python
# ❌ 1. Tag as a comment, not in the docstring
# @biz: KitType | type: entity     ← drifts when code is reordered
class KitType(Base):
    ...

# ❌ 2. Term not in dictionary
def process_stuff():
    """@biz: StuffProcessor | type: operation"""   ← term doesn't exist

# ❌ 3. Wrong term to avoid multi-term problem
def cross_check_fields(...):
    """@biz: DocumentTemplate | type: rule"""   ← function is about CrossCheck

# ❌ 4. Tagging infrastructure
def log_event_safe(...):
    """@biz: EventLog | type: operation"""   ← infrastructure, not business

# ❌ 5. Inventing types outside the taxonomy
def calculate_fee(...):
    """@biz: Fee | type: helper"""   ← 'helper' is not a taxonomy type

# ❌ 6. Tag without a docstring description
def approve_remessa(...):
    """@biz: Remessa | type: operation"""   ← no description
```

---

## Quick Code Review Checklist

When reviewing a PR that touches business-relevant code:

- [ ] Every business symbol has a `@biz` or `@sys` tag in its docstring
- [ ] The `Term` exists in the dictionary
- [ ] The `type` is a valid taxonomy type from the 13-type catalog
- [ ] The docstring has a natural language description above the tag
- [ ] No infrastructure symbols are tagged
- [ ] New dictionary entries have: definition, code equivalent, aliases, edges
- [ ] Edges on new entries are declared on both sides
- [ ] No tags forced under wrong terms to avoid multi-term problems
