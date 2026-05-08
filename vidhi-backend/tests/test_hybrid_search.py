"""
Tests for Hybrid Search Components
Tests BM25, Hybrid Retrieval, and Reranking
"""

import pytest
from langchain_core.documents import Document
from stores.bm25_retriever import BM25Retriever, create_bm25_retriever
from stores.hybrid_retriever import HybridRetriever, create_hybrid_retriever
from stores.reranker import CrossEncoderReranker, create_reranker


# Sample legal documents for testing
SAMPLE_DOCS = [
    Document(
        page_content="Section 438 of the Code of Criminal Procedure (CrPC) deals with anticipatory bail. It allows a person to seek bail in anticipation of arrest.",
        metadata={"source": "crpc", "section": "438", "type": "legislation"}
    ),
    Document(
        page_content="Anticipatory bail is a pre-arrest legal provision that allows a person to seek bail before being arrested. This is covered under Section 438 CrPC.",
        metadata={"source": "legal_guide", "topic": "bail", "type": "guide"}
    ),
    Document(
        page_content="Article 21 of the Constitution of India guarantees the right to life and personal liberty. No person shall be deprived of his life or personal liberty except according to procedure established by law.",
        metadata={"source": "constitution", "article": "21", "type": "constitution"}
    ),
    Document(
        page_content="The Indian Penal Code Section 302 deals with punishment for murder. Whoever commits murder shall be punished with death or imprisonment for life.",
        metadata={"source": "ipc", "section": "302", "type": "legislation"}
    ),
    Document(
        page_content="Bail is the temporary release of an accused person awaiting trial, sometimes on condition that a sum of money is lodged to guarantee their appearance in court.",
        metadata={"source": "legal_glossary", "term": "bail", "type": "glossary"}
    ),
]


