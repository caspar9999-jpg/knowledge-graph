// Physical Composition Chain
// Traces from a commodity/input-material to a finished product
// via [:用于] multi-hop traversal.
//
// Parameters:
//   $start_material: node id for the input material (default: 'm01' = Potash)
//   $max_depth: max traversal hops (default: 6)

MATCH path = (material {id: $start_material})-[:用于*1..$max_depth]->(product:Product)
WHERE NOT EXISTS {
  (product)-[:用于]->()
}
RETURN path,
       length(path) AS hops,
       [node IN nodes(path) | node.id] AS node_ids
ORDER BY hops
LIMIT 20
