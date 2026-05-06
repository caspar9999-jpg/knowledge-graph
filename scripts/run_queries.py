from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'password')

QUERY_DIR = os.path.join(os.path.dirname(__file__), '..', 'queries', 'verification')

def load_query(filename, defaults=None):
    with open(os.path.join(QUERY_DIR, filename), 'r', encoding='utf-8') as f:
        content = f.read()
    lines = [l for l in content.split('\n') if not l.strip().startswith('//')]
    clean = '\n'.join(lines)
    parts = clean.split(';')
    return parts[0].strip()  # first non-comment statement

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as s:
    queries = [
        ("Q1: Commercial dependency chain (Nutrien to companies)",
         load_query('01_dependency_chain.cypher'),
         {'start_company': 'c01', 'confidence_levels': ['confirmed', 'inferred']}),
        ("Q2: Physical composition chain (Potash)",
         load_query('02_composition_chain.cypher'),
         {'start_material': 'm01'}),
        ("Q3: Common dependency",
         load_query('03_common_dependency.cypher'),
         {'min_companies': 2}),
        ("Q4: Alternate supplier (Animal Feed)",
         load_query('04_alternate_supplier.cypher'),
         {'product_id': 'p07'}),
        ("Q5: Hub analysis",
         load_query('05_hub_analysis.cypher'),
         {}),
    ]

    for name, query, params in queries:
        print("\n=== %s ===" % name)
        try:
            results = list(s.run(query, **params))
            if results:
                for i, rec in enumerate(results[:5]):
                    print("  Result %d:" % (i+1))
                    for k in rec.keys():
                        v = rec[k]
                        if isinstance(v, str):
                            v = v.encode('ascii', errors='replace').decode()
                        print("    %s: %s" % (k, str(v)[:100]))
            else:
                print("  No results")
            print("  (%d total results)" % len(results))
        except Exception as e:
            print("  ERROR: %s" % str(e).encode('ascii', errors='replace').decode()[:200])

driver.close()
