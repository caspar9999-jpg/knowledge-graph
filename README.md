# Supply Chain Knowledge Graph — Stage 1: Dependency Backbone

A Neo4j knowledge graph modeling commercial dependencies (who supplies whom) and physical composition (what goes into what) across the fertilizer-to-food supply chain. 28 nodes, 52+ relationships, 3 relationship types.

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j instance (AuraDB or local) — credentials in `.env`

### Setup

```bash
pip install -r requirements.txt
```

Create `.env` in the project root (see `.env.example`):
```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

### Load the Static Data

Run these two scripts in order:

```bash
# Step 1: Create uniqueness constraints + indexes
python scripts/00_schema_init.py

# Step 2: Load CSV data (companies, commodities, products, edges)
python scripts/01_load_data.py
```

The graph is now populated with the 28-node dependency backbone.

## Importing Earnings Call Relations

After running the [Earnings Call Ingestion Pipeline](https://github.com/caspar9999-jpg/Earnings_Call_Ingestion), import extracted relations into the graph:

```bash
python scripts/02_import_relations.py --relations ../path/to/relations_2025Q1.jsonl
```

The script:
1. Creates/updates schema constraints
2. Runs data validation queries
3. Resolves entities against existing graph nodes (Company, Product, Commodity)
4. Creates `[:PROVIDES]`, `[:SUPPLIES_TO]`, and `[:USED_IN]` edges with metadata
5. Logs skipped relations (DIVISION entities, terminations) and flagged review items

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `00_schema_init.py` | Create Neo4j uniqueness constraints + indexes |
| `01_load_data.py` | Bulk-load all CSV data files into Neo4j |
| `02_import_relations.py` | Import relations JSONL from the EC pipeline |
| `run_queries.py` | Run verification Cypher queries against the graph |
| `verify_ac1.py` | Acceptance criteria verification |
| `diagnose.py` | Diagnostic checks on graph state |
| `check_version.py` | Check Neo4j driver/database versions |

## Data Files (CSVs)

| File | Content |
|------|---------|
| `data/companies.csv` | 9 Company nodes (Nutrien, ADM, Cargill, Tyson, etc.) |
| `data/commodities.csv` | 6 Commodity nodes (Corn, Soybeans, Wheat, Potash, Urea, DAP) |
| `data/products.csv` | 13 Product nodes (HFCS, Animal Feed, Ethanol, etc.) |
| `data/edges_provide.csv` | `[:PROVIDES]` — Company produces Product |
| `data/edges_supply.csv` | `[:SUPPLIES_TO]` — commercial supply with confidence |
| `data/edges_used_in.csv` | `[:USED_IN]` — physical composition |
| `data/node_aliases.csv` | Alternative names for graph nodes |
| `data/product_categories.csv` | Product→category classification |

See `data/sources.md` for detailed sourcing of each `[:SUPPLIES_TO]` edge.

## Schema & Validation

- `schema/constraints.cypher` — uniqueness constraints on node IDs + indexes
- `schema/validation.cypher` — quality checks (no self-loops, no missing confidence, no orphan products)

## Verification Queries

Five Cypher queries in `queries/verification/` serve as acceptance tests:

1. **Dependency chain** — trace commercial dependencies multi-hop
2. **Composition chain** — trace physical inputs through products
3. **Common dependency** — find nodes sharing a supplier/material
4. **Alternate supplier** — find same-product providers
5. **Hub analysis** — identify high-degree nodes

## Architecture

```
CSV files ──→ 01_load_data.py ──→ Neo4j (static backbone)
                                        ↑
                                        │ relations via 02_import_relations.py
                                        │
Earnings Call Pipeline ──→ relations_{Q}.jsonl
```

The graph is built in two layers:
1. **Static backbone** — hand-curated CSV data (fertilizer → food chain)
2. **Dynamic relations** — LLM-extracted from earnings calls via the EC pipeline

## Entity Types

- **Company** — Commercial entity (producer, processor, service provider)
- **Product** — Output offered by a Company (physical goods, software, services)
- **Commodity** — Homogeneous, substitutable, exchange-traded (subclass of Product)

## Relationship Types

- `[:PROVIDES]` — Company → Product (produces/makes)
- `[:SUPPLIES_TO]` — Company/Product/Commodity → Company/Product (commercial supply)
- `[:USED_IN]` — Input Material → Product (physical composition)

`[:SUPPLIES_TO]` edges carry `confidence` (confirmed / inferred / associated).
`[:USED_IN]` edges have no confidence in Stage 1 (composition is deterministic).

## Issue Tracker

[GitHub Issues](https://github.com/caspar9999-jpg/knowledge-graph/issues)

## Configuration

See `.env.example` for all required environment variables.
