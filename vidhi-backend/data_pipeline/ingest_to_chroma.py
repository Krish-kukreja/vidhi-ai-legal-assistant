"""
Ingests all downloaded raw data into ChromaDB.
Run AFTER all fetch_* scripts have completed.

Sources loaded:
- constitution_of_india.json
- india_code_acts.json
- myschemes_full.json (or schemes_hf_*.json if scraper not yet done)
"""

import os
import sys
import json
import logging

# Fix pydantic compatibility
os.environ["PYDANTIC_SKIP_VALIDATING_CORE_SCHEMAS"] = "1"
os.environ["USER_AGENT"] = "Vidhi-DataPipeline/1.0"

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)


# 
# DOCUMENT LOADERS
# 

def load_constitution() -> list[Document]:
    path = os.path.join(RAW_DIR, "constitution_of_india.json")
    if not os.path.exists(path):
        logger.warning("Constitution JSON not found. Run fetch_constitution.py first.")
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    docs = []

    # Handle different JSON structures
    if isinstance(data, list):
        articles = data
    elif isinstance(data, dict):
        # Could be {articles: [...]} or {parts: [...]}
        articles = (
            data.get("articles")
            or data.get("parts")
            or data.get("content")
            or [data]
        )
    else:
        articles = []

    def extract_article(obj, parent_context=""):
        """Recursively extract articles from nested JSON"""
        extracted = []
        if isinstance(obj, dict):
            article_no = obj.get("article_no") or obj.get("articleNo") or obj.get("number") or obj.get("id") or ""
            title = obj.get("title") or obj.get("heading") or obj.get("name") or ""
            content = obj.get("description") or obj.get("content") or obj.get("text") or obj.get("body") or ""

            if content:
                full_text = f"Article {article_no}: {title}\n\n{content}"
                extracted.append(Document(
                    page_content=full_text.strip(),
                    metadata={
                        "source": "Constitution of India",
                        "article_no": str(article_no),
                        "title": title,
                        "type": "constitution",
                        "parent": parent_context
                    }
                ))

            # Recurse into nested structures
            for key in ["articles", "clauses", "sub_articles", "parts", "sections", "children"]:
                if key in obj and isinstance(obj[key], list):
                    for child in obj[key]:
                        extracted.extend(extract_article(child, f"Article {article_no}"))

        elif isinstance(obj, list):
            for item in obj:
                extracted.extend(extract_article(item, parent_context))

        return extracted

    for item in articles:
        docs.extend(extract_article(item))

    # If no docs extracted, treat entire JSON as text blobs
    if not docs and articles:
        for i, item in enumerate(articles):
            text = json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item)
            docs.append(Document(
                page_content=text[:2000],
                metadata={"source": "Constitution of India", "type": "constitution", "index": i}
            ))

    logger.info(f"Loaded {len(docs)} constitution documents")
    # Split large articles
    result = splitter.split_documents(docs)
    logger.info(f"After splitting: {len(result)} chunks")
    return result


def load_india_code_acts() -> list[Document]:
    path = os.path.join(RAW_DIR, "india_code_acts.json")
    if not os.path.exists(path):
        logger.warning("India Code acts JSON not found. Run fetch_india_code.py first.")
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for act in data:
        act_name = act.get("act_name", "Unknown Act")
        for section in act.get("sections", []):
            text = section.get("text", "").strip()
            if text and len(text) > 50:
                docs.append(Document(
                    page_content=f"{act_name}\n\n{text}",
                    metadata={
                        "source": "India Code",
                        "act_name": act_name,
                        "type": "legislation",
                        "chunk_index": section.get("chunk_index", 0)
                    }
                ))

    logger.info(f"Loaded {len(docs)} act documents")
    result = splitter.split_documents(docs)
    logger.info(f"After splitting: {len(result)} act chunks")
    return result


