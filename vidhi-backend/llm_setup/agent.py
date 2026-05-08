"""
LangGraph Agent for VIDHI
Multi-step reasoning agent with specialized legal tools.
"""

from __future__ import annotations

import logging
from typing import TypedDict, List, Dict, Any, Annotated, Literal
from operator import add

from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_aws import ChatBedrock

from llm_setup.agent_tools import AgentTools


#  Agent State 

class AgentState(TypedDict):
    """State for the VIDHI legal agent."""
    query: str
    expanded_query: List[str]
    retrieved_docs: List[Dict[str, Any]]
    tool_calls: Annotated[List[Dict[str, Any]], add]  # Accumulate tool calls
    reasoning_steps: Annotated[List[str], add]  # Accumulate reasoning
    final_answer: str
    confidence: float
    citations: List[str]
    iteration: int
    max_iterations: int


#  Agent Nodes 

class VidhiAgent:
    """LangGraph agent for multi-step legal reasoning."""

    def __init__(
        self,
        llm: ChatBedrock,
        retriever: VectorStoreRetriever,
        tools: AgentTools,
        logger: logging.Logger,
        max_iterations: int = 5
    ):
        self.llm = llm
        self.retriever = retriever
        self.tools = tools
        self.logger = logger
        self.max_iterations = max_iterations
        
        # Build graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("expand_query", self._expand_query_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("select_tools", self._select_tools_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("calculate_confidence", self._confidence_node)
        
        # Set entry point
        workflow.set_entry_point("expand_query")
        
        # Add edges
        workflow.add_edge("expand_query", "retrieve")
        workflow.add_edge("retrieve", "select_tools")
        
        # Conditional: use tools or skip to generation
        workflow.add_conditional_edges(
            "select_tools",
            self._should_use_tools,
            {
                "use_tools": "execute_tools",
                "skip_tools": "generate"
            }
        )
        
        workflow.add_edge("execute_tools", "reason")
        
        # Conditional: continue reasoning or finish
        workflow.add_conditional_edges(
            "reason",
            self._should_continue_reasoning,
            {
                "continue": "select_tools",
                "finish": "generate"
            }
        )
        
        workflow.add_edge("generate", "calculate_confidence")
        workflow.add_edge("calculate_confidence", END)
        
        return workflow.compile()

    #  Node Implementations 

    def _expand_query_node(self, state: AgentState) -> AgentState:
        """Expand user query with synonyms and related terms."""
        try:
            self.logger.info(f"Agent Node: expand_query")
            
            query = state["query"]
            
            # Use LLM to expand query
            prompt = f"""Given this legal query, generate 2-3 alternative phrasings or related terms that would help find relevant information.

Query: {query}

Return ONLY the alternative queries, one per line, without numbering or explanation."""

            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # Parse expansions
            expansions = [line.strip() for line in content.split("\n") if line.strip()]
            expansions = [query] + expansions[:2]  # Original + top 2 expansions
            
            state["expanded_query"] = expansions
            state["reasoning_steps"] = [f"Expanded query into {len(expansions)} variations"]
            
            self.logger.info(f"Query expanded: {expansions}")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in expand_query_node: {e}")
            state["expanded_query"] = [state["query"]]
            state["reasoning_steps"] = ["Query expansion failed, using original query"]
            return state

    def _retrieve_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents using hybrid search."""
        try:
            self.logger.info(f"Agent Node: retrieve")
            
            # Use original query for retrieval (expansions used for tool selection)
            query = state["query"]
            
            # Retrieve documents
            docs = self.retriever.invoke(query)
            
            # Format documents
            retrieved = []
            for i, doc in enumerate(docs):
                retrieved.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "rank": i + 1,
                    "confidence": doc.metadata.get("confidence", 1.0)
                })
            
            state["retrieved_docs"] = retrieved
            state["reasoning_steps"].append(f"Retrieved {len(retrieved)} relevant documents")
            
            self.logger.info(f"Retrieved {len(retrieved)} documents")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in retrieve_node: {e}")
            state["retrieved_docs"] = []
            state["reasoning_steps"].append("Document retrieval failed")
            return state

    def _select_tools_node(self, state: AgentState) -> AgentState:
        """Decide which tools to use based on query analysis."""
        try:
            self.logger.info(f"Agent Node: select_tools")
            
            query = state["query"]
            
            # Use LLM to analyze query and select tools
            prompt = f"""Analyze this legal query and determine which tools would be helpful.

