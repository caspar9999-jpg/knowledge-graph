# PRD: Supply Chain Knowledge Graph — Stage 1 Dependency Backbone

## Problem Statement

Analysts investigating supply chain risk currently rely on ad-hoc spreadsheets, siloed databases, or manual research. There is no unified, queryable data model that captures both **commercial dependency** (who supplies what to whom) and **physical composition** (what inputs go into which products) across multi-hop chains. A fertilizer disruption, for example, ripples through corn processors, feed producers, meat companies, and food manufacturers — but no single system can trace that propagation today using public information alone.

## Solution

Build a Neo4j knowledge graph that serves as a **unified data底座 (data base)** for supply chain analysis. Stage 1 covers the fertilizer → food chain with 28 nodes (9 Companies, 6 Commodities, 13 Products) and 52 relationships across three edge types: `[:提供]` (company produces product), `[:供应给]` (commercial supply), and `[:用于]` (physical composition). The graph intentionally separates facts from interpretation — it stores what is known, and leaves analysis to the query layer.

Five verification queries prove the model supports multiple analysis paradigms: commercial dependency traversal, physical composition traversal, common dependency detection, alternate supplier identification, and hub node analysis.

## User Stories

1. As a supply chain analyst, I want to trace commercial dependencies from a fertilizer company to a food company, so that I can identify which downstream brands are exposed to an upstream disruption.
2. As a risk analyst, I want to see which commodities are physically composed into which products, so that I can assess raw material concentration risk in finished goods.
3. As a procurement strategist, I want to find all companies that depend on the same intermediate product or commodity, so that I can assess common-mode failure points in the supply network.
4. As a sourcing analyst, I want to find all companies that provide a given product, so that I can evaluate alternate supply options when a primary supplier is disrupted.
5. As a network analyst, I want to identify hub nodes by in-degree and out-degree, so that I can prioritize monitoring of the most structurally critical entities.
6. As a data curator, I want a repeatable classification rule for Commodity vs Product, so that every node gets the correct label consistently across the dataset.
7. As a data curator, I want confidence levels on every commercial supply edge, so that query results reflect the strength of evidence behind each relationship.
8. As a data curator, I want a documented source hierarchy (regulatory filings > news > estimates), so that conflicting information is resolved consistently.
9. As a data curator, I want clear rules for when to use `[:用于]` vs `[:供应给]`, so that physical composition and commercial supply are never conflated.
10. As a developer extending this graph, I want the data loaded from CSV files with defined schemas, so that I can reproduce and audit the graph build from source.
11. As a developer extending this graph, I want all nodes to have unique ID constraints enforced at the database level, so that duplicate entities are impossible.
12. As a developer extending this graph, I want a validation script that checks for self-loops, missing confidence values, and orphan products, so that data quality is enforced automatically.
13. As a downstream project maintainer (Event project), I want Company nodes to carry geographic attributes (hq_country, operating_countries), so that I can spatially match events to affected entities without model migration.
14. As a downstream project maintainer (Event project), I want relationship edges to carry valid_from/valid_until timestamps, so that I can filter out expired dependencies during historical impact analysis.
15. As a downstream project maintainer (Process project), I want Product nodes to carry a category attribute, so that I can attach product equivalence classes (`[:归类于]`) without schema changes.
16. As a new team member, I want a CONTEXT.md glossary that defines all domain terms precisely, so that I can onboard without ambiguity about what each concept means.
17. As a new team member, I want a design.md that records all architecture decisions (ADRs) with rationales, so that I understand why the model looks the way it does.

## Implementation Decisions

### Modules

- **M1: Schema & Constraints** — Cypher scripts that create uniqueness constraints on node IDs, indexes on frequently-queried properties, and data quality validation queries (no self-loops, no missing confidence, no orphan products).
- **M2: Data Pipeline** — Jupyter notebook orchestrating LOAD CSV import from 7 structured CSV files (companies, commodities, products, and 3 edge types), with post-load verification of node/edge counts.
- **M3: Verification Query Suite** — Five parameterized Cypher query files that serve as acceptance tests: dependency chain traversal, composition chain traversal, common dependency detection, alternate supplier identification, and hub analysis. Each query enforces confidence filtering and maximum traversal depth.
- **M4: Data Sourcing Guide** — Markdown document mapping each `[:供应给]` edge to its specific public data source, with the source hierarchy rule (SEC filings > news > estimates).
- **M5: Application Entry Points** — Python dependency manifest (requirements.txt) for the Jupyter pipeline and Neo4j driver.

### Architecture Decisions

