"""
Fetches the full Constitution of India as structured JSON from GitHub
Source: https://github.com/Yash-Handa/The_Constitution_Of_India
"""

import requests
import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONSTITUTION_URL = (
    "https://raw.githubusercontent.com/Yash-Handa/The_Constitution_Of_India"
    "/master/data/constitution_of_india.json"
)

CONSTITUTION_BACKUP_URL = (
    "https://raw.githubusercontent.com/civictech-India/constitution-of-india"
    "/main/constitution.json"
)


def fetch_constitution():
    print("Fetching Constitution of India JSON...")

    for url in [CONSTITUTION_URL, CONSTITUTION_BACKUP_URL]:
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            out_path = os.path.join(OUTPUT_DIR, "constitution_of_india.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f" Saved constitution to {out_path}")
            return out_path
        except Exception as e:
            print(f"  Failed from {url}: {e}")

    # Fallback: Build from legislative.gov.in HTML
    print("Falling back to legislative.gov.in HTML scrape...")
    return fetch_constitution_from_legislative()


def fetch_constitution_from_legislative():
    """
    Scrapes articles directly from https://legislative.gov.in/constitution-of-india
    """
    from bs4 import BeautifulSoup

    BASE = "https://legislative.gov.in/constitution-of-india"
    articles = []

    try:
        resp = requests.get(BASE, timeout=60)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find all article links
        links = [a["href"] for a in soup.find_all("a", href=True) if "article" in a["href"].lower()]
        print(f"Found {len(links)} article links")

        for link in links[:10]:  # test first 10
            full_url = link if link.startswith("http") else "https://legislative.gov.in" + link
            r = requests.get(full_url, timeout=30)
            s = BeautifulSoup(r.text, "html.parser")
            body = s.find("div", class_="field-item") or s.find("article")
            if body:
                articles.append({
                    "url": full_url,
                    "text": body.get_text(separator="\n", strip=True)
                })

    except Exception as e:
        print(f"Error scraping legislative.gov.in: {e}")

    out_path = os.path.join(OUTPUT_DIR, "constitution_legislative.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f" Saved {len(articles)} articles to {out_path}")
    return out_path


if __name__ == "__main__":
    fetch_constitution()
