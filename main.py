# --- 🟢 Flask keep-alive server ---
from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "✅ Lead Tracker is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()


# --- 📡 Lead Tracker Imports ---
import praw
import requests
import time
import datetime
import tweepy
import itertools
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest


# --- 🔐 Reddit API ---
REDDIT_CLIENT_ID = "jr0eeEBlgHV019FjqGpZIA"
REDDIT_SECRET = "VvgJtBukWWuoqbzQ0mzAvxaHPsQ3aw"
REDDIT_USER_AGENT = "lead-tracker:v1.0 by Pristine-Ad-3177"
SUBREDDITS = [
    "Kenya", "askKenya", "realestate", "freelance", "developers", "webdev",
    "CarsForSale", "CarTalk", "mechanicadvice"
]

# --- 🔐 Twitter API ---
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAGEO3AEAAAAA0y00O1vTqA%2FXnV2SJFlnzIaQAoI%3DWlyv3sNaTaKUeTJd62M19Qeg11IruNaL4ZbyUqanJqriLyKIje"

# --- 🔐 Telegram API ---
TELEGRAM_API_ID = 29271301  # Replace with your actual API ID
TELEGRAM_API_HASH = "5efce68568312af5e01eea891cc75778"
TELEGRAM_PHONE = "+254769255782"
TELEGRAM_SESSION = "lead_tracker_session"

# --- 🔗 Firebase Base URL ---
FIREBASE_BASE = "https://lead-tracker-a2181-default-rtdb.firebaseio.com/leads"

# --- 🔍 Keyword Filters ---
KEYWORDS = {
    "tutoring": [...],
    "real_estate": [...],
    "web_dev": [...],
    "vehicles": [...]
}

EXCLUDE_PHRASES = [
    "i offer", "my services", "hire me", "i do tutoring", "developer here",
    "available for hire", "i can help", "i provide", "i'm a tutor", "i do web"
]


# --- ✅ Lead Validator ---
def is_valid_post(text):
    text = text.lower()
    if any(x in text for x in EXCLUDE_PHRASES):
        return None
    for category, terms in KEYWORDS.items():
        if any(term in text for term in terms):
            return category
    return None


# --- ☁️ Send to Firebase ---
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


# --- 🔎 Scan Reddit ---
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


# --- 🔁 Twitter: Rotate Categories Each Run ---
twitter_category_cycle = itertools.cycle(KEYWORDS.keys())

def scan_twitter():
    print("\n📥 Scanning Twitter...")
    try:
        client = tweepy.Client(bearer_token=BEARER_TOKEN)
        category = next(twitter_category_cycle)
        query = " OR ".join(KEYWORDS[category])
        print(f"🔍 Searching tweets for: {category}")
        try:
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
            time.sleep(60)
        except tweepy.TooManyRequests:
            print("❌ Rate limit hit: Too Many Requests")
            print("⏳ Sleeping 15 minutes...")
            time.sleep(900)
        except Exception as e:
            print(f"❌ Twitter error during category {category}: {e}")
    except Exception as e:
        print(f"❌ Failed to authenticate with Twitter API: {e}")


# --- 🔎 Scan Telegram ---
def scan_telegram():
    print("\n📥 Scanning Telegram...")
    try:
        client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        client.connect()

        if not client.is_user_authorized():
            print("🔐 Logging in...")
            client.send_code_request(TELEGRAM_PHONE)
            code = input("📲 Enter the code from Telegram: ")
            client.sign_in(TELEGRAM_PHONE, code)

        target_groups = [
            "https://t.me/kenyajobs",
            "https://t.me/realestatekenya",
            "https://t.me/tutorke"
        ]

        for group in target_groups:
            try:
                entity = client.get_entity(group)
                messages = client(GetHistoryRequest(
                    peer=entity,
                    limit=20,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                )).messages

                for message in messages:
                    if hasattr(message, 'message') and message.message:
                        category = is_valid_post(message.message)
                        if category:
                            post_id = f"telegram_{message.id}"
                            lead = {
                                "title": message.message,
                                "url": group,
                                "subreddit": "N/A",
                                "author": str(message.from_id.user_id if message.from_id else "Unknown"),
                                "created_utc": message.date.timestamp(),
                                "timestamp": time.time(),
                                "category": category,
                                "source": "Telegram"
                            }
                            post_to_firebase(post_id, lead)
            except Exception as e:
                print(f"❌ Error scanning {group}:", e)

        client.disconnect()

    except Exception as e:
        print("❌ Telegram connection error:", e)


# --- 🔁 Main Loop ---
def run_combined_tracker():
    while True:
        scan_reddit()
        scan_twitter()
        scan_telegram()
        print("⏸ Waiting 3 minutes...\n")
        time.sleep(180)


# --- 🧠 Entry Point ---
if __name__ == "__main__":
    keep_alive()
    run_combined_tracker()

