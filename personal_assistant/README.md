---
tags: [personal-assistant, agent, tools]
node_type: readme
is_session: false
layer: tools
nature: reference
status: active
version: 1.0.0
last_updated: 2026-04-07
---

# Personal Assistant

An agent-powered interface for querying your codebase using the semantic-index knowledge base.

**Related:**
- `/tools/semantic-index/` — The knowledge base (vocabulary + code extraction)

---

## What Is This?

The Personal Assistant turns the semantic-index into something useful:

```
User Question
    ↓
  "How does kit matching work?"
    ↓
Personal Assistant (backend + frontend)
    ├─ Query the semantic-index
    ├─ Retrieve definitions + code locations
    └─ Format a human-readable answer
    ↓
Answer
    ↓
"KitType is [definition].
 Implemented in: [file:line]
 Related: [linked concepts]"
```

---

## Structure

```
personal-assistant/
├── backend/                      ← Django backend
│   ├── api/                     ← REST API endpoints
│   ├── models.py                ← ORM (EmbeddingTerm, EmbeddingAnchor)
│   ├── query_engine.py          ← Query logic
│   ├── views.py                 ← Views
│   ├── urls.py                  ← URL routing
│   ├── admin.py                 ← Admin interface
│   ├── apps.py                  ← App config
│   ├── migrations/              ← Database migrations
│   ├── tests.py                 ← Tests
│   └── README.md                ← Backend documentation
│
├── frontend/                     ← UI (chat, explorer, etc.)
│   └── [TODO: your choice]
│
└── README.md                     ← This file
```

---

## Components

### Backend (`backend/`)

Django app that:
- **Persists** semantic vectors (ORM models)
- **Provides APIs** for querying the knowledge base
- **Integrates** with Claude agents

See `backend/README.md` for details.

### Frontend (`frontend/`)

Optional UI for:
- Chat interface to ask questions
- Interactive ontology explorer
- Admin dashboard

Currently empty. Add your UI here (web, CLI, mobile, etc.).

---

## How It Works

### 1. Semantic-Index Generates Vectors

```bash
# The semantic-index extracts from code + dictionaries
python -m tools.semantic_index.cli extract   # Build registry
python -m tools.semantic_index.cli embed     # Generate embeddings (Gemini API)
```

Result: EmbeddingTerm and EmbeddingAnchor tables populated with 768-dim vectors.

### 2. Personal Assistant Queries Vectors

```python
# Query: pgvector cosine similarity
SELECT * FROM embedding_term
WHERE vector <-> query_vector
ORDER BY similarity LIMIT 5
```

Result: Relevant terms + code anchors.

### 3. Format & Return Answer

```python
# Enrich with registry metadata
answer = {
    "term": "KitType",
    "definition": "...",
    "anchors": [
        { "symbol": "KitType", "file": "...", "line": 42 },
        { "symbol": "evaluate_kit_completion", "file": "...", "line": 122 }
    ],
    "related": ["DocumentTemplate", "KitCompletion"]
}
```

---

## Setup

### Prerequisites

- Docker (for Postgres + pgvector)
- Python 3.10+
- Django configured in `settings.py`

### 1. Create the app

```bash
# If new
python manage.py startapp personal_assistant tools.personal_assistant.backend

# Add to INSTALLED_APPS in settings.py:
INSTALLED_APPS = [
    ...
    'tools.personal_assistant.backend',
    ...
]
```

### 2. Migrate database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Populate embeddings

```bash
# From semantic-index
python -m tools.semantic_index.cli extract
python -m tools.semantic_index.cli embed
```

### 4. Verify

```bash
python manage.py shell
>>> from tools.personal_assistant.backend.models import EmbeddingTerm
>>> EmbeddingTerm.objects.count()
49  # Should match term count in semantic-index
```

---

## Usage

### Query from Django Shell

```python
from tools.personal_assistant.backend.models import EmbeddingTerm, EmbeddingAnchor
from tools.personal_assistant.backend.query_engine import QueryEngine

engine = QueryEngine()
answer = engine.query("How does kit matching work?")
print(answer.formatted())
```

### Query from CLI

```bash
python -m tools.personal_assistant.backend.cli query "How does kit matching work?"
```

### Query from API

```bash
curl "http://localhost:8000/api/semantic-index/query?q=How+does+kit+matching+work"
```

### Query from Agent

```python
# Claude agent has access to query_ontology() tool
result = query_ontology("How does kit matching work?")
# Returns structured data agent can format
```

---

## Development Roadmap

- [ ] Implement `query_engine.py` with pgvector integration
- [ ] Create REST API endpoints in `api/`
- [ ] Build CLI interface for local queries
- [ ] Integrate with Claude agent (MCP tool or skill)
- [ ] Optional: Create web UI for interactive explorer
- [ ] Add caching layer for performance
- [ ] Add authentication for multi-user scenarios

---

## Architecture Decision: Why Separate?

| Component | Reason |
|-----------|--------|
| **semantic-index** (extraction) | Runs independently (CLI, CI/CD, pre-commit hooks). No Django needed. |
| **personal-assistant** (interface) | Consumes the semantic-index. Runs in the web app context. |

This separation means:
- ✅ Extraction tool works anywhere (local, CI, Docker)
- ✅ Personal assistant is optional (can use semantic-index directly)
- ✅ Easy to swap implementations (replace backend with FastAPI, etc.)
- ✅ Clean separation of concerns

---

## Next Steps

1. Read `backend/README.md` for implementation details
2. Implement `query_engine.py` (see `../semantic-index/QUERY_SYSTEM.md`)
3. Create REST API endpoints or CLI interface
4. Integrate with Claude agent
5. Optional: Build UI in `frontend/`

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `backend/README.md` | Backend implementation details |
| `../semantic-index/README.md` | Knowledge base pipeline |
| `../semantic-index/QUERY_SYSTEM.md` | How to query the semantic-index |
| `../semantic-index/OVERVIEW.md` | Master system overview |