Query: {query}

Available tools:
1. search_legal_database - Search for general legal information
2. get_exact_section - Get exact text of a specific section (requires section number and act name)
3. find_amendments - Find amendments to a specific section
4. calculate_limitation_period - Calculate limitation period for legal actions
5. explain_legal_term - Explain a legal term in simple language

Respond with ONLY the tool names that should be used, one per line. If no tools are needed, respond with "NONE"."""

            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # Parse tool selections
            if "NONE" in content.upper():
                selected_tools = []
            else:
                selected_tools = [
                    line.strip() for line in content.split("\n")
                    if line.strip() and any(tool in line for tool in [
                        "search_legal_database",
                        "get_exact_section",
                        "find_amendments",
                        "calculate_limitation_period",
                        "explain_legal_term"
                    ])
                ]
            
            # Store tool selections
            if "tool_calls" not in state:
                state["tool_calls"] = []
            
            for tool in selected_tools:
                state["tool_calls"].append({
                    "tool": tool,
                    "status": "pending",
                    "result": None
                })
            
            state["reasoning_steps"].append(f"Selected {len(selected_tools)} tools: {selected_tools}")
            
            self.logger.info(f"Selected tools: {selected_tools}")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in select_tools_node: {e}")
            state["reasoning_steps"].append("Tool selection failed")
            return state

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute selected tools."""
        try:
            self.logger.info(f"Agent Node: execute_tools")
            
            query = state["query"]
            tool_calls = state.get("tool_calls", [])
            
            # Execute pending tools
            for tool_call in tool_calls:
                if tool_call["status"] == "pending":
                    tool_name = tool_call["tool"]
                    
                    # Execute tool
                    if "search_legal_database" in tool_name:
                        result = self.tools.search_legal_database(query, top_k=5)
                    
                    elif "get_exact_section" in tool_name:
                        # Extract section and act from query
                        section, act = self._extract_section_info(query)
                        if section and act:
                            result = self.tools.get_exact_section(section, act)
                        else:
                            result = {"error": "Could not extract section and act from query"}
                    
                    elif "find_amendments" in tool_name:
                        section, act = self._extract_section_info(query)
                        if section and act:
                            result = self.tools.find_amendments(section, act)
                        else:
                            result = []
                    
                    elif "calculate_limitation_period" in tool_name:
                        # This would need more sophisticated extraction
                        result = {"error": "Limitation period calculation requires offense type and date"}
                    
                    elif "explain_legal_term" in tool_name:
                        # Extract term from query
                        term = self._extract_legal_term(query)
                        result = self.tools.explain_legal_term(term)
                    
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    
                    # Update tool call
                    tool_call["status"] = "completed"
                    tool_call["result"] = result
            
            state["reasoning_steps"].append(f"Executed {len(tool_calls)} tools")
            
            self.logger.info(f"Executed {len(tool_calls)} tools")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in execute_tools_node: {e}")
            state["reasoning_steps"].append("Tool execution failed")
            return state

    def _reason_node(self, state: AgentState) -> AgentState:
        """Analyze tool results and decide if more reasoning is needed."""
        try:
            self.logger.info(f"Agent Node: reason")
            
            # Increment iteration
            state["iteration"] = state.get("iteration", 0) + 1
            
            # Check if we have enough information
            tool_calls = state.get("tool_calls", [])
            retrieved_docs = state.get("retrieved_docs", [])
            
            has_results = len(retrieved_docs) > 0 or any(
                tc.get("result") for tc in tool_calls
            )
            
            if has_results:
                state["reasoning_steps"].append("Sufficient information gathered")
            else:
                state["reasoning_steps"].append("Insufficient information, may need more tools")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error in reason_node: {e}")
            return state

    def _generate_node(self, state: AgentState) -> AgentState:
        """Generate final answer using all gathered information."""
        try:
            self.logger.info(f"Agent Node: generate")
            
            query = state["query"]
            retrieved_docs = state.get("retrieved_docs", [])
            tool_calls = state.get("tool_calls", [])
            reasoning_steps = state.get("reasoning_steps", [])
            
            # Build context from retrieved docs
            context_parts = []
            
            if retrieved_docs:
                context_parts.append("Retrieved Documents:")
                for doc in retrieved_docs[:5]:
                    context_parts.append(f"- {doc['content'][:300]}...")
            
            # Add tool results
            if tool_calls:
                context_parts.append("\nTool Results:")
                for tc in tool_calls:
                    if tc.get("result"):
                        context_parts.append(f"- {tc['tool']}: {str(tc['result'])[:300]}...")
            
            context = "\n".join(context_parts)
            
            # Generate answer
            prompt = f"""You are VIDHI, an AI legal assistant for India.

Query: {query}

Context:
{context}

Reasoning Steps:
{chr(10).join(f"- {step}" for step in reasoning_steps)}

Provide a clear, accurate, and actionable response with:
1. Direct answer to the query
2. Relevant legal citations
3. Actionable guidance
4. Disclaimer that this is not official legal advice

Format using Markdown."""

            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            
            state["final_answer"] = answer
            
            # Extract citations
            citations = self._extract_citations(answer, retrieved_docs)
            state["citations"] = citations
            
            self.logger.info(f"Generated answer with {len(citations)} citations")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in generate_node: {e}")
            state["final_answer"] = "I apologize, but I encountered an error generating the response."
            state["citations"] = []
            return state

    def _confidence_node(self, state: AgentState) -> AgentState:
        """Calculate confidence score for the answer."""
        try:
            self.logger.info(f"Agent Node: calculate_confidence")
            
            # Factors for confidence calculation
            retrieved_docs = state.get("retrieved_docs", [])
            tool_calls = state.get("tool_calls", [])
            citations = state.get("citations", [])
            
            # Base confidence from document scores
            if retrieved_docs:
                doc_confidences = [doc.get("confidence", 0.5) for doc in retrieved_docs[:5]]
                avg_doc_confidence = sum(doc_confidences) / len(doc_confidences)
            else:
                avg_doc_confidence = 0.3
            
            # Boost for tool usage
            tool_boost = min(0.2, len(tool_calls) * 0.05)
            
            # Boost for citations
            citation_boost = min(0.2, len(citations) * 0.05)
            
            # Calculate final confidence
            confidence = min(1.0, avg_doc_confidence + tool_boost + citation_boost)
            
            state["confidence"] = round(confidence, 2)
            
            self.logger.info(f"Confidence score: {confidence:.2f}")
            return state
            
        except Exception as e:
            self.logger.error(f"Error in confidence_node: {e}")
            state["confidence"] = 0.5
            return state

    #  Conditional Edge Functions 

    def _should_use_tools(self, state: AgentState) -> Literal["use_tools", "skip_tools"]:
        """Decide whether to use tools or skip to generation."""
        tool_calls = state.get("tool_calls", [])
        
        if tool_calls and any(tc["status"] == "pending" for tc in tool_calls):
            return "use_tools"
        return "skip_tools"

    def _should_continue_reasoning(self, state: AgentState) -> Literal["continue", "finish"]:
        """Decide whether to continue reasoning or finish."""
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)
        
        # Stop if max iterations reached
        if iteration >= max_iterations:
            self.logger.info(f"Max iterations ({max_iterations}) reached")
            return "finish"
        
        # Stop if we have sufficient information
        retrieved_docs = state.get("retrieved_docs", [])
        tool_calls = state.get("tool_calls", [])
        
        has_results = len(retrieved_docs) > 0 or any(
            tc.get("result") for tc in tool_calls if tc["status"] == "completed"
        )
        
        if has_results:
            return "finish"
        
        return "continue"

    #  Helper Methods 

    def _extract_section_info(self, query: str) -> tuple[str, str]:
        """Extract section number and act name from query."""
        import re
        
        # Pattern: "Section 438 CrPC" or "438 CrPC" or "Section 438 of CrPC"
        patterns = [
            r"section\s+(\d+)\s+(?:of\s+)?(\w+)",
            r"(\d+)\s+(\w+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1), match.group(2)
        
        return None, None

    def _extract_legal_term(self, query: str) -> str:
        """Extract legal term from query."""
        # Simple extraction - take the main noun phrase
        # In production, use NLP for better extraction
        words = query.lower().split()
        
        # Remove common question words
        stop_words = {"what", "is", "are", "the", "a", "an", "explain", "define", "meaning", "of"}
        terms = [w for w in words if w not in stop_words]
        
        return " ".join(terms) if terms else query

    def _extract_citations(self, answer: str, docs: List[Dict[str, Any]]) -> List[str]:
        """Extract citations from answer and documents."""
        import re
        
        citations = []
        
        # Extract section references from answer
        section_pattern = r"Section\s+\d+(?:\s+of\s+)?(?:\w+)?"
        sections = re.findall(section_pattern, answer, re.IGNORECASE)
        citations.extend(sections)
        
        # Extract article references
        article_pattern = r"Article\s+\d+"
        articles = re.findall(article_pattern, answer, re.IGNORECASE)
        citations.extend(articles)
        
        # Add sources from documents
        for doc in docs[:3]:
            source = doc.get("metadata", {}).get("source", "")
            if source and source not in citations:
                citations.append(source)
        
        return list(set(citations))[:10]  # Deduplicate and limit

    #  Public Interface 

    def query(self, query: str, language: str = "English") -> Dict[str, Any]:
        """
        Process a query through the agent.
        
        Args:
            query: User query
            language: Response language
        
        Returns:
            Dict with answer, confidence, citations, and reasoning
        """
        try:
            self.logger.info(f"Agent query: {query}")
            
            # Initialize state
            initial_state: AgentState = {
                "query": query,
                "expanded_query": [],
                "retrieved_docs": [],
                "tool_calls": [],
                "reasoning_steps": [],
                "final_answer": "",
                "confidence": 0.0,
                "citations": [],
                "iteration": 0,
                "max_iterations": self.max_iterations
            }
            
            # Run graph
            final_state = self.graph.invoke(initial_state)
            
            # Format response
            response = {
                "answer": final_state["final_answer"],
                "confidence": final_state["confidence"],
                "citations": final_state["citations"],
                "reasoning_steps": final_state["reasoning_steps"],
                "tool_calls": len(final_state.get("tool_calls", [])),
                "iterations": final_state.get("iteration", 0)
            }
            
            self.logger.info(f"Agent completed: confidence={response['confidence']}, iterations={response['iterations']}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in agent query: {e}")
            return {
                "answer": "I apologize, but I encountered an error processing your query.",
                "confidence": 0.0,
                "citations": [],
                "reasoning_steps": [f"Error: {str(e)}"],
                "tool_calls": 0,
                "iterations": 0
            }


def create_vidhi_agent(
    llm: ChatBedrock,
    retriever: VectorStoreRetriever,
    tools: AgentTools,
    logger: logging.Logger,
    max_iterations: int = 5
) -> VidhiAgent:
    """
    Factory function to create VidhiAgent instance.
    
    Args:
        llm: Bedrock LLM instance
        retriever: Vector store retriever
        tools: Agent tools instance
        logger: Logger instance
        max_iterations: Maximum reasoning iterations
    
    Returns:
        VidhiAgent instance
    """
    return VidhiAgent(
        llm=llm,
        retriever=retriever,
        tools=tools,
        logger=logger,
        max_iterations=max_iterations
    )
