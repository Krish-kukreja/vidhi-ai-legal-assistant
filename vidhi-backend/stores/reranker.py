"""
Cross-Encoder Reranker for VIDHI
Reranks retrieved documents using a cross-encoder model for improved accuracy.

Features:
- Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
- Batch processing for efficiency
- Confidence scores (0-1)
- Caching for performance
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
from langchain.schema import Document
import hashlib
import time

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-encoder reranker for document reranking"""
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        confidence_threshold: float = 0.0,
        batch_size: int = 32,
        cache_enabled: bool = True
    ):
        """
        Initialize cross-encoder reranker.
        
        Args:
            model_name: HuggingFace model name
            confidence_threshold: Minimum confidence score (0-1)
            batch_size: Batch size for reranking
            cache_enabled: Enable caching of reranking results
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        self.cache_enabled = cache_enabled
        self.cache = {} if cache_enabled else None
        
        # Load model
        logger.info(f"Loading cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name)
        logger.info("Cross-encoder model loaded successfully")
    
    def _compute_cache_key(self, query: str, doc_content: str) -> str:
        """Compute cache key for query-document pair"""
        combined = f"{query}||{doc_content}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using cross-encoder.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top results to return (None = all)
            
        Returns:
            List of documents with confidence scores, sorted by score
        """
        if not documents:
            return []
        
        logger.debug(f"Reranking {len(documents)} documents for query: '{query[:50]}...'")
        start_time = time.time()
        
        # Prepare query-document pairs
        pairs = []
        cache_hits = 0
        cached_scores = {}
        
        for doc in documents:
            doc_content = doc.page_content
            
            # Check cache
            if self.cache_enabled:
                cache_key = self._compute_cache_key(query, doc_content)
                if cache_key in self.cache:
                    cached_scores[doc_content] = self.cache[cache_key]
                    cache_hits += 1
                    continue
            
            pairs.append([query, doc_content])
        
        # Compute scores for non-cached pairs
        if pairs:
            scores = self.model.predict(pairs, batch_size=self.batch_size)
            
            # Cache scores
            if self.cache_enabled:
                for i, (query_text, doc_content) in enumerate(pairs):
                    cache_key = self._compute_cache_key(query_text, doc_content)
                    self.cache[cache_key] = float(scores[i])
        else:
            scores = []
        
        # Build results
        results = []
        score_idx = 0
        
        for doc in documents:
            doc_content = doc.page_content
            
            # Get score (from cache or computed)
            if doc_content in cached_scores:
                score = cached_scores[doc_content]
            else:
                score = float(scores[score_idx])
                score_idx += 1
            
            # Filter by confidence threshold
            if score >= self.confidence_threshold:
                results.append({
                    "document": doc,
                    "confidence": score,
                    "rank": 0  # Will be set after sorting
                })
        
        # Sort by confidence score
        results.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Set ranks
        for i, result in enumerate(results, 1):
            result["rank"] = i
        
        # Apply top_k filter
        if top_k is not None:
            results = results[:top_k]
        
        elapsed = time.time() - start_time
        logger.info(
            f"Reranked {len(documents)} docs → {len(results)} results "
            f"(cache hits: {cache_hits}, time: {elapsed:.2f}s)"
        )
        
        return results
    
    def rerank_with_metadata(
        self,
        query: str,
        documents_with_scores: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents that already have scores/metadata.
        
        Args:
            query: Search query
            documents_with_scores: List of dicts with 'document' key
            top_k: Number of top results to return
            
        Returns:
            List of documents with updated confidence scores
        """
        # Extract documents
        documents = [item["document"] for item in documents_with_scores]
        
        # Rerank
        reranked = self.rerank(query, documents, top_k)
        
        # Merge with original metadata
        doc_to_reranked = {
            r["document"].page_content: r for r in reranked
        }
        
        results = []
        for item in documents_with_scores:
            doc_content = item["document"].page_content
            if doc_content in doc_to_reranked:
                # Merge original metadata with reranking results
                merged = {**item, **doc_to_reranked[doc_content]}
                results.append(merged)
        
        return results
    
    def get_top_documents(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 10
    ) -> List[Document]:
        """
        Get top k documents after reranking (convenience method).
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of results to return
            
        Returns:
            List of top k Document objects
        """
        results = self.rerank(query, documents, top_k)
        return [r["document"] for r in results]
    
    def clear_cache(self):
        """Clear reranking cache"""
        if self.cache_enabled:
            self.cache.clear()
            logger.info("Reranking cache cleared")


def create_reranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    confidence_threshold: float = 0.0,
    batch_size: int = 32,
    cache_enabled: bool = True
) -> CrossEncoderReranker:
    """
    Factory function to create reranker.
    
    Args:
        model_name: HuggingFace model name
        confidence_threshold: Minimum confidence score
        batch_size: Batch size for reranking
        cache_enabled: Enable caching
        
    Returns:
        CrossEncoderReranker instance
    """
    return CrossEncoderReranker(
        model_name=model_name,
        confidence_threshold=confidence_threshold,
        batch_size=batch_size,
        cache_enabled=cache_enabled
    )


# Example usage
if __name__ == "__main__":
    # Sample documents
    sample_docs = [
        Document(
            page_content="Section 438 of the Code of Criminal Procedure (CrPC) deals with anticipatory bail.",
            metadata={"source": "crpc", "section": "438"}
        ),
        Document(
            page_content="The Indian Penal Code Section 302 deals with punishment for murder.",
            metadata={"source": "ipc", "section": "302"}
        ),
        Document(
            page_content="Anticipatory bail allows a person to seek bail before arrest under Section 438 CrPC.",
            metadata={"source": "legal_guide"}
        ),
    ]
    
    # Create reranker
    reranker = create_reranker(confidence_threshold=0.3)
    
    # Test query
    query = "What is Section 438 CrPC about?"
    print(f"\nQuery: {query}\n")
    
    results = reranker.rerank(query, sample_docs, top_k=3)
    for r in results:
        print(f"Rank {r['rank']}: Confidence {r['confidence']:.4f}")
        print(f"  {r['document'].page_content[:80]}...")
        print()
