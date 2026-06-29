"""
Deduplication Logic for VIDHI Data Pipeline
Detects and removes duplicate documents before ChromaDB ingestion.

Features:
- Content hashing (SHA-256)
- Fuzzy matching for near-duplicates (Levenshtein distance)
- Metadata-based deduplication
- Merge logic for near-duplicates
- Deduplication reports
"""

import os
import json
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class Deduplicator:
    """Main deduplication class"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Threshold for fuzzy matching (0-1)
                                 0.85 = 85% similar content is considered duplicate
        """
        self.similarity_threshold = similarity_threshold
        self.hash_map: Dict[str, Dict[str, Any]] = {}  # hash -> document
        self.duplicates: List[Dict[str, Any]] = []
        self.near_duplicates: List[Tuple[Dict, Dict, float]] = []

        self.stats = {
            "total_processed": 0,
            "unique": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "merged": 0,
        }

    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def normalize_content(self, content: str) -> str:
        """Normalize content for comparison"""
        # Remove extra whitespace, lowercase, strip
        normalized = " ".join(content.lower().split())
        return normalized

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts using SequenceMatcher.
        Returns value between 0 (completely different) and 1 (identical).
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def extract_content(self, doc: Dict[str, Any]) -> str:
        """Extract main content from document for comparison"""
        # Try different content fields based on document type
        content_fields = ["description", "text", "details", "content", "body"]

        for field in content_fields:
            if field in doc and doc[field]:
                return str(doc[field])

        # Fallback: concatenate all string values
        return " ".join(str(v) for v in doc.values() if isinstance(v, str))

    def is_exact_duplicate(self, doc: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if document is an exact duplicate.
        Returns (is_duplicate, hash_of_duplicate)
        """
        content = self.extract_content(doc)
        normalized = self.normalize_content(content)
        content_hash = self.compute_hash(normalized)

        if content_hash in self.hash_map:
            return True, content_hash

        return False, content_hash

    def find_near_duplicates(
        self, doc: Dict[str, Any], content_hash: str
    ) -> List[Tuple[Dict, float]]:
        """
        Find near-duplicate documents using fuzzy matching.
        Returns list of (document, similarity_score) tuples.
        """
        near_dupes = []
        doc_content = self.normalize_content(self.extract_content(doc))

        for existing_hash, existing_doc in self.hash_map.items():
            if existing_hash == content_hash:
                continue  # Skip exact duplicates

            existing_content = self.normalize_content(
                self.extract_content(existing_doc)
            )
            similarity = self.compute_similarity(doc_content, existing_content)

            if similarity >= self.similarity_threshold:
                near_dupes.append((existing_doc, similarity))

        return near_dupes

    def merge_documents(
        self, doc1: Dict[str, Any], doc2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two near-duplicate documents.
        Strategy: Keep non-empty fields from both, prefer longer content.
        """
        merged = doc1.copy()

        for key, value in doc2.items():
            if key not in merged or not merged[key]:
                # Field missing in doc1, take from doc2
                merged[key] = value
            elif value and len(str(value)) > len(str(merged[key])):
                # doc2 has longer content, prefer it
                merged[key] = value

        # Add metadata about merge
        merged["_merged_from"] = [
            doc1.get("scheme_name")
            or doc1.get("article_no")
            or doc1.get("act_name")
            or "unknown",
            doc2.get("scheme_name")
            or doc2.get("article_no")
            or doc2.get("act_name")
            or "unknown",
        ]

        return merged

    def process_document(
        self, doc: Dict[str, Any], auto_merge: bool = False
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Process a single document for deduplication.

        Returns:
            (should_keep, merged_doc)
            - should_keep: True if document should be kept (unique or merged)
            - merged_doc: Merged document if near-duplicates were found and auto_merge=True
        """
        self.stats["total_processed"] += 1

        # Check for exact duplicate
        is_exact_dup, content_hash = self.is_exact_duplicate(doc)

        if is_exact_dup:
            self.stats["exact_duplicates"] += 1
            self.duplicates.append(
                {
                    "document": doc,
                    "duplicate_of": self.hash_map[content_hash],
                    "hash": content_hash,
                }
            )
            logger.debug(f"Exact duplicate found: {content_hash[:16]}...")
            return False, None

        # Check for near-duplicates
        near_dupes = self.find_near_duplicates(doc, content_hash)

        if near_dupes:
            self.stats["near_duplicates"] += 1

            # Store near-duplicate info
            for near_doc, similarity in near_dupes:
                self.near_duplicates.append((doc, near_doc, similarity))
                logger.debug(f"Near-duplicate found: {similarity:.2%} similar")

            if auto_merge:
                # Merge with the most similar document
                most_similar_doc, _ = max(near_dupes, key=lambda x: x[1])
                merged = self.merge_documents(doc, most_similar_doc)
                self.stats["merged"] += 1

                # Update hash map with merged document
                self.hash_map[content_hash] = merged
                return True, merged
            else:
                # Keep original without merging
                self.hash_map[content_hash] = doc
                self.stats["unique"] += 1
                return True, None

        # Unique document
        self.hash_map[content_hash] = doc
        self.stats["unique"] += 1
        return True, None

    def process_batch(
        self, documents: List[Dict[str, Any]], auto_merge: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of documents.

        Args:
            documents: List of documents to deduplicate
            auto_merge: If True, automatically merge near-duplicates

        Returns:
            List of unique documents (with merged documents if auto_merge=True)
        """
        unique_docs = []

        for doc in documents:
            should_keep, merged_doc = self.process_document(doc, auto_merge)

            if should_keep:
                unique_docs.append(merged_doc if merged_doc else doc)

        logger.info(f"Deduplication complete:")
        logger.info(f"  Total processed: {self.stats['total_processed']}")
        logger.info(f"  Unique: {self.stats['unique']}")
        logger.info(f"  Exact duplicates: {self.stats['exact_duplicates']}")
        logger.info(f"  Near duplicates: {self.stats['near_duplicates']}")
        logger.info(f"  Merged: {self.stats['merged']}")

        return unique_docs

    def generate_report(self) -> Dict[str, Any]:
        """Generate deduplication report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "deduplication_rate": (
                (
                    (self.stats["exact_duplicates"] + self.stats["near_duplicates"])
                    / self.stats["total_processed"]
                    * 100
                )
                if self.stats["total_processed"] > 0
                else 0
            ),
            "exact_duplicates_sample": self.duplicates[:10],  # First 10
            "near_duplicates_sample": [
                {
                    "doc1": doc1.get("scheme_name")
                    or doc1.get("article_no")
                    or "unknown",
                    "doc2": doc2.get("scheme_name")
                    or doc2.get("article_no")
                    or "unknown",
                    "similarity": f"{similarity:.2%}",
                }
                for doc1, doc2, similarity in self.near_duplicates[:10]
            ],
        }

    def save_report(self, output_dir: str = None):
        """Save deduplication report"""
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), "dedup_reports")

        os.makedirs(output_dir, exist_ok=True)

        report = self.generate_report()
        report_path = os.path.join(
            output_dir, f"dedup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Deduplication report saved: {report_path}")
        return report_path


#
# CONVENIENCE FUNCTIONS
#


def deduplicate_json_file(
    file_path: str,
    output_path: str = None,
    auto_merge: bool = False,
    similarity_threshold: float = 0.85,
) -> List[Dict[str, Any]]:
    """
    Deduplicate a JSON file.

    Args:
        file_path: Path to input JSON file
        output_path: Path to output JSON file (optional)
        auto_merge: If True, automatically merge near-duplicates
        similarity_threshold: Threshold for near-duplicate detection (0-1)

    Returns:
        List of unique documents
    """
    logger.info(f"Deduplicating {file_path}...")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    deduplicator = Deduplicator(similarity_threshold=similarity_threshold)
    unique_docs = deduplicator.process_batch(data, auto_merge=auto_merge)

    # Save deduplicated data
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_docs, f, indent=2, ensure_ascii=False)
        logger.info(f"Deduplicated data saved: {output_path}")

    # Save report
    deduplicator.save_report()

    return unique_docs


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python deduplicator.py <input_file> [output_file] [--auto-merge] [--threshold=0.85]"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = (
        sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    )
    auto_merge = "--auto-merge" in sys.argv

    threshold = 0.85
    for arg in sys.argv:
        if arg.startswith("--threshold="):
            threshold = float(arg.split("=")[1])

    deduplicate_json_file(input_file, output_file, auto_merge, threshold)
