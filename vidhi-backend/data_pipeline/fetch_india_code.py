"""
Scrapes priority Indian Acts from indiacode.nic.in (public domain)
Targets the 15 most relevant acts for VIDHI's legal assistance domain.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://www.indiacode.nic.in"

# Priority acts for VIDHI domain — (act name, act ID / URL slug)
PRIORITY_ACTS = [
    ("Indian Penal Code 1860",              "1860/45"),
    ("Code of Criminal Procedure 1973",      "1974/2"),
    ("Protection of Children from Sexual Offences Act 2012", "2012/32"),
    ("Protection of Women from Domestic Violence Act 2005", "2005/43"),
    ("Right to Information Act 2005",        "2005/22"),
    ("Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act 1989", "1989/33"),
    ("Sexual Harassment of Women at Workplace Act 2013", "2013/14"),
    ("Bonded Labour System (Abolition) Act 1976", "1976/19"),
    ("Child Labour (Prohibition and Regulation) Act 1986", "1986/61"),
    ("Right of Children to Free and Compulsory Education Act 2009", "2009/35"),
    ("Legal Services Authorities Act 1987", "1987/39"),
    ("Dowry Prohibition Act 1961",           "1961/28"),
    ("Hindu Marriage Act 1955",              "1955/25"),
    ("Persons with Disabilities Act 1995",   "1995/1"),
    ("National Human Rights Commission Act 1993", "1993/10"),
]


def get_act_sections(year_id: str) -> list[dict]:
    """Fetch all sections of an act from indiacode.nic.in"""
    sections = []
    url = f"{BASE_URL}/handle/123456789/{year_id}"

    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} for {url}")
            return sections

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to get all section links
        section_links = soup.find_all("a", href=True)
        section_links = [a for a in section_links if "/bitstream/" in a.get("href", "") or "section" in a.get("href", "").lower()]

        # Get main text content as fallback
        main_content = (
            soup.find("div", class_="item-page")
            or soup.find("div", class_="ds-div")
            or soup.find("div", id="content")
        )

        if main_content:
            full_text = main_content.get_text(separator="\n", strip=True)
            # Split into chunks of ~2000 chars
            for i, chunk_start in enumerate(range(0, len(full_text), 2000)):
                sections.append({
                    "chunk_index": i,
                    "text": full_text[chunk_start:chunk_start + 2000]
                })

        print(f"   Got {len(sections)} chunks from {url}")
    except Exception as e:
        print(f"   Error fetching {url}: {e}")

    return sections


def fetch_act_via_search(act_name: str) -> list[dict]:
    """Use indiacode search API to find and fetch act content"""
    sections = []
    try:
        search_url = f"{BASE_URL}/search?query={requests.utils.quote(act_name)}"
        resp = requests.get(search_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find first result link
        result_links = soup.select("a[href*='/handle/']")
        if result_links:
            act_url = BASE_URL + result_links[0]["href"]
            act_resp = requests.get(act_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            act_soup = BeautifulSoup(act_resp.text, "html.parser")
            content = act_soup.find("div", class_="item-page") or act_soup.find("main")
            if content:
                text = content.get_text(separator="\n", strip=True)
                for i, start in enumerate(range(0, len(text), 2000)):
                    sections.append({"chunk_index": i, "text": text[start:start+2000]})
    except Exception as e:
        print(f"   Search failed for {act_name}: {e}")
    return sections


def fetch_all_acts():
    all_acts = []

    for act_name, act_id in PRIORITY_ACTS:
        print(f"\n Fetching: {act_name}")
        sections = get_act_sections(act_id)

        if not sections:
            print(f"  Trying search fallback...")
            sections = fetch_act_via_search(act_name)

        if sections:
            all_acts.append({
                "act_name": act_name,
                "act_id": act_id,
                "source": f"{BASE_URL}/handle/123456789/{act_id}",
                "sections": sections,
                "total_chunks": len(sections)
            })
            print(f"   {len(sections)} chunks saved for '{act_name}'")
        else:
            print(f"    No content retrieved for '{act_name}'")

        time.sleep(1.5)  # Be polite

    out_path = os.path.join(OUTPUT_DIR, "india_code_acts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_acts, f, ensure_ascii=False, indent=2)

    print(f"\n Saved {len(all_acts)} acts to {out_path}")
    total_chunks = sum(a["total_chunks"] for a in all_acts)
    print(f" Total chunks: {total_chunks}")
    return out_path


if __name__ == "__main__":
    fetch_all_acts()