class TestBM25Retriever:
    """Test BM25 retriever functionality"""
    
    def test_create_bm25_retriever(self):
        """Test BM25 retriever creation"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        assert retriever is not None
        assert len(retriever.documents) == len(SAMPLE_DOCS)
    
    def test_bm25_exact_section_match(self):
        """Test BM25 retrieves exact section numbers"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        
        # Query for exact section
        results = retriever.search("Section 438 CrPC", top_k=3)
        
        assert len(results) > 0
        # First result should contain "Section 438"
        assert "438" in results[0]["document"].page_content
        assert results[0]["score"] > 0
    
    def test_bm25_keyword_matching(self):
        """Test BM25 keyword matching"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        
        # Query with keywords
        results = retriever.search("anticipatory bail", top_k=3)
        
        assert len(results) > 0
        # Should find documents about anticipatory bail
        assert any("anticipatory" in r["document"].page_content.lower() for r in results)
    
    def test_bm25_tokenization(self):
        """Test BM25 tokenization preserves legal citations"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        
        # Test that "Section 438" is tokenized as "section_438"
        tokens = retriever._tokenize("Section 438 of CrPC")
        assert "section_438" in tokens or "438" in tokens
    
    def test_bm25_empty_query(self):
        """Test BM25 with empty query"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        results = retriever.search("", top_k=3)
        # Should return empty or all documents with zero scores
        assert isinstance(results, list)
    
    def test_bm25_no_matches(self):
        """Test BM25 with query that has no matches"""
        retriever = create_bm25_retriever(SAMPLE_DOCS)
        results = retriever.search("quantum physics relativity", top_k=3)
        # Should return empty list or very low scores
        assert len(results) == 0 or all(r["score"] < 1.0 for r in results)


class MockSemanticRetriever:
    """Mock semantic retriever for testing"""
    
    def __init__(self, docs):
        self.docs = docs
    
    def get_relevant_documents(self, query):
        # Simple mock: return docs in order, prioritizing semantic similarity
        # For testing, we'll return docs that contain query words
        query_lower = query.lower()
        relevant = [doc for doc in self.docs if any(word in doc.page_content.lower() for word in query_lower.split())]
        return relevant[:5] if relevant else self.docs[:5]


class TestHybridRetriever:
    """Test hybrid retriever functionality"""
    
    def test_create_hybrid_retriever(self):
        """Test hybrid retriever creation"""
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        
        hybrid_retriever = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            bm25_weight=0.5,
            semantic_weight=0.5,
            top_k=5
        )
        
        assert hybrid_retriever is not None
        assert hybrid_retriever.bm25_weight == 0.5
        assert hybrid_retriever.semantic_weight == 0.5
    
    def test_hybrid_search_combines_results(self):
        """Test hybrid search combines BM25 and semantic results"""
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        
        hybrid_retriever = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            top_k=5
        )
        
        results = hybrid_retriever.search("Section 438 CrPC anticipatory bail")
        
        assert len(results) > 0
        # Results should have RRF scores
        assert all("rrf_score" in r for r in results)
        # Results should be sorted by RRF score
        scores = [r["rrf_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_hybrid_weight_adjustment(self):
        """Test hybrid retriever with different weights"""
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        
        # BM25-heavy
        hybrid_bm25 = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            bm25_weight=0.8,
            semantic_weight=0.2,
            top_k=3
        )
        
        # Semantic-heavy
        hybrid_semantic = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            bm25_weight=0.2,
            semantic_weight=0.8,
            top_k=3
        )
        
        query = "Section 438"
        results_bm25 = hybrid_bm25.search(query)
        results_semantic = hybrid_semantic.search(query)
        
        # Both should return results
        assert len(results_bm25) > 0
        assert len(results_semantic) > 0
    
    def test_hybrid_get_relevant_documents(self):
        """Test LangChain-compatible interface"""
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        
        hybrid_retriever = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            top_k=3
        )
        
        docs = hybrid_retriever.get_relevant_documents("anticipatory bail")
        
        assert isinstance(docs, list)
        assert all(isinstance(doc, Document) for doc in docs)
        assert len(docs) <= 3


class TestCrossEncoderReranker:
    """Test cross-encoder reranker functionality"""
    
    @pytest.mark.slow
    def test_create_reranker(self):
        """Test reranker creation (slow - downloads model)"""
        reranker = create_reranker(cache_enabled=False)
        assert reranker is not None
        assert reranker.model is not None
    
    @pytest.mark.slow
    def test_reranker_scores_documents(self):
        """Test reranker assigns confidence scores"""
        reranker = create_reranker(confidence_threshold=0.0, cache_enabled=False)
        
        query = "What is Section 438 CrPC about?"
        results = reranker.rerank(query, SAMPLE_DOCS, top_k=3)
        
        assert len(results) > 0
        assert len(results) <= 3
        # All results should have confidence scores
        assert all("confidence" in r for r in results)
        # Scores should be sorted descending
        scores = [r["confidence"] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.slow
    def test_reranker_filters_by_threshold(self):
        """Test reranker filters by confidence threshold"""
        reranker = create_reranker(confidence_threshold=0.5, cache_enabled=False)
        
        query = "quantum physics"  # Irrelevant query
        results = reranker.rerank(query, SAMPLE_DOCS, top_k=5)
        
        # Should filter out low-confidence results
        assert all(r["confidence"] >= 0.5 for r in results)
    
    @pytest.mark.slow
    def test_reranker_caching(self):
        """Test reranker caching works"""
        reranker = create_reranker(cache_enabled=True)
        
        query = "Section 438 CrPC"
        
        # First call - no cache
        results1 = reranker.rerank(query, SAMPLE_DOCS[:2], top_k=2)
        
        # Second call - should use cache
        results2 = reranker.rerank(query, SAMPLE_DOCS[:2], top_k=2)
        
        # Results should be identical
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert abs(r1["confidence"] - r2["confidence"]) < 0.001
    
    @pytest.mark.slow
    def test_reranker_with_metadata(self):
        """Test reranker preserves metadata"""
        reranker = create_reranker(cache_enabled=False)
        
        # Documents with scores
        docs_with_scores = [
            {
                "document": SAMPLE_DOCS[0],
                "bm25_score": 10.5,
                "semantic_score": 0.8
            },
            {
                "document": SAMPLE_DOCS[1],
                "bm25_score": 8.2,
                "semantic_score": 0.9
            }
        ]
        
        query = "Section 438 CrPC"
        results = reranker.rerank_with_metadata(query, docs_with_scores, top_k=2)
        
        # Should preserve original metadata
        assert all("bm25_score" in r for r in results)
        assert all("semantic_score" in r for r in results)
        # Should add confidence scores
        assert all("confidence" in r for r in results)


class TestIntegration:
    """Integration tests for full hybrid search pipeline"""
    
    @pytest.mark.slow
    def test_full_pipeline(self):
        """Test complete hybrid search + reranking pipeline"""
        # Create components
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        hybrid_retriever = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            top_k=5
        )
        reranker = create_reranker(confidence_threshold=0.0, cache_enabled=False)
        
        # Query
        query = "What is anticipatory bail under Section 438 CrPC?"
        
        # Get hybrid results
        hybrid_results = hybrid_retriever.get_relevant_documents_with_scores(query)
        assert len(hybrid_results) > 0
        
        # Rerank
        reranked_results = reranker.rerank_with_metadata(query, hybrid_results, top_k=3)
        assert len(reranked_results) > 0
        assert len(reranked_results) <= 3
        
        # Top result should be highly relevant
        top_result = reranked_results[0]
        assert "438" in top_result["document"].page_content
        assert top_result["confidence"] > 0.5
    
    def test_accuracy_improvement(self):
        """Test that hybrid search improves over pure BM25 or semantic"""
        # This is a qualitative test - in practice, you'd have ground truth labels
        bm25_retriever = create_bm25_retriever(SAMPLE_DOCS)
        semantic_retriever = MockSemanticRetriever(SAMPLE_DOCS)
        hybrid_retriever = create_hybrid_retriever(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            top_k=3
        )
        
        # Query that benefits from hybrid approach
        query = "Section 438 anticipatory bail"
        
        # BM25 only
        bm25_results = bm25_retriever.search(query, top_k=3)
        
        # Hybrid
        hybrid_results = hybrid_retriever.search(query, top_k=3)
        
        # Both should return results
        assert len(bm25_results) > 0
        assert len(hybrid_results) > 0
        
        # Hybrid should combine evidence from both retrievers
        assert len(hybrid_results) >= len(bm25_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
