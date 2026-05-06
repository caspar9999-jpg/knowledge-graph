---

# Supply Chain Knowledge Graph — Stage 1: Dependency Backbone

---

## Project Objective

Build a knowledge graph bounded by **public information**, with **inter-company commercial dependencies and physical composition of commodities** as its backbone, to serve as a unified data foundation supporting multiple supply chain analysis paradigms.

**Core Philosophy**: The graph itself does not predefine analysis types. Entities and relationships describe **facts only**; interpretation is the responsibility of the query layer. Stage 1 focuses on the dependency backbone. Event impact, substitution analysis, geographic matching, and similar capabilities are owned by independent downstream projects.

Analysis paradigms validated in Stage 1:
- **Dependency topology analysis**: structural concentration risk, critical node identification
- **Commercial dependency chain tracing**: multi-hop commercial dependencies along `[:PROVIDES]` and `[:SUPPLIES_TO]`
- **Physical composition chain tracing**: material-to-product consumption relationships along `[:USED_IN]`
- **Common dependency exposure**: multiple companies dependent on the same raw material or intermediate
- **Custom exploratory queries**: users can explore the graph along arbitrary entity and relationship combinations

---

## Project Boundaries

Stage 1 is a **data foundation**; it does not include an analytical application layer. The following capabilities are owned by independent projects:

| Capability | Owning Project | Interface with This Project |
|------------|----------------|---------------------------|
| Event impact and impact propagation | Event Project | Event nodes + `[:IMPACTS]` edges connect into this graph; this graph provides dependency edges with temporal properties for traversal |
| Substitutes and product equivalence classes | Process Project | Product Category nodes + `[:SUBSTITUTE_FOR]`/`[:BELONGS_TO]` edges connect into this graph; this graph provides Product nodes |
| Analyst visualization interface | Demo Project | Consumes Cypher queries and Neo4j instance of this graph |

**This project does not import Event nodes, `[:IMPACTS]` edges, Product Category nodes, or substitute relationship edges.** However, it reserves temporal properties on edges (`valid_from`/`valid_until`), `hq_country`/`operating_countries` on Company, and `category` on Product to provide zero-migration extension points for downstream projects.

**Explicit exclusions**:
- **Growers/Farmers** are not modeled as Company nodes. Crop Commodity nodes serve as the aggregate starting point for supply chains. Farmer nodes may be added on demand if a specific supply chain segment requires them in the future.

---

## Expected Deliverables

1. **Knowledge graph data model**: entity definitions, relationship definitions, property specification document (this file).
2. **Backbone graph instance**: a Neo4j database instance covering the fertilizer→food chain (~60 edges, 28 nodes), including:
   - Fertilizer companies and fertilizer product nodes
   - Intermediate agricultural products and processed goods (corn, soybeans, wheat, starch, HFCS, animal feed, ethanol, etc.)
   - Downstream consumer goods company nodes
   - `[:PROVIDES]` (Company→Product), `[:SUPPLIES_TO]` (supplier→buyer), `[:USED_IN]` (material→product) edges
3. **Verification query set**: 5 standard Cypher queries validating the model's multi-faceted queryability:
   - Commercial dependency chain tracing
   - Physical composition chain tracing
   - Common dependency exposure
   - Same-product alternate supply
   - Graph-structural hub analysis
   All queries include built-in confidence filtering, maximum depth limits, and no-duplicate-node constraints.
4. **Data ingestion guide**: documentation on how public data sources (USDA, FAO, SEC 10-K, etc.) map to the graph structure.

---

## Glossary

### Entity Types