def load_schemes() -> list[Document]:
    # Try full scrape first, then HF fallback, then existing JSON
    candidates = [
        os.path.join(RAW_DIR, "myschemes_full.json"),
        os.path.join(RAW_DIR, "schemes_checkpoint.json"),
    ]
    # Add any HF files
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            if f.startswith("schemes_hf_"):
                candidates.insert(0, os.path.join(RAW_DIR, f))

    # Fallback to old file
    old_path = os.path.join(os.path.dirname(__file__), "..", "myschemes_scraped.json")
    if os.path.exists(old_path):
        candidates.append(old_path)

    data = None
    used_path = None
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    used_path = path
                    break
            except Exception:
                pass

    if not data:
        logger.warning("No scheme data found.")
        return []

    logger.info(f"Loading schemes from {used_path} ({len(data)} records)")
    docs = []

    for scheme in data:
        # Normalize field names
        name = scheme.get("scheme_name") or scheme.get("schemeName") or scheme.get("name") or "Unknown Scheme"
        details = scheme.get("details") or scheme.get("description") or ""
        benefits = scheme.get("benefits") or ""
        eligibility = scheme.get("eligibility") or ""
        application = scheme.get("application_process") or scheme.get("applicationProcess") or scheme.get("howToApply") or ""
        documents = scheme.get("documents_required") or scheme.get("documentsRequired") or scheme.get("documents") or ""
        tags = scheme.get("tags") or []
        ministry = scheme.get("ministry") or scheme.get("nodal_ministry") or ""
        state = scheme.get("state") or "Central"
        link = scheme.get("scheme_link") or scheme.get("schemeLink") or ""

        # Skip if literally everything is "Not Available"
        all_na = all(
            str(v).strip() in ("", "Not Available", "N/A")
            for v in [details, benefits, eligibility, application]
        )
        if all_na:
            continue

        content = f"""Scheme Name: {name}
Ministry/Department: {ministry}
State: {state}
Tags: {', '.join(tags) if isinstance(tags, list) else tags}

Details:
{details}

Benefits:
{benefits}

Eligibility Criteria:
{eligibility}

How to Apply:
{application}

Documents Required:
{documents}
""".strip()

        docs.append(Document(
            page_content=content,
            metadata={
                "source": "MyScheme.gov.in",
                "scheme_name": name,
                "type": "government_scheme",
                "ministry": ministry,
                "state": state,
                "scheme_link": link,
                "tags": json.dumps(tags) if isinstance(tags, list) else str(tags)
            }
        ))

    logger.info(f"Loaded {len(docs)} valid scheme documents (skipped empty ones)")
    result = splitter.split_documents(docs)
    logger.info(f"After splitting: {len(result)} scheme chunks")
    return result


# 
# INGEST INTO CHROMADB
# 

def ingest_all():
    from configs import config
    from stores.chroma import store_embeddings, load_vectorstore

    logger.info("Initializing embeddings...")
    embeddings = config.get_embeddings()
    if not embeddings:
        logger.error(" Could not initialize embeddings. Check AWS credentials.")
        return

    # Load all documents
    logger.info("\n=== Loading Constitution ===")
    constitution_docs = load_constitution()

    logger.info("\n=== Loading India Code Acts ===")
    acts_docs = load_india_code_acts()

    logger.info("\n=== Loading Government Schemes ===")
    schemes_docs = load_schemes()

    all_docs = constitution_docs + acts_docs + schemes_docs
    logger.info(f"\n Total documents to embed: {len(all_docs)}")
    logger.info(f"   - Constitution: {len(constitution_docs)}")
    logger.info(f"   - Acts: {len(acts_docs)}")
    logger.info(f"   - Schemes: {len(schemes_docs)}")

    if not all_docs:
        logger.error("No documents to ingest!")
        return

    # Batch ingest to avoid memory issues
    BATCH_SIZE = 100
    logger.info(f"\n Ingesting into ChromaDB in batches of {BATCH_SIZE}...")

    vectorstore = None
    for i in range(0, len(all_docs), BATCH_SIZE):
        batch = all_docs[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(all_docs) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info(f"  Batch {batch_num}/{total_batches}: embedding {len(batch)} docs...")

        try:
            if vectorstore is None:
                vectorstore = store_embeddings(batch, embeddings, persist_directory=CHROMA_DIR)
            else:
                vectorstore.add_documents(batch)
        except Exception as e:
            logger.error(f"   Error in batch {batch_num}: {e}")
            continue

    logger.info(f"\n Ingestion complete!")
    logger.info(f"   ChromaDB stored at: {CHROMA_DIR}")

    # Quick verification
    if vectorstore:
        test_queries = [
            "What are my fundamental rights?",
            "How to apply for PM Awas Yojana?",
            "Right to information RTI",
        ]
        logger.info("\n Verification tests:")
        for q in test_queries:
            results = vectorstore.similarity_search(q, k=2)
            logger.info(f"  Query: '{q}' → {len(results)} results")
            if results:
                logger.info(f"    Top result source: {results[0].metadata.get('source', 'unknown')}")


if __name__ == "__main__":
    ingest_all()
