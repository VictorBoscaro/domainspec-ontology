"""
setup.py — Infrastructure bootstrap for the ontology extraction pipeline.

Creates the pgvector extension and ontology tables in the existing Postgres.
Connects to the same database used by the Django application.

No Django imports. Uses psycopg2 directly.

Usage:
    python tools/ontology/setup.py
    python tools/ontology/setup.py --check     # verify without creating
    python tools/ontology/setup.py --drop       # drop all ontology tables (destructive)

Environment variables:
    POSTGRES_HOST     (default: localhost)
    POSTGRES_PORT     (default: 5433)
    POSTGRES_DB       (default: postgres)
    POSTGRES_USER     (default: postgres)
    POSTGRES_PASSWORD (required — no default)
"""

from __future__ import annotations

import argparse
import os
import sys


# ─── Connection ──────────────────────────────────────────────────────────────


def get_connection_params() -> dict:
    """Read Postgres connection params from environment."""
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        print("ERROR: POSTGRES_PASSWORD environment variable is required.")
        sys.exit(1)
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5433")),
        "dbname": os.environ.get("POSTGRES_DB", "postgres"),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": password,
    }


def connect():
    """Connect to Postgres. Returns a psycopg2 connection."""
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 is required. Install with: pip install psycopg2-binary")
        sys.exit(1)

    params = get_connection_params()
    print(f"Connecting to {params['host']}:{params['port']}/{params['dbname']}...")

    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        print("  Connected.")
        return conn
    except Exception as e:
        print(f"  FAILED: {e}")
        print()
        print("Make sure the Docker stack is running:")
        print("  docker compose -f docker-compose.dev.yml up -d postgres")
        sys.exit(1)


# ─── SQL Definitions ─────────────────────────────────────────────────────────
#
# Two ontologies, fully symmetric naming:
#
#   Conceptual ontology (document-level, vault graph):
#     conceptual_ontology_nodes        — one row per vault .md file
#     conceptual_ontology_edges        — document-to-document edges (derives-from, contradicts, etc.)
#     conceptual_ontology_embeddings   — document embeddings enriched with graph context
#
#   Operational ontology (term/code-level, extraction pipeline):
#     operational_ontology_terms       — one row per dictionary term
#     operational_ontology_anchors     — one row per tagged code symbol (FK → term)
#     operational_ontology_edges       — term-to-term edges from dictionary
#     operational_ontology_embeddings  — term + anchor embeddings for semantic search
#
#   Shared:
#     ontology_events                  — immutable event log for both ontologies
#

ENABLE_PGVECTOR = "CREATE EXTENSION IF NOT EXISTS vector;"

# ── Conceptual ontology ──────────────────────────────────────────────────────

CREATE_CONCEPTUAL_NODES = """
CREATE TABLE IF NOT EXISTS conceptual_ontology_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    node_type       TEXT NOT NULL,
    layer           TEXT NOT NULL,
    nature          TEXT NOT NULL,
    status          TEXT NOT NULL,
    veracidade      TEXT,
    conviccao       TEXT,
    tags            TEXT[],
    expires         DATE,
    last_updated    DATE,
    synced_at       TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_CONCEPTUAL_EDGES = """
CREATE TABLE IF NOT EXISTS conceptual_ontology_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path     TEXT NOT NULL REFERENCES conceptual_ontology_nodes(path),
    target_path     TEXT NOT NULL REFERENCES conceptual_ontology_nodes(path),
    edge_type       TEXT NOT NULL,
    description     TEXT,
    is_inverse      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_CONCEPTUAL_EMBEDDINGS = """
CREATE TABLE IF NOT EXISTS conceptual_ontology_embeddings (
    node_path       TEXT PRIMARY KEY
                    REFERENCES conceptual_ontology_nodes(path),
    text            TEXT NOT NULL,
    embedding       vector(768),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

# ── Operational ontology ─────────────────────────────────────────────────────

CREATE_OPERATIONAL_TERMS = """
CREATE TABLE IF NOT EXISTS operational_ontology_terms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term            TEXT NOT NULL UNIQUE,           -- canonical name (H3 heading)
    prefix          TEXT NOT NULL,                  -- 'biz' or 'sys'
    category        TEXT NOT NULL,                  -- H2 section in the dictionary
    description     TEXT NOT NULL,
    code_equivalent TEXT,                           -- primary code symbol name (nullable)
    aliases_code    TEXT[],
    aliases_conversation TEXT[],
    distinct_from   TEXT[],
    source_file     TEXT NOT NULL,                  -- dictionary file path
    source_line     INT NOT NULL,
    unanchorable    BOOLEAN NOT NULL DEFAULT FALSE,
    synced_at       TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_OPERATIONAL_ANCHORS = """
CREATE TABLE IF NOT EXISTS operational_ontology_anchors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term            TEXT NOT NULL REFERENCES operational_ontology_terms(term),
    symbol          TEXT NOT NULL,                  -- function/class/method name
    kind            TEXT NOT NULL,                  -- 'function', 'class', 'method'
    taxonomy_type   TEXT NOT NULL,                  -- 'rule', 'entity', 'operation', etc.
    file            TEXT NOT NULL,                  -- relative path from repo root
    line            INT NOT NULL,
    description     TEXT NOT NULL,
    synced_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (file, symbol)                           -- one anchor per symbol per file
);
"""

