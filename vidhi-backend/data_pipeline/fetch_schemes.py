"""
Fixed myscheme.gov.in scraper.
Bug in old scraper: hit rules.myscheme.in instead of myscheme.gov.in — all data was "Not Available".
This scraper correctly hits https://www.myscheme.gov.in/schemes/<slug> for each scheme.

Also includes a Hugging Face fallback for instant data.
"""

import requests
import json
import os
import time
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MYSCHEME_SEARCH_API = "https://www.myscheme.gov.in/api/v1/search"
MYSCHEME_BASE = "https://www.myscheme.gov.in"


# 
# APPROACH 1: Use myscheme.gov.in internal API
# 

def get_all_scheme_slugs_via_api() -> list[dict]:
    """
    Hits the myscheme.gov.in search API to get all scheme slugs.
    The site uses a REST API internally.
    """
    all_schemes = []
    page = 0
    page_size = 50

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.myscheme.gov.in/search"
    }

    print("Fetching all scheme slugs from myscheme.gov.in API...")

    while True:
        try:
            params = {
                "keyword": "",
                "lang": "en",
                "page": page,
                "size": page_size,
                "sortBy": "relevance"
            }
            resp = requests.get(MYSCHEME_SEARCH_API, params=params, headers=headers, timeout=30)

            if resp.status_code != 200:
                print(f"API returned {resp.status_code}, stopping.")
                break

            data = resp.json()
            schemes = data.get("schemes", data.get("data", data.get("results", [])))

            if not schemes:
                print(f"No more schemes at page {page}")
                break

            for s in schemes:
                slug = s.get("slug") or s.get("schemeSlug") or s.get("id")
                name = s.get("name") or s.get("schemeName") or s.get("title")
                if slug:
                    all_schemes.append({"scheme_name": name, "slug": slug})

            print(f"  Page {page}: got {len(schemes)} schemes (total so far: {len(all_schemes)})")
            page += 1
            time.sleep(0.5)

            if len(schemes) < page_size:
                break

        except Exception as e:
            print(f"Error at page {page}: {e}")
            break

    return all_schemes


def get_scheme_detail(slug: str) -> dict:
    """
    Fetches full details of one scheme from myscheme.gov.in/schemes/<slug>
    """
    url = f"{MYSCHEME_BASE}/schemes/{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")

        def extract_section(section_id: str) -> str:
            el = soup.find(id=section_id)
            if el:
                return el.get_text(separator="\n", strip=True)
            # Try by heading text
            for heading in soup.find_all(["h2", "h3", "h4"]):
                if section_id.replace("-", " ").lower() in heading.get_text().lower():
                    sibling = heading.find_next_sibling()
                    if sibling:
                        return sibling.get_text(separator="\n", strip=True)
            return "Not Available"

        # Try Next.js __NEXT_DATA__ JSON first (most reliable)
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag:
            try:
                next_data = json.loads(next_data_tag.string)
                page_props = next_data.get("props", {}).get("pageProps", {})
                scheme = page_props.get("scheme") or page_props.get("schemeData") or {}
                if scheme:
                    return {
                        "scheme_name": scheme.get("name") or scheme.get("schemeName", ""),
                        "scheme_link": url,
                        "slug": slug,
                        "details": scheme.get("details") or scheme.get("description", "Not Available"),
                        "benefits": scheme.get("benefits", "Not Available"),
                        "eligibility": scheme.get("eligibility", "Not Available"),
                        "application_process": scheme.get("applicationProcess") or scheme.get("howToApply", "Not Available"),
                        "documents_required": scheme.get("documents") or scheme.get("documentsRequired", "Not Available"),
                        "tags": scheme.get("tags", []),
                        "ministry": scheme.get("ministry") or scheme.get("nodal_ministry", ""),
                        "state": scheme.get("state", "Central"),
                        "source": "__NEXT_DATA__"
                    }
            except Exception:
                pass

        # HTML fallback
        return {
            "scheme_link": url,
            "slug": slug,
            "details": extract_section("details"),
            "benefits": extract_section("benefits"),
            "eligibility": extract_section("eligibility"),
            "application_process": extract_section("application-process"),
            "documents_required": extract_section("documents-required"),
            "tags": [tag.get_text(strip=True) for tag in soup.select("#tags div, .tag")],
            "source": "html_fallback"
        }

    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return {}


