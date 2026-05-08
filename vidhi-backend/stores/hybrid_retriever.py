"""
Hybrid Retriever for VIDHI
Combines BM25 keyword search with semantic search using Reciprocal Rank Fusion.

Features:
- Hybrid search (BM25 + Semantic)
- Reciprocal Rank Fusion (RRF) for merging results
- Configurable weights
- Deduplication of results
"""

import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain.retrievers import EnsembleRetriever
from stores.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever combining BM25 and semantic search"""
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        semantic_retriever: Any,  # ChromaDB retriever
        bm25_weight: float = 0.5,
        semantic_weight: float = 0.5,
        top_k: int = 50
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            bm25_retriever: BM25 retriever instance
            semantic_retriever: Semantic (ChromaDB) retriever instance
            bm25_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for semantic scores (0-1)
            top_k: Number of results to return
        """
        self.bm25_retriever = bm25_retriever
        self.semantic_retriever = semantic_retriever
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.top_k = top_k
        
        # Normalize weights
        total_weight = bm25_weight + semantic_weight
        self.bm25_weight = bm25_weight / total_weight
        self.semantic_weight = semantic_weight / total_weight
        
        logger.info(f"Hybrid retriever initialized (BM25: {self.bm25_weight:.2f}, Semantic: {self.semantic_weight:.2f})")
    
    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[Dict[str, Any]],
        semantic_results: List[Document],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score = sum(1 / (k + rank_i)) for each retriever
        
        Args:
            bm25_results: Results from BM25 retriever
            semantic_results: Results from semantic retriever
            k: Constant for RRF (default: 60)
            
        Returns:
            Merged and ranked results
        """
        # Build document ID to content mapping
        doc_scores = {}
        
        # Process BM25 results
        for rank, result in enumerate(bm25_results, start=1):
            doc_content = result["document"].page_content
            rrf_score = self.bm25_weight / (k + rank)
            
            if doc_content not in doc_scores:
                doc_scores[doc_content] = {
                    "document": result["document"],
                    "rrf_score": 0,
                    "bm25_rank": rank,
                    "bm25_score": result["score"],
                    "semantic_rank": None,
                    "semantic_score": None
                }
            
            doc_scores[doc_content]["rrf_score"] += rrf_score
        
        # Process semantic results
        for rank, doc in enumerate(semantic_results, start=1):
            doc_content = doc.page_content
            rrf_score = self.semantic_weight / (k + rank)
            
            if doc_content not in doc_scores:
                doc_scores[doc_content] = {
                    "document": doc,
                    "rrf_score": 0,
                    "bm25_rank": None,
                    "bm25_score": None,
                    "semantic_rank": rank,
                    "semantic_score": None  # ChromaDB doesn't return scores by default
                }
            
            doc_scores[doc_content]["rrf_score"] += rrf_score
            doc_scores[doc_content]["semantic_rank"] = rank
        
        # Sort by RRF score
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        return sorted_results[:self.top_k]
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 and semantic search.
        
        Args:
            query: Search query
            top_k: Number of results to return (overrides default)
            
        Returns:
            List of documents with hybrid scores
        """
        top_k = top_k or self.top_k
        
        logger.debug(f"Hybrid search for: '{query[:50]}...'")
        
        # Get BM25 results
        bm25_results = self.bm25_retriever.search(query, top_k=top_k)
        logger.debug(f"BM25 returned {len(bm25_results)} results")
        
        # Get semantic results
        semantic_results = self.semantic_retriever.get_relevant_documents(query)[:top_k]
        logger.debug(f"Semantic search returned {len(semantic_results)} results")
        
        # Merge using RRF
        hybrid_results = self._reciprocal_rank_fusion(bm25_results, semantic_results)
        
        logger.info(f"Hybrid search returned {len(hybrid_results)} results")
        return hybrid_results
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Get relevant documents (LangChain-compatible interface).
        
        Args:
            query: Search query
            
        Returns:
            List of Document objects
        """
        results = self.search(query)
        return [r["document"] for r in results]
    
    def get_relevant_documents_with_scores(self, query: str) -> List[Dict[str, Any]]:
        """
        Get relevant documents with scores.
        
        Args:
            query: Search query
            
        Returns:
            List of documents with scores and metadata
        """
        return self.search(query)


def create_hybrid_retriever(
    bm25_retriever: BM25Retriever,
    semantic_retriever: Any,
    bm25_weight: float = 0.5,
    semantic_weight: float = 0.5,
    top_k: int = 50
) -> HybridRetriever:
    """
    Factory function to create hybrid retriever.
    
    Args:
        bm25_retriever: BM25 retriever instance
        semantic_retriever: Semantic retriever instance
        bm25_weight: Weight for BM25 scores
        semantic_weight: Weight for semantic scores
        top_k: Number of results to return
        
    Returns:
        HybridRetriever instance
    """
    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        semantic_retriever=semantic_retriever,
        bm25_weight=bm25_weight,
        semantic_weight=semantic_weight,
        top_k=top_k
    )


# Example usage
if __name__ == "__main__":
    from stores.bm25_retriever import create_bm25_retriever
    
    # Sample documents
    sample_docs = [
        Document(
            page_content="Section 438 of the Code of Criminal Procedure (CrPC) deals with anticipatory bail. It allows a person to seek bail in anticipation of arrest.",
            metadata={"source": "crpc", "section": "438"}
        ),
        Document(
            page_content="Anticipatory bail is a pre-arrest legal provision that allows a person to seek bail before being arrested.",
            metadata={"source": "legal_guide", "topic": "bail"}
        ),
        Document(
            page_content="Article 21 of the Constitution of India guarantees the right to life and personal liberty.",
            metadata={"source": "constitution", "article": "21"}
        ),
    ]
    
    # Create BM25 retriever
    bm25_retriever = create_bm25_retriever(sample_docs)
    
    # Mock semantic retriever (in real use, this would be ChromaDB)
    class MockSemanticRetriever:
        def __init__(self, docs):
            self.docs = docs
        
        def get_relevant_documents(self, query):
            # Simple mock: return docs in reverse order
            return list(reversed(self.docs))
    
    semantic_retriever = MockSemanticRetriever(sample_docs)
    
    # Create hybrid retriever
    hybrid_retriever = create_hybrid_retriever(
        bm25_retriever=bm25_retriever,
        semantic_retriever=semantic_retriever,
        bm25_weight=0.5,
        semantic_weight=0.5,
        top_k=3
    )
    
    # Test query
    query = "Section 438 CrPC anticipatory bail"
    print(f"\nQuery: {query}\n")
    
    results = hybrid_retriever.get_relevant_documents_with_scores(query)
    for i, r in enumerate(results, 1):
        print(f"{i}. RRF Score: {r['rrf_score']:.4f}")
        print(f"   BM25 Rank: {r['bm25_rank']}, Semantic Rank: {r['semantic_rank']}")
        print(f"   Content: {r['document'].page_content[:80]}...")
        print()
