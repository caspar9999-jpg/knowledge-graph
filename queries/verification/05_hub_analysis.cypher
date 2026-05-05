// Hub Analysis
// Identifies structurally critical nodes in the supply network
// by in-degree, out-degree, and total degree.
//
// No parameters — runs against the full graph.

MATCH (n)
WHERE n.id IS NOT NULL
OPTIONAL MATCH (n)-[r_out]->()
WITH n, count(r_out) AS out_degree
OPTIONAL MATCH (n)<-[r_in]-()
WITH n, out_degree, count(r_in) AS in_degree
RETURN n.id AS node_id,
       n.name AS node_name,
       labels(n)[0] AS primary_label,
       out_degree,
       in_degree,
       (out_degree + in_degree) AS total_degree
ORDER BY total_degree DESC
LIMIT 20
