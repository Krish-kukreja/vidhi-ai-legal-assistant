"""
AWS Bedrock LLM Setup for VIDHI
Upgraded with:
  - Conversational memory (per-session ConversationBufferWindowMemory)
  - Question reformulation (standalone question from history)
  - CRAG (Corrective RAG) — relevance grading before generation
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.documents import Document
from langchain.memory import ConversationBufferWindowMemory

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.documents import format_documents
from llm_setup.crag import RelevanceGrader, Grade, IRRELEVANT_FALLBACK, PARTIAL_PREFIX

# Import agent components (optional - only if agent is enabled)
try:
    from llm_setup.agent_tools import create_agent_tools
    from llm_setup.agent import create_vidhi_agent
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False


#  LLM factory 

def _initialize_bedrock_llm(model_id: str, region: str = "ap-south-1"):
    try:
        llm = ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={
                "temperature": 0.3,   # lower = less hallucination
                "max_tokens": 2048,
                "top_p": 0.9
            }
        )
        return llm, None
    except Exception as e:
        return None, str(e)


def get_llm(
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    region: str = "ap-south-1",
):
    """
    Module-level helper that returns a ready-to-use ChatBedrock LLM handle.

    Used by lightweight services (e.g. services/document_education.py) that just
    need a plain `.invoke()`-able LLM rather than the full RAG pipeline. Returns
    None (instead of raising) when Bedrock can't be initialized, so importing/
    instantiating those services never crashes app startup — the LLM-backed
    methods simply degrade while non-LLM paths (e.g. the static glossary) keep working.
    """
    llm, err = _initialize_bedrock_llm(model_id, region)
    if err:
        logging.getLogger(__name__).warning(f"get_llm: Bedrock unavailable: {err}")
        return None
    return llm


#  Prompts 

# Step 1: Condense the question using chat history
CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template("""\
Given the following conversation history and a follow-up question, \
rewrite the follow-up question as a fully self-contained standalone question \
that captures all necessary context from the history.
If the follow-up question is already standalone, return it unchanged.

Chat History:
{chat_history}

Follow-Up Question: {question}

Standalone Question:""")

# Step 2: RAG answer generation
QA_PROMPT = ChatPromptTemplate.from_template("""\
You are VIDHI (Voice-Integrated Defense for Holistic Inclusion), an AI-powered legal assistant \
designed to empower Indian citizens with accessible legal guidance, government scheme information, \
and rights awareness.

Guidelines:
- Format responses using Markdown (headers, bullet points, **bold**)
- Always cite specific articles, sections, or act names
- Include actionable step-by-step guidance
- Be compassionate toward underserved communities
- NEVER fabricate laws, cases, or sections — if unsure, say so
- Add a disclaimer that this is not official legal advice
- Respond in the user's preferred language if specified

Context from knowledge base:
{context}

Question: {question}

