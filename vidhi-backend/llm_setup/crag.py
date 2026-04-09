"""
CRAG — Corrective RAG for VIDHI
Grades retrieved documents for relevance BEFORE generating a response.
Prevents hallucination by refusing to generate when context is irrelevant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from langchain_aws import ChatBedrock

logger = logging.getLogger(__name__)


class Grade(str, Enum):
    RELEVANT = "RELEVANT"
    PARTIAL = "PARTIAL"
    IRRELEVANT = "IRRELEVANT"


@dataclass
class GradeResult:
    grade: Grade
    relevant_count: int
    total_docs: int
    reasoning: str


IRRELEVANT_FALLBACK = """\
I don't have reliable information about this specific topic in my legal knowledge base.

**For accurate legal advice, please contact:**
-  **NALSA (Free Legal Aid)** — Helpline: **15100** (toll-free)
-  **District Legal Services Authority** — Free lawyers available at every district court
-  **NHRC (Human Rights)** — **14433**
-  **Women Helpline** — **1091**
-  **Child Helpline** — **1098**

*VIDHI is an AI assistant and does not replace professional legal counsel.*
"""

PARTIAL_PREFIX = (
    " *My knowledge on this topic may be limited. "
    "Please verify with a legal professional.*\n\n"
)


class RelevanceGrader:
    """
    Grades a list of retrieved documents against a user question.
    Uses a fast yes/no LLM prompt to determine relevance.
    """

    GRADE_PROMPT = (
        "You are a legal document relevance assessor.\n\n"
        "Question: {question}\n\n"
        "Document excerpt:\n{document}\n\n"
        "Does this document contain information that would help answer the question above? "
        "Reply with a single word: YES or NO."
    )

    def __init__(self, llm: "ChatBedrock"):
        self._llm = llm

    def _grade_single(self, question: str, doc: Document) -> bool:
        """Returns True if the document is relevant to the question."""
        try:
            prompt = self.GRADE_PROMPT.format(
                question=question,
                document=doc.page_content[:800]  # trim to save tokens
            )
            response = self._llm.invoke(prompt)
            answer = (
                response.content if hasattr(response, "content") else str(response)
            ).strip().upper()
            return answer.startswith("YES")
        except Exception as e:
            logger.warning(f"Grading failed for doc: {e}")
            # On error, assume relevant to avoid false negatives
            return True

    def grade(self, question: str, documents: list[Document]) -> GradeResult:
        """
        Grade all retrieved documents.

        Args:
            question: The user's (reformulated) question
            documents: Documents retrieved from ChromaDB

        Returns:
            GradeResult with grade, counts, and reasoning
        """
        if not documents:
            return GradeResult(
                grade=Grade.IRRELEVANT,
                relevant_count=0,
                total_docs=0,
                reasoning="No documents retrieved from knowledge base."
            )

        relevant_count = sum(
            1 for doc in documents
            if self._grade_single(question, doc)
        )
        total = len(documents)

        if relevant_count >= 2:
            grade = Grade.RELEVANT
            reasoning = f"{relevant_count}/{total} documents relevant."
        elif relevant_count == 1:
            grade = Grade.PARTIAL
            reasoning = f"Only 1/{total} documents relevant — limited context."
        else:
            grade = Grade.IRRELEVANT
            reasoning = f"0/{total} documents relevant — refusing to generate."

        logger.info(f"CRAG grade: {grade.value} ({reasoning})")
        return GradeResult(
            grade=grade,
            relevant_count=relevant_count,
            total_docs=total,
            reasoning=reasoning
        )
