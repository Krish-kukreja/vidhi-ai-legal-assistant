"""
VIDHI Data Pipeline — Master Runner
Runs all fetch scripts sequentially, then ingests everything into ChromaDB.

Usage:
    cd vidhi-backend
    python data_pipeline/run_pipeline.py

Options:
    --skip-schemes       Skip myscheme.gov.in scraping (takes longest)
    --skip-acts          Skip India Code scraping
    --skip-constitution  Skip constitution fetch
    --ingest-only        Only run ChromaDB ingestion (use existing raw/)
"""

import sys
import os
import argparse
import logging
import subprocess

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
        capture_output=False
    )
    if result.returncode != 0:
        logger.error(f" {step_label} failed with exit code {result.returncode}")
    else:
        logger.info(f" {step_label} completed")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="VIDHI Data Pipeline")
    parser.add_argument("--skip-schemes", action="store_true")
    parser.add_argument("--skip-acts", action="store_true")
    parser.add_argument("--skip-constitution", action="store_true")
    parser.add_argument("--ingest-only", action="store_true")
    args = parser.parse_args()

    logger.info(" VIDHI RAG Data Pipeline Starting...")
    
    raw_dir = os.path.join(PIPELINE_DIR, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    if not args.ingest_only:
        if not args.skip_constitution:
            run_step("fetch_constitution.py", "Step 1: Fetching Constitution of India")

        if not args.skip_acts:
            run_step("fetch_india_code.py", "Step 2: Fetching India Code Acts")

        if not args.skip_schemes:
            run_step("fetch_schemes.py", "Step 3: Fetching Government Schemes")

    # Always run ingestion last
    run_step("ingest_to_chroma.py", "Step 4: Ingesting all data into ChromaDB")

    logger.info("\n Pipeline complete! ChromaDB is now populated.")
    logger.info("Start your backend: python app.py")


if __name__ == "__main__":
    main()
