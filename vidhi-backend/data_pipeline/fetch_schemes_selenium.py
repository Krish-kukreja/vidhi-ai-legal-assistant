"""
SELENIUM-based myscheme.gov.in scraper (fixes the JS rendering issue)
- Uses headless Chrome/Firefox to render each scheme page
- Extracts data from __NEXT_DATA__ after JS executes
- Saves to data_pipeline/raw/myschemes_selenium.json with checkpointing

Run from vidhi-backend/:
    python data_pipeline/fetch_schemes_selenium.py
"""

import json
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(RAW_DIR, exist_ok=True)

CHECKPOINT_PATH = os.path.join(RAW_DIR, "myschemes_selenium.json")
FAILED_PATH = os.path.join(RAW_DIR, "schemes_selenium_failed.json")

MYSCHEME_BASE = "https://www.myscheme.gov.in/schemes"


def get_driver():
    """Initialize headless browser — tries Chrome first, then Firefox"""
    # Try Chrome
    try:
        opts = ChromeOptions()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1280,800")
        opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
        driver = webdriver.Chrome(options=opts)
        logger.info(" Using headless Chrome")
        return driver
    except Exception as e:
        logger.warning(f"Chrome failed: {e}")

    # Try Firefox
    try:
        opts = FirefoxOptions()
        opts.add_argument("--headless")
        opts.page_load_strategy = "eager"
        driver = webdriver.Firefox(options=opts)
        logger.info(" Using headless Firefox")
        return driver
    except Exception as e:
        logger.error(f"Firefox also failed: {e}")
        raise RuntimeError("No browser available. Install Chrome or Firefox WebDriver.")


def get_slugs_from_existing():
    """Load slugs from existing myschemes_scraped.json"""
    path = os.path.join(os.path.dirname(__file__), "..", "myschemes_scraped.json")
    if not os.path.exists(path):
        logger.error(f"Not found: {path}")
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


def scrape_scheme(driver, slug: str, name: str) -> dict | None:
    url = f"{MYSCHEME_BASE}/{slug}"
    try:
        driver.get(url)

        # Wait for Next.js to hydrate — look for __NEXT_DATA__ to be populated
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        time.sleep(1.5)  # Extra wait for data population

        # Extract from __NEXT_DATA__ (most reliable)
        try:
            script = driver.execute_script(
                "var el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null;"
            )
            if script:
                nd = json.loads(script)
                props = nd.get("props", {}).get("pageProps", {})
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
                        "details": scheme.get("details") or scheme.get("description") or "",
                        "benefits": scheme.get("benefits") or "",
                        "eligibility": scheme.get("eligibility") or "",
                        "application_process": (
                            scheme.get("applicationProcess")
                            or scheme.get("howToApply")
                            or ""
                        ),
                        "documents_required": (
                            scheme.get("documents")
                            or scheme.get("documentsRequired")
                            or ""
                        ),
                        "tags": scheme.get("tags", []),
                        "ministry": scheme.get("ministry") or scheme.get("nodal_ministry") or "",
                        "state": scheme.get("state") or "Central",
                    }
        except Exception:
            pass

        # HTML fallback after JS render
        def get_text_by_id(element_id):
            try:
                el = driver.find_element(By.ID, element_id)
                return el.text.strip()
            except Exception:
                return ""

        return {
            "scheme_name": name,
            "scheme_link": url,
            "slug": slug,
            "details": get_text_by_id("details"),
            "benefits": get_text_by_id("benefits"),
            "eligibility": get_text_by_id("eligibility"),
            "application_process": get_text_by_id("application-process"),
            "documents_required": get_text_by_id("documents-required"),
            "tags": [],
        }

    except TimeoutException:
        logger.warning(f"Timeout: {slug}")
        return None
    except Exception as e:
        logger.error(f"Error {slug}: {e}")
        return None


def is_meaningful(scheme: dict) -> bool:
    """Returns True if scheme has real content (not all empty/NA)"""
    fields = ["details", "benefits", "eligibility", "application_process"]
    return any(
        str(scheme.get(f, "")).strip() not in ("", "Not Available", "N/A", "None", "null")
        for f in fields
    )


def run():
    slugs = get_slugs_from_existing()
    if not slugs:
        logger.error("No slugs to scrape.")
        return

    # Load existing checkpoint to resume
    done_slugs = set()
    all_schemes = []
    if os.path.exists(CHECKPOINT_PATH) and os.path.getsize(CHECKPOINT_PATH) > 2:
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            all_schemes = json.load(f)
        done_slugs = {s["slug"] for s in all_schemes}
        logger.info(f"Resuming from checkpoint: {len(done_slugs)} already done")

    remaining = [s for s in slugs if s["slug"] not in done_slugs]
    logger.info(f"Total: {len(slugs)} | Done: {len(done_slugs)} | Remaining: {len(remaining)}")

    failed = []
    driver = get_driver()

    try:
        for i, stub in enumerate(remaining):
            slug = stub["slug"]
            name = stub["scheme_name"]

            result = scrape_scheme(driver, slug, name)

            if result and is_meaningful(result):
                all_schemes.append(result)
                if len(all_schemes) % 10 == 0:
                    logger.info(f"[{i+1}/{len(remaining)}]  {len(all_schemes)} valid schemes")
            else:
                failed.append(slug)

            # Save checkpoint every 50 schemes
            if (i + 1) % 50 == 0:
                with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                    json.dump(all_schemes, f, ensure_ascii=False, indent=2)
                logger.info(f" Checkpoint: {len(all_schemes)} valid schemes saved")

    except KeyboardInterrupt:
        logger.info("Interrupted — saving progress...")
    finally:
        driver.quit()

    # Final save
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_schemes, f, ensure_ascii=False, indent=2)

    with open(FAILED_PATH, "w", encoding="utf-8") as f:
        json.dump(failed, f, indent=2)

    logger.info(f"\n Done! {len(all_schemes)} valid schemes saved to {CHECKPOINT_PATH}")
    logger.info(f" Failed: {len(failed)} schemes")


if __name__ == "__main__":
    run()
