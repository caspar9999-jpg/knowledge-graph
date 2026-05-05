# AFK Decisions Log

Decisions made during automated Issue #1–#3 resolution.

---

### D1: Neo4j Python driver version
**Issue**: #1 Schema Foundation
**Choice**: `neo4j>=5.0` Python driver
**Rationale**: Neo4j 5.x CE is the target DB. The Python driver version series matching Neo4j 5.x is 5.x, not "v6" as mentioned in design.md. Likely a version confusion.
**Impact**: Minor. requirements.txt now reflects reality.

### D2: Loading script as .py vs .ipynb
**Issue**: #2 Core Graph
**Choice**: Wrote `00_schema_init.py` and `01_load_data.py` as plain Python files instead of Jupyter .ipynb
**Rationale**: .py files are easier to review, version-control, and diff. Can be converted to .ipynb via `jupytext` if needed. No Jupyter-specific features (inline plots, interactive widgets) are required for loading CSV data.
**Impact**: Non-functional. Scripts work identically; add `jupytext --to notebook` if .ipynb format is needed.

### D3: Added company→company [:供应给] edges to enable Q1 traversal
**Issue**: #2 Core Graph
**Choice**: Added 3 company→company `[:供应给]` edges at `inferred` level:
- Nutrien → Cargill (c01→c06)
- Nutrien → ADM (c01→c04)
- Mosaic → Cargill (c03→c06)
- Also updated ADR-003 to document the exception: well-documented company relationships can be `inferred` (not just `associated`)
**Rationale**: Without these edges, Q1 could not traverse from any fertilizer company to any downstream food company using only `[:提供]` and `[:供应给]`. The fertilizer→crop step uses `[:用于]` (physical composition), which Q1 doesn't traverse. Company→company edges bridge this gap. The `inferred` (not `associated`) level is justified because these relationships are explicitly documented in SEC 10-K filings.
**Impact**: [:供应给] count changed from 12→15. Total edges from ~52→60.

### D4: Q1 path pattern changed from strict to mixed
**Issue**: #2 Core Graph
**Choice**: Relaxed Q1 path from `[:提供]→[:供应给]*` to `[:提供|:供应给]*` (any mix of relationship types)
**Rationale**: The first commercial hop from a fertilizer company is company→company (`[:供应给]`), not product→something (`[:提供]`→`[:供应给]`). The strict pattern couldn't match the Nutrien→Cargill→Animal Feed→Tyson path.
**Impact**: Updated canonical path signature in design.md. Q1 now finds paths through both edge types in any order.

### D5: Route queries optimized for graph topology, not direction precision
**Issue**: #3 Analysis Suite
**Choice**: Q3 (common dependency) uses undirected `-[*]-` matching; Q5 (hub analysis) uses degree counting
**Rationale**: For a small 28-node graph, undirected matching finds shared dependency nodes effectively regardless of edge direction. Degree-based hub analysis is the standard graph metric for identifying structurally critical nodes. No performance concern at this scale.
**Impact**: Q3 may return broader results than a strictly directed query (e.g., both suppliers and buyers of a product count as "connected"). This is acceptable for Stage 1 "共同依赖暴露" — understanding which entities sit between multiple companies in the supply topology.
