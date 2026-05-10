"""
Run this once to exchange your short-lived token for a long-lived page token.
After running, PAGE_ACCESS_TOKEN in .env will be filled in automatically.
"""
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
PAGE_ID = os.getenv("PAGE_ID")
SHORT_LIVED_TOKEN = os.getenv("SHORT_LIVED_TOKEN")


def save_to_env(key, value):
    with open(".env", "r") as f:
        content = f.read()
    content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
    with open(".env", "w") as f:
        f.write(content)


def main():
    print("Step 1: Exchanging short-lived token for long-lived user token...")
    resp = requests.get("https://graph.facebook.com/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": SHORT_LIVED_TOKEN,
    })
    exchange = resp.json()
    if "access_token" not in exchange:
        print(f"Token exchange failed: {exchange}")
        return
    long_lived_user_token = exchange["access_token"]
    print("Long-lived user token obtained.")

    print(f"\nStep 2: Fetching page token directly for Page ID {PAGE_ID}...")
    resp = requests.get(f"https://graph.facebook.com/v25.0/{PAGE_ID}", params={
        "fields": "access_token,name",
        "access_token": long_lived_user_token,
    })
    page_data = resp.json()

    if "access_token" not in page_data:
        print(f"Failed to get page token: {page_data}")
        return

    page_token = page_data["access_token"]
    page_name = page_data.get("name", PAGE_ID)
    print(f"Got page token for: {page_name}")

    save_to_env("PAGE_ACCESS_TOKEN", page_token)
    print("\nPage access token saved to .env")
    print("Setup complete! You can now run: python bot.py")


if __name__ == "__main__":
    main()
