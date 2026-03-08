"""
AWS Bedrock LLM Setup for VIDHI
Replaces Google Gemini with AWS Bedrock (Claude)
"""
from langchain_aws import ChatBedrock

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.vectorstores import VectorStoreRetriever
import logging

# Import processing utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.documents import format_documents


def _initialize_bedrock_llm(model_id: str, region: str = "ap-south-1"):
    """
    Initializes the AWS Bedrock LLM instance.

    Args:
        model_id: The Bedrock model ID (e.g., Claude 3 Haiku)
        region: AWS region

    Returns:
        A tuple containing:
        - The initialized BedrockChat instance if successful, otherwise None.
        - An error message as a string if initialization fails, otherwise None.
    """
    try:
        from langchain_aws import ChatBedrock
        
        llm = ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.9
            }
        )
        return llm, None
    except Exception as e:
        return None, str(e)


class BedrockLLMService:
    """
    Service for managing AWS Bedrock LLM interactions and conversational RAG chain.
    Replaces UdhaviBot's Google Gemini implementation.

    Args:
        logger: Logger instance for logging.
        retriever: A VectorStoreRetriever instance for retrieving documents.
        model_id: Bedrock model ID (default: Claude 3 Haiku)
        region: AWS region (default: ap-south-1 for Mumbai)
    """

    def __init__(
        self,
        logger: logging.Logger,
        retriever: Optional[VectorStoreRetriever] = None,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "ap-south-1"
    ):
        self._conversational_rag_chain = None
        self.error = None
        self._logger = logger
        self._retriever = retriever
        self.model_id = model_id
        self.region = region

        # Initialize Bedrock LLM
        self.llm, error = _initialize_bedrock_llm(model_id, region)
        if error:
            self.error = error
            self._logger.error(f"Failed to initialize Bedrock LLM: {error}")
            return

        # Initialize conversational RAG chain
        error = self._initialize_conversational_rag_chain()
        if error:
            self.error = error
            self._logger.error(f"Failed to initialize RAG chain: {error}")
            return

        self._logger.info(f"Successfully initialized Bedrock LLM with model: {model_id}")

    def _initialize_conversational_rag_chain(self) -> Optional[str]:
        """
        Initializes the conversational RAG chain for VIDHI.

        Returns:
            An error message as a string if initialization fails, otherwise None.
        """
        try:
            # VIDHI-specific system prompt
            qa_system_prompt = """You are VIDHI (Voice-Integrated Defense for Holistic Inclusion), an AI-powered legal assistant designed to empower Indian citizens by providing accessible legal guidance, government scheme information, and document analysis.

Your responsibilities:
1. Provide accurate information about Indian constitutional rights and legal procedures
2. Explain government schemes with eligibility criteria, benefits, and application processes
3. Analyze legal documents and identify potential risks
4. Offer emergency legal guidance during critical situations
5. Communicate in simple, understandable language appropriate for users with varying literacy levels

Guidelines:
- Always cite specific articles, sections, or laws when providing legal information
- Include actionable step-by-step guidance
- Link to authoritative sources (India.gov.in, Supreme Court judgments, etc.)
- Provide clear disclaimers that this is not official legal advice
- Be compassionate and supportive, especially for underserved communities
- Respond in the user's preferred language

Context from knowledge base:
{context}

User Question: {question}

Provide a clear, accurate, and actionable response:"""

            prompt = ChatPromptTemplate.from_template(qa_system_prompt)

            if self._retriever:
                # Initialize conversational RAG chain
                self._conversational_rag_chain = (
                    {
                        "context": self._retriever | format_documents,
                        "question": RunnablePassthrough()
                    }
                    | prompt
                    | self.llm
                    | StrOutputParser()
                )
            else:
                # Initialize standard chain without RAG
                self._conversational_rag_chain = (
                    {
                        "context": lambda x: "No external knowledge base available.",
                        "question": RunnablePassthrough()
                    }
                    | prompt
                    | self.llm
                    | StrOutputParser()
                )

            return None
        except Exception as e:
            return str(e)

    def conversational_rag_chain(self):
        """
        Returns the initialized conversational RAG chain.

        Returns:
            The conversational RAG chain instance.
        """
        return self._conversational_rag_chain

    def get_llm(self):
        """
        Returns the Bedrock LLM instance.

        Returns:
            The BedrockChat instance.
        """
        return self.llm

    def query(self, question: str, language: str = "English") -> str:
        """
        Query the RAG system with a question.

        Args:
            question: User's question
            language: Preferred response language

        Returns:
            AI-generated response
        """
        try:
            if language != "English":
                question_with_language = f"{question}\n\nPlease respond in {language}."
            else:
                question_with_language = question

            response = self._conversational_rag_chain.invoke(question_with_language)
            return response
        except Exception as e:
            self._logger.error(f"Error querying RAG system: {e}")
            return f"I apologize, but I encountered an error processing your question. Please try again."

    def query_with_context(self, question: str, context: str, language: str = "English") -> str:
        """
        Query the LLM directly with provided context (bypass retrieval).

        Args:
            question: User's question
            context: Pre-retrieved context
            language: Preferred response language

        Returns:
            AI-generated response
        """
        try:
            prompt = f"""Context: {context}

Question: {question}

Please respond in {language} with accurate, actionable information."""

            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            self._logger.error(f"Error querying with context: {e}")
            return f"I apologize, but I encountered an error processing your question."


class EmergencyLLMService:
    """
    Specialized LLM service for emergency situations.
    Uses faster model and prioritized prompts.
    """

    def __init__(self, logger: logging.Logger, region: str = "ap-south-1"):
        self._logger = logger
        self.error = None
        self.llm, error = _initialize_bedrock_llm(
            "anthropic.claude-3-haiku-20240307-v1:0",  # Fastest model
            region
        )
        if error:
            self.error = error
            self._logger.error(f"Failed to initialize Emergency LLM: {error}")

    def get_emergency_rights(self, situation: str, language: str = "English") -> str:
        """
        Get immediate emergency rights information.

        Args:
            situation: Description of emergency situation
            language: Preferred response language

        Returns:
            Emergency rights and procedures
        """
        try:
            prompt = f"""EMERGENCY SITUATION: {situation}

Provide IMMEDIATE, CRITICAL legal rights information for this emergency situation in India.

Include:
1. Constitutional rights that apply
2. D.K. Basu guidelines (if arrest-related)
3. Immediate actions to take
4. Emergency contact numbers
5. Rights during police detention

Respond in {language}.
Be CONCISE and ACTIONABLE. This is an emergency."""

            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            self._logger.error(f"Error getting emergency rights: {e}")
            return """EMERGENCY RIGHTS:
1. Right to remain silent (Article 20)
2. Right to legal counsel (Article 22)
3. Right to inform family/friend
4. No torture or coercion allowed
5. Medical examination within 48 hours

Call: National Legal Aid - 15100"""
