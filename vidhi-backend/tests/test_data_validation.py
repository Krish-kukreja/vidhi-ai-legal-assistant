"""
Tests for Data Validation Pipeline
"""

import pytest
import json
import os
from data_pipeline.data_validator import (
    DataValidator,
    DataType,
    ValidationStatus,
    ConstitutionArticle,
    LegislationSection,
    GovernmentScheme,
    validate_json_file
)


class TestConstitutionArticleSchema:
    """Test Constitution article validation"""
    
    def test_valid_article(self):
        data = {
            "article_no": "21",
            "title": "Protection of life and personal liberty",
            "description": "No person shall be deprived of his life or personal liberty except according to procedure established by law. This is a fundamental right guaranteed by the Constitution of India."
        }
        article = ConstitutionArticle(**data)
        assert article.article_no == "21"
        assert len(article.description) >= 50
    
    def test_invalid_short_description(self):
        data = {
            "article_no": "21",
            "title": "Protection of life",
            "description": "Short description"
        }
        with pytest.raises(Exception):
            ConstitutionArticle(**data)
    
    def test_invalid_placeholder_description(self):
        data = {
            "article_no": "21",
            "title": "Protection of life",
            "description": "Not Available"
        }
        with pytest.raises(Exception):
            ConstitutionArticle(**data)
    
    def test_empty_article_number(self):
        data = {
            "article_no": "",
            "title": "Test",
            "description": "A" * 100
        }
        with pytest.raises(Exception):
            ConstitutionArticle(**data)


class TestLegislationSectionSchema:
    """Test Legislation section validation"""
    
    def test_valid_section(self):
        data = {
            "act_name": "Indian Penal Code, 1860",
            "text": "A" * 150,  # Long enough text
            "chunk_index": 0
        }
        section = LegislationSection(**data)
        assert section.act_name == "Indian Penal Code, 1860"
        assert len(section.text) >= 100
    
    def test_invalid_short_text(self):
        data = {
            "act_name": "Indian Penal Code",
            "text": "Short text",
            "chunk_index": 0
        }
        with pytest.raises(Exception):
            LegislationSection(**data)
    
    def test_invalid_act_name(self):
        data = {
            "act_name": "Unknown Act",
            "text": "A" * 150,
            "chunk_index": 0
        }
        with pytest.raises(Exception):
            LegislationSection(**data)


class TestGovernmentSchemeSchema:
    """Test Government scheme validation"""
    
    def test_valid_scheme(self):
        data = {
            "scheme_name": "Pradhan Mantri Jan Dhan Yojana",
            "details": "A" * 100,
            "benefits": "Financial inclusion",
            "eligibility": "All Indian citizens",
            "application_process": "Visit nearest bank",
            "documents_required": "Aadhaar, PAN",
            "ministry": "Ministry of Finance",
            "state": "Central"
        }
        scheme = GovernmentScheme(**data)
        assert scheme.scheme_name == "Pradhan Mantri Jan Dhan Yojana"
        assert scheme.completeness_score() > 80
    
    def test_completeness_score(self):
        # All fields filled
        data_complete = {
            "scheme_name": "Test Scheme",
            "details": "A" * 100,
            "benefits": "Benefit 1",
            "eligibility": "Eligible 1",
            "application_process": "Process 1",
            "documents_required": "Doc 1",
            "ministry": "Ministry 1"
        }
        scheme = GovernmentScheme(**data_complete)
        assert scheme.completeness_score() == 100.0
        
        # Half fields filled
        data_half = {
            "scheme_name": "Test Scheme",
            "details": "A" * 100,
            "benefits": "Not Available",
            "eligibility": "Not Available",
            "application_process": "Not Available",
            "documents_required": "Not Available",
            "ministry": "Not Available"
        }
        scheme_half = GovernmentScheme(**data_half)
        assert scheme_half.completeness_score() < 50
    
    def test_invalid_scheme_name(self):
        data = {
            "scheme_name": "Unknown Scheme",
            "details": "A" * 100
        }
        with pytest.raises(Exception):
            GovernmentScheme(**data)


