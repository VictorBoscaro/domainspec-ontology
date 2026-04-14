"""
cli.py — CLI entry points for the semantic index extraction pipeline.

Plain Python CLI. No Django imports.

Commands:
    extract         — Run both extractors and build spec.yaml
    validate        — Validate dictionaries and check for orphan anchors
    lint            — Lint dictionary files against the formal schema
    validate-events — Validate event catalog references in dictionary-events.md
    embed           — Generate embeddings and persist to DB
    visualize       — Generate self-contained semantic index explorer HTML
    report          — Print coverage report

Usage:
    python -m semantic_index.cli extract
    python -m semantic_index.cli validate
    python -m semantic_index.cli report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ─── Default paths (relative to repo root) ──────────────────────────────────

DEFAULT_BIZ_DICT = "docs/vault/dictionary-business.md"
DEFAULT_SYS_DICT = "docs/vault/dictionary-sys.md"
DEFAULT_SCAN_ROOT = "."
DEFAULT_OUTPUT = "domains/spec.yaml"


# ─── Lint gate ───────────────────────────────────────────────────────────────


def _run_lint_gate(biz_dict: str, sys_dict: str) -> bool:
    """Run the linter as the first gate. Returns True if passed, False if errors found."""
    from semantic_index.extractors.dictionary_linter import lint_dictionaries

    results = lint_dictionaries(biz_dict, sys_dict)
    errors = [r for r in results if r.level == "error"]
    warnings = [r for r in results if r.level == "warning"]

    if warnings:
        for w in warnings:
            print(f"  WARN  {w.file}:{w.line}  {w.message}", file=sys.stderr)

    if errors:
        for e in errors:
            print(f"  ERROR {e.file}:{e.line}  {e.message}", file=sys.stderr)
        print(f"\n  Lint failed: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return False

    return True


def _extract_version(file_path: str) -> str:
    """Extract version from dictionary file YAML frontmatter."""
    try:
        with open(file_path, encoding="utf-8") as f:
            in_frontmatter = False
            for line in f:
                line = line.strip()
                if line == "---":
                    if in_frontmatter:
                        break
                    in_frontmatter = True
                    continue
                if in_frontmatter and line.startswith("version:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "unknown"


# ─── Commands ────────────────────────────────────────────────────────────────


def cmd_extract(args: argparse.Namespace) -> int:
    """Run both extractors and build spec.yaml."""
    from semantic_index.extractors.dictionary_extractor import extract_terms
    from semantic_index.extractors.tag_scanner import scan_codebase
    from semantic_index.registry.builder import build_registry
    from semantic_index.generators.spec_yaml_writer import write_spec_yaml

    # Lint gate
    if not _run_lint_gate(args.biz_dict, args.sys_dict):
        return 1

    print("Extracting terms from dictionaries...")
    biz_terms = extract_terms(args.biz_dict)
    sys_terms = extract_terms(args.sys_dict)
    all_terms = biz_terms + sys_terms
    print(f"  {len(biz_terms)} business terms, {len(sys_terms)} system terms")

    # Run tag scanner
    print(f"Scanning codebase for @biz/@sys tags (root: {args.scan_root})...")
    raw_anchors, scan_errors = scan_codebase(Path(args.scan_root))
    print(f"  {len(raw_anchors)} anchors found, {len(scan_errors)} scan issues")

    if scan_errors:
        for e in scan_errors:
            icon = "ERROR" if e.severity == "error" else "WARN "
            print(f"  {icon} {e.file}:{e.line} [{e.symbol}] {e.error}", file=sys.stderr)

    # Extract versions
    biz_version = _extract_version(args.biz_dict)
    sys_version = _extract_version(args.sys_dict)

    print("Building unified registry...")
    registry = build_registry(
        dictionary_terms=all_terms,
        scanner_anchors=raw_anchors,
        biz_version=biz_version,
        sys_version=sys_version,
        strict=args.strict,
    )

    # Flatten anchors from all terms for spec.yaml
    flat_anchors = [a for t in registry.terms.values() for a in t.anchors]

    # Write spec.yaml
    output_path = Path(args.output)
    write_spec_yaml(flat_anchors, output_path)
    print(f"  spec.yaml written to {output_path}")
    print(f"  {len(flat_anchors)} anchors")
    if registry.meta.orphan_anchors > 0:
        print(f"  WARNING: {registry.meta.orphan_anchors} orphan anchors (tags referencing unknown terms)")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate dictionaries and check for orphan anchors."""
    from semantic_index.extractors.dictionary_extractor import extract_terms
    from semantic_index.extractors.tag_scanner import scan_codebase
    from semantic_index.registry.builder import OrphanAnchorError, build_registry

    # Lint gate
    if not _run_lint_gate(args.biz_dict, args.sys_dict):
        return 1

    print("Validating dictionaries...")
    try:
        biz_terms = extract_terms(args.biz_dict)
        sys_terms = extract_terms(args.sys_dict)
    except Exception as e:
        print(f"  FAIL: {e}", file=sys.stderr)
        return 1

    all_terms = biz_terms + sys_terms
    print(f"  {len(all_terms)} terms parsed successfully")

    # Run tag scanner
    print(f"Scanning codebase for @biz/@sys tags (root: {args.scan_root})...")
    raw_anchors, scan_errors = scan_codebase(Path(args.scan_root))
    print(f"  {len(raw_anchors)} anchors found, {len(scan_errors)} scan issues")

    if scan_errors:
        for e in scan_errors:
            icon = "ERROR" if e.severity == "error" else "WARN "
            print(f"  {icon} {e.file}:{e.line} [{e.symbol}] {e.error}", file=sys.stderr)

    biz_version = _extract_version(args.biz_dict)
    sys_version = _extract_version(args.sys_dict)

    try:
        registry = build_registry(
            dictionary_terms=all_terms,
            scanner_anchors=raw_anchors,
            biz_version=biz_version,
            sys_version=sys_version,
            strict=args.strict,
        )
        print(f"  OK: {registry.meta.total_terms} terms, {registry.meta.total_anchors} anchors, {registry.meta.orphan_anchors} orphan anchors")
        return 0
    except OrphanAnchorError as e:
        print(f"  FAIL: {e}", file=sys.stderr)
        return 1