| Term | Definition | Typical Instance | Key Properties |
|------|------------|------------------|----------------|
| **Company** | A commercial entity in the supply chain, including producers, service providers, downstream customers, etc. | Nutrien, Nestlé, Tyson Foods | `hq_country` (required), `hq_region` (optional), `operating_countries` (optional), `external_id` (optional, e.g. ticker/LEI) |
| **Product** | An output offered by a company that can be procured or depended on downstream, including tangible goods, software, basic services, processed intermediates, etc. | DAP fertilizer, Animal Feed, Carbonated Soft Drinks, Corn Starch | `external_id` (optional), `category` (optional, reserved for future product category mapping) |
| **Commodity** | A homogeneous product traded as a basic industrial input or raw material; a sub-type of Product distinguished with the `:Commodity` label. | Potash, Urea, Corn, Soybeans | `major_producing_countries` (optional) |

**Commodity vs. Product classification rule**: A node is classified as a Commodity only if it satisfies all of (a) homogeneous/substitutable, (b) quoted on a public exchange or price index, (c) no strong brand attributes. If any condition is not met, it is a Product. **Each node carries exactly one label** (the most specific one), with no double-labeling. This rule provides a repeatable judgment standard for data entry.

### Relationship Types

| Relationship | Direction / Semantics | Confirmed Usage & Constraints |
|-------------|----------------------|------------------------------|
| `[:PROVIDES]` | `(Company) -[:PROVIDES]-> (Product)` | Indicates the company produces that product. One-to-many; multiple companies may provide the same product. Optional edge properties: gross margin, revenue share, etc. **Self-loops forbidden** (a company does not "provide" to itself). |
| `[:SUPPLIES_TO]` | supplier → buyer | **Used only for commercial supply dependency.** Hard constraint: when a material node serves as a physical input, use `[:USED_IN]`; do not use `[:SUPPLIES_TO]` to express physical composition. Supports all endpoint combinations (Product→Product, Product→Company, Company→Company, Commodity→Company). Edge must carry `confidence` (three-tier scale); optional `valid_from`/`valid_until`. **Self-loops forbidden**. |
| `[:USED_IN]` | `(input material) -[:USED_IN]-> (product)` | Represents physical composition or primary consumption relationship. The input material is not limited to Commodity-labeled nodes—any node that semantically acts as a physical input role (e.g., Corn Starch as an ingredient in Processed Food) can be the source of `[:USED_IN]`. **Strictly separated from `[:SUPPLIES_TO]`.** Optional `valid_from`/`valid_until`. `[:USED_IN]` does not carry a `confidence` property (physical composition relationships are deterministic within Stage 1 scope). **Self-loops forbidden**. |

---

## Data Source Rules

- **Source priority**: Regulatory filings (SEC 10-K, annual reports) > News reports > Industry estimates. When conflicts arise, the higher-priority source prevails.
- **`source` property**: All edges should carry a data source annotation. Format: `<source_type>:<short_reference>`, e.g., `SEC:Corn%20Products%20segment`, `news:Bloomberg%202024`.
- **Data acquisition bottleneck**: Converting market share / business segment descriptions in public financial reports into graph edges involves manual judgment. The initial phase does not pursue precise quantification (e.g., "supplied X% of corn"), only records whether a supply relationship exists.

### Relationship Property Details

| Property | Applies To | Type | Required | Description |
|----------|-----------|------|----------|-------------|
| `confidence` | `[:SUPPLIES_TO]` | enum | Yes | `confirmed` / `inferred` / `associated` (see ADR-003) |
| `valid_from` | `[:SUPPLIES_TO]`, `[:USED_IN]` | date | No | Relationship effective date. If empty, treated as "always valid". |
| `valid_until` | `[:SUPPLIES_TO]`, `[:USED_IN]` | date | No | Relationship expiry date. If empty, treated as "always valid". |
| `gross_margin_pct` | `[:PROVIDES]` | float | No | Gross margin of this product for the company. |
| `revenue_share_pct` | `[:PROVIDES]` | float | No | Share of this product's revenue in the company's total revenue. |
| `source` | All edges | string | No | Data source annotation. |

---

## Key Architecture Decision Records (ADR)

