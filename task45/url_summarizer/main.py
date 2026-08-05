"""
URL Article Summarizer
=======================
User se ek URL leta hai, uska text content BeautifulSoup se
fetch/extract karta hai, aur LLM (Groq - Llama 3.3 70B) se us article
ka 5-line summary generate karwa kar print karta hai.

Setup:
    1. `.env.example` ko `.env` mein copy karein aur apni Groq API key
       aur model daalein:
        GROQ_API_KEY=your-api-key-here
        GROQ_MODEL=llama-3.3-70b-versatile

Run:
    python main.py
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# Kitne characters tak article text LLM ko bheja jaye (bohot lambe
# articles ko truncate karne ke liye, taake prompt size manageable rahe)
MAX_CHARS_TO_LLM = 12000


# ---------------------------------------------------------------------------
# 1. URL se raw HTML fetch karke usable text extract karna (BeautifulSoup)
# ---------------------------------------------------------------------------
def fetch_page_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def extract_article_text(html: str) -> str:
    """HTML se clean, readable article text nikalta hai."""
    soup = BeautifulSoup(html, "html.parser")

    # Non-content tags hata dein (script, style, nav, footer, ads, etc.)
    for tag in soup(["script", "style", "noscript", "nav", "footer",
                      "header", "aside", "form", "iframe", "svg"]):
        tag.decompose()

    # Pehle <article> tag dhoondhein (agar ho), warna poore <body> se text lein
    article_tag = soup.find("article")
    container = article_tag if article_tag else soup.body if soup.body else soup

    # Sirf paragraph-jaisay tags se text nikalein (zyada relevant content)
    paragraphs = container.find_all(["p", "h1", "h2", "h3", "li"])
    if paragraphs:
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    else:
        text = container.get_text(separator="\n", strip=True)

    return text.strip()


# ---------------------------------------------------------------------------
# 2. LLM prompt — 5-line summary generate karna
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = """You are a professional summarization assistant.

Summarize the following article in EXACTLY 5 lines. Each line should be
a concise, complete sentence capturing a key point of the article. Do
not add a title, numbering, bullet points, or any extra commentary —
just 5 plain sentences, one per line.

Article Text:
\"\"\"{article}\"\"\"

5-Line Summary:"""


def generate_summary(client: Groq, model: str, article_text: str) -> str:
    truncated = article_text[:MAX_CHARS_TO_LLM]
    prompt = SUMMARY_PROMPT.format(article=truncated)

    response = client.chat.completions.create(
        model=model,
        max_tokens=400,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------
def main():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Copy .env.example to .env and add your Groq API key, or:")
        print('  export GROQ_API_KEY="your-api-key-here"')
        sys.exit(1)

    client = Groq(api_key=api_key)

    print("=" * 60)
    print(" 📰  URL Article Summarizer")
    print("=" * 60)

    url = input("\nArticle ka URL daalein: ").strip()
    if not url:
        print("URL nahi diya gaya. Exit ho raha hai.")
        sys.exit(1)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    print("\n⏳ Page fetch aur parse ho raha hai...")
    try:
        html = fetch_page_html(url)
    except requests.exceptions.RequestException as exc:
        print(f"❌ URL fetch karne mein masla hua: {exc}")
        sys.exit(1)

    article_text = extract_article_text(html)

    if len(article_text) < 100:
        print("⚠️  Warning: Bohot kam text mila is page se. Ho sakta hai")
        print("    yeh page JavaScript se render hota ho, ya content")
        print("    kisi aur tag mein ho. Phir bhi summary generate")
        print("    karne ki koshish ki ja rahi hai...\n")

    print("⏳ LLM se 5-line summary generate ho raha hai...")
    try:
        summary = generate_summary(client, model, article_text)
    except Exception as exc:
        print(f"❌ Summary generate karne mein masla hua: {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" ✅  5-LINE SUMMARY")
    print("=" * 60)
    print(summary)
    print("=" * 60)


if __name__ == "__main__":
    main()
