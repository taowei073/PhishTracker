#!/usr/bin/env python
import argparse
import sys, os

# Corrected imports to match the actual project structure
from src.data_collection import twitter_collector, whois_collector, pastebin_collector
from src.nlp import nlp_processor, processor_deduplicate
from src.correlation import neo4j_loader
from src.dashboard import dashboard as flask_app


def run_data_collection():
    """Start data collection from different sources."""
    print("Starting data collection...")
    try:
        twitter_collector.collect_tweets()  # Fetch phishing-related tweets
        whois_collector.fetch_domains()  # Fetch WHOIS information
        pastebin_collector.collect_pastes()  # Scrape Pastebin for phishing data
    except Exception as e:
        print(f"Error during data collection: {e}")
        sys.exit(1)


def run_data_processing():
    """Process collected data using NLP and store relationships in Neo4j."""
    print("Processing data with NLP and correlation...")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROCESSED_DATA_PATH = os.path.join(SCRIPT_DIR, "src", "nlp", "processed_data.json")
    try:
        # Step 1: Run NLP processing
        nlp_processor.main()

        # Step 2: Deduplicate processed data
        processor_deduplicate.remove_duplicates()

        # Step 3: Load data into Neo4j
        if hasattr(neo4j_loader, 'load_data'):
            neo4j_loader.load_data()
        else:
            print("Error: `load_data()` not found in neo4j_loader.py")
            sys.exit(1)

    except Exception as e:
        print(f"Error during data processing: {e}")
        sys.exit(1)


def launch_dashboard():
    """Launch the Flask-based web dashboard."""
    print("Launching Flask dashboard...")
    try:
        flask_app.app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error launching dashboard: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='PhishTracker: An OSINT-based Phishing Attribution Framework')
    parser.add_argument('--collect', action='store_true',
                        help='Run the data collection modules')
    parser.add_argument('--process', action='store_true',
                        help='Run the NLP and correlation pipelines')
    parser.add_argument('--dashboard', action='store_true',
                        help='Launch the Flask dashboard')

    args = parser.parse_args()

    if args.collect:
        run_data_collection()
    elif args.process:
        run_data_processing()
    elif args.dashboard:
        launch_dashboard()
    else:
        # If no argument is provided, display help message
        parser.print_help()


if __name__ == '__main__':
    main()
