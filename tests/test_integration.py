import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase

from importers.common import EntityResolver
from importers.earnings_calls import EarningsCallImporter

pytestmark = pytest.mark.run_integration

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "relations_sample.jsonl")


@pytest.fixture(scope="module")
def driver():
    _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield _driver
    _driver.close()


@pytest.fixture(scope="module")
def seed_graph(driver):
    from scripts import schema_init, load_data

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    schema_init.run_cypher_file(
        driver.session(),
        os.path.join(os.path.dirname(__file__), "..", "schema", "constraints.cypher"),
    )

    load_data.main()


class TestEndToEnd:
    def test_importer_creates_correct_edges(self, driver, seed_graph):
        """Verify the importer writes edges with correct properties."""
        resolver = EntityResolver(driver=driver)
        importer = EarningsCallImporter(driver, resolver)

        stats = importer.process_file(FIXTURE_PATH)

        assert stats["processed"] == 10
        assert stats["skipped_division"] == 1
        assert stats["skipped_termination"] == 1

        with driver.session() as session:
            total = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            assert total >= 61, f"Expected at least 61 edges, got {total}"

    def test_provide_edges_have_confidence(self, driver, seed_graph):
        with driver.session() as session:
            rows = list(session.run("MATCH ()-[r:提供]->() WHERE r.relation_id IS NOT NULL RETURN r.confidence AS c, r.relation_id AS id"))
            assert len(rows) >= 2, f"Expected multiple importer [:提供] edges, got {len(rows)}"

    def test_supplies_to_without_dates_has_needs_review(self, driver, seed_graph):
        with driver.session() as session:
            rows = list(session.run(
                "MATCH ()-[r:供应给]->() WHERE r.needs_review = true RETURN r.relation_id AS id"
            ))
            assert len(rows) >= 1

    def test_used_in_edges_have_no_confidence(self, driver, seed_graph):
        with driver.session() as session:
            rows = list(session.run(
                "MATCH ()-[r:用于]->() WHERE r.relation_id IS NOT NULL RETURN r"
            ))
            for row in rows:
                r = row["r"]
                assert not hasattr(r, "confidence") or r.get("confidence") is None

    def test_stub_entities_created(self, driver, seed_graph):
        with driver.session() as session:
            rows = list(session.run(
                "MATCH (n {match_status: 'unmatched'}) RETURN n.id AS id, n.name AS name"
            ))
            stub_names = [r["name"] for r in rows]
            assert any("Novel Plant Protein" in n for n in stub_names)

    def test_source_string_is_structured(self, driver, seed_graph):
        with driver.session() as session:
            row = session.run(
                "MATCH ()-[r]->() WHERE r.relation_id = 'SYNTH--relation--0001' RETURN r.source AS src"
            ).single()
            assert row is not None
            src = row["src"]
            assert src.startswith("transcript:") and "speaker:" in src and "excerpt:" in src

    def test_service_entities_mapped_to_product(self, driver, seed_graph):
        with driver.session() as session:
            rows = list(session.run(
                "MATCH (n:Product) WHERE n.name CONTAINS 'Logistics' RETURN n.id AS id"
            ))
            assert len(rows) >= 1

    def test_verification_queries_still_work(self, driver, seed_graph):
        with driver.session() as session:
            result = session.run(
                """MATCH path = (start:Company {id: 'c01'})
                   -[:提供|供应给*1..6]->
                   (end:Company)
                   WHERE NOT start = end
                     AND length(path) >= 2
                   RETURN count(path) AS cnt"""
            ).single()
            assert result["cnt"] > 0, "Q1 should find paths"

            result = session.run(
                """MATCH path = (m {id: 'm01'})-[:用于*1..6]->(p:Product)
                   WHERE NOT EXISTS { (p)-[:用于]->() }
                   RETURN count(path) AS cnt"""
            ).single()
            assert result["cnt"] > 0, "Q2 should find paths"

    def test_product_category_nodes_exist(self, driver, seed_graph):
        with driver.session() as session:
            count = session.run("MATCH (n:ProductCategory) RETURN count(n) AS cnt").single()["cnt"]
            assert count == 9

    def test_products_have_categorize_edges(self, driver, seed_graph):
        with driver.session() as session:
            count = session.run("MATCH ()-[r:归类于]->() RETURN count(r) AS cnt").single()["cnt"]
            assert count == 13
