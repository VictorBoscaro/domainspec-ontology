# Refactoring Notes: Tools Reorganization (2026-04-07)

## What Changed

The `/tools/` directory has been reorganized for better clarity and separation of concerns.

### Old Structure → New Structure

```
OLD:
/tools/
├── ontology/           ← Extraction pipeline
└── ontology_app/       ← Django models

NEW:
/tools/
├── semantic-index/               ← Renamed from ontology/
│   └── [all extraction code]
└── personal-assistant/           ← Renamed from ontology_app/
    ├── backend/                  ← Django ORM + APIs
    └── frontend/                 ← Optional UI
```

---

## Renamed Components

### `tools/ontology/` → `tools/semantic-index/`

**Why?** The extraction pipeline builds a semantic index (embeddings for vector search), not an "ontology" in the traditional sense.

**What moved:**
- `extractors/` — Dictionary + code tag extraction
- `registry/` — Registry builder
- `embeddings/` — Gemini API integration
- `cli.py` — All CLI commands
- `models.py` — Pydantic data models
- `docs/` — Developer guides + constitution
- `tests/` — Full test suite
- All documentation files (README, OVERVIEW, etc.)

**What to update in your code:**
```python
# OLD
from tools.ontology.models import DictionaryTerm
from tools.ontology.cli import extract

# NEW
from tools.semantic_index.models import DictionaryTerm
from tools.semantic_index.cli import extract
```

### `tools/ontology_app/` → `tools/personal-assistant/backend/`

**Why?** The Django app is not the ontology itself; it's an interface/backend for querying it. Structurally separating backend from potential frontend.

**What moved:**
- `models.py` — ORM models (EmbeddingTerm, EmbeddingAnchor)
- `views.py` — Django views
- `admin.py` — Django admin
- `apps.py` — App configuration
- `migrations/` — Database migrations

**What to update in Django settings:**
```python
# OLD
INSTALLED_APPS = [
    'tools.ontology_app',
]

# NEW
INSTALLED_APPS = [
    'tools.personal_assistant.backend',
]
```

**What to update in Django URLs:**
```python
# OLD
path('ontology/', include('tools.ontology_app.urls'))

# NEW
path('assistant/', include('tools.personal_assistant.backend.urls'))
```

---

## New Structure

```
/tools/
├── README.md                          ← Master navigation (NEW)
│
├── semantic-index/                    ← Knowledge base extraction
│   ├── README.md                      ← Start here
│   ├── OVERVIEW.md                    ← Master system overview
│   ├── ARCHITECTURE_DIAGRAM.md        ← Visual pipeline
│   ├── IMPLEMENTATION_STATUS.md       ← What's done/pending
│   ├── QUERY_SYSTEM.md                ← How to build query engine
│   ├── CLAUDE.md                      ← Agent instructions
│   ├── cli.py
│   ├── models.py
│   ├── extractors/
│   ├── registry/
│   ├── embeddings/
│   ├── docs/
│   ├── tests/
│   └── examples/
│
└── personal-assistant/                ← Agent interface & backend
    ├── README.md                      ← Start here
    ├── backend/                       ← Django ORM + APIs
    │   ├── README.md                  ← Backend docs
    │   ├── api/                       ← REST endpoints (TODO)
    │   ├── models.py                  ← ORM models
    │   ├── query_engine.py            ← Query logic (TODO)
    │   ├── views.py
    │   ├── urls.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── migrations/
    │   └── tests.py
    └── frontend/                      ← Optional UI (TODO)
```

---

## Import Updates Required

### Everywhere in the codebase

```bash
# Find all imports that need updating
grep -r "from tools.ontology" --include="*.py"
grep -r "import tools.ontology" --include="*.py"
grep -r "from tools.ontology_app" --include="*.py"
grep -r "import tools.ontology_app" --include="*.py"
```

**Bulk replacement:**
```bash
# In Python files
find . -type f -name "*.py" -exec sed -i '' \
  's/from tools\.ontology\./from tools.semantic_index./g' {} +
find . -type f -name "*.py" -exec sed -i '' \
  's/import tools\.ontology\./import tools.semantic_index./g' {} +

find . -type f -name "*.py" -exec sed -i '' \
  's/from tools\.ontology_app/from tools.personal_assistant.backend/g' {} +
find . -type f -name "*.py" -exec sed -i '' \
  's/import tools\.ontology_app/import tools.personal_assistant.backend/g' {} +
```

---

## Django Configuration Updates

### settings.py

```python
# OLD
INSTALLED_APPS = [
    ...
    'tools.ontology_app',
]

# NEW
INSTALLED_APPS = [
    ...
    'tools.personal_assistant.backend',
]
```

### urls.py

```python
# OLD
path('api/ontology/', include('tools.ontology_app.urls')),

# NEW
path('api/assistant/', include('tools.personal_assistant.backend.urls')),
```

### Database Migrations

Old app label: `ontology`
New app label: `personal_assistant`

**If you have existing migrations:**
```bash
# Option 1: Create a new migration to rename the app
python manage.py makemigrations --name rename_app_label

# Option 2: Reset (if fresh DB)
python manage.py migrate personal_assistant 0001_initial
```

---

## CLI Commands (No Changes)

```bash
# All semantic-index commands still work the same way
python -m tools.semantic_index.cli extract
python -m tools.semantic_index.cli validate
python -m tools.semantic_index.cli embed
python -m tools.semantic_index.cli report
python -m tools.semantic_index.cli visualize
```

---

## Documentation Navigation

**Old entry point:** `tools/ontology/README.md`
**New entry point:** `tools/README.md` (master nav)

Then:
- `tools/semantic-index/README.md` for knowledge base
- `tools/personal-assistant/README.md` for agent interface

---

## What Stayed the Same

- ✅ Extraction logic (extractors/)
- ✅ Registry builder (registry/)
- ✅ Embeddings client (embeddings/)
- ✅ All tests
- ✅ All documentation content (just reorganized)
- ✅ CLI commands
- ✅ ORM models
- ✅ Database schema

Only **names** and **structure** changed, not functionality.

---

## Migration Checklist

- [ ] Update imports in house_project/settings.py
- [ ] Update imports in house_project/urls.py
- [ ] Update any custom Django management commands
- [ ] Update test imports
- [ ] Run: `grep -r "tools.ontology" . --include="*.py"` to find remaining old imports
- [ ] Run: `python manage.py migrate` to apply any schema changes
- [ ] Run: `python -m tools.semantic_index.cli extract` to verify extraction works
- [ ] Read `tools/README.md` for new navigation structure
- [ ] Update any documentation that references `/tools/ontology/`

---

## If You Have Custom Code

**Extraction pipeline users:**
```python
# OLD
from tools.ontology.extractors.tag_scanner import scan_codebase
from tools.ontology.models import OperationalOntologyRegistry

# NEW
from tools.semantic_index.extractors.tag_scanner import scan_codebase
from tools.semantic_index.models import OperationalOntologyRegistry
```

**Django app users:**
```python
# OLD
from tools.ontology_app.models import EmbeddingTerm

# NEW
from tools.personal_assistant.backend.models import EmbeddingTerm
```

**CLI users:**
```bash
# No change!
python -m tools.semantic_index.cli extract
```

---

## Questions?

- **About the extraction pipeline?** → See `tools/semantic-index/README.md`
- **About the agent backend?** → See `tools/personal-assistant/README.md`
- **About the overall system?** → See `tools/README.md`

---

**Completed:** 2026-04-07
**Impact:** Folder structure only (no functional changes)
**Status:** Ready to use
