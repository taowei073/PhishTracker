import spacy
import json
import os
from datetime import datetime

nlp = spacy.load("en_core_web_sm")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILES = [os.path.join(SCRIPT_DIR,"../data_collection", f) for f in ["twitter_data.json", "whois_data.json", "pastebin_data.json"]]
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "processed_data.json")

PHISHING_KEYWORDS = [
    "urgent", "account", "update", "login", "verify", "password", "credential",
    "phishing", "scam", "reset", "security", "alert", "suspended", "bank"
]

def is_valid_email(email):
    """Check if a string is a valid email format (enhanced check)."""
    if not email or not isinstance(email, str):
        return False
    # Check for presence of @
    if "@" not in email:
        return False
    # Split into local and domain parts
    parts = email.split("@", 1)  # Split only once to handle emails with multiple @
    if len(parts) != 2:
        return False
    local_part, domain_part = parts
    # Check local and domain parts are non-empty
    if not local_part.strip() or not domain_part.strip():
        return False
    # Domain must contain a dot and not start/end with it
    if "." not in domain_part:
        return False
    if domain_part.startswith(".") or domain_part.endswith("."):
        return False
    # Domain parts after splitting must be valid
    domain_subparts = domain_part.split(".")
    if len(domain_subparts) < 2 or any(not part for part in domain_subparts):
        return False
    return True

def extract_entities(text, explicit_emails=None):
    """Extract entities, prioritizing explicit emails if provided."""
    if not text or not isinstance(text, str):
        return {"domains": [], "ips": [], "emails": [], "keywords": []}
    doc = nlp(text)
    entities = {"domains": [], "ips": [], "emails": [], "keywords": []}
    
    # Use explicit emails first (must pass validation)
    if explicit_emails:
        for email in explicit_emails:
            if is_valid_email(email):
                entities["emails"].append(email.lower().strip())  # Normalize
                print(f"Added explicit email: {email}")
            else:
                print(f"Skipped invalid explicit email: {email}")

    # Track found emails to avoid duplicates
    seen_emails = set(entities["emails"])
    
    # Scan text for additional entities
    for token in doc:
        current_token = token.text.strip().lower()
        # Check for valid email in the token
        if "@" in current_token:
            if is_valid_email(current_token):
                email = current_token
                if email not in seen_emails:
                    entities["emails"].append(email)
                    seen_emails.add(email)
                    print(f"Found valid email in text: {email}")
            continue  # Skip further checks for this token if it's an email
        
        # Domain detection (simplified)
        if token.like_url:
            domain = token.text.split("//")[-1].split("/")[0].split(":")[0]
            if "." in domain and not domain[0].isdigit():
                entities["domains"].append(domain)
        
        # IP detection
        if token.text.count(".") == 3 and all(part.isdigit() and 0 <= int(part) <=255 for part in token.text.split(".")):
            entities["ips"].append(token.text)
        
        # Keyword check
        if current_token in PHISHING_KEYWORDS and current_token not in entities["keywords"]:
            entities["keywords"].append(current_token)
    
    # Remove duplicates from domains and ips
    entities["domains"] = list(set(entities["domains"]))
    entities["ips"] = list(set(entities["ips"]))
    
    print(f"Entities extracted: {entities}")
    return entities

def process_twitter(line):
    try:
        data = json.loads(line)
        if isinstance(data, dict) and "text" in data:
            text = data["text"]
            entities = extract_entities(text)
            return {
                "source": "twitter",
                "tweet_id": data.get("tweet_id", ""),
                "text": text,
                "username": data.get("username", "unknown"),
                "created_at": data.get("created_at", ""),
                "entities": entities
            }
        else:
            print(f"Skipping malformed Twitter data: {data}")
            return None
    except json.JSONDecodeError as e:
        print(f"Error decoding Twitter JSON: {e}")
        return None

def process_whois(line):
    try:
        data = json.loads(line)
        if isinstance(data, dict) and "domain" in data:
            # Handle emails safely, defaulting to empty list if None or invalid
            emails = data.get("emails", [])
            if emails is None or (isinstance(emails, str) and not emails.strip()):
                emails = []
            elif isinstance(emails, str):
                emails = [emails]  # Convert single string to list
            elif not isinstance(emails, list):
                emails = [str(emails)]  # Handle unexpected types
            
            # Filter for valid emails using the strict check
            valid_emails = [e for e in emails if is_valid_email(e)]
            
            # Use emails and text for entity extraction
            text = f"{data['domain']} {data.get('registrar', '')} {' '.join(valid_emails)}"
            entities = extract_entities(text, explicit_emails=valid_emails)
            print(f"Processed WHOIS for {data['domain']}: {entities}")
            return {
                "source": "whois",
                "domain": data["domain"],
                "registrar": data["registrar"],
                "creation_date": data.get("creation_date", ""),
                "entities": entities
            }
        else:
            print(f"Skipping malformed WHOIS data: {data}")
            return None
    except json.JSONDecodeError as e:
        print(f"Error decoding WHOIS JSON: {e}")
        return None

def process_pastebin(line):
    try:
        data = json.loads(line)
        if isinstance(data, dict) and "url" in data and "content" in data:
            text = data["content"]
            entities = extract_entities(text)
            # Try to link IPs to domains from WHOIS data (simplified example)
            linked_domains = []
            if entities["ips"]:
                # Assume we have access to WHOIS data or a lookup function
                # For now, this is a placeholder—implement a real lookup or correlation
                for ip in entities["ips"]:
                    # Hypothetical: Check if IP matches any WHOIS record (you’d need to store or query WHOIS data)
                    if ip == "87.106.162.209":  # Example IP from Pastebin
                        linked_domains.extend(["suspicious.site", "secure-update.org"])  # Example linkage
            return {
                "source": "pastebin",
                "url": data["url"],
                "content_preview": text[:200],
                "entities": entities,
                "linked_domains": linked_domains  # New field for dashboard
            }
        else:
            print(f"Skipping malformed Pastebin data: {data}")
            return None
    except json.JSONDecodeError as e:
        print(f"Error decoding Pastebin JSON: {e}")
        return None

def save_to_json(data, filename=OUTPUT_FILE):
    if data:  # Only save if data exists
        mode = "a" if os.path.exists(filename) else "w"
        try:
            with open(filename, mode, encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            print(f"Error saving to {filename}: {e}")

def main():
    print(f"Starting NLP processing at {datetime.now()}")
    processed_count = 0

    for input_file in INPUT_FILES:
        print(f"Processing {input_file}")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    processed_data = None
                    if "twitter" in input_file:
                        processed_data = process_twitter(line)
                    elif "whois" in input_file:
                        processed_data = process_whois(line)
                    elif "pastebin" in input_file:
                        processed_data = process_pastebin(line)
                    
                    if processed_data:
                        save_to_json(processed_data)
                        processed_count += 1
        except FileNotFoundError:
            print(f"File {input_file} not found. Skipping.")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

    print(f"Processing complete. Total items processed: {processed_count}")

if __name__ == "__main__":
    main()
