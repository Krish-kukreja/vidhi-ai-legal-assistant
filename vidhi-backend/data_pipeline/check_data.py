import json, os

raw = "data_pipeline/raw"

for fname in os.listdir(raw):
    path = os.path.join(raw, fname)
    size = os.path.getsize(path)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            print(f"{fname}: {len(data)} items, {size//1024} KB")
        elif isinstance(data, dict):
            print(f"{fname}: dict with keys {list(data.keys())[:5]}, {size//1024} KB")
    except Exception as e:
        print(f"{fname}: {size//1024} KB (error: {e})")
