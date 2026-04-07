# Ontology Tool — Agent Instructions

## What this tool does

This tool bridges domain vocabulary and code. Two dictionaries define business and system concepts in plain language. Developers tag their code with `@biz`/`@sys` annotations that bind symbols to those dictionary terms. The extraction pipeline cross-validates both sides and produces a unified registry.

## Before writing any code

Read the domain documentation first. The pipeline is:

```
Domain Docs → Formal States → Tests → Implementation
```

If you don't understand the domain, you'll build the wrong thing.

## Dictionary maintenance

When creating or editing dictionary entries, follow the schema in `docs/domain-tagging-constitution.md` (Rule 6).

**Required fields** for every term:
- Description (prose after the H3 heading)
- Code equivalent (or `—` if none)

**Optional but recommended:**
- Aliases in codebase
- Aliases in conversation
- Edges (using the approved vocabulary — see Rule 12)
- Distinct from (disambiguation)

**Structure rules:**
- H1 = document title (one per file)
- H2 = category section
- H3 = term name — **always H3, no exceptions**

## Tagging code

When you modify a business-relevant function or class:

1. Check if the symbol represents a dictionary concept
2. If yes and it has no tag, add one
3. If the term doesn't exist in the dictionary, create it first — do NOT force a wrong term

**Tag format** (last line of the docstring):
```
@biz: <Term> | type: <type>
@sys: <Term> | type: <type>
```

**Valid types** (13 total):
- Structural: `entity`, `value-object`, `enum`
- Behavioral: `operation`, `query`, `calculation`, `rule`, `policy`, `workflow`
- Connective: `interface`, `event`, `mapping`
- Lifecycle: `state-machine`

**Do NOT tag:**
- Infrastructure (logging, HTTP clients, serialization)
- Framework plumbing (admin, routing, middleware)
- Test files
- Configuration (unless it represents a business enum)

## Validation

After making changes to dictionaries or tagged code, run:

```bash
python -m tools.ontology.cli extract          # lint + scan + build registry
python -m tools.ontology.cli validate --strict # catch orphan anchors
```

**Orphan anchors block commits.** An orphan anchor is a `@biz`/`@sys` tag referencing a term that doesn't exist in the dictionary. Fix it by either:
- Adding the missing term to the dictionary, or
- Correcting the tag to reference the right term

## Key rules

- The dictionary is the authority on **meaning**. The tag is the authority on **location**.
- A single term can have multiple types across different symbols (e.g., `Order` can be an `entity` on the class and a `query` on a read function).
- Edges must be declared on **both sides** (redundant by design).
- When a function resists clean tagging under one term, it probably represents its own concept — create a new dictionary entry.

## Reference

- `docs/USAGE.md` — developer guide with 5-step walkthrough
- `docs/domain-tagging-constitution.md` — full rules
- `docs/quick-reference.md` — one-page checklist
- `examples/example_tagged_module.py` — properly tagged Python module
