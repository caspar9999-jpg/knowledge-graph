from neo4j import GraphDatabase
import os

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'schema')

def run_cypher_file(session, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for statement in content.split(';'):
        stmt = statement.strip()
        if stmt and not stmt.startswith('//'):
            session.run(stmt)
            print(f"  executed: {stmt[:60]}...")

def main():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        print("Running constraints.cypher...")
        run_cypher_file(session, os.path.join(SCHEMA_DIR, 'constraints.cypher'))
        print("Constraints created.")

    driver.close()

if __name__ == '__main__':
    main()