CREATE_OPERATIONAL_EDGES = """
CREATE TABLE IF NOT EXISTS operational_ontology_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_term     TEXT NOT NULL REFERENCES operational_ontology_terms(term),
    target_term     TEXT NOT NULL REFERENCES operational_ontology_terms(term),
    edge_type       TEXT NOT NULL,                  -- 'enforces', 'contains', 'produced-by', etc.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_OPERATIONAL_EMBEDDINGS = """
CREATE TABLE IF NOT EXISTS operational_ontology_embeddings (
    key             TEXT PRIMARY KEY,              -- 'term:KitType' or 'anchor:evaluate_kit_completion'
    source_type     TEXT NOT NULL,                  -- 'dictionary_term' or 'code_anchor'
    text            TEXT NOT NULL,                  -- composed text that was embedded
    embedding       vector(768),
    metadata        JSONB,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

# ── Shared ───────────────────────────────────────────────────────────────────

CREATE_ONTOLOGY_EVENTS = """
CREATE TABLE IF NOT EXISTS ontology_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor               TEXT NOT NULL,
    action              TEXT NOT NULL,
    target_document     TEXT NOT NULL,
    previous_level      TEXT,
    new_level           TEXT,
    reason              TEXT NOT NULL,
    source_session_id   TEXT,
    source_pr_url       TEXT,
    metadata            JSONB
);
"""

# ── Indexes ──────────────────────────────────────────────────────────────────

CREATE_INDEXES = [
    # Conceptual ontology
    "CREATE INDEX IF NOT EXISTS idx_con_nodes_node_type ON conceptual_ontology_nodes (node_type);",
    "CREATE INDEX IF NOT EXISTS idx_con_nodes_layer ON conceptual_ontology_nodes (layer);",
    "CREATE INDEX IF NOT EXISTS idx_con_nodes_status ON conceptual_ontology_nodes (status);",
    "CREATE INDEX IF NOT EXISTS idx_con_edges_source ON conceptual_ontology_edges (source_path);",
    "CREATE INDEX IF NOT EXISTS idx_con_edges_target ON conceptual_ontology_edges (target_path);",
    "CREATE INDEX IF NOT EXISTS idx_con_edges_type ON conceptual_ontology_edges (edge_type);",
    # Operational ontology
    "CREATE INDEX IF NOT EXISTS idx_op_terms_prefix ON operational_ontology_terms (prefix);",
    "CREATE INDEX IF NOT EXISTS idx_op_anchors_term ON operational_ontology_anchors (term);",
    "CREATE INDEX IF NOT EXISTS idx_op_anchors_taxonomy ON operational_ontology_anchors (taxonomy_type);",
    "CREATE INDEX IF NOT EXISTS idx_op_anchors_file ON operational_ontology_anchors (file);",
    "CREATE INDEX IF NOT EXISTS idx_op_edges_source ON operational_ontology_edges (source_term);",
    "CREATE INDEX IF NOT EXISTS idx_op_edges_target ON operational_ontology_edges (target_term);",
    "CREATE INDEX IF NOT EXISTS idx_op_embeddings_source_type ON operational_ontology_embeddings (source_type);",
    # Shared
    "CREATE INDEX IF NOT EXISTS idx_events_action ON ontology_events (action);",
    "CREATE INDEX IF NOT EXISTS idx_events_target ON ontology_events (target_document);",
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON ontology_events (timestamp);",
]

# ── Table registry (for check/drop) ─────────────────────────────────────────

# Order matters for DROP: embeddings/edges first (they have FKs), then nodes/terms
DROP_ALL = [
    "DROP TABLE IF EXISTS conceptual_ontology_embeddings CASCADE;",
    "DROP TABLE IF EXISTS conceptual_ontology_edges CASCADE;",
    "DROP TABLE IF EXISTS conceptual_ontology_nodes CASCADE;",
    "DROP TABLE IF EXISTS operational_ontology_embeddings CASCADE;",
    "DROP TABLE IF EXISTS operational_ontology_edges CASCADE;",
    "DROP TABLE IF EXISTS operational_ontology_anchors CASCADE;",
    "DROP TABLE IF EXISTS operational_ontology_terms CASCADE;",
    "DROP TABLE IF EXISTS ontology_events CASCADE;",
]

TABLES = [
    # Conceptual
    "conceptual_ontology_nodes",
    "conceptual_ontology_edges",
    "conceptual_ontology_embeddings",
    # Operational
    "operational_ontology_terms",
    "operational_ontology_anchors",
    "operational_ontology_edges",
    "operational_ontology_embeddings",
    # Shared
    "ontology_events",
]


# ─── Commands ────────────────────────────────────────────────────────────────


def cmd_setup(conn) -> int:
    """Create pgvector extension and all ontology tables."""
    cur = conn.cursor()

    print("\n1. Enabling pgvector extension...")
    cur.execute(ENABLE_PGVECTOR)
    print("   Done.")

    print("\n2. Creating ontology tables...")
    for name, sql in [
        # Conceptual ontology (nodes first, then edges/embeddings that reference them)
        ("conceptual_ontology_nodes", CREATE_CONCEPTUAL_NODES),
        ("conceptual_ontology_edges", CREATE_CONCEPTUAL_EDGES),
        ("conceptual_ontology_embeddings", CREATE_CONCEPTUAL_EMBEDDINGS),
        # Operational ontology (terms first, then anchors/edges/embeddings)
        ("operational_ontology_terms", CREATE_OPERATIONAL_TERMS),
        ("operational_ontology_anchors", CREATE_OPERATIONAL_ANCHORS),
        ("operational_ontology_edges", CREATE_OPERATIONAL_EDGES),
        ("operational_ontology_embeddings", CREATE_OPERATIONAL_EMBEDDINGS),
        # Shared
        ("ontology_events", CREATE_ONTOLOGY_EVENTS),
    ]:
        cur.execute(sql)
        print(f"   {name} — OK")

    print("\n3. Creating indexes...")
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)
    print(f"   {len(CREATE_INDEXES)} indexes — OK")

    print("\n--- Setup complete ---")
    return cmd_check(conn)