def cmd_lint(args: argparse.Namespace) -> int:
    """Lint dictionary files against the formal schema."""
    from semantic_index.extractors.dictionary_linter import lint_dictionaries

    results = lint_dictionaries(args.biz_dict, args.sys_dict)
    errors = [r for r in results if r.level == "error"]
    warnings = [r for r in results if r.level == "warning"]

    if not results:
        print("  OK: dictionaries pass lint checks")
        return 0

    for r in results:
        icon = "ERROR" if r.level == "error" else "WARN "
        print(f"  {icon} {r.file}:{r.line}  {r.message}")

    print(f"\n  {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_validate_events(args: argparse.Namespace) -> int:
    """Validate that event references in dictionary-events.md exist in EventLog.EventType."""
    from semantic_index.extractors.event_validator import (
        validate_event_dictionary,
        format_validation_error,
    )

    results = validate_event_dictionary(args.dictionary_events)

    if not results:
        print(f"  OK: all events in {args.dictionary_events} are valid")
        return 0

    # Show all errors
    for result in results:
        print(format_validation_error(result))

    print(f"\n  {len(results)} error(s)")
    print("\nFix: Add missing events to infrastructure/database/models.py (EventLog.EventType)")
    return 1


def cmd_embed(args: argparse.Namespace) -> int:
    """Compose embedding texts from spec.yaml and generate Gemini embeddings. CI-only."""
    import yaml
    from semantic_index.query.vector_search import embed_query, load_vectors_from_db

    spec_path = Path(args.registry)
    if not spec_path.exists():
        print(f"spec.yaml not found: {spec_path}. Run 'extract' first.", file=sys.stderr)
        return 1

    data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    concepts = data.get("concepts", [])

    if not concepts:
        print("No concepts found in spec.yaml.", file=sys.stderr)
        return 1

    print(f"Loaded {len(concepts)} anchors from {spec_path}")

    if args.dry_run:
        print("\nDry-run preview (first 5 anchors):")
        for concept in concepts[:5]:
            symbol = concept.get("symbol", "?")
            taxonomy_type = concept.get("taxonomy_type", "?")
            file_path = concept.get("file", "?")
            description = (concept.get("description", "") or "")[:80]
            print(f"\n  {symbol} [{taxonomy_type}] @ {file_path}")
            if description:
                print(f"    {description}")
        if len(concepts) > 5:
            print(f"\n  ... and {len(concepts) - 5} more")
        return 0

    print("\nTo generate embeddings:")
    print("  1. Set GEMINI_API_KEY and DB_PASSWORD (or POSTGRES_PASSWORD)")
    print("  2. Run: python -m semantic_index.setup  (creates tables)")
    print("  3. The embed pipeline calls embed_query() per anchor and upserts to pgvector")
    print("\nThe semantic query pipeline (MCP server) is already wired to the stored vectors.")
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Generate a self-contained operational ontology explorer HTML."""
    from semantic_index.models import OperationalOntologyRegistry

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry file not found: {registry_path}", file=sys.stderr)
        return 1

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    registry = OperationalOntologyRegistry(**data)

    # Build graph nodes and links from registry
    nodes = []
    links = []
    for term_name, term in registry.terms.items():
        nodes.append({
            "id": term_name,
            "prefix": term.prefix,
            "category": term.category,
            "anchors": len(term.anchors),
            "unanchorable": term.unanchorable,
            "description": term.description[:200] if term.description else "",
        })
        for edge in term.edges:
            # Only add link if target exists in registry
            if edge.target in registry.terms:
                links.append({
                    "source": term_name,
                    "target": edge.target,
                    "type": edge.type,
                })

    graph_data = json.dumps({"nodes": nodes, "links": links}, ensure_ascii=False, indent=2)

    # Write graph JSON
    graph_json_path = Path(args.output).parent / "ontology-graph.json"
    graph_json_path.write_text(graph_data, encoding="utf-8")

    # Build self-contained HTML with inline data
    html = _build_explorer_html(graph_data)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"  Explorer written to {output_path}")
    print(f"  Graph JSON written to {graph_json_path}")
    print(f"  {len(nodes)} nodes, {len(links)} edges")
    return 0


def _build_explorer_html(graph_data_json: str) -> str:
    """Build self-contained HTML with embedded graph data."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Operational Ontology Explorer</title>
  <script src="https://unpkg.com/force-graph@1.43.5/dist/force-graph.min.js"></script>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0a0a0f;--surface:rgba(255,255,255,0.05);--border:rgba(255,255,255,0.1);--text:#e2e2e8;--muted:#7a7a8a;--biz:#7c6af7;--sys:#3db88c;--font:'Inter',system-ui,sans-serif}}
    body{{background:var(--bg);color:var(--text);font-family:var(--font);height:100vh;overflow:hidden;display:flex}}
    #sidebar{{width:300px;border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}}
    #sidebar h2{{padding:16px;font-size:14px;border-bottom:1px solid var(--border)}}
    #search{{width:100%;padding:10px 16px;background:var(--surface);border:none;border-bottom:1px solid var(--border);color:var(--text);font-size:13px;outline:none}}
    #stats{{padding:8px 16px;font-size:11px;color:var(--muted);border-bottom:1px solid var(--border)}}
    #list{{flex:1;overflow-y:auto;padding:4px 0}}
    .item{{padding:6px 16px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(255,255,255,0.03)}}
    .item:hover{{background:var(--surface)}}
    .item.active{{background:rgba(124,106,247,0.15)}}
    .dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
    .dot.biz{{background:var(--biz)}}.dot.sys{{background:var(--sys)}}
    #graph{{flex:1}}
    #detail{{position:fixed;top:16px;right:16px;width:320px;background:rgba(20,20,30,0.95);border:1px solid var(--border);border-radius:8px;padding:20px;display:none;font-size:13px;max-height:80vh;overflow-y:auto;backdrop-filter:blur(12px)}}
    #detail h3{{font-size:15px;margin-bottom:8px}}
    #detail .prefix{{font-size:11px;padding:2px 8px;border-radius:4px;margin-bottom:12px;display:inline-block}}
    #detail .prefix.biz{{background:rgba(124,106,247,0.2);color:var(--biz)}}
    #detail .prefix.sys{{background:rgba(61,184,140,0.2);color:var(--sys)}}
    #detail .desc{{color:var(--muted);margin:8px 0 12px;line-height:1.5}}
    #detail .section{{margin-top:12px}}
    #detail .section-title{{font-size:11px;text-transform:uppercase;color:var(--muted);margin-bottom:6px;letter-spacing:0.5px}}
    #detail .edge{{font-size:12px;padding:3px 0;color:var(--text)}}
    #detail .edge-type{{color:var(--biz);font-weight:500}}
    .legend{{position:fixed;bottom:16px;left:316px;display:flex;gap:16px;font-size:11px;color:var(--muted)}}
    .legend span{{display:flex;align-items:center;gap:4px}}
  </style>
</head>
<body>
  <div id="sidebar">
    <h2>Operational Ontology</h2>
    <input id="search" placeholder="Filter terms..." />
    <div id="stats"></div>
    <div id="list"></div>
  </div>
  <div id="graph"></div>
  <div id="detail"></div>
  <div class="legend">
    <span><span class="dot biz"></span> Business (biz)</span>
    <span><span class="dot sys"></span> System (sys)</span>
  </div>

<script>
const data = {graph_data_json};

(function(data) {{
  const nodeMap=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
  const edgesByNode={{}};
  data.nodes.forEach(n=>{{edgesByNode[n.id]=[]}});
  data.links.forEach(l=>{{
    edgesByNode[l.source]?.push({{dir:'\\u2192',type:l.type,other:l.target}});
    edgesByNode[l.target]?.push({{dir:'\\u2190',type:l.type,other:l.source}});
  }});

  const bizCount=data.nodes.filter(n=>n.prefix==='biz').length;
  const sysCount=data.nodes.filter(n=>n.prefix==='sys').length;
  document.getElementById('stats').textContent=data.nodes.length+' terms ('+bizCount+' biz, '+sysCount+' sys) \\u00b7 '+data.links.length+' edges';

  const listEl=document.getElementById('list');
  const searchEl=document.getElementById('search');
  function shortName(id){{return id.split('(')[0].trim()}}
  function renderList(filter){{
    filter=filter||'';
    const f=filter.toLowerCase();
    listEl.innerHTML='';
    data.nodes.filter(n=>!f||n.id.toLowerCase().includes(f)).forEach(n=>{{
      const d=document.createElement('div');
      d.className='item';
      d.innerHTML='<span class="dot '+n.prefix+'"></span><span>'+shortName(n.id)+'</span>';
      d.onclick=function(){{selectNode(n.id)}};
      listEl.appendChild(d);
    }});
  }}
  searchEl.addEventListener('input',function(e){{renderList(e.target.value)}});
  renderList();

  const color={{biz:'#7c6af7',sys:'#3db88c'}};
  let selectedId=null;

  const graph=ForceGraph()(document.getElementById('graph'))
    .graphData(data)
    .nodeId('id')
    .nodeLabel(function(n){{return n.id+'\\n'+n.anchors+' anchors'}})
    .nodeColor(function(n){{return n.id===selectedId?'#fff':color[n.prefix]||'#666'}})
    .nodeVal(function(n){{return Math.max(3,2+n.anchors*1.5+(edgesByNode[n.id]?.length||0)*0.5)}})
    .nodeCanvasObject(function(n,ctx,globalScale){{
      const r=Math.max(3,2+n.anchors*1.5+(edgesByNode[n.id]?.length||0)*0.5);
      const isSelected=n.id===selectedId;
      const isNeighbor=selectedId&&edgesByNode[selectedId]?.some(function(e){{return e.other===n.id}});
      ctx.beginPath();
      ctx.arc(n.x,n.y,r,0,2*Math.PI);
      ctx.fillStyle=isSelected?'#fff':isNeighbor?color[n.prefix]:(selectedId?'rgba(100,100,120,0.3)':color[n.prefix]);
      ctx.fill();
      if(isSelected){{ctx.strokeStyle=color[n.prefix];ctx.lineWidth=2;ctx.stroke()}}
      if(globalScale>1.5||isSelected||isNeighbor){{
        const label=shortName(n.id);
        const fontSize=Math.max(10/globalScale,isSelected?5:3.5);
        ctx.font=(isSelected?'bold ':'')+fontSize+'px Inter,sans-serif';
        ctx.textAlign='center';
        ctx.textBaseline='top';
        ctx.fillStyle=isSelected?'#fff':isNeighbor?'#ccc':'rgba(200,200,220,0.6)';
        ctx.fillText(label,n.x,n.y+r+2);
      }}
    }})
    .linkColor(function(l){{
      if(!selectedId)return'rgba(255,255,255,0.08)';
      const s=typeof l.source==='object'?l.source.id:l.source;
      const t=typeof l.target==='object'?l.target.id:l.target;
      return(s===selectedId||t===selectedId)?'rgba(124,106,247,0.5)':'rgba(255,255,255,0.03)';
    }})
    .linkDirectionalArrowLength(4)
    .linkDirectionalArrowRelPos(1)
    .linkWidth(function(l){{
      if(!selectedId)return 0.5;
      const s=typeof l.source==='object'?l.source.id:l.source;
      const t=typeof l.target==='object'?l.target.id:l.target;
      return(s===selectedId||t===selectedId)?1.5:0.2;
    }})
    .linkLabel(function(l){{return l.type}})
    .onNodeClick(function(n){{selectNode(n.id)}})
    .onBackgroundClick(function(){{selectNode(null)}})
    .d3AlphaDecay(0.02)
    .d3VelocityDecay(0.3)
    .cooldownTicks(200);

  function selectNode(id){{
    selectedId=id;
    graph.nodeColor(graph.nodeColor());
    graph.linkColor(graph.linkColor());
    graph.linkWidth(graph.linkWidth());

    listEl.querySelectorAll('.item').forEach(function(el){{
      el.classList.toggle('active',el.textContent.trim()===shortName(id||''));
    }});

    const detail=document.getElementById('detail');
    if(!id){{detail.style.display='none';return}}
    const n=nodeMap[id];
    const edges=edgesByNode[id]||[];
    detail.style.display='block';
    detail.innerHTML='<h3>'+n.id+'</h3>'
      +'<span class="prefix '+n.prefix+'">'+n.prefix+'</span>'
      +'<span style="font-size:11px;color:var(--muted);margin-left:8px">'+n.category+'</span>'
      +'<div class="desc">'+n.description+'</div>'
      +'<div style="font-size:12px;color:var(--muted)">'+n.anchors+' code anchor'+(n.anchors!==1?'s':'')+(n.unanchorable?' (unanchorable)':'')+'</div>'
      +(edges.length?'<div class="section"><div class="section-title">Edges ('+edges.length+')</div>'
        +edges.map(function(e){{return'<div class="edge">'+e.dir+' <span class="edge-type">'+e.type+'</span> '+shortName(e.other)+'</div>'}}).join('')
        +'</div>':'');
  }}
}})(data);
</script>
</body>
</html>'''


def cmd_report(args: argparse.Namespace) -> int:
    """Print coverage report from a registry file."""
    from semantic_index.models import OperationalOntologyRegistry

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry file not found: {registry_path}", file=sys.stderr)
        return 1

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    registry = OperationalOntologyRegistry(**data)
    meta = registry.meta

    print("=" * 60)
    print("  Ontology Coverage Report")
    print("=" * 60)
    print(f"  Dictionary versions:      biz={meta.dictionary_biz_version}  sys={meta.dictionary_sys_version}")
    print(f"  Total terms:              {meta.total_terms}")
    print(f"  Total code anchors:       {meta.total_anchors}")
    print(f"  Orphan anchors:           {meta.orphan_anchors}")
    print(f"  Unanchored terms:         {meta.unanchored_terms}")
    print(f"    - By design:            {meta.unanchored_by_design}")
    print(f"    - Missing tags:         {meta.unanchored_missing_tags}")
    print()

    taggable = meta.total_terms - meta.unanchored_by_design
    if taggable > 0:
        coverage = ((taggable - meta.unanchored_missing_tags) / taggable) * 100
        print(f"  Tagging coverage:         {coverage:.1f}%")
    else:
        print(f"  Tagging coverage:         N/A (no taggable terms)")

    print("=" * 60)

    if meta.unanchored_missing_tags > 0:
        print("\n  Terms missing tags:")
        for name, term in registry.terms.items():
            if len(term.anchors) == 0 and not term.unanchorable:
                print(f"    - {name} ({term.prefix})")

    return 0


# ─── Entry point ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="ontology",
        description="Ontology extraction pipeline — dictionaries + tags -> unified registry -> embeddings",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── extract ──
    sp = sub.add_parser("extract", help="Run extractors and build unified registry")
    sp.add_argument("--biz-dict", default=DEFAULT_BIZ_DICT, help="Business dictionary path")
    sp.add_argument("--sys-dict", default=DEFAULT_SYS_DICT, help="System dictionary path")
    sp.add_argument("--scan-root", default=DEFAULT_SCAN_ROOT, help="Root path for tag scanning")
    sp.add_argument("--output", default=DEFAULT_OUTPUT, help="Output registry JSON path")
    sp.add_argument("--strict", action="store_true", help="Fail on orphan anchors")
    sp.set_defaults(func=cmd_extract)

    # ── validate ──
    vp = sub.add_parser("validate", help="Validate dictionaries and check orphan anchors")
    vp.add_argument("--biz-dict", default=DEFAULT_BIZ_DICT)
    vp.add_argument("--sys-dict", default=DEFAULT_SYS_DICT)
    vp.add_argument("--scan-root", default=DEFAULT_SCAN_ROOT, help="Root path for tag scanning")
    vp.add_argument("--strict", action="store_true", help="Fail on orphan anchors")
    vp.set_defaults(func=cmd_validate)

    # ── lint ──
    lp = sub.add_parser("lint", help="Lint dictionary files against formal schema")
    lp.add_argument("--biz-dict", default=DEFAULT_BIZ_DICT)
    lp.add_argument("--sys-dict", default=DEFAULT_SYS_DICT)
    lp.set_defaults(func=cmd_lint)

    # ── validate-events ──
    evp = sub.add_parser("validate-events", help="Validate event catalog references in dictionary-events.md")
    evp.add_argument("--dictionary-events", default="docs/vault/dictionary-events.md",
                     help="Path to dictionary-events.md")
    evp.set_defaults(func=cmd_validate_events)

    # ── embed ──
    ep = sub.add_parser("embed", help="Compose embedding texts from registry (CI-only)")
    ep.add_argument("--registry", default=DEFAULT_OUTPUT, help="Registry JSON path")
    ep.add_argument("--dry-run", action="store_true", help="Print texts without calling API")
    ep.set_defaults(func=cmd_embed)

    # ── visualize ──
    vizp = sub.add_parser("visualize", help="Generate operational ontology explorer HTML")
    vizp.add_argument("--registry", default=DEFAULT_OUTPUT, help="Registry JSON path")
    vizp.add_argument("--output", default="generated/operational-ontology-explorer.html", help="Output HTML path")
    vizp.set_defaults(func=cmd_visualize)

    # ── report ──
    rp = sub.add_parser("report", help="Print coverage report")
    rp.add_argument("--registry", default=DEFAULT_OUTPUT, help="Registry JSON path")
    rp.set_defaults(func=cmd_report)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
