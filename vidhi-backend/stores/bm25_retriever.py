"""
BM25 Retriever for VIDHI
Keyword-based search for exact legal citations.

Features:
- BM25 algorithm for keyword matching
- Tokenization optimized for legal text
- Caching for performance
- Configurable top_k results
"""

import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import re
from langchain.schema import Document

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25-based keyword retriever for legal documents"""

    def __init__(self, documents: List[Document]):
        """
        Initialize BM25 retriever with documents.

        Args:
            documents: List of LangChain Document objects
        """
        self.documents = documents
        self.tokenized_corpus = [self._tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25 index built with {len(documents)} documents")

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.
        Optimized for legal text with section numbers, citations, etc.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Preserve legal citations (e.g., "section 438", "438 crpc")
        # Replace common patterns with single tokens
        text = re.sub(r"section\s+(\d+)", r"section_\1", text)
        text = re.sub(r"(\d+)\s+(crpc|ipc|cpc)", r"\1_\2", text)
        text = re.sub(r"article\s+(\d+)", r"article_\1", text)

        # Split on whitespace and punctuation (except underscores)
        tokens = re.findall(r"\b[\w_]+\b", text)

        # Remove very short tokens (except numbers)
        tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]

        return tokens

    def search(self, query: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of documents with BM25 scores
        """
        # Tokenize query
        tokenized_query = self._tokenize(query)

        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
            :top_k
        ]

        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include documents with non-zero scores
                results.append(
                    {
                        "document": self.documents[idx],
                        "score": float(scores[idx]),
                        "rank": len(results) + 1,
                    }
                )

        logger.debug(
            f"BM25 search for '{query[:50]}...' returned {len(results)} results"
        )
        return results

    def get_top_documents(self, query: str, top_k: int = 50) -> List[Document]:
        """
        Get top k documents for a query (convenience method).

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of Document objects
        """
        results = self.search(query, top_k)
        return [r["document"] for r in results]


def create_bm25_retriever(documents: List[Document]) -> BM25Retriever:
    """
    Factory function to create BM25 retriever.

    Args:
        documents: List of documents to index

    Returns:
        BM25Retriever instance
    """
    return BM25Retriever(documents)


# Example usage
if __name__ == "__main__":
    # Test with sample legal documents
    sample_docs = [
        Document(
            page_content="Section 438 of the Code of Criminal Procedure (CrPC) deals with anticipatory bail.",
            metadata={"source": "crpc", "section": "438"},
        ),
        Document(
            page_content="Article 21 of the Constitution of India guarantees the right to life and personal liberty.",
            metadata={"source": "constitution", "article": "21"},
        ),
        Document(
            page_content="The Indian Penal Code Section 302 deals with punishment for murder.",
            metadata={"source": "ipc", "section": "302"},
        ),
    ]

    # Create retriever
    retriever = create_bm25_retriever(sample_docs)

    # Test queries
    test_queries = [
        "Section 438 CrPC",
        "anticipatory bail",
        "Article 21 Constitution",
        "murder punishment",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = retriever.search(query, top_k=2)
        for r in results:
            print(f"  Score: {r['score']:.2f} - {r['document'].page_content[:80]}...")
