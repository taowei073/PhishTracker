import requests
from bs4 import BeautifulSoup
import json
import time
import os 
from datetime import datetime

# Configuration
PASTEBIN_URL = "https://pastebin.com/archive"
KEYWORDS = ["phishing", "login", "password", "credential"]  # Phishing-related terms
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "pastebin_data.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_pastebin_archive():
    """Fetch the Pastebin archive page."""
    try:
        response = requests.get(PASTEBIN_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching Pastebin archive: {e}")
        return None

def extract_paste_links(html):
    """Extract paste links from the archive page."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="maintable")
    if not table:
        print("No paste table found on archive page.")
        return []
    links = []
    for row in table.find_all("tr")[1:]:  # Skip header row
        title_cell = row.find("a")
        if title_cell and "href" in title_cell.attrs:
            paste_id = title_cell["href"].strip("/")
            links.append(f"https://pastebin.com/raw/{paste_id}")
    return links[:10]  # Limit to 10 pastes to respect rate limits

def fetch_paste_content(url):
    """Fetch raw paste content and check for phishing keywords."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        content = response.text
        if any(keyword.lower() in content.lower() for keyword in KEYWORDS):
            return {"url": url, "content": content}
        return None
    except requests.RequestException as e:
        print(f"Error fetching paste '{url}': {e}")
        return None

# def save_to_json(data, filename=OUTPUT_FILE):
#     """Append data to a JSON file."""
#     try:
#         with open(filename, "a", encoding="utf-8") as f:
#             json.dump(data, f, ensure_ascii=False)
#             f.write("\n")
#     except Exception as e:
#         print(f"Error saving to JSON: {e}")

def save_to_json(data, filename=OUTPUT_FILE):
    mode = "a" if os.path.exists(filename) else "w"
    try:
        with open(filename, mode, encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
        print(f"Data written to {filename}")
    except Exception as e:
        print(f"Error saving to {filename}: {e}")

def main():
    print(f"Starting Pastebin collection at {datetime.now()}")
    folder_path = os.getcwd()
    all_data = []

    # Fetch archive page
    archive_html = fetch_pastebin_archive()
    if not archive_html:
        return

    # Get paste links
    paste_links = extract_paste_links(archive_html)
    print(f"Found {len(paste_links)} paste links to process")

    # Fetch and filter pastes
    for url in paste_links:
        print(f"Fetching paste: '{url}'")
        paste_data = fetch_paste_content(url)
        if paste_data:
            all_data.append(paste_data)
            save_to_json(paste_data)
            print(f"Saved paste data from '{url}'")
        
        time.sleep(10)  # Respect Pastebin’s robots.txt (conservative delay)

    print(f"Collection complete. Total pastes saved: {len(all_data)}")

if __name__ == "__main__":
    # Install dependencies: pip install requests beautifulsoup4
    main()