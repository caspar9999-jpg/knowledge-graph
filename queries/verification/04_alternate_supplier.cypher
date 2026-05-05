// Alternate Supplier
// Given a product, returns all companies that provide it
// via reverse [:提供] edge traversal (same-product substitution).
//
// Parameters:
//   $product_id: Product.id to search for (default: 'p07' = Animal Feed)

MATCH (p:Product {id: $product_id})<-[:提供]-(c:Company)
RETURN c.id AS company_id,
       c.name AS company_name,
       c.hq_country AS country
ORDER BY c.id