class TestDataValidator:
    """Test DataValidator class"""
    
    def test_validate_constitution_article_valid(self):
        validator = DataValidator()
        data = {
            "article_no": "14",
            "title": "Equality before law",
            "description": "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India. This is a fundamental right that ensures equal treatment for all citizens."
        }
        result = validator.validate_constitution_article(data)
        assert result.status == ValidationStatus.VALID
        assert len(result.errors) == 0
    
    def test_validate_constitution_article_warning(self):
        validator = DataValidator()
        data = {
            "article_no": "14",
            "title": "Equality before law",
            "description": "A" * 100  # Valid but short
        }
        result = validator.validate_constitution_article(data)
        assert result.status == ValidationStatus.WARNING
        assert len(result.warnings) > 0
    
    def test_validate_constitution_article_invalid(self):
        validator = DataValidator()
        data = {
            "article_no": "14",
            "title": "Equality",
            "description": "Short"  # Too short
        }
        result = validator.validate_constitution_article(data)
        assert result.status == ValidationStatus.INVALID
        assert len(result.errors) > 0
    
    def test_validate_scheme_valid(self):
        validator = DataValidator()
        data = {
            "scheme_name": "PM-KISAN",
            "details": "A" * 100,
            "benefits": "Financial support",
            "eligibility": "Small farmers",
            "application_process": "Online application",
            "documents_required": "Land records",
            "ministry": "Agriculture"
        }
        result = validator.validate_scheme(data)
        assert result.status == ValidationStatus.VALID
        assert result.completeness_score > 70
    
    def test_validate_scheme_low_completeness(self):
        validator = DataValidator()
        data = {
            "scheme_name": "Test Scheme",
            "details": "A" * 100,
            "benefits": "Not Available",
            "eligibility": "Not Available",
            "application_process": "Not Available",
            "documents_required": "Not Available",
            "ministry": "Not Available"
        }
        result = validator.validate_scheme(data)
        assert result.status == ValidationStatus.INVALID
        assert result.completeness_score < 50
    
    def test_validate_batch(self):
        validator = DataValidator()
        data = [
            {
                "article_no": "14",
                "title": "Equality before law",
                "description": "A" * 200
            },
            {
                "article_no": "15",
                "title": "Prohibition of discrimination",
                "description": "B" * 200
            },
            {
                "article_no": "16",
                "title": "Equality of opportunity",
                "description": "Short"  # Invalid
            }
        ]
        results = validator.validate_batch(data, DataType.CONSTITUTION)
        assert len(results) == 3
        assert validator.stats["total"] == 3
        assert validator.stats["valid"] >= 2
        assert validator.stats["invalid"] >= 1
    
    def test_get_valid_data(self):
        validator = DataValidator()
        data = [
            {
                "article_no": "14",
                "title": "Equality",
                "description": "A" * 200
            },
            {
                "article_no": "15",
                "title": "Prohibition",
                "description": "Short"  # Invalid
            }
        ]
        validator.validate_batch(data, DataType.CONSTITUTION)
        valid_data = validator.get_valid_data()
        assert len(valid_data) >= 1
    
    def test_get_invalid_data(self):
        validator = DataValidator()
        data = [
            {
                "article_no": "14",
                "title": "Equality",
                "description": "Short"  # Invalid
            }
        ]
        validator.validate_batch(data, DataType.CONSTITUTION)
        invalid_data = validator.get_invalid_data()
        assert len(invalid_data) >= 1
        assert "errors" in invalid_data[0]
    
    def test_generate_report(self):
        validator = DataValidator()
        data = [
            {
                "article_no": "14",
                "title": "Equality",
                "description": "A" * 200
            }
        ]
        validator.validate_batch(data, DataType.CONSTITUTION)
        report = validator.generate_report()
        
        assert "timestamp" in report
        assert "summary" in report
        assert "pass_rate" in report
        assert report["summary"]["total"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
