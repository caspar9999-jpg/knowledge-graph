from neo4j import GraphDatabase
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'schema')

def run_cypher_file(session, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    results = []
    for statement in content.split(';'):
        stmt = statement.strip()
        if stmt and not stmt.startswith('//'):
            result = session.run(stmt)
            results.append(result)
    return results

def load_csv(session, filepath, load_query):
    csv_path = filepath.replace('\\', '/')
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{csv_path}' AS row
    {load_query}
    """
    result = session.run(query)
    summary = result.consume()
    print(f"  loaded: {filepath} ({summary.counters.properties_set} properties set)")
    return summary

def main():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Step 1: Clear existing data
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")

        # Step 2: Load companies
        print("\nLoading companies...")
        load_csv(session, os.path.join(DATA_DIR, 'companies.csv'),
            """
            MERGE (c:Company {id: row.id})
            SET c.name = row.name,
                c.hq_country = row.hq_country
            """)

        # Step 3: Load commodities (also labeled as Product)
        print("\nLoading commodities...")
        load_csv(session, os.path.join(DATA_DIR, 'commodities.csv'),
            """
            MERGE (c:Commodity:Product {id: row.id})
            SET c.name = row.name,
                c.major_producing_countries = split(coalesce(row.major_producing_countries, ''), ',')
            """)

        # Step 4: Load products
        print("\nLoading products...")
        load_csv(session, os.path.join(DATA_DIR, 'products.csv'),
            """
            MERGE (p:Product {id: row.id})
            SET p.name = row.name,
                p.category = row.category
            """)

        # Step 5: Load [:提供] edges
        print("\nLoading [:提供] edges...")
        load_csv(session, os.path.join(DATA_DIR, 'edges_provide.csv'),
            """
            MATCH (c:Company {id: row.company_id})
            MATCH (p:Product {id: row.product_id})
            MERGE (c)-[r:提供]->(p)
            SET r.gross_margin_pct = toFloatOrNull(row.gross_margin_pct),
                r.revenue_share_pct = toFloatOrNull(row.revenue_share_pct),
                r.source = row.source
            """)

        # Step 6: Load [:供应给] edges
        print("\nLoading [:供应给] edges...")
        load_csv(session, os.path.join(DATA_DIR, 'edges_supply.csv'),
            """
            MATCH (from {id: row.from_id})
            MATCH (to {id: row.to_id})
            MERGE (from)-[r:供应给]->(to)
            SET r.confidence = row.confidence,
                r.valid_from = row.valid_from,
                r.valid_until = row.valid_until,
                r.source = row.source
            """)

        # Step 7: Load [:用于] edges
        print("\nLoading [:用于] edges...")
        load_csv(session, os.path.join(DATA_DIR, 'edges_used_in.csv'),
            """
            MATCH (from {id: row.from_id})
            MATCH (to {id: row.to_id})
            MERGE (from)-[r:用于]->(to)
            SET r.valid_from = row.valid_from,
                r.valid_until = row.valid_until,
                r.source = row.source
            """)

        # Step 8: Validate
        print("\nRunning validation queries...")
        results = run_cypher_file(session, os.path.join(SCHEMA_DIR, 'validation.cypher'))
        all_pass = True
        for result in results:
            records = list(result)
            if records:
                print(f"  FAIL: {len(records)} violation(s) found")
                for rec in records[:5]:
                    print(f"    {rec}")
                all_pass = False
            else:
                print(f"  PASS — 0 violations")

        # Step 9: Summary
        print("\n--- Summary ---")
        for label in ['Company', 'Product', 'Commodity']:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
            count = result.single()['count']
            print(f"  {label}: {count}")

        for rel_type in ['提供', '供应给', '用于']:
            result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
            count = result.single()['count']
            print(f"  :{rel_type}: {count}")

        if all_pass:
            print("\n✓ All validation checks passed")
        else:
            print("\n✗ Some validation checks failed — see above")

    driver.close()

if __name__ == '__main__':
    main()
