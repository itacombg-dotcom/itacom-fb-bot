"""
Checks recent Facebook posts for new comments and replies automatically.
Uses keyword-based template replies — no AI API required.
Tracks replied comment IDs in replied_comments.txt to avoid double-replying.
Run: python comment_bot.py
"""
import os
import sys
import random
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

PAGE_ID           = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

REPLIED_FILE = os.path.join(os.path.dirname(__file__), "replied_comments.txt")
CONTACT      = "📞 0888 993 204"
SIGNATURE    = "Екипът на ИТА КОМ 🌐 itacom.bg"

# ── Keyword lists (Bulgarian) ─────────────────────────────────────────────────

PRICE_KEYWORDS    = ["цена", "цени", "струва", "оферта", "оферти", "плащане", "колко", "тарифа", "бюджет"]
SERVICE_KEYWORDS  = ["монтаж", "инсталац", "поставяне", "връзване", "сервиз", "ремонт", "поддръжка",
                     "правите ли", "предлагате", "услуга", "обслужване", "идвате ли", "работите ли"]
SOLAR_KEYWORDS    = ["соларн", "фотоволтаич", "слънч", "панел", "pv", "фв"]
HEATING_KEYWORDS  = ["топлофикац", "отоплен", "абонатна", "топлоснабдяв", "радиатор", "бойлер",
                     "топлинна помпа", "термо"]
SCADA_KEYWORDS    = ["scada", "дистанционн", "управление", "контрол", "автоматик"]
PRAISE_KEYWORDS   = ["благодаря", "благодарим", "отлично", "страхотно", "браво", "👍", "❤️", "🙏",
                     "препоръчвам", "доволен", "доволна", "харесвам", "супер", "перфектно", "добра работа"]
COMPLAINT_KEYWORDS= ["проблем", "повреда", "не работи", "счупен", "лошо", "недоволен", "оплаквам",
                     "рекламация", "грешка", "авария", "теч"]
CONTACT_KEYWORDS  = ["телефон", "адрес", "имейл", "email", "контакт", "свържете", "офис", "работно"]

# ── Reply templates ───────────────────────────────────────────────────────────

PRICE_REPLIES = [
    f"Здравейте! За точна оферта, съобразена с вашите нужди, моля свържете се с нас на {CONTACT} — ще се радваме да ви помогнем! 😊\n{SIGNATURE}",
    f"Благодарим за интереса! Цените зависят от конкретния проект, затова ви каним на безплатна консултация: {CONTACT}\n{SIGNATURE}",
    f"Изпратете ни запитване и ще ви подготвим индивидуална оферта! {CONTACT} | itacom@abv.bg\n{SIGNATURE}",
]

SERVICE_REPLIES = [
    f"Да, предлагаме пълен пакет услуги — от проектиране до монтаж и сервиз! За повече информация: {CONTACT}\n{SIGNATURE}",
    f"Обслужваме клиенти в цяла България. Свържете се с нас за детайли: {CONTACT} | itacom@abv.bg\n{SIGNATURE}",
    f"С удоволствие! Обадете се на {CONTACT} и нашите специалисти ще отговорят на всичките ви въпроси. 🔧\n{SIGNATURE}",
]

SOLAR_REPLIES = [
    f"Соларните системи са чудесна инвестиция! Монтираме системи за топла вода и фотоволтаици с дистанционно управление. За консултация: {CONTACT}\n{SIGNATURE}",
    f"Имаме богат опит в монтажа на соларни и фотоволтаични системи ☀️ Свържете се с нас за безплатна консултация: {CONTACT}\n{SIGNATURE}",
]

HEATING_REPLIES = [
    f"Топлоенергетиката е нашата специалност от 1995 г.! За въпроси относно отопление и абонатни станции: {CONTACT}\n{SIGNATURE}",
    f"Проектираме и монтираме абонатни станции с модерна автоматика и дистанционно управление. За повече info: {CONTACT}\n{SIGNATURE}",
]

SCADA_REPLIES = [
    f"SCADA системите ни позволяват дистанционен контрол на цялото ви оборудване 24/7! За демонстрация и консултация: {CONTACT}\n{SIGNATURE}",
    f"Нашите SCADA решения са доказани в стотици обекти в България. За повече информация: {CONTACT} | itacom@abv.bg\n{SIGNATURE}",
]

PRAISE_REPLIES = [
    "Благодарим от сърце! 🙏 Радваме се, че сме успели да ви помогнем. Доверието ви е нашата най-голяма награда!",
    "Много ни радва вашата оценка! 😊 Ще продължаваме да работим с отдаденост и качество. Благодарим!",
    "Благодарим за топлите думи! ❤️ Стараем се да даваме най-доброто от себе си за всеки клиент.",
    "Радваме се, че сте доволни! Именно такива моменти ни мотивират всеки ден. Благодарим! 🌟",
]

COMPLAINT_REPLIES = [
    f"Съжаляваме за неудобството! Моля свържете се с нас незабавно на {CONTACT} и ще решим проблема възможно най-бързо. 🙏\n{SIGNATURE}",
    f"Разбираме притеснението ви и съжаляваме за ситуацията. Обадете се на {CONTACT} — нашите техници ще реагират веднага.\n{SIGNATURE}",
    f"Благодарим, че ни уведомихте. Моля свържете се директно с нас на {CONTACT} за бързо решение. itacom@abv.bg\n{SIGNATURE}",
]

