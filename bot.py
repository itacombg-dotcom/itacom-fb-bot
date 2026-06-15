"""
Usage:
  python bot.py          — picks a random post and publishes it once, then exits
  python bot.py --test   — generates the image locally and saves it (no Facebook post)
"""
import os
import sys
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from content import POSTS

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

FONT_PATH = os.path.join(os.path.dirname(__file__), "DejaVuSans-Bold.ttf")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

BRAND_BLUE = (0, 51, 153)       # dark blue from ITA COM brand
BRAND_BLUE_DARK = (0, 30, 100)  # darker shade for gradient


def load_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# Safe fallback queries — guaranteed to return heating/energy related images
SAFE_FALLBACK_QUERIES = [
    "district heating pipes",
    "solar panels rooftop installation",
    "industrial boiler room pipes",
    "heating system radiator pipes",
    "photovoltaic solar energy panels",
    "industrial energy plant machinery",
]


def get_pexels_image(query):
    headers = {"Authorization": PEXELS_API_KEY}
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers=headers,
        params={"query": query, "per_page": 15, "orientation": "square"},
    )
    photos = resp.json().get("photos", [])
    if len(photos) < 3:
        # Too few results — use a safe domain-specific fallback
        fallback = random.choice(SAFE_FALLBACK_QUERIES)
        print(f"  Low results for '{query}', using fallback: '{fallback}'")
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params={"query": fallback, "per_page": 15, "orientation": "square"},
        )
        photos = resp.json().get("photos", [])
    photo = random.choice(photos)
    img_url = photo["src"]["large2x"]
    img_resp = requests.get(img_url, timeout=30)
    return Image.open(BytesIO(img_resp.content)).convert("RGB")


def crop_to_square(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side)).resize((1080, 1080), Image.LANCZOS)


def add_text_overlay(img, text):
    img = img.copy().convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Dark blue gradient from bottom, covering ~45% of image
    grad_h = int(h * 0.48)
    for i in range(grad_h):
        t = i / grad_h
        alpha = int(235 * t)
        r = int(BRAND_BLUE_DARK[0] * t)
        g = int(BRAND_BLUE_DARK[1] * t)
        b = int(BRAND_BLUE_DARK[2] * t)
        draw_ov.rectangle(
            [(0, h - grad_h + i), (w, h - grad_h + i + 1)],
            fill=(r, g, b, alpha),
        )

    # Dark blue brand bar at very bottom
    bar_h = 72
    draw_ov.rectangle([(0, h - bar_h), (w, h)], fill=(*BRAND_BLUE, 255))

    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Logo top-left
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_w = 300
        ratio = logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        # White background pill behind logo for visibility
        pad = 10
        bg = Image.new("RGBA", (logo_w + pad * 2, logo_h + pad * 2), (255, 255, 255, 220))
        img.paste(bg, (28 - pad, 28 - pad), bg)
        img.paste(logo, (28, 28), logo)

    # Main text — wrap and center
    font = load_font(66)
    max_width = w - 100
    words = text.split()
    lines, current = [], []
    for word in words:
        current.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current), font=font)
        if bbox[2] > max_width:
            current.pop()
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    line_h = 82
    total_h = len(lines) * line_h
    y = h - bar_h - 24 - total_h

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        # Shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill="white")
        y += line_h

    # Brand bar text
    font_sm = load_font(32)
    brand = "itacom.bg   |   0888 993 204"
    bbox = draw.textbbox((0, 0), brand, font=font_sm)
    bx = (w - (bbox[2] - bbox[0])) // 2
    by = h - bar_h + (bar_h - (bbox[3] - bbox[1])) // 2
    draw.text((bx, by), brand, font=font_sm, fill="white")

    return img


def post_to_facebook(image_text, caption, image_query):
    print(f"Fetching image for: '{image_query}'")
    raw_img = get_pexels_image(image_query)
    img = crop_to_square(raw_img)
    img = add_text_overlay(img, image_text)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    buffer.seek(0)

    # Step 1: Upload photo as unpublished
    upload_resp = requests.post(
        f"https://graph.facebook.com/v25.0/{PAGE_ID}/photos",
        data={"published": "false", "access_token": PAGE_ACCESS_TOKEN},
        files={"source": ("post.jpg", buffer, "image/jpeg")},
    )
    upload_result = upload_resp.json()
    if "id" not in upload_result:
        print(f"Photo upload failed: {upload_result}")
        sys.exit(1)
    photo_id = upload_result["id"]

    # Step 2: Publish as a proper feed post (counts as a Publication in Insights)
    post_resp = requests.post(
        f"https://graph.facebook.com/v25.0/{PAGE_ID}/feed",
        data={
            "message": caption,
            "attached_media": f'[{{"media_fbid":"{photo_id}"}}]',
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    result = post_resp.json()
    if "id" in result:
        print(f"Posted successfully! ID: {result['id']}")
    else:
        print(f"Post failed: {result}")
        sys.exit(1)


def main():
    test_mode = "--test" in sys.argv

    if not PEXELS_API_KEY:
        print("ERROR: PEXELS_API_KEY missing in .env")
        sys.exit(1)

    if not test_mode and not PAGE_ACCESS_TOKEN:
        print("ERROR: PAGE_ACCESS_TOKEN missing. Run setup.py first.")
        sys.exit(1)

    entry = random.choice(POSTS)
    print(f"Selected post: {entry['image_text'][:50]}...")

    if test_mode:
        raw_img = get_pexels_image(entry["image_query"])
        img = crop_to_square(raw_img)
        img = add_text_overlay(img, entry["image_text"])
        img.save("test_output.jpg")
        print("Saved test_output.jpg — check it before going live.")
    else:
        post_to_facebook(entry["image_text"], entry["caption"], entry["image_query"])


if __name__ == "__main__":
    main()
