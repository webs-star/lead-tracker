import praw
import requests
import time
import datetime
import tweepy

# --- Reddit API ---
REDDIT_CLIENT_ID = "jr0eeEBlgHV019FjqGpZIA"
REDDIT_SECRET = "VvgJtBukWWuoqbzQ0mzAvxaHPsQ3aw"
REDDIT_USER_AGENT = "lead-tracker:v1.0 by Pristine-Ad-3177"
SUBREDDITS = [
    "Kenya", "askKenya", "realestate", "freelance", "developers", "webdev",
     "CarsForSale",  "CarTalk", "mechanicadvice"
]


# --- Twitter API ---
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAGEO3AEAAAAA0y00O1vTqA%2FXnV2SJFlnzIaQAoI%3DWlyv3sNaTaKUeTJd62M19Qeg11IruNaL4ZbyUqanJqriLyKIje"  # 🔐 Replace this

# --- Firebase ---
FIREBASE_BASE = "https://lead-tracker-a2181-default-rtdb.firebaseio.com/leads"

# --- Filters ---

KEYWORDS = {
    "tutoring": [
        "need math tutor", "tuition for form", "math revision", "physics tutor",
        "urgent math help", "kcse revision", "form 4 revision", "biology tuition"
    ],
    "real_estate": [
        "buying land", "selling plot", "plot in mombasa", "real estate mombasa",
        "land for sale", "plot wanted"
    ],
    "web_dev": [
        "need website", "build app", "looking for developer", "create site",
        "mobile app", "website developer", "web design", "app for my business"
    ],
    "vehicles": [
         "selling car", "buying car", "sell my car", "car for sale",
    "toyota for sale", "buy motorbike", "selling motorbike", "selling lorry",
    "selling truck", "bus for sale", "matatu for sale", "car wanted",
    "vehicle wanted", "sell motorbike", "car hire kenya", "used car",
    "subaru for sale",
    "#carforsaleKenya", "#buycarKenya", "#motorbikeKenya", "#carKenya", "#usedcars"
    ]
}


EXCLUDE_PHRASES = [
    "i offer", "my services", "hire me", "i do tutoring", "developer here",
    "available for hire", "i can help", "i provide", "i'm a tutor", "i do web"
]


def is_valid_post(text):
    text = text.lower()
    if any(x in text for x in EXCLUDE_PHRASES):
        return None
    for category, terms in KEYWORDS.items():
        if any(term in text for term in terms):
            return category
    return None


def post_to_firebase(post_id, lead):
    url = f"{FIREBASE_BASE}/{post_id}.json"
    if requests.get(url).json():
        print(f"⚠️ Already exists: {lead['title']}")
        return
    try:
        res = requests.put(url, json=lead)
        if res.status_code == 200:
            print(f"✅ Saved: {lead['title']}")
    except Exception as e:
        print("❌ Firebase error:", e)


def scan_reddit():
    print("\n📥 Scanning Reddit...")
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    for sub in SUBREDDITS:
        try:
            for post in reddit.subreddit(sub).new(limit=25):
                if not post.title:
                    continue
                match = is_valid_post(post.title)
                if match:
                    post_id = f"reddit_{post.id}"
                    lead = {
                        "title": post.title,
                        "url": f"https://reddit.com{post.permalink}",
                        "subreddit": str(post.subreddit),
                        "author": str(post.author),
                        "created_utc": post.created_utc,
                        "timestamp": time.time(),
                        "category": match,
                        "source": "Reddit"
                    }
                    post_to_firebase(post_id, lead)
        except Exception as e:
            print(f"❌ Reddit error in /r/{sub}:", e)


def scan_twitter():
    print("\n📥 Scanning Twitter...")
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    queries = {k: " OR ".join(v) for k, v in KEYWORDS.items()}

    for category, query in queries.items():
        try:
            print(f"🔍 Searching tweets for: {category}")
            tweets = client.search_recent_tweets(query=query, max_results=10)
            for tweet in tweets.data or []:
                text = tweet.text
                if is_valid_post(text):
                    tweet_id = f"twitter_{tweet.id}"
                    lead = {
                        "title": text,
                        "url": f"https://twitter.com/user/status/{tweet.id}",
                        "subreddit": "N/A",
                        "author": "Twitter",
                        "created_utc": datetime.datetime.now().timestamp(),
                        "timestamp": time.time(),
                        "category": category,
                        "source": "Twitter"
                    }
                    post_to_firebase(tweet_id, lead)
        except Exception as e:
            print(f"❌ Twitter error: {e}")
            print("⏳ Sleeping 5 minutes to respect rate limits...")
            time.sleep(300)
            break


def run_combined_tracker():
    while True:
        scan_reddit()
        scan_twitter()
        print("⏸ Waiting 3 minutes...\n")
        time.sleep(180)


if __name__ == "__main__":
    run_combined_tracker()
