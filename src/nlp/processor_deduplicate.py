import json
import os

# Ensure paths are always correct
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "../nlp", "processed_data.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "../nlp", "processed_data_deduped.json")


def load_records(filename):
    """Load records from a JSON file."""
    records = []
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. No deduplication performed.")
        return records
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def deduplicate_records(records):
    """Remove duplicate records based on unique keys."""
    unique = {}
    for record in records:
        key = None
        if record["source"] == "twitter":
            key = f"twitter_{record.get('tweet_id')}"
        elif record["source"] == "whois":
            key = f"whois_{record.get('domain')}"
        elif record["source"] == "pastebin":
            key = f"pastebin_{record.get('url')}"
        if key:
            unique[key] = record  # Store the latest record with the same key
    return list(unique.values())


def save_records(records, filename):
    """Save deduplicated records back to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        for record in records:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")


def remove_duplicates():
    """Wrapper function to load, deduplicate, and save records."""
    print(f"Checking for processed data at: {INPUT_FILE}")

    records = load_records(INPUT_FILE)
    if not records:
        print("No records found. Skipping deduplication.")
        return
    print(f"Loaded {len(records)} records")

    deduped = deduplicate_records(records)
    print(f"Deduplicated to {len(deduped)} records")

    save_records(deduped, OUTPUT_FILE)
    print(f"Deduplicated data saved to {OUTPUT_FILE}")


# Ensure this script runs when executed directly
if __name__ == "__main__":
    remove_duplicates()
