# Migration Notes

## Scraper Update (May 2026)

### What Changed
- **Deleted**: `scraper.py` (broken - hit wrong URL `rules.myscheme.in`)
- **Use instead**: `data_pipeline/fetch_schemes.py` (correct URL `myscheme.gov.in`)

### Why
The old scraper had a critical bug where it scraped `https://rules.myscheme.in/` instead of `https://www.myscheme.gov.in/schemes/<slug>`. This resulted in all fields showing "Not Available".

The new scraper:
- ✅ Hits correct URLs
- ✅ Has HuggingFace fallback for instant data
- ✅ Better error handling with checkpoints
- ✅ Retry logic and rate limiting
- ✅ Extracts data from Next.js `__NEXT_DATA__` JSON (more reliable)

### Migration Steps

If you have `myschemes_scraped.json` from the old scraper:

1. **Run the new scraper**:
   ```bash
   python data_pipeline/fetch_schemes.py
   ```
   This creates `data_pipeline/raw/myschemes_full.json`

2. **Or run the full pipeline**:
   ```bash
   python data_pipeline/run_pipeline.py
   ```
   This fetches Constitution, schemes, acts, and ingests to ChromaDB

3. **Update your code** (if you referenced the old file):
   - Old: `myschemes_scraped.json`
   - New: `data_pipeline/raw/myschemes_full.json`

### Config Changes
- `configs/config.py` now points to `data_pipeline/raw/myschemes_full.json`
- S3 key updated to `schemes/myschemes_full.json`

### Backward Compatibility
The data pipeline scripts still check for `myschemes_scraped.json` as a fallback for slug extraction, but this will be removed in a future version.
