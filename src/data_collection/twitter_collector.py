import tweepy
import json
import time
import os
from datetime import datetime

# Twitter API credentials (replace with your actual token)
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN") # Ensure this is set
KEYWORDS = ["urgent account update", "login issue", "verify your account", "phishing","account verification","credential harvest"]
#query = '(phishing OR "account verification" OR "credential harvest") lang:en -is:retweet'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "twitter_data.json")

# Adjusted limits based on dashboard (100 posts/month instead of 1500)
MONTHLY_POST_LIMIT = 2  # Total posts retrievable per month (as per dashboard)
MAX_PER_REQUEST = 10      # Reduced to fetch fewer posts per call (was 100)
REQUESTS_PER_WINDOW = 18 # Max requests per 15-min window (900 seconds)
WINDOW_DURATION = 900     # 15 minutes in seconds
SAFETY_THRESHOLD = 1     # Reserve 10 posts for debugging/testing

# Track usage
usage_file = "twitter_usage.json"

def load_usage():
    """Load usage data from file, ensuring all required keys are present."""
    default_usage = {
        "posts_fetched": 0,
        "last_reset": str(datetime.now().replace(day=1).date()),
        "window_start": time.time(),
        "requests_in_window": 0
    }
    try:
        with open(usage_file, "r") as f:
            usage = json.load(f)
            # Ensure all required keys are present
            for key in default_usage:
                if key not in usage:
                    usage[key] = default_usage[key]
            return usage
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn’t exist or is invalid, use default
        return default_usage

# Initialize usage with all required keys
usage = load_usage()

# Initialize Tweepy client (v2 API)
try:
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
except tweepy.TweepyException as e:
    print(f"Error initializing Twitter client: {e}")
    exit(1)

def check_usage_limit():
    """Check and reset monthly post limit, reserving posts for debugging."""
    now = datetime.now()
    last_reset = datetime.strptime(usage["last_reset"], "%Y-%m-%d")
    if now.month != last_reset.month:
        usage["posts_fetched"] = 0
        usage["last_reset"] = str(now.replace(day=1).date())
    remaining_posts = MONTHLY_POST_LIMIT - usage["posts_fetched"]
    return remaining_posts > SAFETY_THRESHOLD  # Only proceed if more than 10 posts remain

def check_window_limit():
    """Check and reset 15-minute request window, using dynamic wait if possible."""
    now = time.time()
    if now - usage["window_start"] >= WINDOW_DURATION:
        usage["window_start"] = now
        usage["requests_in_window"] = 0
    return usage["requests_in_window"] < REQUESTS_PER_WINDOW

def update_usage(count, request_made=False):
    """Update usage tracking file with thread safety."""
    usage["posts_fetched"] += count
    if request_made:
        usage["requests_in_window"] += 1
    try:
        with open(usage_file, "w") as f:
            json.dump(usage, f)
    except Exception as e:
        print(f"Error updating usage file: {e}")

def fetch_tweets(query, max_results=MAX_PER_REQUEST):
    """Fetch tweets with retry on rate limit, using Retry-After header if available."""
    remaining_posts = MONTHLY_POST_LIMIT - usage["posts_fetched"]
    if remaining_posts <= 0:
        print("Monthly post limit reached!")
        return None
    max_results = min(max_results, remaining_posts)

    for attempt in range(3):  # Retry up to 3 times
        try:
            tweets = client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["created_at", "author_id", "text"],
                user_fields=["username"],
                expansions=["author_id"]
            )
            update_usage(len(tweets.data) if tweets.data else 0, request_made=True)
            return tweets
        except tweepy.TweepyException as e:
            if e.response and e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After", WINDOW_DURATION)
                print(f"Rate limit hit (429) for '{query}'. Waiting {retry_after} seconds (Attempt {attempt + 1}/3)...")
                time.sleep(int(retry_after))
                usage["window_start"] = time.time()  # Reset window after wait
                usage["requests_in_window"] = 0
            elif e.response and e.response.status_code in [401, 403]:
                print(f"Authentication or permission error for '{query}': {e}")
                return None
            else:
                print(f"Error fetching tweets for '{query}': {e}")
                return None
    print(f"Failed to fetch '{query}' after 3 attempts due to rate limits.")
    return None

