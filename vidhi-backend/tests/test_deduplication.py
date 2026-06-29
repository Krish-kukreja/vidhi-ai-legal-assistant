"""
Tests for Deduplication Logic
"""

import pytest
from data_pipeline.deduplicator import Deduplicator, deduplicate_json_file


class TestDeduplicator:
    """Test Deduplicator class"""

    def test_compute_hash(self):
        dedup = Deduplicator()
        hash1 = dedup.compute_hash("test content")
        hash2 = dedup.compute_hash("test content")
        hash3 = dedup.compute_hash("different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_normalize_content(self):
        dedup = Deduplicator()

        # Test whitespace normalization
        assert dedup.normalize_content("  test   content  ") == "test content"

        # Test lowercase
        assert dedup.normalize_content("TEST Content") == "test content"

        # Test multiple spaces
        assert dedup.normalize_content("test\n\n  content") == "test content"

    def test_compute_similarity(self):
        dedup = Deduplicator()

        # Identical strings
        assert dedup.compute_similarity("test", "test") == 1.0

        # Completely different
        similarity = dedup.compute_similarity("abc", "xyz")
        assert similarity < 0.5

        # Similar strings
        similarity = dedup.compute_similarity("hello world", "hello world!")
        assert similarity > 0.9

    def test_extract_content(self):
        dedup = Deduplicator()

        # Test with description field
        doc1 = {"description": "Test content", "other": "data"}
        assert dedup.extract_content(doc1) == "Test content"

        # Test with text field
        doc2 = {"text": "Test text", "other": "data"}
        assert dedup.extract_content(doc2) == "Test text"

        # Test with details field
        doc3 = {"details": "Test details", "other": "data"}
        assert dedup.extract_content(doc3) == "Test details"

        # Test fallback
        doc4 = {"field1": "value1", "field2": "value2"}
        content = dedup.extract_content(doc4)
        assert "value1" in content and "value2" in content

    def test_is_exact_duplicate(self):
        dedup = Deduplicator()

        doc1 = {"description": "Test content"}
        doc2 = {"description": "Test content"}  # Exact duplicate
        doc3 = {"description": "Different content"}

        # First document is not a duplicate
        is_dup1, hash1 = dedup.is_exact_duplicate(doc1)
        assert not is_dup1

        # Add to hash map
        dedup.hash_map[hash1] = doc1

        # Second document is a duplicate
        is_dup2, hash2 = dedup.is_exact_duplicate(doc2)
        assert is_dup2
        assert hash2 == hash1

        # Third document is not a duplicate
        is_dup3, hash3 = dedup.is_exact_duplicate(doc3)
        assert not is_dup3
        assert hash3 != hash1

    def test_find_near_duplicates(self):
        dedup = Deduplicator(similarity_threshold=0.85)

        doc1 = {"description": "This is a test document about legal rights"}
        doc2 = {
            "description": "This is a test document about legal rights!"
        }  # Very similar
        doc3 = {"description": "Completely different content here"}

        # Add doc1 to hash map
        _, hash1 = dedup.is_exact_duplicate(doc1)
        dedup.hash_map[hash1] = doc1

        # Find near-duplicates for doc2
        _, hash2 = dedup.is_exact_duplicate(doc2)
        near_dupes = dedup.find_near_duplicates(doc2, hash2)

        assert len(near_dupes) > 0
        assert near_dupes[0][1] >= 0.85  # Similarity score

        # Find near-duplicates for doc3
        _, hash3 = dedup.is_exact_duplicate(doc3)
        near_dupes3 = dedup.find_near_duplicates(doc3, hash3)

        assert len(near_dupes3) == 0  # No near-duplicates

    def test_merge_documents(self):
        dedup = Deduplicator()

        doc1 = {
            "scheme_name": "Test Scheme",
            "details": "Short details",
            "benefits": "Benefit 1",
        }

        doc2 = {
            "scheme_name": "Test Scheme",
            "details": "Much longer and more detailed description",
            "eligibility": "Eligible criteria",
        }

        merged = dedup.merge_documents(doc1, doc2)

        # Should keep longer details from doc2
        assert merged["details"] == doc2["details"]

        # Should keep benefits from doc1
        assert merged["benefits"] == "Benefit 1"

        # Should add eligibility from doc2
        assert merged["eligibility"] == "Eligible criteria"

        # Should have merge metadata
        assert "_merged_from" in merged

    def test_process_document_unique(self):
        dedup = Deduplicator()

        doc = {"description": "Unique content"}
        should_keep, merged = dedup.process_document(doc)

        assert should_keep
        assert merged is None
        assert dedup.stats["unique"] == 1
        assert dedup.stats["exact_duplicates"] == 0

    def test_process_document_exact_duplicate(self):
        dedup = Deduplicator()

        doc1 = {"description": "Test content"}
        doc2 = {"description": "Test content"}  # Exact duplicate

        # Process first document
        should_keep1, _ = dedup.process_document(doc1)
        assert should_keep1

        # Process duplicate
        should_keep2, _ = dedup.process_document(doc2)
        assert not should_keep2
        assert dedup.stats["exact_duplicates"] == 1

    def test_process_document_near_duplicate_no_merge(self):
        dedup = Deduplicator(similarity_threshold=0.85)

        doc1 = {"description": "This is a test document"}
        doc2 = {"description": "This is a test document!"}  # Near-duplicate

        # Process first document
        should_keep1, _ = dedup.process_document(doc1, auto_merge=False)
        assert should_keep1

        # Process near-duplicate without merging
        should_keep2, merged2 = dedup.process_document(doc2, auto_merge=False)
        assert should_keep2
        assert merged2 is None
        assert dedup.stats["near_duplicates"] == 1

    def test_process_document_near_duplicate_with_merge(self):
        dedup = Deduplicator(similarity_threshold=0.85)

        doc1 = {"description": "This is a test document", "field1": "value1"}
        doc2 = {"description": "This is a test document!", "field2": "value2"}

        # Process first document
        should_keep1, _ = dedup.process_document(doc1, auto_merge=True)
        assert should_keep1

        # Process near-duplicate with merging
        should_keep2, merged2 = dedup.process_document(doc2, auto_merge=True)
        assert should_keep2
        assert merged2 is not None
        assert "field1" in merged2
        assert "field2" in merged2
        assert dedup.stats["merged"] == 1

    def test_process_batch(self):
        dedup = Deduplicator()

        documents = [
            {"description": "Document 1"},
            {"description": "Document 1"},  # Exact duplicate
            {"description": "Document 2"},
            {"description": "Document 3"},
        ]

        unique_docs = dedup.process_batch(documents)

        assert len(unique_docs) == 3  # 1 duplicate removed
        assert dedup.stats["total_processed"] == 4
        assert dedup.stats["unique"] == 3
        assert dedup.stats["exact_duplicates"] == 1

    def test_process_batch_with_near_duplicates(self):
        dedup = Deduplicator(similarity_threshold=0.90)

        documents = [
            {"description": "This is a legal document about rights"},
            {"description": "This is a legal document about rights!"},  # Near-duplicate
            {"description": "Completely different content"},
        ]

        unique_docs = dedup.process_batch(documents, auto_merge=False)

        # All should be kept (no exact duplicates)
        assert len(unique_docs) == 3
        assert dedup.stats["near_duplicates"] >= 1

    def test_generate_report(self):
        dedup = Deduplicator()

        documents = [
            {"description": "Document 1"},
            {"description": "Document 1"},  # Duplicate
            {"description": "Document 2"},
        ]

        dedup.process_batch(documents)
        report = dedup.generate_report()

        assert "timestamp" in report
        assert "stats" in report
        assert "deduplication_rate" in report
        assert report["stats"]["total_processed"] == 3
        assert report["stats"]["exact_duplicates"] == 1
        assert report["deduplication_rate"] > 0

    def test_different_similarity_thresholds(self):
        # Strict threshold (0.95)
        dedup_strict = Deduplicator(similarity_threshold=0.95)

        doc1 = {"description": "This is a test"}
        doc2 = {"description": "This is a test!"}

        _, hash1 = dedup_strict.is_exact_duplicate(doc1)
        dedup_strict.hash_map[hash1] = doc1

        _, hash2 = dedup_strict.is_exact_duplicate(doc2)
        near_dupes_strict = dedup_strict.find_near_duplicates(doc2, hash2)

        # Lenient threshold (0.80)
        dedup_lenient = Deduplicator(similarity_threshold=0.80)
        dedup_lenient.hash_map[hash1] = doc1
        near_dupes_lenient = dedup_lenient.find_near_duplicates(doc2, hash2)

        # Lenient should find more near-duplicates
        assert len(near_dupes_lenient) >= len(near_dupes_strict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
