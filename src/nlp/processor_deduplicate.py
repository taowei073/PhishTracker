import json
import os

INPUT_FILE = "processed_data.json"
OUTPUT_FILE = "processed_data_deduped.json"

def load_records(filename):
    records = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def deduplicate_records(records):
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
            unique[key] = record
    return list(unique.values())

def save_records(records, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for record in records:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")

if __name__ == "__main__":
    records = load_records(INPUT_FILE)
    print(f"Loaded {len(records)} records")
    deduped = deduplicate_records(records)
    print(f"Deduplicated to {len(deduped)} records")
    save_records(deduped, OUTPUT_FILE)