def process_tweets(tweets):
    """Extract relevant data from tweets, with deduplication and validation."""
    if not tweets or not tweets.data:
        return []
    users = {u["id"]: u["username"] for u in tweets.includes.get("users", [])}
    tweet_data = []
    seen_tweets = set()  # Track unique tweets by tweet_id
    for tweet in tweets.data:
        if not hasattr(tweet, 'id') or not hasattr(tweet, 'text') or not hasattr(tweet, 'created_at'):
            print(f"Skipping malformed tweet data: {tweet}")
            continue
        tweet_id = tweet.id
        if tweet_id not in seen_tweets:
            tweet_info = {
                "tweet_id": tweet_id,
                "text": tweet.text,
                "created_at": str(tweet.created_at),
                "username": users.get(tweet.author_id, "unknown")
            }
            tweet_data.append(tweet_info)
            seen_tweets.add(tweet_id)
    return tweet_data

def save_to_json(data, filename=OUTPUT_FILE):
    """Append data to a JSON file, ensuring no duplicates and validating input."""
    if not data or not isinstance(data, list):
        print(f"Error: Invalid data format for saving - expected list, got {type(data)}")
        return
    try:
        # Read existing file to check for duplicates
        seen_tweets = set()
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            tweet = json.loads(line)
                            seen_tweets.add(tweet["tweet_id"])
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Warning: Skipping malformed line in {filename}: {e}")

        # Filter out duplicates and save new data
        new_data = [item for item in data if item["tweet_id"] not in seen_tweets]
        if new_data:
            mode = "a" if os.path.exists(filename) else "w"
            with open(filename, mode, encoding="utf-8", newline="\n") as f:
                for item in new_data:
                    if not isinstance(item, dict) or "tweet_id" not in item or "text" not in item:
                        print(f"Warning: Skipping invalid tweet data: {item}")
                        continue
                    json.dump(item, f, ensure_ascii=False)
                    f.write("\n")
            print(f"Saved {len(new_data)} new tweets to {filename}")
    except Exception as e:
        print(f"Error saving to {filename}: {e}")

def main():
    print(f"Starting Twitter collection at {datetime.now()}")
    if not BEARER_TOKEN:
        print("Error: BEARER_TOKEN is not set. Please update the script with your Twitter API bearer token.")
        return

    if not check_usage_limit():
        print("Cannot proceed: Monthly post limit reached or too few posts remain for safety.")
        return

    all_data = []

    for keyword in KEYWORDS:
        if not check_usage_limit():
            print("Monthly post limit reached during this run. Stopping collection.")
            break
        if not check_window_limit():
            wait_time = WINDOW_DURATION - (time.time() - usage["window_start"])
            print(f"Hit 15-min request limit ({usage['requests_in_window']}/{REQUESTS_PER_WINDOW}). Waiting {wait_time:.0f} seconds...")
            time.sleep(wait_time)
            usage["window_start"] = time.time()
            usage["requests_in_window"] = 0

        print(f"Fetching tweets for: '{keyword}'")
        tweets = fetch_tweets(keyword)
        if tweets and tweets.data:
            processed_data = process_tweets(tweets)
            if processed_data:
                save_to_json(processed_data)
                all_data.extend(processed_data)
                update_usage(len(processed_data), request_made=True)
                print(f"Saved {len(processed_data)} tweets for '{keyword}' (Total fetched: {usage['posts_fetched']}/{MONTHLY_POST_LIMIT}, {100 * usage['posts_fetched'] / MONTHLY_POST_LIMIT:.1f}%)")
            else:
                print(f"No new data for '{keyword}' after deduplication")
        else:
            print(f"No data for '{keyword}'")

        # Increase delay to 30 seconds to slow down collection and conserve quota
        time.sleep(30)  # More conservative delay to spread out requests

    print(f"Collection complete. Total tweets this run: {len(all_data)}. Total this month: {usage['posts_fetched']}/{MONTHLY_POST_LIMIT} ({100 * usage['posts_fetched'] / MONTHLY_POST_LIMIT:.1f}%)")

if __name__ == "__main__":
    main()
