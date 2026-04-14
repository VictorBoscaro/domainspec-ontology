---
tags: [personal-assistant, backend, api]
node_type: readme
is_session: false
layer: tools
nature: reference
status: active
version: 1.0.0
last_updated: 2026-04-07
---

# Personal Assistant — Backend

Django backend that provides API endpoints for querying the semantic-index and orchestrating agent queries.

**Related:**
- `/tools/semantic-index/` — The knowledge base (extraction pipeline + registry)
- `/tools/personal-assistant/frontend/` — UI (if applicable)

---

## What This Does

This backend:
- **Persists embeddings** via Django ORM (EmbeddingTerm, EmbeddingAnchor models)
- **Provides query APIs** for searching the semantic-index
- **Orchestrates agent interactions** (Claude agent queries)
- **Manages infrastructure** (migrations, database schema)

---

## Structure

```
backend/
├── api/                          ← REST API endpoints (TODO)
├── models.py                     ← ORM models: EmbeddingTerm, EmbeddingAnchor
├── query_engine.py              ← Query logic (TODO)
├── views.py                      ← Django views (empty, ready to expand)
├── urls.py                       ← URL routing (TODO)
├── admin.py                      ← Django admin (TODO)
├── apps.py                       ← App configuration
├── migrations/                   ← Database migrations
└── tests.py                      ← Tests (TODO)
```

---

## Models

### EmbeddingTerm
Stores vector embeddings for dictionary terms (business/system concepts).

```python
class EmbeddingTerm(models.Model):
    term: str                    # Dictionary term name (e.g., "KitType")
    prefix: str                  # 'biz' or 'sys'
    composed_text: str          # Rich text from term metadata
    vector: ArrayField          # 768-dim embedding (pgvector)
    updated_at: datetime        # When embedding was last updated
```

### EmbeddingAnchor
Stores vector embeddings for code anchors (tagged functions/classes).

```python
class EmbeddingAnchor(models.Model):
    symbol: str                 # Code symbol name
    term: str                   # Dictionary term it implements
    file: str                   # Source file path
    line: int                   # Line number
    composed_text: str          # Rich text from symbol metadata
    vector: ArrayField          # 768-dim embedding (pgvector)
    updated_at: datetime        # When embedding was last updated
```

---

## Development

### Migrate the database
```bash
python manage.py makemigrations
python manage.py migrate
```

### Register models in admin
```python
# admin.py
from django.contrib import admin
from .models import EmbeddingTerm, EmbeddingAnchor

admin.site.register(EmbeddingTerm)
admin.site.register(EmbeddingAnchor)
```

### Build query APIs
```python
# api/views.py
from rest_framework import viewsets
from ..models import EmbeddingTerm, EmbeddingAnchor
from .serializers import EmbeddingTermSerializer, EmbeddingAnchorSerializer

class EmbeddingTermViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmbeddingTerm.objects.all()
    serializer_class = EmbeddingTermSerializer
```

### Create URL routing
```python
# urls.py
from django.urls import path, include
from rest_framework import routers
from . import api

router = routers.DefaultRouter()
router.register(r'terms', api.EmbeddingTermViewSet)
router.register(r'anchors', api.EmbeddingAnchorViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## Integration with Semantic-Index

The `semantic-index` tool generates embeddings and populates these tables:

```bash
# 1. Generate registry from code + dictionaries
python -m semantic_index.cli extract

# 2. Embed the registry (Gemini API)
python -m semantic_index.cli embed

# 3. Backend tables are now populated
# (embeddings automatically upserted to EmbeddingTerm / EmbeddingAnchor)
```

---

## Next Steps

- [ ] Create REST API endpoints in `api/`
- [ ] Register models in Django admin
- [ ] Build query engine (semantic search wrapper)
- [ ] Create serializers for ORM models
- [ ] Add authentication/authorization
- [ ] Write tests
- [ ] Document API endpoints

---

## Database Schema

```sql
-- Created by Django migrations
CREATE TABLE embedding_term (
    id BIGINT PRIMARY KEY,
    term VARCHAR(255) UNIQUE NOT NULL,
    prefix VARCHAR(10) NOT NULL,
    composed_text TEXT NOT NULL,
    vector vector(768),              -- pgvector column
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX embedding_term_term__idx ON embedding_term(term);
CREATE INDEX embedding_term_prefix__idx ON embedding_term(prefix);

CREATE TABLE embedding_anchor (
    id BIGINT PRIMARY KEY,
    symbol VARCHAR(255) UNIQUE NOT NULL,
    term VARCHAR(255),
    file VARCHAR(500) NOT NULL,
    line INTEGER NOT NULL,
    composed_text TEXT NOT NULL,
    vector vector(768),              -- pgvector column
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX embedding_anchor_symbol__idx ON embedding_anchor(symbol);
CREATE INDEX embedding_anchor_term__idx ON embedding_anchor(term);
CREATE INDEX embedding_anchor_file__idx ON embedding_anchor(file);
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `../semantic-index/README.md` | Knowledge base extraction pipeline |
| `../semantic-index/QUERY_SYSTEM.md` | How to query the semantic-index |
| `../semantic-index/OVERVIEW.md` | Master overview of the system |
