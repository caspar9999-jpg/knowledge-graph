"""
Import relations from a pipeline relations JSONL file into the knowledge graph.

Usage:
    python scripts/02_import_relations.py --relations ../path/to/relations_2025Q1.jsonl

Credentials via environment variables (or .env):
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from importers.common import EntityResolver
from importers.earnings_calls import EarningsCallImporter

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'schema')


def _run_cypher_file(session, filepath: str) -> None:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = [line for line in content.split('\n') if not line.strip().startswith('//')]
    clean = '\n'.join(lines)
    for statement in clean.split(';'):
        stmt = statement.strip()
        if stmt:
            session.run(stmt)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import relations JSONL into Neo4j knowledge graph"
    )
    parser.add_argument(
        "--relations",
        required=True,
        help="Path to relations_XXXXQN.jsonl file from the pipeline",
    )
    args = parser.parse_args()

    relations_path = Path(args.relations)
    if not relations_path.exists():
        print(f"Error: file not found: {relations_path}")
        sys.exit(1)

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        print("Error: NEO4J_PASSWORD not set. Add to .env or set environment variable.")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))

    print("Step 1: Running schema constraints...")
    with driver.session() as session:
        _run_cypher_file(session, os.path.join(SCHEMA_DIR, "constraints.cypher"))
    print("  OK")

    print("Step 2: Running validation...")
    with driver.session() as session:
        _run_cypher_file(session, os.path.join(SCHEMA_DIR, "validation.cypher"))
    print("  OK")

    print("Step 3: Importing relations...")
    resolver = EntityResolver(driver)
    with driver.session() as session:
        resolver.load_cache(session)
    importer = EarningsCallImporter(driver, resolver)
    stats = importer.process_file(str(relations_path))
    print(f"  Importer stats: {stats}")

    driver.close()
    print("Done.")


if __name__ == "__main__":
    main()
