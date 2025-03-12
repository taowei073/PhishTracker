#!/usr/bin/env python
import whois
import json
import time
import os
from datetime import datetime


class WhoisCollector:
    def __init__(self, domains=None, output_file=None):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.domains = domains or [
            "example.com",
            "suspicious.site",
            "login-phish.net",
            "secure-update.org",
            "bank-alert.com"
        ]
        self.output_file = output_file or os.path.join(self.script_dir, "whois_data.json")

    def fetch_whois(self, domain):
        """
        Fetch WHOIS data for a single domain.
        Retries up to 3 times on failure.
        """
        for attempt in range(3):
            try:
                w = whois.whois(domain)
                if w.status is None:
                    print(f"No WHOIS data for '{domain}'")
                    return None
                # Ensure emails are stored as a list
                emails = w.emails if hasattr(w, "emails") and w.emails else []
                if emails and isinstance(emails, str):
                    emails = [emails]
                whois_data = {
                    "domain": domain,
                    "registrar": w.registrar,
                    "creation_date": str(w.creation_date) if w.creation_date else None,
                    "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                    "name_servers": w.name_servers,
                    "registrant": w.registrant if hasattr(w, "registrant") else None,
                    "emails": emails,
                    "updated_date": str(w.updated_date) if w.updated_date else None,
                    "status": w.status
                }
                return whois_data
            except Exception as e:
                print(f"Attempt {attempt + 1}/3 failed for '{domain}': {e}")
                time.sleep(10)
        print(f"Failed to fetch WHOIS for '{domain}' after 3 attempts.")
        return None

    def save_to_json(self, data):
        """
        Save a single WHOIS data entry to the output JSON file.
        Appends if the file already exists.
        """
        mode = "a" if os.path.exists(self.output_file) else "w"
        print(f"Attempting to write to: {self.output_file}")
        try:
            with open(self.output_file, mode, encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
                f.flush()
            print(f"Successfully wrote data to {self.output_file}")
        except Exception as e:
            print(f"Failed to save to {self.output_file}: {e}")
            raise

    def collect_data(self):
        """
        Iterate through the list of domains, fetch their WHOIS data,
        save the data, and pause between requests.
        """
        print(f"Starting WHOIS collection at {datetime.now()}")
        all_data = []

        for domain in self.domains:
            print(f"Fetching WHOIS for: '{domain}'")
            whois_data = self.fetch_whois(domain)
            if whois_data:
                all_data.append(whois_data)
                self.save_to_json(whois_data)
                print(f"Saved WHOIS data for '{domain}'")
            else:
                print(f"No data for '{domain}'")

            time.sleep(5)

        print(f"Collection complete. Total domains processed: {len(all_data)}")
        if os.path.exists(self.output_file):
            print(f"Output saved to {self.output_file}")
        else:
            print(f"Warning: {self.output_file} not created!")
        return all_data

    def run(self):
        """
        Run the entire WHOIS data collection process.
        """
        self.collect_data()


if __name__ == "__main__":
    collector = WhoisCollector()
    collector.run()
