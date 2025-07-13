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

# --- 📡 Imports ---
import praw
import requests
import time
import datetime
import tweepy
import itertools
import re
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

# --- 🔐 API Keys (Replace with environment variables for Render) ---
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "jr0eeEBlgHV019FjqGpZIA")
REDDIT_SECRET = os.environ.get("REDDIT_SECRET", "VvgJtBukWWuoqbzQ0mzAvxaHPsQ3aw")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "lead-tracker:v1.0")

BEARER_TOKEN = os.environ.get("BEARER_TOKEN", "AAAAAAAAAAAAAAAAAAAAAGEO3AEAAAAA0y00O1vTqA%2FXnV2SJFlnzIaQAoI%3DWlyv3sNaTaKUeTJd62M19Qeg11IruNaL4ZbyUqanJqriLyKIje")

TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID", 29271301))
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "5efce68568312af5e01eea891cc75778")
TELEGRAM_PHONE = os.environ.get("TELEGRAM_PHONE", "+254769255782")
TELEGRAM_SESSION = "lead_tracker_session"

FIREBASE_BASE = os.environ.get("FIREBASE_BASE", "https://lead-tracker-a2181-default-rtdb.firebaseio.com/leads")

SUBREDDITS = [
    "Kenya", "askKenya", "realestate", "freelance", "developers",
    "webdev", "CarsForSale", "CarTalk", "mechanicadvice"
]

KEYWORDS = {
    "tutoring": ["need math tutor", "tuition for form", "math revision", "physics tutor", "urgent math help", "kcse revision", "form 4 revision", "biology tuition"],
    "real_estate": ["buying land", "selling plot", "plot in mombasa", "real estate mombasa", "land for sale", "plot wanted"],
    "web_dev": ["need website", "build app", "looking for developer", "create site", "mobile app", "website developer", "web design", "app for my business"],
    "vehicles": ["selling car", "buying car", "sell my car", "car for sale", "toyota for sale", "buy motorbike", "selling motorbike", "selling lorry", "selling truck", "bus for sale", "matatu for sale", "car wanted", "vehicle wanted", "sell motorbike", "car hire kenya", "used car", "subaru for sale", "#carforsaleKenya", "#buycarKenya", "#motorbikeKenya", "#carKenya", "#usedcars"]
}

EXCLUDE_PHRASES = ["i offer", "my services", "hire me", "i do tutoring", "developer here", "available for hire", "i can help", "i provide", "i'm a tutor", "i do web"]

SEEN_TEXTS = set()

# --- 🧠 Helper Functions ---
def normalize_text(text):
    text = text.lower()
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_post(text):
    text = text.lower()
    if any(x in text for x in EXCLUDE_PHRASES):
        return None
    for category, terms in KEYWORDS.items():
        if any(term in text for term in terms):
            return category
    return None

# --- ☁️ Save to Firebase ---
def post_to_firebase(post_id, lead):
    norm = normalize_text(lead['title'])
    if norm in SEEN_TEXTS:
        print("⚠️ Duplicate skipped:", lead['title'][:60])
        return
    SEEN_TEXTS.add(norm)

    url = f"{FIREBASE_BASE}/{post_id}.json"
    try:
        check = requests.get(url)
        if check.status_code == 200 and check.json():
            print(f"⚠️ Already in Firebase: {lead['title']}")
            return
        res = requests.put(url, json=lead)
        if res.status_code == 200:
            print(f"✅ Saved: {lead['title']}")
        else:
            print(f"❌ Firebase error: {res.text}")
    except Exception as e:
        print("❌ Firebase connection error:", e)

# --- Reddit Scanner ---
def scan_reddit():
    print("\n📥 Scanning Reddit...")
    reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID, client_secret=REDDIT_SECRET, user_agent=REDDIT_USER_AGENT)
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
            print(f"❌ Reddit /r/{sub} error:", e)

# --- Twitter Scanner ---
twitter_category_cycle = itertools.cycle(KEYWORDS.keys())

def scan_twitter():
    print("\n📥 Scanning Twitter...")
    try:
        client = tweepy.Client(bearer_token=BEARER_TOKEN)
        category = next(twitter_category_cycle)
        query = " OR ".join(KEYWORDS[category])
        print(f"🔍 Searching: {category}")
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
    except tweepy.TooManyRequests:
        print("❌ Twitter rate limit hit, sleeping 15 min...")
        time.sleep(900)
    except Exception as e:
        print("❌ Twitter error:", e)

# --- Telegram Group Loader ---
def load_telegram_groups():
    try:
        with open("groups.txt", "r") as file:
            groups = [line.strip() for line in file if line.strip()]
            print(f"📂 {len(groups)} Telegram groups loaded.")
            return groups
    except Exception as e:
        print("❌ Error reading groups.txt:", e)
        return []

# --- Telegram Scanner ---
def scan_telegram():
    print("\n📥 Scanning Telegram...")
    try:
        client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH, timeout=5)
        client.connect()

        if not client.is_user_authorized():
            print("🔐 Login required.")
            client.send_code_request(TELEGRAM_PHONE)
            code = input("📲 Enter code from Telegram: ")
            client.sign_in(TELEGRAM_PHONE, code)

        for group in load_telegram_groups():
            try:
                username = group.split("/")[-1]
                entity = client.get_entity(username)
                print(f"🔍 {username}...")

                messages = client(GetHistoryRequest(peer=entity, limit=10, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0)).messages
                for message in messages:
                    try:
                        text = getattr(message, 'message', '') or (getattr(message.media, 'caption', '') if message.media else '')
                        if message.fwd_from:
                            if hasattr(message.fwd_from, 'from_name'):
                                text = f"(Forwarded from {message.fwd_from.from_name}): {text}"
                            elif hasattr(message.fwd_from, 'channel_id'):
                                text = f"(Forwarded from channel {message.fwd_from.channel_id}): {text}"

                        if text:
                            print("📩", text[:60])
                            category = is_valid_post(text)
                            if category:
                                post_id = f"telegram_{message.id}"
                                lead = {
                                    "title": text,
                                    "url": f"https://t.me/{username}",
                                    "subreddit": "N/A",
                                    "author": str(message.from_id.user_id if message.from_id else "Unknown"),
                                    "created_utc": message.date.timestamp(),
                                    "timestamp": time.time(),
                                    "category": category,
                                    "source": "Telegram"
                                }
                                post_to_firebase(post_id, lead)
                    except Exception as inner:
                        print("❌ Telegram message error:", inner)
            except Exception as e:
                print(f"❌ Group scan failed {group}:", e)
        client.disconnect()
    except Exception as e:
        print("❌ Telegram error:", e)

# --- 🔁 Main Tracker ---
def run_combined_tracker():
    while True:
        scan_reddit()
        scan_twitter()
        scan_telegram()
        print("⏸ Sleeping 3 minutes...\n")
        time.sleep(180)

# --- 🚀 Start Everything ---
if __name__ == "__main__":
    keep_alive()
    run_combined_tracker()
