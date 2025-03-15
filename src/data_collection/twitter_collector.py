import tweepy
import json
import time
import os
from datetime import datetime


class TwitterCollector:
    """ A class-based Twitter collector for fetching tweets based on specific keywords. """

    # Class-level configuration
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_FILE = os.path.join(SCRIPT_DIR, "twitter_data.json")
    USAGE_FILE = os.path.join(SCRIPT_DIR, "twitter_usage.json")

    # Twitter API credentials
    BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")  # Ensure this is set

    # Query settings
    KEYWORDS = [
        "urgent account update", "login issue", "verify your account",
        "phishing", "account verification", "credential harvest"
    ]

    # API limits
    MONTHLY_POST_LIMIT = 100  # Example limit
    MAX_PER_REQUEST = 10
    REQUESTS_PER_WINDOW = 18  # Requests allowed per 15-min window
    WINDOW_DURATION = 900  # 15 minutes
    SAFETY_THRESHOLD = 1  # Reserve 1 post for debugging

    def __init__(self):
        """Initialize the Twitter client and load usage tracking."""
        self.usage = self.load_usage()

        try:
            self.client = tweepy.Client(bearer_token=self.BEARER_TOKEN)
        except tweepy.TweepyException as e:
            print(f"Error initializing Twitter client: {e}")
            exit(1)

    def load_usage(self):
        """Load usage data from file or initialize if missing."""
        default_usage = {
            "posts_fetched": 0,
            "last_reset": str(datetime.now().replace(day=1).date()),
            "window_start": time.time(),
            "requests_in_window": 0
        }
        try:
            with open(self.USAGE_FILE, "r") as f:
                usage = json.load(f)
                # Ensure all required keys are present
                for key in default_usage:
                    if key not in usage:
                        usage[key] = default_usage[key]
                return usage
        except (FileNotFoundError, json.JSONDecodeError):
            return default_usage

    def check_usage_limit(self):
        """Check and reset monthly post limit if needed."""
        now = datetime.now()
        last_reset = datetime.strptime(self.usage["last_reset"], "%Y-%m-%d")
        if now.month != last_reset.month:
            self.usage["posts_fetched"] = 0
            self.usage["last_reset"] = str(now.replace(day=1).date())
        return (self.MONTHLY_POST_LIMIT - self.usage["posts_fetched"]) > self.SAFETY_THRESHOLD

    def check_window_limit(self):
        """Ensure request limits per 15-minute window."""
        now = time.time()
        if now - self.usage["window_start"] >= self.WINDOW_DURATION:
            self.usage["window_start"] = now
            self.usage["requests_in_window"] = 0
        return self.usage["requests_in_window"] < self.REQUESTS_PER_WINDOW

    def update_usage(self, count, request_made=False):
        """Update API usage statistics."""
        self.usage["posts_fetched"] += count
        if request_made:
            self.usage["requests_in_window"] += 1
        try:
            with open(self.USAGE_FILE, "w") as f:
                json.dump(self.usage, f)
        except Exception as e:
            print(f"Error updating usage file: {e}")

    def fetch_tweets(self, query, max_results=None):
        """Fetch tweets for a given query, handling rate limits."""
        remaining_posts = self.MONTHLY_POST_LIMIT - self.usage["posts_fetched"]
        if remaining_posts <= 0:
            print("Monthly post limit reached!")
            return None
        max_results = min(max_results or self.MAX_PER_REQUEST, remaining_posts)

        for attempt in range(3):
            try:
                tweets = self.client.search_recent_tweets(
                    query=query,
                    max_results=max_results,
                    tweet_fields=["created_at", "author_id", "text"],
                    expansions=["author_id"]
                )
                self.update_usage(len(tweets.data) if tweets.data else 0, request_made=True)
                return tweets
            except tweepy.TweepyException as e:
                if hasattr(e, "response") and e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", self.WINDOW_DURATION)
                    print(f"Rate limit hit for '{query}'. Waiting {retry_after} seconds...")
                    time.sleep(int(retry_after))
                elif hasattr(e, "response") and e.response.status_code in [401, 403]:
                    print(f"Authentication error: {e}")
                    return None
                else:
                    print(f"Error fetching tweets: {e}")
                    return None
        return None

    def process_tweets(self, tweets):
        """Process and clean up tweet data."""
        if not tweets or not tweets.data:
            return []
        tweet_data = []
        seen_tweets = set()
        users = {u["id"]: u["username"] for u in tweets.includes.get("users", [])}

        for tweet in tweets.data:
            tweet_id = tweet.id
            if tweet_id not in seen_tweets:
                tweet_data.append({
                    "tweet_id": tweet_id,
                    "text": tweet.text,
                    "created_at": str(tweet.created_at),
                    "username": users.get(tweet.author_id, "unknown")
                })
                seen_tweets.add(tweet_id)
        return tweet_data

    def save_to_json(self, data):
        """Save collected tweets to a JSON file."""
        if not data:
            return
        seen_tweets = set()
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            tweet = json.loads(line)
                            seen_tweets.add(tweet["tweet_id"])
                        except json.JSONDecodeError:
                            continue

        new_data = [item for item in data if item["tweet_id"] not in seen_tweets]
        if new_data:
            with open(self.OUTPUT_FILE, "a", encoding="utf-8", newline="\n") as f:
                for item in new_data:
                    json.dump(item, f, ensure_ascii=False)
                    f.write("\n")
            print(f"Saved {len(new_data)} new tweets to {self.OUTPUT_FILE}")

    def collect_tweets(self):
        """Main function to fetch and save tweets for all keywords."""
        print(f"Starting Twitter collection at {datetime.now()}")
        if not self.BEARER_TOKEN:
            print("Error: Twitter API token is missing!")
            return

        if not self.check_usage_limit():
            print("Cannot proceed: Monthly post limit reached.")
            return

        for keyword in self.KEYWORDS:
            if not self.check_usage_limit():
                break
            if not self.check_window_limit():
                wait_time = self.WINDOW_DURATION - (time.time() - self.usage["window_start"])
                print(f"Hit request limit. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)

            print(f"Fetching tweets for: '{keyword}'")
            tweets = self.fetch_tweets(keyword)
            if tweets and tweets.data:
                processed_data = self.process_tweets(tweets)
                self.save_to_json(processed_data)
                print(f"Saved {len(processed_data)} tweets for '{keyword}'")

            time.sleep(30)

        print("Collection complete.")


# Run script if executed directly
if __name__ == "__main__":
    collector = TwitterCollector()
    collector.collect_tweets()
