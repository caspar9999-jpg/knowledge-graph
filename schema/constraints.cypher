// ==========================================
// Database Constraints & Indexes
//
// Run before data load via 00_schema_init.ipynb
// Run with: Cypher shell or Neo4j Browser
// ==========================================

// Unique constraints (also create backing indexes)
CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;

// Property indexes for query performance
CREATE INDEX confidence_index IF NOT EXISTS FOR ()-[r:供应给]-() ON (r.confidence);
CREATE INDEX company_hq_country_index IF NOT EXISTS FOR (c:Company) ON (c.hq_country);
