"""
Usage:
  python instagram_bot.py          — picks a random post, publishes it to Instagram, then exits
  python instagram_bot.py --test   — generates the image locally and saves it (no Instagram post)

Instagram's Content Publishing API needs a public image_url (unlike Facebook's
raw photo upload), so this script commits the generated image to this public
repo and publishes it from its raw.githubusercontent.com URL.

Requires the same PAGE_ACCESS_TOKEN as bot.py — the Meta system user must be
granted instagram_basic + instagram_content_publish on the linked Instagram
account (via Meta Business Suite) for that token to work for IG publishing.
"""
import os
import sys
import time
import random
import subprocess
import requests
from dotenv import load_dotenv
from content import POSTS
from bot import get_pexels_image, crop_to_square, add_text_overlay

load_dotenv()

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

REPO_RAW_BASE = "https://raw.githubusercontent.com/itacombg-dotcom/itacom-fb-bot/main"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "instagram_output")
IMAGE_PATH = os.path.join(OUTPUT_DIR, "post.jpg")


def commit_and_push_image():
    """Publishes post.jpg to the public repo so Instagram can fetch it by URL."""
    git = lambda *args: subprocess.run(
        ["git", "-c", "user.name=ITA COM Bot", "-c", "user.email=bot@itacom.bg", *args],
        cwd=os.path.dirname(__file__),
    )
    git("add", IMAGE_PATH)
    commit = subprocess.run(
        ["git", "-c", "user.name=ITA COM Bot", "-c", "user.email=bot@itacom.bg",
         "commit", "-m", "Instagram post image"],
        cwd=os.path.dirname(__file__),
    )
    if commit.returncode != 0:
        print("Nothing new to commit (image identical?) — aborting Instagram post.")
        sys.exit(1)
    push = subprocess.run(["git", "push"], cwd=os.path.dirname(__file__))
    if push.returncode != 0:
        print("git push failed.")
        sys.exit(1)


def wait_for_public_url(url, timeout=90):
    """raw.githubusercontent.com can lag a few seconds after a push."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.head(url, timeout=15)
        if resp.status_code == 200:
            return
        time.sleep(5)
    print(f"Timed out waiting for {url} to become publicly available.")
    sys.exit(1)


def create_ig_container(image_url, caption):
    resp = requests.post(
        f"https://graph.facebook.com/v25.0/{IG_USER_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": PAGE_ACCESS_TOKEN},
    )
    result = resp.json()
    if "id" not in result:
        print(f"Container creation failed: {result}")
        sys.exit(1)
    return result["id"]


def wait_until_ready(creation_id, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"https://graph.facebook.com/v25.0/{creation_id}",
            params={"fields": "status_code", "access_token": PAGE_ACCESS_TOKEN},
        )
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            print(f"Container processing failed: {resp.json()}")
            sys.exit(1)
        time.sleep(3)
    print("Timed out waiting for media container to finish processing.")
    sys.exit(1)


def publish_container(creation_id):
    resp = requests.post(
        f"https://graph.facebook.com/v25.0/{IG_USER_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": PAGE_ACCESS_TOKEN},
    )
    result = resp.json()
    if "id" not in result:
        print(f"Publish failed: {result}")
        sys.exit(1)
    print(f"Posted to Instagram! ID: {result['id']}")


def post_to_instagram(image_text, caption, image_query):
    print(f"Fetching image for: '{image_query}'")
    raw_img = get_pexels_image(image_query)
    img = crop_to_square(raw_img)
    img = add_text_overlay(img, image_text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    img.save(IMAGE_PATH, format="JPEG", quality=92)

    commit_and_push_image()

    image_url = f"{REPO_RAW_BASE}/instagram_output/post.jpg?v={int(time.time())}"
    print(f"Waiting for {image_url} to go live...")
    wait_for_public_url(image_url)

    creation_id = create_ig_container(image_url, caption)
    wait_until_ready(creation_id)
    publish_container(creation_id)


def main():
    test_mode = "--test" in sys.argv

    if not PEXELS_API_KEY:
        print("ERROR: PEXELS_API_KEY missing in .env")
        sys.exit(1)

    if not test_mode and (not PAGE_ACCESS_TOKEN or not IG_USER_ID):
        print("ERROR: PAGE_ACCESS_TOKEN or IG_USER_ID missing.")
        sys.exit(1)

    entry = random.choice(POSTS)
    print(f"Selected post: {entry['image_text'][:50]}...")

    if test_mode:
        raw_img = get_pexels_image(entry["image_query"])
        img = crop_to_square(raw_img)
        img = add_text_overlay(img, entry["image_text"])
        img.save("test_instagram_output.jpg")
        print("Saved test_instagram_output.jpg — check it before going live.")
    else:
        post_to_instagram(entry["image_text"], entry["caption"], entry["image_query"])


if __name__ == "__main__":
    main()