- **Schema-first development**: Uniqueness constraints and indexes loaded before any data. Edge data loaded incrementally thereafter.
- **Verification queries as acceptance tests**: If a query returns unexpected results, fix the data or model — never alter the query to fit broken data.
- **Confidence model**: `[:供应给]` edges carry `confirmed` (L1, rigid dependency), `inferred` (L2, business structure inference, including all Commodity→Company edges), or `associated` (L3, company-company with known transactions). Default filter: `confirmed` + `inferred`.
- **[:用于] vs [:供应给] separation**: Physical composition always uses `[:用于]`; commercial supply always uses `[:供应给]`. Same node pair may carry both when semantics differ (e.g., Corn→Ethanol `[:用于]` and Corn→ADM `[:供應给]`).
- **[:用于] sources**: Any node serving as a physical input (Input Material role), not only Commodity-labeled nodes. Product→Product `[:用于]` is valid (e.g., Corn Starch→Processed Food).
- **No self-loops**: No relationship where source equals target.
- **Entity list is locked**: 9 Companies, 6 Commodities, 13 Products — exactly 28 nodes.
- **Growers/farmers excluded**: Commodity nodes serve as the upstream aggregation boundary.
- **Neo4j Community Edition 5.x**: Single database instance. Adequate for ~28-node graph.

### Data Schema

**Node CSVs**:
- `companies.csv`: id, name, type, hq_country (required), hq_region, operating_countries, external_id
- `commodities.csv`: id, name, major_producing_countries
- `products.csv`: id, name, category

**Edge CSVs**:
- `edges_provide.csv`: company_id, product_id, gross_margin_pct, revenue_share_pct, source
- `edges_supply.csv`: from_id, to_id, confidence (required), valid_from, valid_until, source
- `edges_used_in.csv`: from_id, to_id, valid_from, valid_until, source

### Canonical Traversal Signatures

| Analysis | Path | Constraint |
|----------|------|------------|
| Commercial dependency | `(C)-[:提供]→(P)-[:供应给]→..→(C)` | Every `[:提供]`→`[:供应给]` switch passes through a Product node |
| Physical composition | `(M)-[:用于]→(P)-[:用于]→(P)..` | Source can be Commodity or Product in Input Material role |
| Mixed traversal | `(C)-[:提供]→(P)-[:用于]→..→(P)-[:提供]→(C)` | Relationship type switch always passes through entity node |
| Common dependency | `(c1)-[*..]→(m)←[*..]-(c2)` | Direction-agnostic topology match |
| Alternate supply | `(p)←[:提供]-(c)` | Only existing `[:提供]` edges |

## Testing Decisions

- **What makes a good test**: Tests validate external observable behavior (query output, constraint violations, data counts), not internal implementation (Cypher syntax details, notebook cell order).
- **M1 testing**: Run constraint creation against empty Neo4j. Verify constraints reject duplicate IDs and null required fields. Run validation queries after data load and assert zero violations.
- **M2 testing**: Assert node counts (9 Companies, 6 Commodities, 13 Products) and edge counts (22 provide, 18 used_in, 12 supply). Assert no orphan nodes exist.
- **M3 testing**: Run each verification query and assert non-empty results. For the dependency chain query (Q1), assert a path exists from Nutrien to Nestlé via Potash→Corn→Corn Starch. For alternate supplier (Q4), assert multiple suppliers exist for Animal Feed (ADM and Cargill).
- **Prior art**: None in this codebase (greenfield project). Testing convention is Cypher queries run via Neo4j Browser or Python driver, with manual result inspection in Stage 1.

## Out of Scope

- **Event nodes and impact propagation** (`[:影响]` edges) — deferred to Event project
- **Substitution logic** (`[:替代品]` edges, Product Category nodes) — deferred to Process project
- **Growers/farmers** as Company nodes
- **Financial attribution analysis** — cost/revenue are edge properties only, no FinancialImpactEvent nodes
- **Time-filtered queries** — `valid_from`/`valid_until` data is loaded but no time-aware queries in Stage 1
- **Precise geographic locations** (city/port level) — geography limited to country/region
- **Multi-tenant or multi-database** Neo4j deployment
- **CI/CD pipeline** for data loading or query validation

## Further Notes

- The 28-node entity list and 52-edge relationship list are fully specified in `design.md`. No entity discovery is needed during implementation.
- All 7 ADRs (001-007) in `design.md` are confirmed and stable. No new architectural decisions expected for this stage.
- `CONTEXT.md` contains the domain glossary. Use its terminology throughout implementation.
- Data sourcing is the highest-risk activity — each `[:供应给]` edge requires manual research against SEC 10-K filings, USDA reports, and industry publications. The bottleneck is human judgment time, not technical complexity.
