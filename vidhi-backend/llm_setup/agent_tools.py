"""
LangGraph Agent Tools for VIDHI
Specialized tools for legal query processing and multi-hop reasoning.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever


class AgentTools:
    """Collection of specialized tools for the VIDHI legal agent."""

    def __init__(
        self,
        retriever: VectorStoreRetriever,
        logger: logging.Logger
    ):
        self.retriever = retriever
        self.logger = logger

    def search_legal_database(
        self,
        query: str,
        doc_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search legal database with hybrid search + reranking.
        
        Args:
            query: Legal query (e.g., "Section 438 CrPC")
            doc_type: Filter by type (constitution, legislation, scheme)
            top_k: Number of results to return
        
        Returns:
            List of relevant documents with confidence scores
        """
        try:
            self.logger.info(f"Tool: search_legal_database(query='{query}', doc_type={doc_type})")
            
            # Retrieve documents
            docs = self.retriever.invoke(query)
            
            # Filter by doc_type if specified
            if doc_type:
                docs = [
                    doc for doc in docs
                    if doc.metadata.get("source_type", "").lower() == doc_type.lower()
                ]
            
            # Limit to top_k
            docs = docs[:top_k]
            
            # Format results
            results = []
            for i, doc in enumerate(docs):
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "rank": i + 1,
                    "confidence": doc.metadata.get("confidence", 1.0)
                })
            
            self.logger.info(f"Tool: search_legal_database returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in search_legal_database: {e}")
            return []

    def get_exact_section(
        self,
        section_number: str,
        act_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve exact section text from legislation.
        
        Args:
            section_number: Section number (e.g., "438")
            act_name: Act name (e.g., "CrPC", "IPC")
        
        Returns:
            Exact section text with metadata, or None if not found
        """
        try:
            self.logger.info(f"Tool: get_exact_section(section={section_number}, act={act_name})")
            
            # Normalize act name
            act_name_normalized = act_name.upper().strip()
            
            # Build precise query
            query = f"Section {section_number} {act_name_normalized}"
            
            # Search with high precision
            docs = self.retriever.invoke(query)
            
            # Find exact match
            for doc in docs:
                content = doc.page_content.lower()
                metadata = doc.metadata
                
                # Check if this is the exact section
                section_pattern = rf"section\s+{re.escape(section_number)}\b"
                if re.search(section_pattern, content, re.IGNORECASE):
                    # Check if act name matches
                    if act_name_normalized.lower() in content or \
                       act_name_normalized.lower() in str(metadata).lower():
                        self.logger.info(f"Tool: get_exact_section found match")
                        return {
                            "content": doc.page_content,
                            "metadata": metadata,
                            "section_number": section_number,
                            "act_name": act_name
                        }
            
            self.logger.warning(f"Tool: get_exact_section found no match")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in get_exact_section: {e}")
            return None

    def find_amendments(
        self,
        section_number: str,
        act_name: str
    ) -> List[Dict[str, Any]]:
        """
        Find all amendments to a specific section.
        
        Args:
            section_number: Section number
            act_name: Act name
        
        Returns:
            List of amendments sorted by date (newest first)
        """
        try:
            self.logger.info(f"Tool: find_amendments(section={section_number}, act={act_name})")
            
            # Build amendment query
            query = f"amendment Section {section_number} {act_name}"
            
            # Search for amendments
            docs = self.retriever.invoke(query)
            
            # Filter for amendment-related content
            amendments = []
            for doc in docs:
                content = doc.page_content.lower()
                
                # Check if this mentions amendments
                if any(keyword in content for keyword in ["amend", "modified", "substituted", "inserted"]):
                    amendments.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "section_number": section_number,
                        "act_name": act_name
                    })
            
            # Sort by date if available (newest first)
            amendments.sort(
                key=lambda x: x["metadata"].get("date", "1900-01-01"),
                reverse=True
            )
            
            self.logger.info(f"Tool: find_amendments found {len(amendments)} amendments")
            return amendments
            
        except Exception as e:
            self.logger.error(f"Error in find_amendments: {e}")
            return []

    def calculate_limitation_period(
        self,
        offense_type: str,
        offense_date: str
    ) -> Dict[str, Any]:
        """
        Calculate limitation period for legal actions.
        
        Args:
            offense_type: Type of offense
            offense_date: Date of offense (YYYY-MM-DD)
        
        Returns:
            Limitation period details with expiry date
        """
        try:
            self.logger.info(f"Tool: calculate_limitation_period(type={offense_type}, date={offense_date})")
            
            # Parse offense date
            try:
                offense_dt = datetime.strptime(offense_date, "%Y-%m-%d")
            except ValueError:
                return {
                    "error": "Invalid date format. Use YYYY-MM-DD",
                    "offense_type": offense_type,
                    "offense_date": offense_date
                }
            
            # Search for limitation period information
            query = f"limitation period {offense_type}"
            docs = self.retriever.invoke(query)
            
            # Default limitation periods (can be overridden by retrieved docs)
            limitation_days = {
                "cognizable": 0,  # No limitation for cognizable offenses
                "non-cognizable": 180,  # 6 months
                "civil": 1095,  # 3 years (general)
                "contract": 1095,  # 3 years
                "tort": 1095,  # 3 years
                "property": 4380,  # 12 years
                "default": 1095  # 3 years
            }
            
            # Determine limitation period
            offense_lower = offense_type.lower()
            days = limitation_days.get("default", 1095)
            
            for key, value in limitation_days.items():
                if key in offense_lower:
                    days = value
                    break
            
            # Calculate expiry date
            if days == 0:
                expiry_date = None
                status = "No limitation period"
            else:
                expiry_dt = offense_dt + timedelta(days=days)
                expiry_date = expiry_dt.strftime("%Y-%m-%d")
                
                # Check if expired
                today = datetime.now()
                if today > expiry_dt:
                    status = "Expired"
                else:
                    days_remaining = (expiry_dt - today).days
                    status = f"Active ({days_remaining} days remaining)"
            
            result = {
                "offense_type": offense_type,
                "offense_date": offense_date,
                "limitation_period_days": days if days > 0 else "No limitation",
                "expiry_date": expiry_date,
                "status": status,
                "relevant_law": "Limitation Act, 1963" if days > 0 else "CrPC (cognizable offenses)"
            }
            
            # Add context from retrieved docs
            if docs:
                result["additional_context"] = docs[0].page_content[:500]
            
            self.logger.info(f"Tool: calculate_limitation_period result: {status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in calculate_limitation_period: {e}")
            return {
                "error": str(e),
                "offense_type": offense_type,
                "offense_date": offense_date
            }

    def explain_legal_term(
        self,
        term: str,
        language: str = "english"
    ) -> str:
        """
        Explain legal term in simple language.
        
        Args:
            term: Legal term (e.g., "anticipatory bail")
            language: Response language
        
        Returns:
            Simple explanation of the term
        """
        try:
            self.logger.info(f"Tool: explain_legal_term(term='{term}', language={language})")
            
            # Search for term definition
            query = f"what is {term} definition meaning"
            docs = self.retriever.invoke(query)
            
            if not docs:
                return f"No information found for the term '{term}'."
            
            # Extract relevant explanation
            explanation = docs[0].page_content
            
            # Add source information
            source = docs[0].metadata.get("source", "Legal database")
            
            result = f"**{term.title()}**\n\n{explanation}\n\n*Source: {source}*"
            
            self.logger.info(f"Tool: explain_legal_term returned explanation")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in explain_legal_term: {e}")
            return f"Error explaining term '{term}': {str(e)}"


def create_agent_tools(
    retriever: VectorStoreRetriever,
    logger: logging.Logger
) -> AgentTools:
    """
    Factory function to create AgentTools instance.
    
    Args:
        retriever: Vector store retriever (hybrid or semantic)
        logger: Logger instance
    
    Returns:
        AgentTools instance
    """
    return AgentTools(retriever=retriever, logger=logger)