def cmd_check(conn) -> int:
    """Verify pgvector and all ontology tables exist."""
    cur = conn.cursor()
    print("\nChecking infrastructure...")

    # pgvector
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
    pgvector_ok = cur.fetchone() is not None
    print(f"  pgvector extension:  {'OK' if pgvector_ok else 'MISSING'}")

    # Tables
    all_ok = pgvector_ok
    for table in TABLES:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s;",
            (table,),
        )
        exists = cur.fetchone() is not None
        all_ok = all_ok and exists

        # Row count if exists
        if exists:
            cur.execute(f"SELECT COUNT(*) FROM {table};")  # noqa: S608
            count = cur.fetchone()[0]
            print(f"  {table:30s} OK  ({count} rows)")
        else:
            print(f"  {table:30s} MISSING")

    if all_ok:
        print("\n  All infrastructure ready.")
    else:
        print("\n  Some components are missing. Run: python tools/ontology/setup.py")

    return 0 if all_ok else 1


def cmd_drop(conn) -> int:
    """Drop all ontology tables. Destructive."""
    cur = conn.cursor()
    print("\nDropping all ontology tables...")
    for sql in DROP_ALL:
        cur.execute(sql)
        table_name = sql.split("DROP TABLE IF EXISTS ")[1].split(" ")[0]
        print(f"  {table_name} — dropped")
    print("\n  Done. Run setup again to recreate.")
    return 0


# ─── Entry point ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="ontology-setup",
        description="Bootstrap ontology infrastructure in the existing Postgres.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Verify infrastructure without creating anything",
    )
    parser.add_argument(
        "--drop", action="store_true",
        help="Drop all ontology tables (destructive)",
    )

    args = parser.parse_args()
    conn = connect()

    try:
        if args.drop:
            confirm = input("This will DROP all ontology tables. Type 'yes' to confirm: ")
            if confirm.strip().lower() != "yes":
                print("Aborted.")
                return
            sys.exit(cmd_drop(conn))
        elif args.check:
            sys.exit(cmd_check(conn))
        else:
            sys.exit(cmd_setup(conn))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
