import json
import requests
from pathlib import Path
import os

API_URL = os.getenv("PUSH_API_URL")
SECRET = os.getenv("PUSH_API_SECRET")

STATE_FILE = Path("data/notified.json")


def load_state():
    if not STATE_FILE.exists():
        return {}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def notify(item_name, url):
    requests.post(
        API_URL,
        json={
            "secret": SECRET,
            "title": "🚨 Meaco 有貨！",
            "body": item_name,
            "url": url,
        },
        timeout=20,
    )