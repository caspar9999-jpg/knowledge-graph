# Supply Chain Knowledge Graph

A dependency-backbone knowledge graph built from public information, modeling commercial dependencies between companies and physical composition relationships of commodities. The graph itself does not prescribe analysis types — entities and relationships describe facts; interpretation belongs to the query layer.

## Language

**Company**:
A commercial entity in the supply chain — producer, processor, service provider, or downstream customer.
_Avoid_: Firm, organization, corporation

**Product**:
An output offered by a Company that can be procured or depended upon downstream. Includes physical goods, software, basic services, and processed intermediates.
_Avoid_: Item, SKU, good

**Commodity**:
A homogeneous, substitutable product traded on public exchanges or price indices, with no strong brand attribute. A subclass of Product, labeled `:Commodity` in the graph.
_Avoid_: Raw material (too narrow — includes exchange-traded semi-processed goods)

**Input Material** (物料):
The semantic role of any node serving as a physical ingredient or consumable input in a manufacturing process. The node may have any label (Commodity or Product) — "Input Material" describes its role in a `[:用于]` relationship, not its node type.
_Avoid_: Raw input, component

## Relationships

- A **Company** `[:提供]` one or more **Products**
- A **Company** `[:供应给]` another **Company** (commercial supply)
- A **Product** `[:供应给]` a **Company** (known product-level supply)
- A **Product** `[:供应给]` another **Product** (product used as commercial input)
- A **Commodity** `[:供应给]` a **Company** (commodity sold to processor)
- An **Input Material** `[:用于]` a **Product** (physical composition or consumption)
- `[:供应给]` edges carry `confidence` (confirmed / inferred / associated)
- `[:用于]` edges carry no confidence (composition is deterministic in Stage 1 scope)

## Example dialogue

> **Dev:** "If Corn goes into Ethanol via `[:用于]`, and ADM buys Corn via `[:供应给]`, which edge do I follow to trace the physical dependency?"
> **Domain expert:** "Follow `[:用于]` to track the physical chain (Corn → Ethanol). Follow `[:供应给]` to track the commercial chain (Corn → ADM). They're different dimensions. If you want to know 'who depends on Corn for their products,' you traverse both."

> **Dev:** "Corn Starch is a Product, but it's a physical ingredient in Snack Foods. Can I use `[:用于]`?"
> **Domain expert:** "Yes. `[:用于]`'s source is any Input Material, regardless of whether it's labeled Commodity or Product. Corn Starch acting as a Snack Food ingredient is the Input Material role — it's `[:用于]`."

## Flagged ambiguities

- "物料" was used to mean both "Commodity the node type" and "Input Material the semantic role" — resolved: `[:用于]` takes any node in the Input Material role, not only Commodity-labeled nodes.
- "玉米供应商" — resolved: growers/farmers are not modeled as Company nodes. Commodity nodes serve as the aggregation point at the upstream boundary.
