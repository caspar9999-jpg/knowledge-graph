// ==========================================
// Data Quality Validation Queries
//
// Each query should return 0 rows on a clean,
// fully-validated graph. Run after data load.
// ==========================================

// -------- Validation 1: Orphan Products --------
// A Product that is not a Commodity must have an incoming [:提供]
// from at least one Company. Commodities are exempt because
// growers/farmers are not modeled as Company nodes.
MATCH (p:Product)
WHERE NOT p:Commodity
  AND NOT EXISTS { MATCH (c:Company)-[:提供]->(p) }
RETURN p.id AS orphan_product_id, p.name AS orphan_product_name
ORDER BY p.id;

// -------- Validation 2: Self-loops --------
// No relationship should have the same node as source and target.
MATCH (n)-[r]->(n)
RETURN labels(n) AS node_labels, n.id AS node_id, type(r) AS rel_type
ORDER BY n.id;

// -------- Validation 3: Missing confidence on [:供应给] --------
// Every [:供应给] edge must carry a non-null confidence value.
MATCH ()-[r:供应给]->()
WHERE r.confidence IS NULL
RETURN startNode(r).id AS from_id, endNode(r).id AS to_id, 'missing confidence on [:供应给]' AS violation
ORDER BY from_id;

// -------- Validation 4: Missing confidence on [:提供] --------
// Every [:提供] edge must carry a non-null confidence value.
MATCH ()-[r:提供]->()
WHERE r.confidence IS NULL
RETURN startNode(r).id AS from_id, endNode(r).id AS to_id, 'missing confidence on [:提供]' AS violation
ORDER BY from_id;

// -------- Validation 5: Commodity label consistency --------
// Every Commodity node must also carry the Product label.
MATCH (c:Commodity)
WHERE NOT c:Product
RETURN c.id AS node_id, c.name AS node_name, 'Commodity without Product label' AS violation
ORDER BY c.id;

// -------- Validation 6: Orphan ProductCategory --------
// Every ProductCategory must have at least one incoming [:归类于] edge.
MATCH (cat:ProductCategory)
WHERE NOT EXISTS { MATCH ()-[r:归类于]->(cat) }
RETURN cat.id AS category_id, cat.name AS category_name, 'ProductCategory without products' AS violation
ORDER BY cat.id;

// -------- Validation 7: Products without category --------
// Every Product should have at least one outgoing [:归类于] edge to a ProductCategory.
MATCH (p:Product)
WHERE NOT EXISTS { MATCH (p)-[r:归类于]->(:ProductCategory) }
RETURN p.id AS product_id, p.name AS product_name, 'Product without category' AS violation
ORDER BY p.id;
