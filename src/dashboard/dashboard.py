from flask import Flask, render_template
from neo4j import GraphDatabase
import os

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
            result = session.run("MATCH (d:Domain) RETURN d.name, d.registrar, d.creation_date LIMIT 10")
            return [(record["d.name"], record["d.registrar"], record["d.creation_date"]) for record in result]

    def get_emails(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("MATCH (e:Email) RETURN e.address LIMIT 10")
            return [record["e.address"] for record in result]

    def get_ips(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("MATCH (i:IP) RETURN i.address LIMIT 10")
            return [record["i.address"] for record in result]

    def get_paste_connections(self):
        with self.driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (p:Paste)-[:CONTAINS]->(d:Domain)
                RETURN p.url, d.name LIMIT 10
            """)
            return [(record["p.url"], record["d.name"]) for record in result]

neo4j_client = Neo4jClient(URI, USERNAME, PASSWORD)

@app.route('/')
def index():
    domains = neo4j_client.get_domains()
    paste_connections = neo4j_client.get_paste_connections()
    emails = neo4j_client.get_emails()
    ips = neo4j_client.get_ips()
    return render_template('index.html', domains=domains, paste_connections=paste_connections, emails=emails, ips=ips)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)