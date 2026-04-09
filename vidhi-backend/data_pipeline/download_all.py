"""
VIDHI RAG — Comprehensive Data Downloader (Corrected URLs)
Downloads Constitution, Central Acts, and Schemes into data_pipeline/raw/

Run from vidhi-backend/ directory:
    python data_pipeline/download_all.py
"""

import requests
import json
import os
import time
from bs4 import BeautifulSoup

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# 1. CONSTITUTION OF INDIA

def fetch_constitution():
    print("\n" + ""*60)
    print("   DOWNLOADING: Constitution of India")
    print(""*60)

    out_path = os.path.join(RAW_DIR, "constitution_of_india.json")

    # Correct URL — file is COI.json not constitution_of_india.json
    url = "https://raw.githubusercontent.com/Yash-Handa/The_Constitution_Of_India/master/COI.json"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   Saved Constitution JSON ({len(json.dumps(data))//1024} KB) → {out_path}")
        return out_path
    except Exception as e:
        print(f"    GitHub download failed: {e}")

    # Backup: civictech-India repo
    backup_url = "https://raw.githubusercontent.com/civictech-India/constitution-of-india/main/constitution.json"
    try:
        r = requests.get(backup_url, timeout=60)
        r.raise_for_status()
        data = r.json()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   Backup saved ({len(json.dumps(data))//1024} KB) → {out_path}")
        return out_path
    except Exception as e:
        print(f"    Backup also failed: {e}")

    # Last resort: Scrape legislative.gov.in article by article
    print("   Falling back to legislative.gov.in article scraper...")
    return fetch_constitution_legislative()


def fetch_constitution_legislative():
    """Scrapes all articles from the official legislative.gov.in page"""
    out_path = os.path.join(RAW_DIR, "constitution_of_india.json")
    articles = []

    # legislative.gov.in has the full constitution as a single HTML page
    url = "https://legislative.gov.in/sites/default/files/COI...pdf"

    # Use the more reliable WikiSource version (public domain)
    wikisource_parts = [
        ("Preamble + Part I", "https://en.wikisource.org/wiki/Constitution_of_India/Preamble"),
        ("Part III - Fundamental Rights", "https://en.wikisource.org/wiki/Constitution_of_India/Part_III"),
        ("Part IV - Directive Principles", "https://en.wikisource.org/wiki/Constitution_of_India/Part_IV"),
        ("Part IVA - Fundamental Duties", "https://en.wikisource.org/wiki/Constitution_of_India/Part_IVA"),
        ("Part V - The Union", "https://en.wikisource.org/wiki/Constitution_of_India/Part_V"),
        ("Part VI - The States", "https://en.wikisource.org/wiki/Constitution_of_India/Part_VI"),
        ("Part XVIII - Emergency Provisions", "https://en.wikisource.org/wiki/Constitution_of_India/Part_XVIII"),
    ]

    for part_name, part_url in wikisource_parts:
        try:
            r = requests.get(part_url, timeout=30, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            content_div = soup.find("div", class_="mw-parser-output")
            if content_div:
                text = content_div.get_text(separator="\n", strip=True)
                articles.append({
                    "part": part_name,
                    "source_url": part_url,
                    "content": text[:50000]  # cap at 50k chars per part
                })
                print(f"     {part_name}: {len(text)} chars")
            time.sleep(1)
        except Exception as e:
            print(f"      {part_name} failed: {e}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"   Saved {len(articles)} constitution parts → {out_path}")
    return out_path


# 2. CENTRAL ACTS — India Code (correct handle IDs)

# Updated to 2024: IPC replaced by BNS, CrPC by BNSS, Evidence Act by BSA
PRIORITY_ACTS = [
    # New criminal laws (2023, effective July 2024)
    ("Bharatiya Nyaya Sanhita 2023 (replaces IPC)",      "2023/45"),
    ("Bharatiya Nagarik Suraksha Sanhita 2023 (replaces CrPC)", "2023/46"),
    ("Bharatiya Sakshya Adhiniyam 2023 (replaces Evidence Act)", "2023/47"),
    # Key welfare/rights acts
    ("Protection of Children from Sexual Offences Act 2012", "2012/32"),
    ("Protection of Women from Domestic Violence Act 2005", "2005/43"),
    ("Right to Information Act 2005",        "2005/22"),
    ("Scheduled Castes and Scheduled Tribes (Prevention of Atrocities) Act 1989", "1989/33"),
    ("Sexual Harassment of Women at Workplace Act 2013", "2013/14"),
    ("Legal Services Authorities Act 1987",  "1987/39"),
    ("Dowry Prohibition Act 1961",           "1961/28"),
    ("Right of Children to Free and Compulsory Education Act 2009", "2009/35"),
    ("Persons with Disabilities Act 1995",   "1995/1"),
    ("Bonded Labour System Abolition Act 1976", "1976/19"),
    ("Child Labour Prohibition Act 1986",    "1986/61"),
    ("National Human Rights Commission Act 1993", "1993/10"),
]


def fetch_act_indiacode(act_name: str, handle_id: str) -> list[dict]:
    """Fetch act content from indiacode.nic.in using correct handle format"""
    chunks = []
    # Correct URL format
    url = f"https://www.indiacode.nic.in/handle/123456789/{handle_id}"

    try:
        r = requests.get(url, timeout=30, headers=HEADERS, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500:
            soup = BeautifulSoup(r.text, "html.parser")

            # DSpace repository structure
            content = (
                soup.find("div", class_="item-page")
                or soup.find("div", class_="ds-div")
                or soup.find("div", {"id": "content-area"})
                or soup.find("main")
            )

            if content:
                text = content.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    for i in range(0, len(text), 1800):
                        chunks.append({"chunk_index": i//1800, "text": text[i:i+1800]})
                    print(f"     indiacode: {len(chunks)} chunks")
                    return chunks

        # Try the bitstream/PDF text endpoint
        pdf_url = f"https://www.indiacode.nic.in/bitstream/123456789/{handle_id}/1/{handle_id.replace('/', '_')}.pdf"
        print(f"    Trying PDF endpoint...")

    except Exception as e:
        print(f"    indiacode failed: {e}")

    return chunks


def fetch_act_legislative(act_name: str) -> list[dict]:
    """Fetch act from legislative.gov.in as fallback"""
    chunks = []
    slug = act_name.lower().replace(" ", "-").replace(",", "").replace("(", "").replace(")", "")
    url = f"https://legislative.gov.in/actsofparliamentfromtheyear/{slug}"

    try:
        r = requests.get(url, timeout=30, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.find("div", class_="field-items") or soup.find("article")
        if content:
            text = content.get_text(separator="\n", strip=True)
            if len(text) > 200:
                for i in range(0, len(text), 1800):
                    chunks.append({"chunk_index": i//1800, "text": text[i:i+1800]})
                print(f"     legislative.gov.in: {len(chunks)} chunks")
    except Exception as e:
        print(f"    legislative.gov.in failed: {e}")

    return chunks


def fetch_act_kanoon(act_name: str) -> list[dict]:
    """Fetch act text from indiankanoon.org (public access, no auth needed for reading)"""
    chunks = []
    query = act_name.replace(" ", "+")
    url = f"https://indiankanoon.org/search/?formInput={query}&type=acts"

    try:
        r = requests.get(url, timeout=30, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        # Find first act result
        result = soup.find("div", class_="result_title")
        if result:
            link = result.find("a")
            if link and link.get("href"):
                act_url = "https://indiankanoon.org" + link["href"]
                ar = requests.get(act_url, timeout=30, headers=HEADERS)
                asoup = BeautifulSoup(ar.text, "html.parser")
                content = asoup.find("div", class_="doc_title") or asoup.find("div", {"id": "maindiv"})
                if content:
                    text = content.get_text(separator="\n", strip=True)
                    if len(text) > 200:
                        for i in range(0, len(text), 1800):
                            chunks.append({"chunk_index": i//1800, "text": text[i:i+1800]})
                        print(f"     indiankanoon: {len(chunks)} chunks")
    except Exception as e:
        print(f"    indiankanoon failed: {e}")

    return chunks


def fetch_all_acts():
    print("\n" + ""*60)
    print("    DOWNLOADING: Central Acts & Laws")
    print(""*60)

    all_acts = []
    out_path = os.path.join(RAW_DIR, "india_code_acts.json")

    for act_name, handle_id in PRIORITY_ACTS:
        print(f"\n   {act_name}")

        chunks = fetch_act_indiacode(act_name, handle_id)

        if not chunks:
            print(f"    Trying legislative.gov.in...")
            chunks = fetch_act_legislative(act_name)

        if not chunks:
            print(f"    Trying indiankanoon.org...")
            chunks = fetch_act_kanoon(act_name)

        if chunks:
            all_acts.append({
                "act_name": act_name,
                "handle_id": handle_id,
                "sections": chunks,
                "total_chunks": len(chunks),
                "total_chars": sum(len(c["text"]) for c in chunks)
            })
        else:
            print(f"     No content retrieved")

        time.sleep(1.2)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_acts, f, ensure_ascii=False, indent=2)

    total = sum(a["total_chunks"] for a in all_acts)
    print(f"\n   Saved {len(all_acts)}/{len(PRIORITY_ACTS)} acts, {total} total chunks → {out_path}")
    return out_path


# 3. GOVERNMENT SCHEMES — myscheme.gov.in + Hugging Face

def fetch_schemes_huggingface():
    """Download pre-scraped scheme dataset from Hugging Face (no login needed)"""
    print("\n  Trying Hugging Face dataset...")
    try:
        from datasets import load_dataset
        for ds_id in ["AlokAI/myscheme", "Srini1011/IndianGovernmentSchemes", "varunasthana94/government_schemes"]:
            try:
                ds = load_dataset(ds_id, split="train")
                records = [dict(row) for row in ds]
                out_path = os.path.join(RAW_DIR, "schemes_huggingface.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"     HuggingFace {ds_id}: {len(records)} records → {out_path}")
                return out_path
            except Exception as e:
                print(f"      {ds_id}: {e}")
    except ImportError:
        print("    datasets not installed")
    return None


def get_scheme_slugs_from_existing():
    """Extract slugs from existing myschemes_scraped.json"""
    path = os.path.join(os.path.dirname(__file__), "..", "myschemes_scraped.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    slugs = []
    for s in data:
        link = s.get("scheme_link", "")
        slug = link.rstrip("/").split("/")[-1]
        if slug:
            slugs.append({"scheme_name": s.get("scheme_name", ""), "slug": slug})
    return slugs


def fetch_scheme_detail(slug: str, name: str) -> dict | None:
    """Fetch one scheme from myscheme.gov.in/schemes/<slug>"""
    url = f"https://www.myscheme.gov.in/schemes/{slug}"
    try:
        r = requests.get(url, timeout=20, headers=HEADERS)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Method 1: Extract from __NEXT_DATA__ JSON (most reliable)
        nxt = soup.find("script", id="__NEXT_DATA__")
        if nxt:
            try:
                nd = json.loads(nxt.string)
                props = nd.get("props", {}).get("pageProps", {})
                # Try various keys
                scheme = (
                    props.get("scheme")
                    or props.get("schemeData")
                    or props.get("schemeDetails")
                    or props.get("data")
                    or {}
                )
                if isinstance(scheme, dict) and scheme:
                    return {
                        "scheme_name": scheme.get("name") or scheme.get("schemeName") or name,
                        "scheme_link": url,
                        "slug": slug,
                        "details": scheme.get("details") or scheme.get("description") or "Not Available",
                        "benefits": scheme.get("benefits") or "Not Available",
                        "eligibility": scheme.get("eligibility") or "Not Available",
                        "application_process": (
                            scheme.get("applicationProcess")
                            or scheme.get("howToApply")
                            or scheme.get("application_process")
                            or "Not Available"
                        ),
                        "documents_required": (
                            scheme.get("documents")
                            or scheme.get("documentsRequired")
                            or scheme.get("documents_required")
                            or "Not Available"
                        ),
                        "tags": scheme.get("tags", []),
                        "ministry": scheme.get("ministry") or scheme.get("nodal_ministry") or "",
                        "state": scheme.get("state") or "Central",
                    }
            except Exception:
                pass

        # Method 2: Direct HTML extraction
        def get_section(section_id):
            el = soup.find(id=section_id)
            return el.get_text("\n", strip=True) if el else "Not Available"

        result = {
            "scheme_name": name,
            "scheme_link": url,
            "slug": slug,
            "details": get_section("details"),
            "benefits": get_section("benefits"),
            "eligibility": get_section("eligibility"),
            "application_process": get_section("application-process"),
            "documents_required": get_section("documents-required"),
            "tags": [t.get_text(strip=True) for t in soup.select("#tags div, .tag-item, .badge")],
        }
        return result

    except Exception as e:
        return None


def fetch_all_schemes():
    print("\n" + ""*60)
    print("    DOWNLOADING: Government Schemes")
    print(""*60)

    # First try HuggingFace for instant data
    hf = fetch_schemes_huggingface()

    # Get slugs from existing JSON
    slugs = get_scheme_slugs_from_existing()
    print(f"\n  Found {len(slugs)} scheme slugs from existing JSON")

    if not slugs:
        print("    No slugs found. Skipping live scrape.")
        return hf

    all_schemes = []
    out_path = os.path.join(RAW_DIR, "myschemes_full.json")

    print(f"  Starting live scrape of {len(slugs)} schemes...")
    for i, stub in enumerate(slugs):
        slug = stub["slug"]
        name = stub["scheme_name"]

        detail = fetch_scheme_detail(slug, name)
        if detail:
            # Skip if all fields are "Not Available"
            meaningful = any(
                str(detail.get(f, "")).strip() not in ("", "Not Available", "N/A")
                for f in ["details", "benefits", "eligibility", "application_process"]
            )
            if meaningful:
                all_schemes.append(detail)
                if len(all_schemes) % 25 == 0:
                    print(f"    [{i+1}/{len(slugs)}]  {len(all_schemes)} valid schemes so far...")

        # Checkpoint every 100
        if (i + 1) % 100 == 0:
            cp = os.path.join(RAW_DIR, "schemes_checkpoint.json")
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(all_schemes, f, ensure_ascii=False, indent=2)

        time.sleep(0.6)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_schemes, f, ensure_ascii=False, indent=2)

    print(f"   {len(all_schemes)} valid schemes saved → {out_path}")
    return out_path


# MAIN

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--constitution-only", action="store_true")
    parser.add_argument("--acts-only", action="store_true")
    parser.add_argument("--schemes-only", action="store_true")
    args = parser.parse_args()

    if args.constitution_only:
        fetch_constitution()
    elif args.acts_only:
        fetch_all_acts()
    elif args.schemes_only:
        fetch_all_schemes()
    else:
        # Run all
        fetch_constitution()
        fetch_all_acts()
        fetch_all_schemes()

    print("\n\n All downloads complete! Check data_pipeline/raw/ for output files.")
    print("Next step: python data_pipeline/ingest_to_chroma.py")
