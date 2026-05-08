"""
Enhanced India Code Acts Scraper with Checkpoint Recovery
Scrapes priority Indian Acts from indiacode.nic.in (public domain)
Targets the 15 most relevant acts for VIDHI's legal assistance domain.

Features:
- Checkpoint recovery for interrupted scraping
- Retry logic with exponential backoff
- Rate limiting and polite scraping
- Progress tracking and reporting
- Deduplication within acts
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
import argparse
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

BASE_URL = "https://www.indiacode.nic.in"
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "india_code_checkpoint.json")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_DELAY = 1.5  # seconds between requests

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


class CheckpointManager:
    """Manages checkpoint state for resumable scraping"""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.state = self.load()
    
    def load(self) -> Dict:
        """Load checkpoint from file"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return {
            "completed_acts": [],
            "failed_acts": [],
            "last_act_index": -1,
            "timestamp": None
        }
    
    def save(self):
        """Save checkpoint to file"""
        try:
            self.state["timestamp"] = datetime.now().isoformat()
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            logger.info(f"Checkpoint saved: {len(self.state['completed_acts'])} acts completed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def mark_completed(self, act_name: str, act_id: str):
        """Mark an act as completed"""
        self.state["completed_acts"].append({"name": act_name, "id": act_id})
        self.save()
    
    def mark_failed(self, act_name: str, act_id: str, error: str):
        """Mark an act as failed"""
        self.state["failed_acts"].append({
            "name": act_name,
            "id": act_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save()
    
    def is_completed(self, act_id: str) -> bool:
        """Check if an act is already completed"""
        return any(act["id"] == act_id for act in self.state["completed_acts"])
    
    def update_index(self, index: int):
        """Update the last processed act index"""
        self.state["last_act_index"] = index
        self.save()


def retry_with_backoff(func, *args, **kwargs):
    """Retry a function with exponential backoff"""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    return None


def deduplicate_chunks(chunks: List[Dict]) -> List[Dict]:
    """Remove duplicate chunks based on text content"""
    seen_texts = set()
    unique_chunks = []
    
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if text and text not in seen_texts:
            seen_texts.add(text)
            unique_chunks.append(chunk)
    
    if len(unique_chunks) < len(chunks):
        logger.info(f"Deduplicated: {len(chunks)} -> {len(unique_chunks)} chunks")
    
    return unique_chunks


def get_act_sections(year_id: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetch all sections of an act from indiacode.nic.in
    Returns: (sections, error_message)
    """
    sections = []
    url = f"{BASE_URL}/handle/123456789/{year_id}"

    try:
        def fetch_url():
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp
        
        resp = retry_with_backoff(fetch_url)
        
        if not resp:
            return sections, f"Failed to fetch after {MAX_RETRIES} retries"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove navigation, headers, footers
        for tag in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
            tag.decompose()

        # Try to get all section links
        section_links = soup.find_all("a", href=True)
        section_links = [a for a in section_links if "/bitstream/" in a.get("href", "") or "section" in a.get("href", "").lower()]

        # Get main text content as fallback
        main_content = (
            soup.find("div", class_="item-page")
            or soup.find("div", class_="ds-div")
            or soup.find("div", id="content")
            or soup.find("main")
        )

        if main_content:
            full_text = main_content.get_text(separator="\n", strip=True)
            
            # Remove excessive whitespace
            full_text = "\n".join(line.strip() for line in full_text.split("\n") if line.strip())
            
            # Split into chunks of ~2000 chars
            for i, chunk_start in enumerate(range(0, len(full_text), 2000)):
                sections.append({
                    "chunk_index": i,
                    "text": full_text[chunk_start:chunk_start + 2000]
                })
        
        # Deduplicate chunks
        sections = deduplicate_chunks(sections)
        
        logger.info(f"Fetched {len(sections)} chunks from {url}")
        return sections, None
        
    except requests.RequestException as e:
        error_msg = f"HTTP error: {str(e)}"
        logger.error(f"Error fetching {url}: {error_msg}")
        return sections, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Error fetching {url}: {error_msg}")
        return sections, error_msg


def fetch_act_via_search(act_name: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Use indiacode search API to find and fetch act content
    Returns: (sections, error_message)
    """
    sections = []
    try:
        def search_act():
            search_url = f"{BASE_URL}/search?query={requests.utils.quote(act_name)}"
            resp = requests.get(search_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp
        
        resp = retry_with_backoff(search_act)
        if not resp:
            return sections, f"Search failed after {MAX_RETRIES} retries"
        
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find first result link
        result_links = soup.select("a[href*='/handle/']")
        if result_links:
            act_url = BASE_URL + result_links[0]["href"]
            
            def fetch_act():
                act_resp = requests.get(act_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                act_resp.raise_for_status()
                return act_resp
            
            act_resp = retry_with_backoff(fetch_act)
            if not act_resp:
                return sections, f"Act fetch failed after {MAX_RETRIES} retries"
            
            act_soup = BeautifulSoup(act_resp.text, "html.parser")
            
            # Remove navigation elements
            for tag in act_soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
                tag.decompose()
            
            content = act_soup.find("div", class_="item-page") or act_soup.find("main")
            if content:
                text = content.get_text(separator="\n", strip=True)
                text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
                
                for i, start in enumerate(range(0, len(text), 2000)):
                    sections.append({"chunk_index": i, "text": text[start:start+2000]})
                
                sections = deduplicate_chunks(sections)
        
        return sections, None if sections else "No content found in search results"
        
    except requests.RequestException as e:
        error_msg = f"Search HTTP error: {str(e)}"
        logger.error(f"Search failed for {act_name}: {error_msg}")
        return sections, error_msg
    except Exception as e:
        error_msg = f"Search unexpected error: {str(e)}"
        logger.error(f"Search failed for {act_name}: {error_msg}")
        return sections, error_msg


def fetch_all_acts(resume: bool = False, specific_acts: Optional[List[str]] = None):
    """
    Fetch all priority acts with checkpoint recovery
    
    Args:
        resume: If True, resume from last checkpoint
        specific_acts: List of act IDs to scrape (if None, scrape all)
    """
    checkpoint = CheckpointManager(CHECKPOINT_FILE)
    all_acts = []
    
    # Filter acts if specific ones requested
    acts_to_scrape = PRIORITY_ACTS
    if specific_acts:
        acts_to_scrape = [(name, id) for name, id in PRIORITY_ACTS if id in specific_acts]
        logger.info(f"Scraping {len(acts_to_scrape)} specific acts")
    
    # Resume from checkpoint if requested
    start_index = 0
    if resume:
        start_index = checkpoint.state["last_act_index"] + 1
        logger.info(f"Resuming from act index {start_index}")
        logger.info(f"Already completed: {len(checkpoint.state['completed_acts'])} acts")
    
    # Track statistics
    stats = {
        "total": len(acts_to_scrape),
        "completed": len(checkpoint.state["completed_acts"]),
        "failed": len(checkpoint.state["failed_acts"]),
        "skipped": 0,
        "start_time": datetime.now()
    }
    
    for idx, (act_name, act_id) in enumerate(acts_to_scrape[start_index:], start=start_index):
        logger.info(f"\n[{idx + 1}/{len(acts_to_scrape)}] Fetching: {act_name}")
        
        # Skip if already completed
        if checkpoint.is_completed(act_id):
            logger.info(f"  ✓ Already completed, skipping")
            stats["skipped"] += 1
            continue
        
        # Update checkpoint index
        checkpoint.update_index(idx)
        
        # Fetch act sections
        sections, error = get_act_sections(act_id)

        # Try search fallback if direct fetch failed
        if not sections:
            logger.info(f"  Trying search fallback...")
            sections, error = fetch_act_via_search(act_name)

        if sections:
            act_data = {
                "act_name": act_name,
                "act_id": act_id,
                "source": f"{BASE_URL}/handle/123456789/{act_id}",
                "sections": sections,
                "total_chunks": len(sections),
                "scrape_timestamp": datetime.now().isoformat()
            }
            all_acts.append(act_data)
            checkpoint.mark_completed(act_name, act_id)
            stats["completed"] += 1
            logger.info(f"  ✓ {len(sections)} chunks saved for '{act_name}'")
        else:
            error_msg = error or "No content retrieved"
            checkpoint.mark_failed(act_name, act_id, error_msg)
            stats["failed"] += 1
            logger.error(f"  ✗ Failed: {error_msg}")

        # Be polite - wait between requests
        time.sleep(REQUEST_DELAY)

    # Save final output
    out_path = os.path.join(OUTPUT_DIR, "india_code_acts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_acts, f, ensure_ascii=False, indent=2)

    # Generate report
    stats["end_time"] = datetime.now()
    stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SCRAPING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Saved {len(all_acts)} acts to {out_path}")
    logger.info(f"Total chunks: {sum(a['total_chunks'] for a in all_acts)}")
    logger.info(f"\nStatistics:")
    logger.info(f"  Total acts: {stats['total']}")
    logger.info(f"  Completed: {stats['completed']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Duration: {stats['duration_seconds']:.1f}s")
    logger.info(f"  Success rate: {stats['completed']/stats['total']*100:.1f}%")
    
    if checkpoint.state["failed_acts"]:
        logger.info(f"\nFailed acts:")
        for failed in checkpoint.state["failed_acts"]:
            logger.info(f"  - {failed['name']}: {failed['error']}")
    
    # Save report
    report_path = os.path.join(OUTPUT_DIR, "scraping_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "stats": {
                "total": stats["total"],
                "completed": stats["completed"],
                "failed": stats["failed"],
                "skipped": stats["skipped"],
                "duration_seconds": stats["duration_seconds"],
                "success_rate": stats["completed"]/stats["total"]*100 if stats["total"] > 0 else 0
            },
            "failed_acts": checkpoint.state["failed_acts"],
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nReport saved to {report_path}")
    
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Indian legal acts from indiacode.nic.in")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--acts", nargs="+", help="Specific act IDs to scrape (e.g., 1860/45 1974/2)")
    parser.add_argument("--clear-checkpoint", action="store_true", help="Clear checkpoint and start fresh")
    
    args = parser.parse_args()
    
    if args.clear_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            logger.info("Checkpoint cleared")
    
    fetch_all_acts(resume=args.resume, specific_acts=args.acts)
