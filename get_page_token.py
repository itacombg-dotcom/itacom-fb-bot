"""
Called by the GitHub Actions workflow before each bot run.
Uses the never-expiring SYSTEM_USER_TOKEN to fetch a fresh page token
and prints it to stdout so the workflow can pass it to the bots.
"""
import os
import sys
import requests

SYSTEM_USER_TOKEN = os.getenv("SYSTEM_USER_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")

if not SYSTEM_USER_TOKEN or not PAGE_ID:
    print("ERROR: SYSTEM_USER_TOKEN or PAGE_ID not set", file=sys.stderr)
    sys.exit(1)

resp = requests.get(
    "https://graph.facebook.com/v25.0/me/accounts",
    params={"access_token": SYSTEM_USER_TOKEN, "limit": 25},
)
data = resp.json()

if "data" not in data:
    print(f"ERROR: {data}", file=sys.stderr)
    sys.exit(1)

for page in data["data"]:
    if page["id"] == PAGE_ID:
        print(page["access_token"], end="")
        sys.exit(0)

print(f"ERROR: Page {PAGE_ID} not found in {[p['id'] for p in data['data']]}", file=sys.stderr)
sys.exit(1)
