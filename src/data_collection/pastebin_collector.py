#!/usr/bin/env python
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime


class PastebinCollector:
    def __init__(self,
                 archive_url="https://pastebin.com/archive",
                 keywords=None,
                 output_file=None,
                 delay=10,
                 link_limit=10):
        self.archive_url = archive_url
        self.keywords = keywords or ["phishing", "login", "password", "credential"]
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_file = output_file or os.path.join(self.script_dir, "pastebin_data.json")
        self.delay = delay  # Delay in seconds between requests
        self.link_limit = link_limit  # Maximum number of paste links to process
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        # Pattern for Pastebin paste IDs: usually an 8-character alphanumeric string, preceded by a slash.
        self.paste_pattern = re.compile(r"^/[A-Za-z0-9]{8}$")

    def fetch_archive(self):
        """Fetch the Pastebin archive page."""
        try:
            response = requests.get(self.archive_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching Pastebin archive: {e}")
            return None

    def extract_links(self, html):
        """Extract paste links from the archive page using regex on href values."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="maintable")
        if not table:
            print("No paste table found on archive page.")
            return []
        links = []
        # Search for all <a> tags within the table and filter by the expected paste ID pattern.
        for a_tag in table.find_all("a"):
            href = a_tag.get("href", "").strip()
            if self.paste_pattern.match(href):
                paste_id = href.strip("/")
                full_url = f"https://pastebin.com/raw/{paste_id}"
                if full_url not in links:
                    links.append(full_url)
        print(f"DEBUG: Extracted {len(links)} paste links before limiting.")
        limited_links = links[:self.link_limit]
        print(f"DEBUG: Returning {len(limited_links)} paste links (limit set to {self.link_limit}).")
        return limited_links

    def fetch_paste_content(self, url):
        """Fetch raw paste content and check for phishing keywords."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            content = response.text
            if any(keyword.lower() in content.lower() for keyword in self.keywords):
                return {"url": url, "content": content}
            return None
        except requests.RequestException as e:
            print(f"Error fetching paste '{url}': {e}")
            return None

    def save_to_json(self, data):
        """Append data to the output JSON file."""
        mode = "a" if os.path.exists(self.output_file) else "w"
        try:
            with open(self.output_file, mode, encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
            print(f"Data written to {self.output_file}")
        except Exception as e:
            print(f"Error saving to {self.output_file}: {e}")

    def collect_data(self):
        """Main method to collect and save Pastebin data."""
        print(f"Starting Pastebin collection at {datetime.now()}")
        all_data = []

        archive_html = self.fetch_archive()
        if not archive_html:
            return all_data

        paste_links = self.extract_links(archive_html)
        print(f"Found {len(paste_links)} paste links to process.")

        for url in paste_links:
            print(f"Fetching paste: '{url}'")
            paste_data = self.fetch_paste_content(url)
            if paste_data:
                all_data.append(paste_data)
                self.save_to_json(paste_data)
                print(f"Saved paste data from '{url}'")
            else:
                print(f"No matching keywords found in paste '{url}'.")
            time.sleep(self.delay)

        print(f"Collection complete. Total pastes saved: {len(all_data)}")
        return all_data

    def run(self):
        """Run the Pastebin data collection process."""
        self.collect_data()


if __name__ == "__main__":
    collector = PastebinCollector(link_limit=10)
    collector.run()
