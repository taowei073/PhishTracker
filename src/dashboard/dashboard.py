from flask import Flask, render_template
from neo4j import GraphDatabase

app = Flask(__name__)

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "test1234"
DATABASE = "PhishTrackerDB"

class Neo4jClient:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_domains(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (d:Domain) 
                RETURN d.name, d.registrar, d.creation_date 
                LIMIT 20
            """)
            return [(record["d.name"], record["d.registrar"], record["d.creation_date"]) for record in result]

    def get_emails(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (e:Email) 
                RETURN e.address 
                LIMIT 20
            """)
            return [record["e.address"] for record in result]

    def get_ips(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (i:IP) 
                RETURN i.address 
                LIMIT 20
            """)
            return [record["i.address"] for record in result]

    def get_paste_connections(self):
        """Retrieve Pastebin links along with linked and extracted domains."""
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (p:Paste)
                OPTIONAL MATCH (p)-[:CONTAINS]->(d:Domain)
                OPTIONAL MATCH (p)-[:LINKED_TO]->(ld:Domain)
                RETURN p.url, COLLECT(DISTINCT d.name) AS Extracted_Domains, 
                              COLLECT(DISTINCT ld.name) AS Linked_Domains 
                LIMIT 20
            """)
            return [
                (record["p.url"], ', '.join(record["Extracted_Domains"] + record["Linked_Domains"]))
                for record in result
            ]

    def get_paste_keywords(self):
        """Retrieve Pastebin links with associated keywords."""
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (p:Paste)-[:HAS_KEYWORD]->(k:Keyword)
                RETURN p.url, COLLECT(DISTINCT k.text) AS Keywords
                LIMIT 20
            """)
            return [{
                "url": record["p.url"],
                "keywords": record["Keywords"]
            } for record in result]

neo4j_client = Neo4jClient(URI, USERNAME, PASSWORD)

@app.route('/')
def index():
    domains = neo4j_client.get_domains()
    paste_connections = neo4j_client.get_paste_connections()
    paste_keywords = neo4j_client.get_paste_keywords()
    emails = neo4j_client.get_emails()
    ips = neo4j_client.get_ips()
    return render_template(
        'index.html',
        domains=domains,
        paste_connections=paste_connections,
        paste_keywords=paste_keywords,
        emails=emails,
        ips=ips
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
