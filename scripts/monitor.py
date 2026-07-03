import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

CONFIG = Path(__file__).parent / "config.json"
STATE = Path(__file__).parent / "state.json"

OUT_OF_STOCK_KEYWORDS = [
    "sold out",
    "out of stock",
    "currently unavailable",
    "notify me when available",
]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json,text/html,*/*",
})


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


def get_shopify_product_json_url(product_url):
    parsed = urlparse(product_url)
    path = parsed.path.rstrip("/")

    if not path.endswith(".js"):
        path = f"{path}.js"

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def check_stock_with_shopify(product_url):
    json_url = get_shopify_product_json_url(product_url)

    response = session.get(json_url, timeout=20)
    response.raise_for_status()

    product = response.json()
    variants = product.get("variants", [])

    available_variants = [
        variant
        for variant in variants
        if variant.get("available") is True
    ]

    if available_variants:
        print("Shopify API: available variant found")
        for variant in available_variants:
          print(f"- {variant.get('title')} / £{variant.get('price')}")
        return True

    print("Shopify API: no available variants")
    return False


def check_stock_with_html(product_url):
    response = session.get(product_url, timeout=20)
    response.raise_for_status()

    html = response.text.lower()

    for keyword in OUT_OF_STOCK_KEYWORDS:
        if keyword in html:
            print(f"HTML fallback: found keyword '{keyword}'")
            return False

    print("HTML fallback: no out-of-stock keyword found")
    return True


def check_stock(product_url):
    for attempt in range(1, 4):
        try:
            try:
                return check_stock_with_shopify(product_url)
            except Exception as shopify_error:
                print(f"Shopify API failed: {shopify_error}")
                return check_stock_with_html(product_url)

        except Exception as error:
            print(f"Attempt {attempt}/3 failed: {error}")

            if attempt < 3:
                time.sleep(2)

    print("All attempts failed. Treating as out of stock.")
    return False


def send_push_notification(product_name, product_url):
    api_url = os.getenv("PUSH_API_URL")
    secret = os.getenv("PUSH_API_SECRET")

    print("PUSH_API_URL =", api_url)
    print("PUSH_API_SECRET exists =", bool(secret))

    if not api_url or not secret:
        print("Push API not configured. Skipping notification.")
        return False

    response = session.post(
        api_url,
        json={
            "secret": secret,
            "title": "🚨 Meaco 有貨！",
            "body": f"{product_name} 已經可以買",
            "url": product_url,
        },
        timeout=20,
    )

   
    print("Final URL =", response.url)
    print("Status =", response.status_code)
    print("Content-Type =", response.headers.get("content-type"))
    print("Body =", response.text[:200])
    return response.ok


def main():
    print("=" * 60)
    print("Stock monitor started")
    print(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    print("=" * 60)

    config = load_config()
    state = load_state()

    for product in config["products"]:
        name = product["name"]
        url = product["url"]

        print()
        print("=" * 60)
        print(name)
        print(url)

        in_stock = check_stock(url)
        was_in_stock = state.get(name, False)

        print("Previous stock:", was_in_stock)
        print("Current stock :", in_stock)

        if in_stock and not was_in_stock:
            print("🎉 BACK IN STOCK! Sending push notification...")
            sent = send_push_notification(name, url)

            if sent:
                print("✅ Notification sent")
            else:
                print("⚠️ Notification failed")

        elif in_stock and was_in_stock:
            print("In stock already. No duplicate notification.")

        elif not in_stock and was_in_stock:
            print("Out of stock again. Resetting state.")

        else:
            print("Still out of stock. No notification.")

        state[name] = in_stock

    save_state(state)

    print()
    print("=" * 60)
    print("Stock monitor finished")
    print("=" * 60)


if __name__ == "__main__":
    main()