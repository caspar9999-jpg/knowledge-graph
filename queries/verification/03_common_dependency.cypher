// Common Dependency Exposure
// Finds products/commodities that connect to multiple companies
// in the supply graph, revealing shared dependency points.
//
// Uses undirected matching to capture both commercial supply
// (buyer + seller) and physical composition dependencies.
//
// Parameters:
//   $max_depth: max traversal hops (default: 3)
//   $min_companies: minimum companies sharing this node (default: 2)

MATCH (m:Product)
WITH m
MATCH (c:Company)-[*1..$max_depth]-(m)
WITH m, collect(DISTINCT c.id) AS related_companies
WHERE size(related_companies) >= $min_companies
RETURN m.id AS dependency_id,
       m.name AS dependency_name,
       labels(m) AS node_labels,
       related_companies,
       size(related_companies) AS company_count
ORDER BY company_count DESC, m.id
LIMIT 15
