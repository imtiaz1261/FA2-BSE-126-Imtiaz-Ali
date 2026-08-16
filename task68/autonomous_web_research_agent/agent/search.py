from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests

def web_search(query, max_results=8):
    url = "https://www.google.com/search?q=" + quote_plus(query)
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()
    for a in soup.select("a"):
        href = a.get("href","")
        title = a.get_text(" ",strip=True)
        if href.startswith("/url?q="):
            href = href.split("/url?q=",1)[1].split("&",1)[0]
        if not href.startswith(("http://","https://")) or "google.com" in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append({"title":title[:200],"url":href})
        if len(out) >= max_results:
            break
    return out
