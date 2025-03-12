from neo4j import GraphDatabase
import json
import os
from datetime import datetime

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "test1234"  # Update this!
DATABASE = "PhishTrackerDB"      # Target database
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR,"../nlp", "processed_data_deduped.json")

class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print("Testing connection...")
        self.driver.verify_connectivity()
        print("Connection successful!")

    def close(self):
        self.driver.close()

    def clear_database(self):
        with self.driver.session(database=DATABASE) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print(f"Database '{DATABASE}' cleared.")

    def load_tweet(self, data):
        with self.driver.session(database=DATABASE) as session:
            print(f"Loading tweet: {data['tweet_id']}")
            session.run("""
                MERGE (t:Tweet {tweet_id: $tweet_id})
                SET t.text = $text, t.created_at = $created_at, t.username = $username
            """, **data)

            for domain in data["entities"]["domains"]:
                session.run("""
                    MERGE (d:Domain {name: $domain})
                    MERGE (t:Tweet {tweet_id: $tweet_id})-[:MENTIONS]->(d)
                """, {"tweet_id": data["tweet_id"], "domain": domain})
                print(f"Linked tweet {data['tweet_id']} to domain {domain}")

            for ip in data["entities"]["ips"]:
                session.run("""
                    MERGE (i:IP {address: $ip})
                    MERGE (t:Tweet {tweet_id: $tweet_id})-[:MENTIONS]->(i)
                """, {"tweet_id": data["tweet_id"], "ip": ip})
                print(f"Linked tweet {data['tweet_id']} to IP {ip}")

            # NEW: Link keywords
            for kw in data["entities"].get("keywords", []):
                session.run("""
                    MERGE (k:Keyword {text: $kw})
                    MERGE (t:Tweet {tweet_id: $tweet_id})-[:HAS_KEYWORD]->(k)
                """, {"tweet_id": data["tweet_id"], "kw": kw})
                print(f"Linked tweet {data['tweet_id']} to keyword {kw}")

    def load_whois(self, data):
        creation_date = data["creation_date"]
        if isinstance(creation_date, str) and creation_date.startswith("[datetime.datetime"):
            creation_date = creation_date.split(",")[0].strip("[datetime.datetime(").split(")")[0]
            creation_date = " ".join(creation_date.split())
        with self.driver.session(database=DATABASE) as session:
            print(f"Loading domain: {data['domain']}")
            session.run("""
                MERGE (d:Domain {name: $domain})
                SET d.registrar = $registrar, d.creation_date = $creation_date
            """, domain=data["domain"], registrar=data["registrar"], creation_date=creation_date)
            for email in data["entities"]["emails"]:
                session.run("""
                    MERGE (e:Email {address: $email})
                    MERGE (d:Domain {name: $domain})-[:REGISTERED_WITH]->(e)
                """, {"domain": data["domain"], "email": email})
                print(f"Linked domain {data['domain']} to email {email}")
            for domain in data["entities"]["domains"]:  # Ensure self-links if present
                if domain != data["domain"]:  # Avoid self-reference
                    session.run("""
                        MERGE (d2:Domain {name: $linked_domain})
                        MERGE (d:Domain {name: $domain})-[:RELATED]->(d2)
                    """, {"domain": data["domain"], "linked_domain": domain})
                    print(f"Linked domain {data['domain']} to related domain {domain}")

    def load_pastebin(self, data):
        with self.driver.session(database=DATABASE) as session:
            # Begin a transaction
            tx = session.begin_transaction()
            try:
                print(f"Loading paste: {data['url']}")

                # Ensure the Paste node exists
                tx.run("""
                    MERGE (p:Paste {url: $url})
                    SET p.content_preview = $content_preview
                """, {"url": data["url"], "content_preview": data.get("content_preview", "")})

                # Use a set to track domains and avoid duplicates
                all_domains = set()

                # Handle extracted domains (from paste content)
                for domain in data["entities"].get("domains", []):
                    normalized_domain = domain.lower().strip()
                    all_domains.add(normalized_domain)

                    tx.run("""
                        MERGE (d:Domain {name: $domain})
                        MERGE (p:Paste {url: $url})-[:CONTAINS]->(d)
                    """, {"url": data["url"], "domain": normalized_domain})
                    print(f"Linked paste {data['url']} to extracted domain {normalized_domain}")

                # Handle explicitly linked domains
                for linked_domain in data.get("linked_domains", []):
                    normalized_linked = linked_domain.lower().strip()

                    # Prevent duplicate domain merging
                    if normalized_linked not in all_domains:
                        tx.run("""
                            MERGE (d:Domain {name: $linked_domain})
                            MERGE (p:Paste {url: $url})-[:LINKED_TO]->(d)
                        """, {"url": data["url"], "linked_domain": normalized_linked})
                        print(f"Linked paste {data['url']} to linked domain {normalized_linked}")

                # Link Paste to extracted IPs
                for ip in data["entities"].get("ips", []):
                    tx.run("""
                        MERGE (i:IP {address: $ip})
                        MERGE (p:Paste {url: $url})-[:HOSTED_ON]->(i)
                    """, {"url": data["url"], "ip": ip})
                    print(f"Linked paste {data['url']} to IP {ip}")

                # Link Paste to extracted Keywords
                for kw in data["entities"].get("keywords", []):
                    normalized_kw = kw.lower().strip()
                    tx.run("""
                        MERGE (k:Keyword {text: $kw})
                        MERGE (p:Paste {url: $url})-[:HAS_KEYWORD]->(k)
                    """, {"url": data["url"], "kw": normalized_kw})
                    print(f"Linked paste {data['url']} to keyword {normalized_kw}")

                # Commit the transaction
                tx.commit()
            except Exception as e:
                tx.rollback()
                print(f"Error in load_pastebin: {e}")

    def load_data(self):
        print(f"Starting Neo4j load at {datetime.now()} into database '{DATABASE}'")
        twitter_found = False
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print(f"Found {len(lines)} records in {INPUT_FILE}")
                if not lines:
                    print("No data to process!")
                    return
                for i, line in enumerate(lines, 1):
                    if not line.strip():
                        print(f"Skipping empty line {i}")
                        continue
                    try:
                        data = json.loads(line)
                        key = data.get('tweet_id', data.get('domain', data.get('url')))
                        print(f"Processing record {i}: {data['source']} - {key}")
                        if data["source"] == "twitter":
                            self.load_tweet(data)
                            twitter_found = True
                        elif data["source"] == "whois":
                            self.load_whois(data)
                        elif data["source"] == "pastebin":
                            self.load_pastebin(data)
                        else:
                            print(f"Unknown source in record {i}: {data['source']}")
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON in line {i}: {e}")
                    except KeyError as e:
                        print(f"Missing key in record {i}: {e}")
            if not twitter_found:
                print("Warning: No Twitter data found in processed_data.json")
        except FileNotFoundError:
            print(f"Error: {INPUT_FILE} not found.")
        except Exception as e:
            print(f"Error loading data: {e}")
        print("Neo4j load complete.")

def main():
    loader = Neo4jLoader(URI, USERNAME, PASSWORD)
    loader.clear_database()  # Reset to ensure clean slate
    loader.load_data()
    loader.close()

if __name__ == "__main__":
    main()