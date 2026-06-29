"""
Data Validation Pipeline for VIDHI
Validates scraped data before ingestion into ChromaDB.

Features:
- Pydantic schemas for all data types
- Field validation (required, length, format)
- Content quality checks
- Data completeness scoring
- Validation reports
- Manual review queue for failed validations
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class DataType(str, Enum):
    CONSTITUTION = "constitution"
    LEGISLATION = "legislation"
    SCHEME = "scheme"
    TEMPLATE = "template"


#
# PYDANTIC SCHEMAS
#


class ConstitutionArticle(BaseModel):
    """Schema for Constitution articles"""

    article_no: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=50)

    @validator("description")
    def validate_description(cls, v):
        if len(v.strip()) < 50:
            raise ValueError("Description too short (min 50 chars)")
        if v.strip().lower() in ["not available", "n/a", "na", ""]:
            raise ValueError("Description is placeholder text")
        return v.strip()

    @validator("article_no")
    def validate_article_no(cls, v):
        # Allow formats like "1", "1A", "14A", "21", etc.
        if not v.strip():
            raise ValueError("Article number cannot be empty")
        return v.strip()


class LegislationSection(BaseModel):
    """Schema for India Code Act sections"""

    act_name: str = Field(..., min_length=5, max_length=500)
    text: str = Field(..., min_length=100)
    chunk_index: Optional[int] = 0

    @validator("text")
    def validate_text(cls, v):
        if len(v.strip()) < 100:
            raise ValueError("Section text too short (min 100 chars)")
        if v.strip().lower() in ["not available", "n/a", "na", ""]:
            raise ValueError("Section text is placeholder")
        return v.strip()

    @validator("act_name")
    def validate_act_name(cls, v):
        if v.strip().lower() in ["unknown act", "not available", ""]:
            raise ValueError("Act name is invalid")
        return v.strip()


class GovernmentScheme(BaseModel):
    """Schema for government schemes"""

    scheme_name: str = Field(..., min_length=5, max_length=500)
    details: str = Field(..., min_length=50)
    benefits: Optional[str] = "Not Available"
    eligibility: Optional[str] = "Not Available"
    application_process: Optional[str] = "Not Available"
    documents_required: Optional[str] = "Not Available"
    ministry: Optional[str] = ""
    state: Optional[str] = "Central"
    scheme_link: Optional[str] = ""
    tags: Optional[List[str]] = []

    @validator("scheme_name")
    def validate_scheme_name(cls, v):
        if v.strip().lower() in ["unknown scheme", "not available", ""]:
            raise ValueError("Scheme name is invalid")
        return v.strip()

    @validator("details")
    def validate_details(cls, v):
        if len(v.strip()) < 50:
            raise ValueError("Details too short (min 50 chars)")
        if v.strip().lower() in ["not available", "n/a", "na", ""]:
            raise ValueError("Details are placeholder text")
        return v.strip()

    def completeness_score(self) -> float:
        """Calculate data completeness (0-100%)"""
        fields = [
            self.details,
            self.benefits,
            self.eligibility,
            self.application_process,
            self.documents_required,
            self.ministry,
        ]

        valid_fields = sum(
            1
            for f in fields
            if f
            and f.strip()
            and f.strip().lower() not in ["not available", "n/a", "na", ""]
        )

        return (valid_fields / len(fields)) * 100


#
# VALIDATION RESULT
#


class ValidationResult(BaseModel):
    """Result of validating a single document"""

    status: ValidationStatus
    data_type: DataType
    original_data: Dict[str, Any]
    errors: List[str] = []
    warnings: List[str] = []
    completeness_score: Optional[float] = None
    validated_at: datetime = Field(default_factory=datetime.now)


#
# VALIDATOR CLASS
#


class DataValidator:
    """Main validator class"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "validation_reports"
        )
        os.makedirs(self.output_dir, exist_ok=True)

        self.results: List[ValidationResult] = []
        self.stats = {
            "total": 0,
            "valid": 0,
            "warning": 0,
            "invalid": 0,
            "needs_review": 0,
        }

    def validate_constitution_article(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a constitution article"""
        errors = []
        warnings = []
        status = ValidationStatus.VALID

        try:
            article = ConstitutionArticle(**data)

            # Additional quality checks
            if len(article.description) < 200:
                warnings.append("Description is short (< 200 chars)")
                status = ValidationStatus.WARNING

            if not article.title:
                warnings.append("Title is empty")
                status = ValidationStatus.WARNING

        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            status = ValidationStatus.INVALID

        return ValidationResult(
            status=status,
            data_type=DataType.CONSTITUTION,
            original_data=data,
            errors=errors,
            warnings=warnings,
        )

    def validate_legislation_section(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a legislation section"""
        errors = []
        warnings = []
        status = ValidationStatus.VALID

        try:
            section = LegislationSection(**data)

            # Additional quality checks
            if len(section.text) < 300:
                warnings.append("Section text is short (< 300 chars)")
                status = ValidationStatus.WARNING

        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            status = ValidationStatus.INVALID

        return ValidationResult(
            status=status,
            data_type=DataType.LEGISLATION,
            original_data=data,
            errors=errors,
            warnings=warnings,
        )

    def validate_scheme(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a government scheme"""
        errors = []
        warnings = []
        status = ValidationStatus.VALID

        try:
            scheme = GovernmentScheme(**data)
            completeness = scheme.completeness_score()

            # Quality checks
            if completeness < 50:
                errors.append(f"Data completeness too low: {completeness:.1f}%")
                status = ValidationStatus.INVALID
            elif completeness < 70:
                warnings.append(f"Data completeness is low: {completeness:.1f}%")
                status = ValidationStatus.WARNING

            # Check for all "Not Available"
            all_na = all(
                str(v).strip().lower() in ["not available", "n/a", "na", ""]
                for k, v in data.items()
                if k not in ["scheme_name", "scheme_link", "slug", "tags", "source"]
            )

            if all_na:
                errors.append("All fields are 'Not Available'")
                status = ValidationStatus.INVALID

            return ValidationResult(
                status=status,
                data_type=DataType.SCHEME,
                original_data=data,
                errors=errors,
                warnings=warnings,
                completeness_score=completeness,
            )

        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            status = ValidationStatus.INVALID

            return ValidationResult(
                status=status,
                data_type=DataType.SCHEME,
                original_data=data,
                errors=errors,
                warnings=warnings,
            )

    def validate_batch(
        self, data: List[Dict[str, Any]], data_type: DataType
    ) -> List[ValidationResult]:
        """Validate a batch of documents"""
        results = []

        for item in data:
            if data_type == DataType.CONSTITUTION:
                result = self.validate_constitution_article(item)
            elif data_type == DataType.LEGISLATION:
                result = self.validate_legislation_section(item)
            elif data_type == DataType.SCHEME:
                result = self.validate_scheme(item)
            else:
                continue

            results.append(result)
            self.results.append(result)

            # Update stats
            self.stats["total"] += 1
            self.stats[result.status.value] += 1

        return results

    def get_valid_data(self) -> List[Dict[str, Any]]:
        """Get only valid documents"""
        return [
            r.original_data for r in self.results if r.status == ValidationStatus.VALID
        ]

    def get_invalid_data(self) -> List[Dict[str, Any]]:
        """Get invalid documents for review"""
        return [
            {"data": r.original_data, "errors": r.errors, "warnings": r.warnings}
            for r in self.results
            if r.status == ValidationStatus.INVALID
        ]

    def get_needs_review(self) -> List[Dict[str, Any]]:
        """Get documents that need manual review"""
        return [
            {
                "data": r.original_data,
                "warnings": r.warnings,
                "completeness": r.completeness_score,
            }
            for r in self.results
            if r.status == ValidationStatus.WARNING
            and r.completeness_score
            and r.completeness_score < 70
        ]

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.stats,
            "pass_rate": (
                (self.stats["valid"] / self.stats["total"] * 100)
                if self.stats["total"] > 0
                else 0
            ),
            "by_type": {},
        }

        # Group by data type
        for data_type in DataType:
            type_results = [r for r in self.results if r.data_type == data_type]
            if type_results:
                report["by_type"][data_type.value] = {
                    "total": len(type_results),
                    "valid": sum(
                        1 for r in type_results if r.status == ValidationStatus.VALID
                    ),
                    "warning": sum(
                        1 for r in type_results if r.status == ValidationStatus.WARNING
                    ),
                    "invalid": sum(
                        1 for r in type_results if r.status == ValidationStatus.INVALID
                    ),
                }

        return report

    def save_report(self, filename: str = None):
        """Save validation report to file"""
        if not filename:
            filename = (
                f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        report = self.generate_report()
        report_path = os.path.join(self.output_dir, filename)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Validation report saved: {report_path}")
        return report_path

    def save_review_queue(self):
        """Save documents that need manual review"""
        needs_review = self.get_needs_review()
        invalid = self.get_invalid_data()

        if needs_review:
            review_path = os.path.join(
                self.output_dir,
                f"needs_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(needs_review, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Review queue saved: {review_path} ({len(needs_review)} items)"
            )

        if invalid:
            invalid_path = os.path.join(
                self.output_dir,
                f"invalid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            with open(invalid_path, "w", encoding="utf-8") as f:
                json.dump(invalid, f, indent=2, ensure_ascii=False)
            logger.info(f"Invalid data saved: {invalid_path} ({len(invalid)} items)")


#
# CONVENIENCE FUNCTIONS
#


def validate_json_file(file_path: str, data_type: DataType) -> DataValidator:
    """Validate a JSON file"""
    logger.info(f"Validating {file_path} as {data_type.value}...")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    validator = DataValidator()
    validator.validate_batch(data, data_type)

    report = validator.generate_report()
    logger.info(f"Validation complete:")
    logger.info(f"  Total: {report['summary']['total']}")
    logger.info(f"  Valid: {report['summary']['valid']}")
    logger.info(f"  Warning: {report['summary']['warning']}")
    logger.info(f"  Invalid: {report['summary']['invalid']}")
    logger.info(f"  Pass rate: {report['pass_rate']:.1f}%")

    validator.save_report()
    validator.save_review_queue()

    return validator


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python data_validator.py <file_path> <data_type>")
        print("Data types: constitution, legislation, scheme")
        sys.exit(1)

    file_path = sys.argv[1]
    data_type_str = sys.argv[2].lower()

    data_type_map = {
        "constitution": DataType.CONSTITUTION,
        "legislation": DataType.LEGISLATION,
        "scheme": DataType.SCHEME,
    }

    if data_type_str not in data_type_map:
        print(f"Invalid data type: {data_type_str}")
        sys.exit(1)

    validate_json_file(file_path, data_type_map[data_type_str])
