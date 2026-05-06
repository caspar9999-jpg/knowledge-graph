from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as s:
    r = s.run("CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")
    for rec in r:
        name = rec["name"]
        version = rec["versions"][0]
        edition = rec["edition"]
        print("Product: %s" % name)
        print("Version: %s" % version)
        print("Edition: %s" % edition)

    # Check constraints
    print("\nConstraints:")
    for rec in s.run("SHOW CONSTRAINTS"):
        for k, v in rec.items():
            print("  %s: %s" % (k, v))

    # Check indexes
    print("\nIndexes:")
    for rec in s.run("SHOW INDEXES"):
        for k, v in rec.items():
            if k in ("name", "type", "entityType", "labelsOrTypes", "properties"):
                print("  %s: %s" % (k, v))

driver.close()
