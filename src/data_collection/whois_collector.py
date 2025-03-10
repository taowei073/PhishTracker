import whois
import json
import time
import os
from datetime import datetime

try:
    import whois
except ImportError:
    print("Error: 'python-whois' not installed. Run 'pip install python-whois'.")
    exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOMAINS = ["example.com", "suspicious.site", "login-phish.net", "secure-update.org", "bank-alert.com"]
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "whois_data.json")

def fetch_whois(domain):
    for attempt in range(3):
        try:
            w = whois.whois(domain)
            if w.status is None:
                print(f"No WHOIS data for '{domain}'")
                return None
            # Handle emails as a list, even if single
            emails = w.emails if hasattr(w, "emails") and w.emails else []
            if emails and isinstance(emails, str):
                emails = [emails]  # Convert string to list
            whois_data = {
                "domain": domain,
                "registrar": w.registrar,
                "creation_date": str(w.creation_date) if w.creation_date else None,
                "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                "name_servers": w.name_servers,
                "registrant": w.registrant if hasattr(w, "registrant") else None,
                "emails": emails,  # Now a list
                "updated_date": str(w.updated_date) if w.updated_date else None,
                "status": w.status
            }
            return whois_data
        except Exception as e:
            print(f"Attempt {attempt + 1}/3 failed for '{domain}': {e}")
            time.sleep(10)
    print(f"Failed to fetch WHOIS for '{domain}' after 3 attempts.")
    return None

def save_to_json(data, filename=OUTPUT_FILE):
    mode = "a" if os.path.exists(filename) else "w"
    print(f"Attempting to write to: {filename}")
    try:
        with open(filename, mode, encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
            f.flush()
        print(f"Successfully wrote data to {filename}")
    except Exception as e:
        print(f"Failed to save to {filename}: {e}")
        raise

def main():
    print(f"Starting WHOIS collection at {datetime.now()}")
    print(f"Script directory: {SCRIPT_DIR}")
    all_data = []

    for domain in DOMAINS:
        print(f"Fetching WHOIS for: '{domain}'")
        whois_data = fetch_whois(domain)
        if whois_data:
            all_data.append(whois_data)
            save_to_json(whois_data)
            print(f"Saved WHOIS data for '{domain}'")
        else:
            print(f"No data for '{domain}'")
        
        time.sleep(5)

    print(f"Collection complete. Total domains processed: {len(all_data)}")
    if os.path.exists(OUTPUT_FILE):
        print(f"Output saved to {OUTPUT_FILE}")
    else:
        print(f"Warning: {OUTPUT_FILE} not created!")

if __name__ == "__main__":
    main()