CONTACT_REPLIES = [
    f"Можете да се свържете с нас по следните начини:\n📞 {CONTACT}\n✉️ itacom@abv.bg\n🌐 itacom.bg\n📍 София, кв. Враждебна, ул. \"3-та\" №16А\n\nРаботно време: Пон–Пет, 8:00–18:00 ч.",
]

DEFAULT_REPLIES = [
    f"Благодарим за коментара! Ако имате въпроси относно нашите услуги, не се колебайте да се свържете с нас: {CONTACT}\n{SIGNATURE}",
    f"Благодарим! 😊 За всякакви запитвания сме на ваше разположение: {CONTACT} | itacom@abv.bg\n{SIGNATURE}",
    f"Радваме се на вашето мнение! За повече информация за нашите услуги: {CONTACT} | 🌐 itacom.bg\n{SIGNATURE}",
]


def classify_comment(text):
    t = text.lower()
    if any(k in t for k in COMPLAINT_KEYWORDS):  return "complaint"
    if any(k in t for k in PRAISE_KEYWORDS):      return "praise"
    if any(k in t for k in PRICE_KEYWORDS):        return "price"
    if any(k in t for k in SOLAR_KEYWORDS):        return "solar"
    if any(k in t for k in HEATING_KEYWORDS):      return "heating"
    if any(k in t for k in SCADA_KEYWORDS):        return "scada"
    if any(k in t for k in SERVICE_KEYWORDS):      return "service"
    if any(k in t for k in CONTACT_KEYWORDS):      return "contact"
    return "default"


def generate_reply(comment_text):
    category = classify_comment(comment_text)
    replies = {
        "price":     PRICE_REPLIES,
        "service":   SERVICE_REPLIES,
        "solar":     SOLAR_REPLIES,
        "heating":   HEATING_REPLIES,
        "scada":     SCADA_REPLIES,
        "praise":    PRAISE_REPLIES,
        "complaint": COMPLAINT_REPLIES,
        "contact":   CONTACT_REPLIES,
        "default":   DEFAULT_REPLIES,
    }
    return random.choice(replies[category]), category


def load_replied():
    if not os.path.exists(REPLIED_FILE):
        return set()
    with open(REPLIED_FILE) as f:
        return set(line.strip() for line in f if line.strip())


def save_replied(comment_id):
    with open(REPLIED_FILE, "a") as f:
        f.write(comment_id + "\n")
    try:
        subprocess.run(["git", "config", "user.email", "bot@itacom.bg"], check=False)
        subprocess.run(["git", "config", "user.name", "ITA COM Bot"], check=False)
        subprocess.run(["git", "add", REPLIED_FILE], check=False)
        subprocess.run(["git", "commit", "-m", f"Track replied comment {comment_id}"], check=False)
        subprocess.run(["git", "push"], check=False)
    except Exception as e:
        print(f"Git commit warning: {e}")


def get_recent_posts(limit=10):
    url = f"https://graph.facebook.com/v25.0/{PAGE_ID}/posts"
    resp = requests.get(url, params={
        "fields": "id,message,created_time",
        "limit": limit,
        "access_token": PAGE_ACCESS_TOKEN,
    })
    data = resp.json()
    if "error" in data:
        print(f"Error fetching posts: {data['error']}")
        return []
    return data.get("data", [])


def get_comments(post_id):
    url = f"https://graph.facebook.com/v25.0/{post_id}/comments"
    resp = requests.get(url, params={
        "fields": "id,message,from,created_time",
        "limit": 50,
        "access_token": PAGE_ACCESS_TOKEN,
    })
    data = resp.json()
    if "error" in data:
        print(f"Error fetching comments for {post_id}: {data['error']}")
        return []
    return data.get("data", [])


def post_reply(comment_id, reply_text):
    url = f"https://graph.facebook.com/v25.0/{comment_id}/replies"
    resp = requests.post(url, data={
        "message": reply_text,
        "access_token": PAGE_ACCESS_TOKEN,
    })
    result = resp.json()
    if "id" in result:
        print(f"  Replied to {comment_id}: {reply_text[:60]}...")
        return True
    else:
        print(f"  Failed to reply to {comment_id}: {result}")
        return False


def main():
    test_mode = "--test" in sys.argv

    replied = load_replied()
    print(f"Already replied to {len(replied)} comments.")

    posts = get_recent_posts(limit=10)
    print(f"Checking {len(posts)} recent posts for new comments...")

    new_replies = 0
    for post in posts:
        post_id  = post["id"]
        comments = get_comments(post_id)

        for comment in comments:
            cid     = comment["id"]
            message = comment.get("message", "").strip()
            author  = comment.get("from", {}).get("name", "someone")

            if not message:
                continue
            if cid in replied:
                continue
            if comment.get("from", {}).get("id") == PAGE_ID:
                replied.add(cid)
                continue

            reply, category = generate_reply(message)
            print(f"\nComment [{category}] from {author}: {message[:60]}")
            print(f"  Reply: {reply[:80]}...")

            if test_mode:
                replied.add(cid)
            else:
                success = post_reply(cid, reply)
                if success:
                    save_replied(cid)
                    replied.add(cid)
                    new_replies += 1

    print(f"\nDone. {new_replies} new replies posted.")


if __name__ == "__main__":
    main()