# 
# APPROACH 2: Hugging Face dataset (instant fallback)
# 

def fetch_from_huggingface():
    """
    Downloads pre-scraped myscheme dataset from Hugging Face.
    No API key needed for public datasets.
    """
    print("\nTrying Hugging Face dataset download...")
    try:
        from datasets import load_dataset
        # Try multiple known datasets
        dataset_ids = [
            "AlokAI/myscheme",
            "Srini1011/IndianGovernmentSchemes",
            "varunasthana94/government_schemes",
        ]
        for dataset_id in dataset_ids:
            try:
                ds = load_dataset(dataset_id, split="train")
                records = [dict(row) for row in ds]
                out_path = os.path.join(OUTPUT_DIR, f"schemes_hf_{dataset_id.replace('/', '_')}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f" Saved {len(records)} records from HuggingFace {dataset_id} → {out_path}")
                return out_path
            except Exception as e:
                print(f"    {dataset_id} failed: {e}")
    except ImportError:
        print("  datasets library not installed. Run: pip install datasets")
    return None


# 
# MAIN
# 

def fetch_all_schemes():
    # Step 1: Try Hugging Face for instant data
    hf_path = fetch_from_huggingface()

    # Step 2: Fetch from myscheme.gov.in directly
    print("\nFetching scheme list from myscheme.gov.in...")
    scheme_stubs = get_all_scheme_slugs_via_api()

    if not scheme_stubs:
        print("  API failed, trying to load slugs from existing JSON...")
        existing = os.path.join(os.path.dirname(__file__), "..", "myschemes_scraped.json")
        if os.path.exists(existing):
            with open(existing, encoding="utf-8") as f:
                old = json.load(f)
            # Extract slugs from existing scheme_link
            scheme_stubs = [
                {
                    "scheme_name": s.get("scheme_name", ""),
                    "slug": s.get("scheme_link", "").rstrip("/").split("/")[-1]
                }
                for s in old if s.get("scheme_link")
            ]
            print(f"  Loaded {len(scheme_stubs)} slugs from existing JSON")

    if not scheme_stubs:
        print(" No scheme slugs found. Cannot proceed with myscheme.gov.in scrape.")
        return hf_path

    print(f"\n Total schemes to scrape: {len(scheme_stubs)}")
    all_schemes = []
    failed = []

    for i, stub in enumerate(scheme_stubs):
        slug = stub.get("slug", "")
        name = stub.get("scheme_name", slug)

        if not slug:
            continue

        print(f"[{i+1}/{len(scheme_stubs)}] {name[:60]}...")
        detail = get_scheme_detail(slug)

        if detail:
            detail["scheme_name"] = detail.get("scheme_name") or name
            all_schemes.append(detail)
        else:
            failed.append(slug)

        # Save progress every 50 schemes
        if (i + 1) % 50 == 0:
            checkpoint = os.path.join(OUTPUT_DIR, "schemes_checkpoint.json")
            with open(checkpoint, "w", encoding="utf-8") as f:
                json.dump(all_schemes, f, ensure_ascii=False, indent=2)
            print(f"   Checkpoint saved: {len(all_schemes)} schemes")

        time.sleep(0.8)  # Rate limiting

    out_path = os.path.join(OUTPUT_DIR, "myschemes_full.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_schemes, f, ensure_ascii=False, indent=2)

    print(f"\n Saved {len(all_schemes)} schemes to {out_path}")
    print(f" Failed: {len(failed)} schemes")
    if failed:
        fail_path = os.path.join(OUTPUT_DIR, "schemes_failed.json")
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failed, f, indent=2)

    return out_path


if __name__ == "__main__":
    fetch_all_schemes()
