from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as s:
    # Q1: Nutrien -> downstream companies  
    r = s.run("""MATCH path = (start:Company {id: 'c01'})
                 -[:提供|供应给*1..6]->
                 (end:Company)
                 WHERE NOT start = end
                 RETURN [n IN nodes(path) | n.id] AS node_path,
                        length(path) AS hops
                 ORDER BY hops LIMIT 5""")
    print("Q1: Nutrien commercial chain")
    for rec in r:
        p = '-'.join(rec['node_path'])
        print(f"  {p} ({rec['hops']} hops)")

    # Q2: Potash -> leaf products  
    r = s.run("""MATCH path = (m {id: 'm01'})-[:用于*1..6]->(p:Product)
                 WHERE NOT EXISTS { (p)-[:用于]->() }
                 RETURN [n IN nodes(path) | n.id] AS node_path,
                        length(path) AS hops
                 ORDER BY hops LIMIT 5""")
    print("\nQ2: Potash composition chain")
    for rec in r:
        p = '-'.join(rec['node_path'])
        print(f"  {p} ({rec['hops']} hops)")

    # Q3: Top common dependencies  
    r = s.run("""MATCH (c:Company)-[*1..2]-(m:Product)
                 WITH m, count(DISTINCT c) AS cnt
                 WHERE cnt >= 3
                 RETURN m.id AS id, cnt ORDER BY cnt DESC LIMIT 5""")
    print("\nQ3: Common dependencies (top 5)")
    for rec in r:
        print(f"  {rec['id']}: {rec['cnt']} companies")

    # Q4: Animal Feed suppliers  
    r = s.run("""MATCH (p:Product {id: 'p07'})<-[:提供]-(c:Company)
                 RETURN c.id, c.name ORDER BY c.id""")
    print("\nQ4: Animal Feed suppliers")
    for rec in r:
        print(f"  {rec['c.id']}: {rec['c.name']}")

    # Q5: Top hubs  
    r = s.run("""MATCH (n) WHERE n.id IS NOT NULL
                 OPTIONAL MATCH (n)-[ro]->()
                 WITH n, count(ro) AS out_d
                 OPTIONAL MATCH (n)<-[ri]-()
                 WITH n, out_d, count(ri) AS in_d
                 RETURN n.id, out_d + in_d AS total
                 ORDER BY total DESC LIMIT 5""")
    print("\nQ5: Top hubs (total degree)")
    for rec in r:
        print(f"  {rec['n.id']}: {rec['total']}")

driver.close()
