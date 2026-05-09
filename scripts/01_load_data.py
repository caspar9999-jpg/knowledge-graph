from neo4j import GraphDatabase
import pandas as pd
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'schema')


def load_csv_data(session, filepath, merge_query, params_fn):
    df = pd.read_csv(filepath, keep_default_na=False)
    for _, row in df.iterrows():
        params = params_fn(row)
        session.run(merge_query, **params)
    print(f"  loaded: {os.path.basename(filepath)} ({len(df)} rows)")


def run_validation(session, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content_clean = '\n'.join(
        line for line in content.split('\n')
        if not line.strip().startswith('//')
    )
    for statement in content_clean.split(';'):
        stmt = statement.strip()
        if stmt:
            result = session.run(stmt)
            records = list(result)
            if records:
                for rec in records:
                    safe = {k: str(v)[:60] for k, v in rec.items()}
                    print(f"  VIOLATION: {safe}")
                return False
    return True


def safe(text):
    return text.encode('ascii', errors='replace').decode()


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
        load_csv_data(session, os.path.join(DATA_DIR, 'companies.csv'),
            "MERGE (c:Company {id: $id}) SET c.name = $name, c.hq_country = $hq_country, "
            "c.aliases = $aliases, c.match_status = 'matched'",
            lambda r: {'id': r['id'], 'name': r['name'], 'hq_country': r['hq_country'],
                       'aliases': []})

        # Step 3: Load commodities (also labeled as Product)
        print("\nLoading commodities...")
        def commodity_params(row):
            countries = row['major_producing_countries'] if pd.notna(row.get('major_producing_countries')) else ''
            return {'id': row['id'], 'name': row['name'],
                    'countries': [c.strip() for c in countries.split(',') if c.strip()]}
        load_csv_data(session, os.path.join(DATA_DIR, 'commodities.csv'),
            "MERGE (c:Commodity:Product {id: $id}) SET c.name = $name, "
            "c.major_producing_countries = $countries, c.aliases = $aliases, c.match_status = 'matched'",
            lambda r: {**commodity_params(r), 'aliases': []})

        # Step 4: Load products
        print("\nLoading products...")
        def product_params(row):
            cats = row['categories'] if pd.notna(row.get('categories')) else ''
            return {'id': row['id'], 'name': row['name'],
                    'categories': [c.strip() for c in cats.split('|') if c.strip()],
                    'aliases': []}
        load_csv_data(session, os.path.join(DATA_DIR, 'products.csv'),
            "MERGE (p:Product {id: $id}) SET p.name = $name, p.categories = $categories, "
            "p.aliases = $aliases, p.match_status = 'matched'",
            product_params)

        # Step 5: Load ProductCategory nodes
        print("\nLoading product categories...")
        load_csv_data(session, os.path.join(DATA_DIR, 'product_categories.csv'),
            "MERGE (cat:ProductCategory {id: $id}) SET cat.name = $name",
            lambda r: {'id': r['id'], 'name': r['name']})

        # Step 6: Load [:归类于] edges (Product -> ProductCategory)
        print(safe("\nLoading [:归类于] edges..."))
        def categorized_params(row):
            return {'product_id': row['product_id'], 'category_id': row['category_id']}
        load_csv_data(session, os.path.join(DATA_DIR, 'edges_categorized.csv'),
            """MATCH (p:Product {id: $product_id})
               MATCH (cat:ProductCategory {id: $category_id})
               MERGE (p)-[r:归类于]->(cat)
               SET r.needs_review = false""",
            categorized_params)

        # Step 7: Load aliases onto existing nodes
        print("\nLoading aliases...")
        alias_groups: dict[str, list[str]] = defaultdict(list)
        alias_df = pd.read_csv(os.path.join(DATA_DIR, 'node_aliases.csv'), keep_default_na=False)
        for _, row in alias_df.iterrows():
            alias_groups[row['node_id']].append(row['alias'])
        for node_id, aliases in alias_groups.items():
            session.run(
                "MATCH (n {id: $id}) SET n.aliases = $aliases",
                {'id': node_id, 'aliases': aliases}
            )
        print(f"  loaded: node_aliases.csv ({len(alias_groups)} nodes with aliases)")

        # Step 8: Load [:提供] edges (with confidence)
        print(safe("\nLoading [:提供] edges..."))
        def provide_params(row):
            return {
                'company_id': row['company_id'],
                'product_id': row['product_id'],
                'margin': float(row['gross_margin_pct']) if row.get('gross_margin_pct') else None,
                'revenue_share': float(row['revenue_share_pct']) if row.get('revenue_share_pct') else None,
                'source': row.get('source') or None,
                'confidence': row.get('confidence') or None,
            }
        load_csv_data(session, os.path.join(DATA_DIR, 'edges_provide.csv'),
            """MATCH (c:Company {id: $company_id})
               MATCH (p:Product {id: $product_id})
               MERGE (c)-[r:提供]->(p)
               SET r.gross_margin_pct = $margin, r.revenue_share_pct = $revenue_share,
                   r.source = $source, r.confidence = $confidence, r.needs_review = false""",
            provide_params)

        # Step 9: Load [:供应给] edges
        print(safe("\nLoading [:供应给] edges..."))
        def supply_params(row):
            return {
                'from_id': row['from_id'], 'to_id': row['to_id'],
                'confidence': row.get('confidence') or None,
                'valid_from': row.get('valid_from') or None,
                'valid_until': row.get('valid_until') or None,
                'source': row.get('source') or None,
            }
        load_csv_data(session, os.path.join(DATA_DIR, 'edges_supply.csv'),
            """MATCH (from {id: $from_id})
               MATCH (to {id: $to_id})
               MERGE (from)-[r:供应给]->(to)
               SET r.confidence = $confidence, r.valid_from = $valid_from,
                   r.valid_until = $valid_until, r.source = $source,
                   r.needs_review = false""",
            supply_params)

        # Step 10: Load [:用于] edges
        print(safe("\nLoading [:用于] edges..."))
        def used_in_params(row):
            return {
                'from_id': row['from_id'], 'to_id': row['to_id'],
                'valid_from': row.get('valid_from') or None,
                'valid_until': row.get('valid_until') or None,
                'source': row.get('source') or None,
            }
        load_csv_data(session, os.path.join(DATA_DIR, 'edges_used_in.csv'),
            """MATCH (from {id: $from_id})
               MATCH (to {id: $to_id})
               MERGE (from)-[r:用于]->(to)
               SET r.valid_from = $valid_from, r.valid_until = $valid_until,
                   r.source = $source, r.needs_review = false""",
            used_in_params)

        # Step 11: Set match_status on Commodity nodes (override aliases-preset if needed)
        session.run("MATCH (c:Commodity) WHERE c.match_status IS NULL SET c.match_status = 'matched'")
        session.run("MATCH (n) WHERE n.match_status IS NULL SET n.match_status = 'matched'")

        # Step 12: Validate
        print("\nRunning validation queries...")
        passed = run_validation(session, os.path.join(SCHEMA_DIR, 'validation.cypher'))
        if passed:
            print("  All validation checks passed")
        else:
            print("  Some validation checks failed — see above")

        # Step 13: Summary
        print("\n--- Summary ---")
        for label in ['Company', 'Product', 'Commodity', 'ProductCategory']:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
            print(f"  {label}: {result.single()['count']}")

        for rel_type in ['提供', '供应给', '用于', '归类于']:
            result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
            print(safe(f"  :{rel_type}: {result.single()['count']}"))

    driver.close()


if __name__ == '__main__':
    main()
