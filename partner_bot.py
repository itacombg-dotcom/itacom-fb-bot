"""
Posts partner company news to ITA COM's Facebook page.
Tracks posted URLs in posted_urls.txt to avoid repeats.
Run: python partner_bot.py
"""
import os
import sys
import random
import requests
import subprocess
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from partner_news import get_all_articles
from bot import load_font, get_pexels_image, crop_to_square, BRAND_BLUE, BRAND_BLUE_DARK

load_dotenv()

PAGE_ID           = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PEXELS_API_KEY    = os.getenv("PEXELS_API_KEY")

LOGO_PATH        = os.path.join(os.path.dirname(__file__), "logo.png")
POSTED_URLS_FILE = os.path.join(os.path.dirname(__file__), "posted_urls.txt")


def load_posted_urls():
    if not os.path.exists(POSTED_URLS_FILE):
        return set()
    with open(POSTED_URLS_FILE) as f:
        return set(line.strip() for line in f if line.strip())


def save_posted_url(url):
    with open(POSTED_URLS_FILE, "a") as f:
        f.write(url + "\n")
    # Commit back to GitHub so it persists across runs
    try:
        subprocess.run(["git", "config", "user.email", "bot@itacom.bg"], check=False)
        subprocess.run(["git", "config", "user.name", "ITA COM Bot"], check=False)
        subprocess.run(["git", "add", POSTED_URLS_FILE], check=False)
        subprocess.run(["git", "commit", "-m", f"Track posted: {url[:60]}"], check=False)
        subprocess.run(["git", "push"], check=False)
    except Exception as e:
        print(f"Git commit warning: {e}")


def create_partner_image(company, bg_name, title, image_query):
    raw = get_pexels_image(image_query)
    img = crop_to_square(raw).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Dark blue gradient bottom half
    grad_h = int(h * 0.55)
    for i in range(grad_h):
        t = i / grad_h
        alpha = int(240 * t)
        r = int(BRAND_BLUE_DARK[0] * t)
        g = int(BRAND_BLUE_DARK[1] * t)
        b = int(BRAND_BLUE_DARK[2] * t)
        draw_ov.rectangle([(0, h - grad_h + i), (w, h - grad_h + i + 1)],
                          fill=(r, g, b, alpha))

    # Partner badge at top-right
    badge_w, badge_h = 320, 64
    draw_ov.rectangle([(w - badge_w - 20, 20), (w - 20, 20 + badge_h)],
                      fill=(*BRAND_BLUE, 230))

    # Bottom brand bar
    bar_h = 72
    draw_ov.rectangle([(0, h - bar_h), (w, h)], fill=(*BRAND_BLUE, 255))

    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ITA COM logo top-left
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_w = 280
        logo_h = int(logo.height * (logo_w / logo.width))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        pad = 10
        bg = Image.new("RGBA", (logo_w + pad*2, logo_h + pad*2), (255, 255, 255, 215))
        img.paste(bg, (28 - pad, 28 - pad), bg)
        img.paste(logo, (28, 28), logo)

    # Partner name badge top-right
    font_badge = load_font(30)
    badge_text = f"Партньор: {bg_name}"
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bx = w - badge_w - 20 + (badge_w - (bbox[2] - bbox[0])) // 2
    by = 20 + (badge_h - (bbox[3] - bbox[1])) // 2
    draw.text((bx, by), badge_text, font=font_badge, fill="white")

    # Article title (wrapped)
    font = load_font(52)
    max_width = w - 80
    words = title.split()
    lines, current = [], []
    for word in words:
        current.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current), font=font)
        if bbox[2] > max_width:
            current.pop()
            if current:
                lines.append(" ".join(current))
            current = [word]
        if len(lines) >= 3:
            if current:
                lines.append(" ".join(current))
            current = []
            break
    if current:
        lines.append(" ".join(current))
    lines = lines[:3]

    line_h = 70
    total_h = len(lines) * line_h
    y = h - bar_h - 28 - total_h

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill="white")
        y += line_h

    # Bottom bar
    font_sm = load_font(32)
    brand = "itacom.bg   |   0888 993 204"
    bbox = draw.textbbox((0, 0), brand, font=font_sm)
    bx = (w - (bbox[2] - bbox[0])) // 2
    by = h - bar_h + (bar_h - (bbox[3] - bbox[1])) // 2
    draw.text((bx, by), brand, font=font_sm, fill="white")

    return img


def build_caption(company, bg_name, title, url):
    return (
        f"📢 Нашият партньор {bg_name} сподели:\n\n"
        f"«{title}»\n\n"
        f"ИТА КОМ работи с водещи световни производители като {bg_name}, "
        f"за да ви предостави най-качественото оборудване за отопление, автоматика и енергийни системи.\n\n"
        f"🔗 Прочетете повече: {url}\n\n"
        f"#ИТА_КОМ #{bg_name.replace(' ', '_')} #Топлофикация #ЕнергийниРешения"
    )


def post_to_facebook(img, caption):
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    buffer.seek(0)
    url = f"https://graph.facebook.com/v25.0/{PAGE_ID}/photos"
    resp = requests.post(url,
        data={"caption": caption, "access_token": PAGE_ACCESS_TOKEN},
        files={"source": ("post.jpg", buffer, "image/jpeg")})
    result = resp.json()
    if "id" in result:
        print(f"Posted successfully! ID: {result['id']}")
        return True
    else:
        print(f"Post failed: {result}")
        return False


def main():
    test_mode = "--test" in sys.argv

    print("Fetching partner news...")
    articles = get_all_articles()

    if not articles:
        print("No articles found from any partner.")
        sys.exit(0)

    posted = load_posted_urls()
    fresh  = [a for a in articles if a["url"] not in posted]

    if not fresh:
        print("No new articles to post — all already shared.")
        sys.exit(0)

    # Prefer variety: pick from a company not recently posted
    article = fresh[0]
    print(f"Selected: [{article['company']}] {article['title'][:60]}")

    image_query = article.get("image_query", "technology industrial")
    img = create_partner_image(article["company"], article.get("bg_name", article["company"]), article["title"], image_query)
    caption = build_caption(article["company"], article.get("bg_name", article["company"]), article["title"], article["url"])

    if test_mode:
        img.save("test_partner.jpg")
        print("Saved test_partner.jpg")
        print("\nCaption preview:\n")
        print(caption)
    else:
        success = post_to_facebook(img, caption)
        if success:
            save_posted_url(article["url"])


if __name__ == "__main__":
    main()
