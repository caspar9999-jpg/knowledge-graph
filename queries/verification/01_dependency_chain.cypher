// Commercial Dependency Chain
// Traces from a supplier company to a downstream company
// along commercial dependency paths.
//
// The path may use [:提供] (company produces product) and
// [:供应给] (commercial supply) in any combination.
//
// Parameters:
//   $start_company: Company.id to start from (default: 'c01' = Nutrien)
//   $confidence_levels: allowed confidence values (default: ['confirmed', 'inferred'])
//   $max_depth: max traversal hops (default: 6)

MATCH path = (start:Company {id: $start_company})
            -[:提供|供应给*1..$max_depth]->
            (end:Company)
WHERE ALL(rel IN relationships(path) WHERE rel.confidence IN $confidence_levels)
  AND NOT start = end
  AND length(path) >= 2
RETURN path,
       length(path) AS hops,
       [node IN nodes(path) | node.id] AS node_ids,
       [rel IN relationships(path) | type(rel) + ':' + coalesce(rel.confidence, 'n/a')] AS rels
ORDER BY hops
LIMIT 20
