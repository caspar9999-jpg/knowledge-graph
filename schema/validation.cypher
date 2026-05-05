// ==========================================
// Data Quality Validation Queries
//
// Each query should return 0 rows on a clean,
// fully-validated graph. Run after data load.
// ==========================================

// -------- Tracer bullet 1: Orphan Products --------
// A Product that is not a Commodity must have an incoming [:提供]
// from at least one Company. Commodities are exempt because
// growers/farmers are not modeled as Company nodes.
MATCH (p:Product)
WHERE NOT p:Commodity
  AND NOT EXISTS { MATCH (c:Company)-[:提供]->(p) }
RETURN p.id AS orphan_product_id, p.name AS orphan_product_name
ORDER BY p.id;

// -------- Tracer bullet 2: Self-loops --------
// No relationship should have the same node as source and target.
MATCH (n)-[r]->(n)
RETURN labels(n) AS node_labels, n.id AS node_id, type(r) AS rel_type
ORDER BY n.id;

// -------- Tracer bullet 3: Missing confidence --------
// Every [:供应给] edge must carry a non-null confidence value.
MATCH ()-[r:供应给]->()
WHERE r.confidence IS NULL
RETURN startNode(r).id AS from_id, endNode(r).id AS to_id, 'missing confidence' AS violation
ORDER BY from_id;

// -------- Bonus: Commodity label consistency --------
// Every Commodity node must also carry the Product label.
MATCH (c:Commodity)
WHERE NOT c:Product
RETURN c.id AS node_id, c.name AS node_name, 'Commodity without Product label' AS violation
ORDER BY c.id;
