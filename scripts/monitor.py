import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

CONFIG = Path(__file__).parent / "config.json"
STATE = Path(__file__).parent / "state.json"


def load_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if not STATE.exists():
        return {}

    with open(STATE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def check_stock(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers, timeout=20)

    html = r.text.lower()

    keywords = [
        "sold out",
        "out of stock",
        "currently unavailable"
    ]

    for keyword in keywords:
        if keyword in html:
            return False

    return True


def main():
    config = load_config()
    state = load_state()

    for product in config["products"]:

        print("=" * 50)
        print(product["name"])

        in_stock = check_stock(product["url"])

        print("Stock:", in_stock)

        old = state.get(product["name"])

        if old is False and in_stock is True:
            print("🎉 BACK IN STOCK!")

        state[product["name"]] = in_stock

    save_state(state)


if __name__ == "__main__":
    main()