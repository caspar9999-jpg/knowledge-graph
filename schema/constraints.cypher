// ==========================================
// Database Constraints & Indexes
//
// Run before data load via 00_schema_init.py
// Run with: Cypher shell or Neo4j Browser
// ==========================================

// Unique constraints (also create backing indexes)
CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT product_category_id_unique IF NOT EXISTS FOR (c:ProductCategory) REQUIRE c.id IS UNIQUE;

// Property indexes for query performance
CREATE INDEX confidence_index IF NOT EXISTS FOR ()-[r:供应给]-() ON (r.confidence);
CREATE INDEX confidence_provide_index IF NOT EXISTS FOR ()-[r:提供]-() ON (r.confidence);
CREATE INDEX company_hq_country_index IF NOT EXISTS FOR (c:Company) ON (c.hq_country);
CREATE INDEX needs_review_provide IF NOT EXISTS FOR ()-[r:提供]-() ON (r.needs_review);
CREATE INDEX needs_review_supply IF NOT EXISTS FOR ()-[r:供应给]-() ON (r.needs_review);
CREATE INDEX needs_review_used_in IF NOT EXISTS FOR ()-[r:用于]-() ON (r.needs_review);
CREATE INDEX needs_review_categorized IF NOT EXISTS FOR ()-[r:归类于]-() ON (r.needs_review);

// Indexed lookup properties for entity resolution
CREATE INDEX aliases_company_index IF NOT EXISTS FOR (c:Company) ON (c.aliases);
CREATE INDEX aliases_product_index IF NOT EXISTS FOR (p:Product) ON (p.aliases);
CREATE INDEX aliases_commodity_index IF NOT EXISTS FOR (c:Commodity) ON (c.aliases);