Provide a clear, accurate, and actionable response:""")


#  BedrockLLMService 

class BedrockLLMService:
    """
    Service for VIDHI's conversational RAG with CRAG hallucination prevention.

    Features:
      - Per-session ConversationBufferWindowMemory (last 5 turns)
      - Question reformulation to handle follow-up questions correctly
      - CRAG relevance grading before generation
      - Fallback to NALSA referral when context is irrelevant
    """

    def __init__(
        self,
        logger: logging.Logger,
        retriever: Optional[VectorStoreRetriever] = None,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "ap-south-1",
        memory_window: int = 5,           # keep last 5 Q&A pairs in context
        enable_crag: bool = True,         # set False to disable grading (faster)
        enable_agent: bool = False,       # set True to enable agentic workflows
        agent_max_iterations: int = 5,    # max reasoning iterations for agent
    ):
        self._logger = logger
        self._retriever = retriever
        self.model_id = model_id
        self.region = region
        self.enable_crag = enable_crag
        self.enable_agent = enable_agent
        self.error: Optional[str] = None

        # Session memory store: {session_id: ConversationBufferWindowMemory}
        self._memories: dict[str, ConversationBufferWindowMemory] = {}
        self._memory_window = memory_window

        # Initialize LLM
        self.llm, err = _initialize_bedrock_llm(model_id, region)
        if err:
            self.error = err
            self._logger.error(f"Failed to initialize Bedrock LLM: {err}")
            return

        # Initialize CRAG grader
        self._grader = RelevanceGrader(self.llm) if enable_crag else None

        # Initialize agent (optional)
        self._agent = None
        if enable_agent and AGENT_AVAILABLE and retriever:
            try:
                tools = create_agent_tools(retriever, logger)
                self._agent = create_vidhi_agent(
                    llm=self.llm,
                    retriever=retriever,
                    tools=tools,
                    logger=logger,
                    max_iterations=agent_max_iterations
                )
                self._logger.info(f"Agent initialized with max_iterations={agent_max_iterations}")
            except Exception as e:
                self._logger.error(f"Failed to initialize agent: {e}")
                self.enable_agent = False

        # Build chains
        self._condense_chain = CONDENSE_QUESTION_PROMPT | self.llm | StrOutputParser()
        self._qa_chain = QA_PROMPT | self.llm | StrOutputParser()

        self._logger.info(f"BedrockLLMService initialized — model={model_id}, CRAG={'ON' if enable_crag else 'OFF'}, Agent={'ON' if enable_agent else 'OFF'}")

    #  Memory helpers 

    def _get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create session memory."""
        if session_id not in self._memories:
            self._memories[session_id] = ConversationBufferWindowMemory(
                k=self._memory_window,
                memory_key="chat_history",
                return_messages=False,   # plain text format
                human_prefix="User",
                ai_prefix="VIDHI"
            )
        return self._memories[session_id]

    def _get_history_str(self, session_id: str) -> str:
        """Get formatted chat history string for a session."""
        mem = self._get_memory(session_id)
        history = mem.load_memory_variables({}).get("chat_history", "")
        return history or "No prior conversation."

    def _save_to_memory(self, session_id: str, question: str, answer: str):
        """Save a Q&A pair to session memory."""
        mem = self._get_memory(session_id)
        mem.save_context({"input": question}, {"output": answer})

    def clear_session(self, session_id: str):
        """Clear memory for a given session (e.g., 'new conversation' button)."""
        if session_id in self._memories:
            del self._memories[session_id]
            self._logger.info(f"Cleared memory for session: {session_id}")

    #  Core query flow 

    def query(
        self,
        question: str,
        session_id: str = "default",
        language: str = "English",
        use_agent: bool = None  # Override enable_agent setting
    ) -> str:
        """
        Full CRAG + conversational RAG query with optional agentic workflows.

        Steps:
          1. Load session history
          2. Reformulate question (handles follow-ups like "what about this?")
          3. Route to agent OR standard RAG based on configuration
          4. Save to memory

        Args:
            question:   Raw user question
            session_id: Session identifier for memory isolation
            language:   Response language preference
            use_agent:  Override enable_agent setting (None = use default)

        Returns:
            AI-generated answer string
        """
        try:
            #  Step 1: Get history 
            history = self._get_history_str(session_id)

            #  Step 2: Reformulate question 
            if history and history != "No prior conversation.":
                standalone_q = self._condense_chain.invoke({
                    "chat_history": history,
                    "question": question
                })
                self._logger.debug(f"Reformulated: '{question}' → '{standalone_q}'")
            else:
                standalone_q = question

            # Apply language preference
            if language and language.lower() not in ("english", "en"):
                standalone_q_with_lang = f"{standalone_q}\n\nPlease respond in {language}."
            else:
                standalone_q_with_lang = standalone_q

            #  Step 3: Route to agent or standard RAG 
            should_use_agent = use_agent if use_agent is not None else self.enable_agent
            
            if should_use_agent and self._agent:
                # Use agentic workflow
                self._logger.info(f"Routing to agent for session {session_id}")
                agent_response = self._agent.query(standalone_q_with_lang, language)
                
                # Format agent response
                answer = agent_response["answer"]
                
                # Add confidence and citations if available
                if agent_response.get("confidence", 0) > 0:
                    confidence_text = f"\n\n**Confidence**: {agent_response['confidence']:.0%}"
                    answer += confidence_text
                
                if agent_response.get("citations"):
                    citations_text = "\n\n**Citations**: " + ", ".join(agent_response["citations"][:5])
                    answer += citations_text
                
                # Save to memory
                self._save_to_memory(session_id, question, answer)
                return answer
            
            # Standard RAG flow (existing code)
            if not self._retriever:
                # No retriever — plain LLM fallback
                answer = self._qa_chain.invoke({
                    "context": "No knowledge base available.",
                    "question": standalone_q_with_lang
                })
                self._save_to_memory(session_id, question, answer)
                return answer

            docs: list[Document] = self._retriever.invoke(standalone_q)

            #  Step 4: CRAG grading 
            if self.enable_crag and self._grader:
                grade_result = self._grader.grade(standalone_q, docs)

                if grade_result.grade == Grade.IRRELEVANT:
                    self._logger.info(f"CRAG: IRRELEVANT — returning fallback for session {session_id}")
                    self._save_to_memory(session_id, question, IRRELEVANT_FALLBACK)
                    return IRRELEVANT_FALLBACK

                prefix = PARTIAL_PREFIX if grade_result.grade == Grade.PARTIAL else ""
            else:
                prefix = ""

            #  Step 5: Generate 
            context = format_documents(docs)
            answer = self._qa_chain.invoke({
                "context": context,
                "question": standalone_q_with_lang
            })

            final_answer = prefix + answer

            #  Step 6: Save to memory 
            self._save_to_memory(session_id, question, final_answer)

            return final_answer

        except Exception as e:
            import traceback
            with open("llm_error.log", "w") as f:
                f.write(traceback.format_exc())
            self._logger.exception(f"Error in CRAG query: {e}")
            return "I apologize, but I encountered an error. Please try again."

    def query_with_context(
        self,
        question: str,
        context: str,
        language: str = "English"
    ) -> str:
        """Bypass retrieval — use pre-supplied context directly (for doc analysis)."""
        try:
            answer = self._qa_chain.invoke({
                "context": context,
                "question": f"{question}\n\nPlease respond in {language}." if language != "English" else question
            })
            return answer
        except Exception as e:
            self._logger.error(f"Error in query_with_context: {e}")
            return "I apologize, but I encountered an error."

    #  Streaming query flow (Phase 2) 

    async def query_stream(
        self,
        question: str,
        session_id: str = "default",
        language: str = "English",
        use_agent: bool = None
    ):
        """
        Stream LLM response token-by-token using async generator.
        
        This is the streaming version of query() method.
        Yields events as they occur instead of returning complete response.
        
        Args:
            question: Raw user question
            session_id: Session identifier for memory isolation
            language: Response language preference
            use_agent: Override enable_agent setting (None = use default)
        
        Yields:
            Dict with type (token/metadata/done/error) and content
        """
        try:
            import time
            start_time = time.time()
            
            #  Step 1: Get history 
            history = self._get_history_str(session_id)

            #  Step 2: Reformulate question 
            if history and history != "No prior conversation.":
                standalone_q = self._condense_chain.invoke({
                    "chat_history": history,
                    "question": question
                })
                self._logger.debug(f"Reformulated: '{question}' → '{standalone_q}'")
            else:
                standalone_q = question

            # Apply language preference
            if language and language.lower() not in ("english", "en"):
                standalone_q_with_lang = f"{standalone_q}\n\nPlease respond in {language}."
            else:
                standalone_q_with_lang = standalone_q

            #  Step 3: Route to agent or standard RAG 
            should_use_agent = use_agent if use_agent is not None else self.enable_agent
            
            if should_use_agent and self._agent:
                # Agent doesn't support streaming yet - fall back to regular query
                self._logger.info(f"Agent doesn't support streaming, using regular query")
                answer = self.query(question, session_id, language, use_agent)
                
                # Simulate streaming by yielding words
                words = answer.split()
                for i, word in enumerate(words):
                    yield {
                        "type": "token",
                        "content": word + " ",
                        "index": i
                    }
                
                yield {
                    "type": "done",
                    "total_tokens": len(words),
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
                return
            
            # Standard RAG flow with streaming
            if not self._retriever:
                # No retriever — plain LLM fallback with streaming
                prompt = self._qa_chain.first.invoke({
                    "context": "No knowledge base available.",
                    "question": standalone_q_with_lang
                })
                
                token_count = 0
                full_answer = ""
                
                async for chunk in self.llm.astream(prompt):
                    if chunk.content:
                        yield {
                            "type": "token",
                            "content": chunk.content,
                            "index": token_count
                        }
                        full_answer += chunk.content
                        token_count += 1
                
                # Save to memory
                self._save_to_memory(session_id, question, full_answer)
                
                yield {
                    "type": "done",
                    "total_tokens": token_count,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
                return

            # Retrieve documents
            docs = self._retriever.invoke(standalone_q)

            #  Step 4: CRAG grading 
            if self.enable_crag and self._grader:
                grade_result = self._grader.grade(standalone_q, docs)

                if grade_result.grade == Grade.IRRELEVANT:
                    self._logger.info(f"CRAG: IRRELEVANT — returning fallback for session {session_id}")
                    
                    # Stream fallback message
                    words = IRRELEVANT_FALLBACK.split()
                    for i, word in enumerate(words):
                        yield {
                            "type": "token",
                            "content": word + " ",
                            "index": i
                        }
                    
                    self._save_to_memory(session_id, question, IRRELEVANT_FALLBACK)
                    
                    yield {
                        "type": "done",
                        "total_tokens": len(words),
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                    return

                prefix = PARTIAL_PREFIX if grade_result.grade == Grade.PARTIAL else ""
            else:
                prefix = ""

            #  Step 5: Generate with streaming 
            context = format_documents(docs)
            
            # Build prompt
            prompt = self._qa_chain.first.invoke({
                "context": context,
                "question": standalone_q_with_lang
            })
            
            # Stream from LLM
            token_count = 0
            full_answer = ""
            
            # Send prefix if any
            if prefix:
                yield {
                    "type": "token",
                    "content": prefix,
                    "index": token_count
                }
                full_answer += prefix
                token_count += 1
            
            # Stream tokens
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    yield {
                        "type": "token",
                        "content": chunk.content,
                        "index": token_count
                    }
                    full_answer += chunk.content
                    token_count += 1
            
            # Send metadata
            confidence = self._calculate_confidence(docs) if docs else 0.5
            citations = self._extract_citations(docs) if docs else []
            
            yield {
                "type": "metadata",
                "confidence": confidence,
                "citations": citations[:5]
            }
            
            #  Step 6: Save to memory 
            final_answer = prefix + full_answer
            self._save_to_memory(session_id, question, final_answer)
            
            # Send done
            yield {
                "type": "done",
                "total_tokens": token_count,
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            self._logger.exception(f"Error in streaming query: {e}")
            yield {
                "type": "error",
                "message": "I apologize, but I encountered an error. Please try again."
            }

    def _calculate_confidence(self, docs: list) -> float:
        """Calculate confidence score based on retrieved documents."""
        if not docs:
            return 0.3
        
        # Use confidence from reranker if available
        confidences = [doc.metadata.get("confidence", 0.7) for doc in docs[:3]]
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _extract_citations(self, docs: list) -> list:
        """Extract citations from retrieved documents."""
        citations = []
        for doc in docs[:5]:
            source = doc.metadata.get("source", "")
            if source and source not in citations:
                citations.append(source)
        return citations

    #  Backward-compat property 

    @property
    def conversational_rag_chain(self):
        """Legacy property — returns self so existing callers don't break."""
        return self

    def invoke(self, question: str) -> str:
        """Legacy invoke() shim for callers using the old chain directly."""
        return self.query(question, session_id="legacy")

    def get_llm(self):
        return self.llm


#  EmergencyLLMService (unchanged) 

class EmergencyLLMService:
    """Specialized LLM service for emergency situations. Uses fastest model."""

    def __init__(self, logger: logging.Logger, region: str = "ap-south-1"):
        self._logger = logger
        self.error = None
        self.llm, error = _initialize_bedrock_llm(
            "anthropic.claude-3-haiku-20240307-v1:0", region
        )
        if error:
            self.error = error
            self._logger.error(f"Failed to initialize Emergency LLM: {error}")

    def get_emergency_rights(self, situation: str, language: str = "English") -> str:
        try:
            prompt = f"""EMERGENCY SITUATION: {situation}

Provide IMMEDIATE, CRITICAL legal rights information for this emergency in India.

Include:
1. Constitutional rights that apply
2. D.K. Basu guidelines (if arrest-related)
3. Immediate actions to take
4. Emergency contact numbers
5. Rights during police detention

Respond in {language}. Be CONCISE and ACTIONABLE. This is an emergency."""

            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            self._logger.error(f"Error in emergency LLM: {e}")
            return """\
EMERGENCY RIGHTS:
1. Right to remain silent (Article 20)
2. Right to legal counsel (Article 22)
3. Right to inform family/friend of arrest
4. No torture or coercion allowed
5. Medical examination within 48 hours

 National Legal Aid: **15100** (toll-free)
 Police: **100**
 Women Helpline: **1091**"""
