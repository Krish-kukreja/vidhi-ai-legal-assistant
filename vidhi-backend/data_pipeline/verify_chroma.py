import os, sys
os.environ["PYDANTIC_SKIP_VALIDATING_CORE_SCHEMAS"] = "1"
sys.path.insert(0, ".")
from stores.chroma import load_vectorstore
from configs.config import get_embeddings

e = get_embeddings()
vs = load_vectorstore(e)
count = vs._collection.count()
print(f"ChromaDB total docs: {count}")

results = vs.similarity_search("fundamental rights arrest India", k=3)
for i, r in enumerate(results):
    src = r.metadata.get("source", "unknown")
    preview = r.page_content[:120].replace("\n", " ")
    print(f"  [{i+1}] {src} | {preview}")