### ADR-001: Cost/Revenue Modeling Approach [Confirmed]

- **Decision**: Cost and revenue are not modeled as independent entity nodes but as relationship properties on the corresponding edges. Priority is on `[:PROVIDES]` edges.
- **Rationale**: The core objective is a queryable dependency network, not precise financial aggregation.
- **Consequences**: Path queries run quickly, but complex financial attribution is not directly possible. A `FinancialImpactEvent` node may be added in the future.

### ADR-002: Supply Relationship Modeling Granularity [Confirmed]

- **Decision**: Use direct edge connections; do not introduce intermediate "supply contract/relationship" nodes. `[:SUPPLIES_TO]` direction is fixed as "supplier → buyer", strictly separated from `[:USED_IN]`.
- **Rationale**: Public information cannot support term-level data; direct connection yields the shortest query path. A `relationship_id` property is reserved for potential future migration.
- **Consequences**: Cannot express price differences for the same product across different customers, which aligns with current data constraints.

### ADR-003: Three-Tier Confidence Scale [Confirmed]

- **Decision**: `confidence` on `[:SUPPLIES_TO]` has three levels:
  - `confirmed`: L1 hard dependency (physical/chemical hard dependency, exclusive public announcement). Applicable only to Product-Product or Product-Company edges.
  - `inferred`: L2 inferred dependency (inferred from revenue/business structure). Applicable to Product-Product, Product-Company, and **Commodity-Company** edges. Commodity→Company relationships are uniformly classified here (e.g., Corn→ADM has clear business-segment basis in public filings).
  - `associated`: L3 inter-company dependency (only known that a transaction exists). Company-Company edges default to this level.
  - **Exception**: When a Company-Company relationship has clear evidence in public regulatory filings (e.g., Nutrien's 10-K explicitly records a distribution relationship with Cargill), it may be elevated to `inferred`.
- **Query convention**: By default, traverse only `confirmed` + `inferred`; `associated` must be explicitly requested. Implemented via the `$confidence_levels` parameter:
  ```cypher
  WHERE ALL(rel IN relationships(path) WHERE rel.confidence IN $confidence_levels)
  ```

### ADR-004: Temporal Modeling Strategy [Confirmed]

- **Decision**: `[:SUPPLIES_TO]` and `[:USED_IN]` edges add optional `valid_from` and `valid_until`. Queries will cross-check the target time point against the edge's validity period. Edges without validity properties are always considered valid.
- **Rationale**: Supply chain relationships are temporal; without a temporal dimension, downstream projects performing historical analysis will incorrectly associate expired relationships.
- **Consequences**: Many edges will initially have empty dates, which does not affect queries (edges with null dates always pass filters). Stage 1 does not yet implement time-filtered queries—temporal properties are data-ready; filtering logic is defined by the Event project.

### ADR-005: Event Impact Modeling [Deferred to Event Project]

- **Decision**: Event nodes and all associated properties (`event_type`, `severity`, `scope_geo`, `scope_industry`, etc.) and `[:IMPACTS]` edges are out of scope for Stage 1. The independent Event project will define the complete Event model, geographic matching rules, severity criteria, and connect to this graph's dependency network.
- **Rationale**: Event modeling involves multiple independent design decisions (impact intensity determination, geographic matching semantics, event effect duration). Premature inclusion in Stage 1 would pollute the model. This graph reserves Company's `hq_country`/`operating_countries`, Commodity's `major_producing_countries`, and all relationship edges' `valid_from`/`valid_until` for the Event project.
- **Consequences**: Stage 1 does not include impact propagation queries. Geographic properties are modeled but have no active consumer.

### ADR-006: Entity Geographic Location Properties [Confirmed]

- **Decision**: Company nodes add `hq_country` (required), `hq_region` (optional), `operating_countries` (optional). Commodity nodes add `major_producing_countries` (optional). Precise origin nodes are not modeled.
- **Geographic matching rules**: Deferred to the Event project. Stage 1 only loads geographic data; it does not produce geo-filtered queries.
- **Consequences**: Propagation precision is limited to country/region level. Origin sub-nodes may be added in the future.

### ADR-007: Substitutes and Product Equivalence Classes [Deferred to Process Project]

- **Decision**: Substitute relationships (`[:SUBSTITUTE_FOR]`), Product Category nodes, and `[:BELONGS_TO]` edges are out of scope for Stage 1. The independent Process project will define product equivalence classes and substitution logic and connect to this graph's Product nodes.
- **Rationale**: Substitute determination involves independent modeling problems such as functional equivalence analysis and process matching. This graph reserves Product's `category` property for the Process project.
- **Consequences**: Stage 1's "alternate supply" verification query is limited to "which other companies provide the same product" (same-product alternate supply), not true functional substitution.

---

## Verification Query Set

Five standard queries, each in a separate `.cypher` file:

| # | Query Type | Cypher File | Verification Goal |
|---|-----------|------------|-------------------|
| 1 | Commercial dependency chain tracing | `01_dependency_chain.cypher` | Trace from fertilizer companies along `[:PROVIDES]→[:SUPPLIES_TO]*` to consumer goods companies |
| 2 | Physical composition chain tracing | `02_composition_chain.cypher` | Trace from commodities along `[:USED_IN]*` through processing chains to final products |
| 3 | Common dependency exposure | `03_common_dependency.cypher` | Find multiple companies dependent on the same intermediate or raw material |
| 4 | Same-product alternate supply | `04_alternate_supplier.cypher` | Given a product, find all companies providing that product (reverse `[:PROVIDES]` lookup) |
| 5 | Graph-structural hub analysis | `05_hub_analysis.cypher` | Identify hub nodes in the supply network by in-degree and out-degree |

**All queries uniformly follow these constraints**:

- Default confidence `$confidence_levels = ['confirmed', 'inferred']`
- Maximum traversal depth defaults to 6, overridable via `$max_depth` parameter
- No duplicate node visits within a single path (Cypher default `isTrail` or explicit `NODE_UNIQUENESS`)
- No temporal filtering logic included (temporal properties are loaded; filtering is appended by the Event project)

**Every hop must pass through a Product/Commodity node to switch relationship types**. Standard path signatures:

| Query Type | Path Signature | Constraint |
|-----------|----------------|------------|
| Commercial dependency chain | `(Company)-[:PROVIDES|SUPPLIES_TO]->...->(Company)` | Mix of company→product (`[:PROVIDES]`) and commercial supply (`[:SUPPLIES_TO]`). First hop from a fertilizer company may be company→company. |
| Physical composition chain | `(Commodity)-[:USED_IN]->(Product)-[:USED_IN]->(Product)...` | Source may be Commodity or Product (any input material role) |
| Mixed traversal | `(Company)-[:PROVIDES]->(Product)-[:USED_IN]->...->(Product)-[:PROVIDES]->(Company)` | Traverse through entity nodes on each relationship switch |
| Common dependency | `(c1)-[*..]->(m)<-[*..]-(c2)` | No constraint on relationship direction; detects topological common dependency |
| Alternate supply | `(p)<-[:PROVIDES]-(c)` | Only `[:PROVIDES]` edges present in the graph |

**Data entry validation rules**:

- `[:USED_IN]` and `[:SUPPLIES_TO]` are strictly separated by semantics: physical composition uses `[:USED_IN]`, commercial supply uses `[:SUPPLIES_TO]`. The same node pair may have both types of edges simultaneously (e.g., Corn→Ethanol `[:USED_IN]` physical composition + Corn→ADM `[:SUPPLIES_TO]` commercial sale); this is not a conflict when semantics differ.
- When constructing L1/L2 product-product edges, the downstream product must already be connected to a company via `[:PROVIDES]`.
- All self-loop edges forbidden (source == target).
- All `[:SUPPLIES_TO]` edges must carry `confidence`.

---

## Entity Inventory (Stage 1 Instance)

### Companies (9)

| ID | Name | Country |
|----|------|---------|
| c01 | Nutrien | CA |
| c02 | Yara International | NO |
| c03 | Mosaic | US |
| c04 | ADM | US |
| c05 | Bunge | US |
| c06 | Cargill | US |
| c07 | Tyson Foods | US |
| c08 | Nestlé | CH |
| c09 | The Coca-Cola Company | US |

### Commodities (6)

| ID | Name | Major Producing Countries |
|----|------|---------------------------|
| m01 | Potash | CA, RU, BY |
| m02 | Urea | CN, IN, US |
| m03 | DAP | CN, IN, US |
| m04 | Corn | US, CN, BR |
| m05 | Soybeans | US, BR, AR |
| m06 | Wheat | CN, IN, RU |

### Products (13)

| ID | Name | Category |
|----|------|----------|
| p01 | NPK Compound Fertilizer | fertilizer |
| p02 | Corn Starch | food-ingredient |
| p03 | High Fructose Corn Syrup (HFCS) | sweetener |
| p04 | Soybean Meal | animal-feed |
| p05 | Soybean Oil | food-oil |
| p06 | Wheat Flour | food-ingredient |
| p07 | Animal Feed | animal-feed |
| p08 | Ethanol | fuel |
| p09 | Poultry Products | meat |
| p10 | Pork Products | meat |
| p11 | Processed Food | packaged-food |
| p12 | Carbonated Soft Drinks | beverage |
| p13 | Snack Foods | packaged-food |

**Total: 28 nodes, 60 edges (23 [:PROVIDES] + 22 [:USED_IN] + 15 [:SUPPLIES_TO])**

---

## Relationship Inventory (Stage 1 Instance)

### [:PROVIDES] (23 edges)

| Company | Products |
|---------|----------|
| Nutrien | Potash, Urea, DAP |
| Yara | Urea, NPK Compound Fertilizer |
| Mosaic | Potash, DAP |
| ADM | Corn Starch, HFCS, Soybean Meal, Soybean Oil, Ethanol, Animal Feed |
| Bunge | Soybean Meal, Soybean Oil |
| Cargill | Corn Starch, Animal Feed, Soybean Meal |
| Tyson | Poultry Products, Pork Products |
| Nestlé | Processed Food, Snack Foods |
| Coca-Cola | Carbonated Soft Drinks |

### [:USED_IN] (22 edges)

| Input Material | Product |
|----------------|---------|
| Potash | Corn, Soybeans |
| Urea | Corn, Wheat |
| DAP | Corn, Soybeans |
| Corn | Corn Starch, HFCS, Ethanol, Animal Feed |
| Soybeans | Soybean Meal, Soybean Oil, Animal Feed |
| Wheat | Wheat Flour, Animal Feed |
| Corn Starch | Processed Food, Snack Foods |
| HFCS | Carbonated Soft Drinks |
| Wheat Flour | Snack Foods |
| Soybean Oil | Processed Food |
| Animal Feed | Poultry Products, Pork Products |

### [:SUPPLIES_TO] (15 edges)

| Supplier | Buyer | Confidence |
|----------|------|------------|
| Nutrien | ADM | inferred |
| Nutrien | Cargill | inferred |
| Mosaic | Cargill | inferred |
| Corn | ADM | inferred |
| Corn | Cargill | inferred |
| Soybeans | ADM | inferred |
| Soybeans | Bunge | inferred |
| Wheat | ADM | inferred |
| Wheat | Cargill | inferred |
| HFCS | Coca-Cola | inferred |
| Corn Starch | Nestlé | inferred |
| Soybean Meal | Tyson | inferred |
| Soybean Oil | Nestlé | inferred |
| Animal Feed | Tyson | inferred |
| Wheat Flour | Nestlé | inferred |

---

## Project Structure

```
C:\Projects\knowledge_graph\
├── design.md                     # This file: data model + ADRs
├── schema/
│   ├── constraints.cypher        # Uniqueness constraints + indexes
│   └── validation.cypher         # Data quality validation queries
├── data/
│   ├── sources.md                # Data ingestion guide (public data source mapping)
│   ├── companies.csv             # columns: id, name, type, hq_country, hq_region, operating_countries, external_id
│   ├── commodities.csv           # columns: id, name, major_producing_countries
│   ├── products.csv              # columns: id, name, category
│   ├── edges_provide.csv         # columns: company_id, product_id, gross_margin_pct, revenue_share_pct, source
│   ├── edges_supply.csv          # columns: from_id, to_id, confidence, valid_from, valid_until, source
│   └── edges_used_in.csv         # columns: from_id, to_id, valid_from, valid_until, source
├── scripts/
│   ├── 00_schema_init.ipynb      # Run constraints + validation scripts
│   └── 01_load_data.ipynb        # LOAD CSV data import pipeline
├── queries/
│   └── verification/
│       ├── 01_dependency_chain.cypher
│       ├── 02_composition_chain.cypher
│       ├── 03_common_dependency.cypher
│       ├── 04_alternate_supplier.cypher
│       └── 05_hub_analysis.cypher
└── requirements.txt              # neo4j, jupyter, pandas
```

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Graph Database | Neo4j Community Edition 5.x | The most mature property graph database; Cypher query language offers the best support for multi-hop traversals; GDS library (65+ algorithms) and APOC (350+ procedures) available for free |
| Data Loading | CSV + LOAD CSV + Jupyter orchestration | CSV is the lowest-friction manual curation format (Excel-editable); Jupyter provides visual feedback and iterative development experience |
| Data Pipeline | Python 3.11 + neo4j driver v6 | Python ecosystem integrates seamlessly with pandas for data cleaning; neo4j official driver is mature and stable |
| Visual Exploration | Neo4j Browser | Included free with CE; supports interactive graph visualization and Cypher editing |

**Development strategy**: Schema-first. Establish uniqueness constraints and indexes first (`constraints.cypher`), then incrementally load edge data. The verification query set (5 Cypher queries) serves as acceptance tests—if query results do not meet expectations, fix the data or model; do not modify the queries to fit an incorrect model.

**Database topology confirmation**: Neo4j CE 5.x single-database instance; Stage 1 has no multi-tenancy or separate dev/test environment requirements.

---

## Known Limitations & Next-Stage Expansion

- **Event impact analysis**: Stage 1 does not include Event nodes or `[:IMPACTS]` edges. Event modeling, geographic matching rules, and impact propagation queries are defined by the independent Event project. Interface: this graph provides dependency edges with `valid_from`/`valid_until` and Company nodes with `hq_country`/`operating_countries`.
- **Substitute analysis**: Stage 1 does not include `[:SUBSTITUTE_FOR]` edges or Product Category nodes. Defined by the Process project. Interface: this graph provides Product nodes and the `category` property. Stage 1's "alternate supply" query is limited to same-product multi-supplier scenarios.
- **Precise origin and logistics nodes**: Current geographic precision is limited to country/region level; city/port-level analysis is not supported. Origin, warehousing, and transportation nodes may be added in the future.
- **Financial attribution analysis**: Cost/revenue information exists only as edge properties; complex event-driven financial attribution is not possible. A `FinancialImpactEvent` node may be added in the future.
- **Temporal property completeness**: Initially, `valid_from`/`valid_until` will be mostly empty. It is recommended to backfill validity periods for core L1 relationships in Phase 2.
- **Controlled vocabulary**: Field values such as `hq_country` should ideally use ISO 3166 country codes; the graph layer does not enforce a hard constraint—consistent query results are ensured through entry conventions.
