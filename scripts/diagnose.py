from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'password')

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as s:
    print("All nodes:")
    for r in s.run("MATCH (n) RETURN n.id, labels(n) ORDER BY n.id"):
        print("  id=%-10s labels=%s" % (r["n.id"], str(r["labels(n)"])))
    print("Edge counts:")
    for r in s.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY t"):
        t = r["t"].encode("ascii", errors="replace").decode()
        print("  %s: %d" % (t, r["c"]))
driver.close()
