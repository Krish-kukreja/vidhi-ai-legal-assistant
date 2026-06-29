"""
VIDHI Data Pipeline — Master Runner
Runs all fetch scripts sequentially, validates data, deduplicates, then ingests into ChromaDB.

Usage:
    cd vidhi-backend
    python data_pipeline/run_pipeline.py

Options:
    --skip-schemes       Skip myscheme.gov.in scraping (takes longest)
    --skip-acts          Skip India Code scraping
    --skip-constitution  Skip constitution fetch
    --skip-validation    Skip data validation step
    --skip-dedup         Skip deduplication step
    --ingest-only        Only run ChromaDB ingestion (use existing raw/)
    --auto-merge         Automatically merge near-duplicate documents
"""

import sys
import os
import argparse
import logging
import subprocess
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(script_name: str, step_label: str):
    script_path = os.path.join(PIPELINE_DIR, script_name)
    logger.info(f"\n{'='*60}")
    logger.info(f" {step_label}")
    logger.info(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=os.path.join(PIPELINE_DIR, ".."),
        capture_output=False,
    )
    if result.returncode != 0:
        logger.error(f" {step_label} failed with exit code {result.returncode}")
    else:
        logger.info(f" {step_label} completed")
    return result.returncode == 0


def validate_and_deduplicate(
    skip_validation: bool = False, skip_dedup: bool = False, auto_merge: bool = False
):
    """Run validation and deduplication on all raw data files"""
    from data_pipeline.data_validator import DataValidator, DataType
    from data_pipeline.deduplicator import Deduplicator

    raw_dir = os.path.join(PIPELINE_DIR, "raw")

    # Define data files and their types
    data_files = [
        ("constitution_articles.json", DataType.CONSTITUTION),
        ("india_code_sections.json", DataType.LEGISLATION),
        ("myschemes_full.json", DataType.SCHEME),
    ]

    for filename, data_type in data_files:
        file_path = os.path.join(raw_dir, filename)

        if not os.path.exists(file_path):
            logger.warning(f"File not found: {filename}, skipping...")
            continue

        logger.info(f"\nProcessing {filename}...")

        # Load data
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        original_count = len(data)
        logger.info(f"  Original count: {original_count}")

        # Step 1: Validation
        if not skip_validation:
            logger.info(f"  Running validation...")
            validator = DataValidator()
            validator.validate_batch(data, data_type)

            report = validator.generate_report()
            logger.info(f"    Valid: {report['summary']['valid']}")
            logger.info(f"    Warning: {report['summary']['warning']}")
            logger.info(f"    Invalid: {report['summary']['invalid']}")
            logger.info(f"    Pass rate: {report['pass_rate']:.1f}%")

            # Save validation report
            validator.save_report()
            validator.save_review_queue()

            # Keep only valid data
            data = validator.get_valid_data()
            logger.info(f"  After validation: {len(data)} documents")

        # Step 2: Deduplication
        if not skip_dedup:
            logger.info(f"  Running deduplication...")
            deduplicator = Deduplicator(similarity_threshold=0.85)
            data = deduplicator.process_batch(data, auto_merge=auto_merge)

            logger.info(f"    Unique: {deduplicator.stats['unique']}")
            logger.info(
                f"    Exact duplicates: {deduplicator.stats['exact_duplicates']}"
            )
            logger.info(f"    Near duplicates: {deduplicator.stats['near_duplicates']}")
            logger.info(f"    Merged: {deduplicator.stats['merged']}")

            # Save deduplication report
            deduplicator.save_report()

            logger.info(f"  After deduplication: {len(data)} documents")

        # Save cleaned data
        cleaned_path = file_path.replace(".json", "_cleaned.json")
        with open(cleaned_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"  Cleaned data saved: {cleaned_path}")
        logger.info(
            f"  Reduction: {original_count - len(data)} documents ({(original_count - len(data)) / original_count * 100:.1f}%)"
        )


def main():
    parser = argparse.ArgumentParser(description="VIDHI Data Pipeline")
    parser.add_argument("--skip-schemes", action="store_true")
    parser.add_argument("--skip-acts", action="store_true")
    parser.add_argument("--skip-constitution", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--skip-dedup", action="store_true")
    parser.add_argument(
        "--auto-merge",
        action="store_true",
        help="Automatically merge near-duplicate documents",
    )
    parser.add_argument("--ingest-only", action="store_true")
    args = parser.parse_args()

    logger.info(" VIDHI RAG Data Pipeline Starting...")

    raw_dir = os.path.join(PIPELINE_DIR, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    if not args.ingest_only:
        # Step 1-3: Fetch data
        if not args.skip_constitution:
            run_step("fetch_constitution.py", "Step 1: Fetching Constitution of India")

        if not args.skip_acts:
            run_step("fetch_india_code.py", "Step 2: Fetching India Code Acts")

        if not args.skip_schemes:
            run_step("fetch_schemes.py", "Step 3: Fetching Government Schemes")

        # Step 4: Validate and deduplicate
        logger.info(f"\n{'='*60}")
        logger.info(f" Step 4: Data Validation & Deduplication")
        logger.info(f"{'='*60}")
        validate_and_deduplicate(
            skip_validation=args.skip_validation,
            skip_dedup=args.skip_dedup,
            auto_merge=args.auto_merge,
        )

    # Step 5: Ingest into ChromaDB
    run_step("ingest_to_chroma.py", "Step 5: Ingesting all data into ChromaDB")

    logger.info("\n Pipeline complete! ChromaDB is now populated.")
    logger.info("Start your backend: python app.py")


if __name__ == "__main__":
    main()
