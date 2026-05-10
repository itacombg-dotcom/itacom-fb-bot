"""
Fetches latest news about partner companies using Google News RSS.
No API key required.
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ITAComBot/1.0)"}
TIMEOUT = 12

PARTNERS = [
    {
        "company": "Siemens",
        "query": "Siemens+building+energy+heating+automation",
        "bg_name": "Siemens",
        "image_query": "siemens technology industrial automation",
    },
    {
        "company": "Honeywell",
        "query": "Honeywell+building+heating+automation+energy",
        "bg_name": "Honeywell",
        "image_query": "honeywell building automation smart",
    },
    {
        "company": "Grundfos",
        "query": "Grundfos+pump+heating+water+energy",
        "bg_name": "Grundfos",
        "image_query": "water pump industrial energy efficient",
    },
    {
        "company": "Wilo",
        "query": "Wilo+pump+heating+energy+efficiency",
        "bg_name": "Wilo Group",
        "image_query": "heating pump industrial wilo energy",
    },
    {
        "company": "Danfoss",
        "query": "Danfoss+heating+district+energy+valve",
        "bg_name": "Danfoss",
        "image_query": "danfoss heating valve district energy",
    },
]


def fetch_company_news(partner, max_articles=8):
    query = partner["query"]
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(resp.text, "xml")
        articles = []
        for item in soup.find_all("item")[:max_articles]:
            title = item.find("title")
            link  = item.find("link")
            if not title or not link:
                continue
            t = title.text.strip()
            l = link.text.strip() if link.text.strip() else (link.next_sibling or "").strip()
            if t and l:
                articles.append({
                    "company":     partner["company"],
                    "bg_name":     partner["bg_name"],
                    "image_query": partner["image_query"],
                    "title":       t,
                    "url":         l,
                })
        return articles
    except Exception as e:
        print(f"[{partner['company']}] fetch error: {e}")
        return []


def get_all_articles():
    all_articles = []
    for partner in PARTNERS:
        articles = fetch_company_news(partner)
        print(f"[{partner['company']}] {len(articles)} articles found")
        all_articles.extend(articles)
    return all_articles
