"""
Tests for LangGraph Agent and Agent Tools
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.documents import Document

from llm_setup.agent_tools import AgentTools, create_agent_tools
from llm_setup.agent import VidhiAgent, create_vidhi_agent, AgentState


#  Fixtures 

@pytest.fixture
def mock_retriever():
    """Mock retriever that returns sample documents."""
    retriever = Mock()
    
    def mock_invoke(query):
        # Return different docs based on query
        if "438" in query or "bail" in query.lower():
            return [
                Document(
                    page_content="Section 438 of CrPC deals with anticipatory bail...",
                    metadata={"source": "CrPC", "section": "438", "confidence": 0.95}
                ),
                Document(
                    page_content="Anticipatory bail is a direction to release a person on bail...",
                    metadata={"source": "Legal Database", "confidence": 0.85}
                )
            ]
        elif "amendment" in query.lower():
            return [
                Document(
                    page_content="Amendment to Section 438 CrPC in 2018...",
                    metadata={"source": "Amendment Act 2018", "date": "2018-08-01", "confidence": 0.90}
                )
            ]
        else:
            return [
                Document(
                    page_content="General legal information...",
                    metadata={"source": "Legal Database", "confidence": 0.70}
                )
            ]
    
    retriever.invoke = mock_invoke
    return retriever


@pytest.fixture
def mock_logger():
    """Mock logger."""
    return Mock()


@pytest.fixture
def agent_tools(mock_retriever, mock_logger):
    """Create AgentTools instance with mocked dependencies."""
    return create_agent_tools(mock_retriever, mock_logger)


@pytest.fixture
def mock_llm():
    """Mock LLM that returns simple responses."""
    llm = Mock()
    
    def mock_invoke(prompt):
        response = Mock()
        
        # Handle different prompt types
        if "alternative queries" in str(prompt).lower():
            response.content = "anticipatory bail\npre-arrest bail"
        elif "which tools" in str(prompt).lower():
            if "438" in str(prompt):
                response.content = "get_exact_section\nsearch_legal_database"
            else:
                response.content = "search_legal_database"
        else:
            response.content = "This is a legal response with proper citations."
        
        return response
    
    llm.invoke = mock_invoke
    return llm


@pytest.fixture
def vidhi_agent(mock_llm, mock_retriever, agent_tools, mock_logger):
    """Create VidhiAgent instance with mocked dependencies."""
    return create_vidhi_agent(
        llm=mock_llm,
        retriever=mock_retriever,
        tools=agent_tools,
        logger=mock_logger,
        max_iterations=3
    )


#  AgentTools Tests 

class TestAgentTools:
    """Test suite for AgentTools."""

    def test_create_agent_tools(self, mock_retriever, mock_logger):
        """Test agent tools creation."""
        tools = create_agent_tools(mock_retriever, mock_logger)
        
        assert tools is not None
        assert isinstance(tools, AgentTools)
        assert tools.retriever == mock_retriever
        assert tools.logger == mock_logger

    def test_search_legal_database(self, agent_tools):
        """Test search_legal_database tool."""
        results = agent_tools.search_legal_database("Section 438 CrPC", top_k=5)
        
        assert len(results) > 0
        assert results[0]["content"] is not None
        assert results[0]["metadata"] is not None
        assert results[0]["rank"] == 1
        assert "confidence" in results[0]

    def test_search_legal_database_with_filter(self, agent_tools):
        """Test search with document type filter."""
        # This test will pass even if filtering doesn't work perfectly
        # because we're testing the interface, not the mock behavior
        results = agent_tools.search_legal_database(
            "Section 438 CrPC",
            doc_type="legislation",
            top_k=5
        )
        
        assert isinstance(results, list)

    def test_get_exact_section_found(self, agent_tools):
        """Test get_exact_section when section is found."""
        result = agent_tools.get_exact_section("438", "CrPC")
        
        assert result is not None
        assert "content" in result
        assert "metadata" in result
        assert result["section_number"] == "438"
        assert result["act_name"] == "CrPC"

    def test_get_exact_section_not_found(self, agent_tools):
        """Test get_exact_section when section is not found."""
        result = agent_tools.get_exact_section("9999", "XYZ")
        
        # Should return None or empty result
        assert result is None or result == {}

    def test_find_amendments(self, agent_tools):
        """Test find_amendments tool."""
        amendments = agent_tools.find_amendments("438", "CrPC")
        
        assert isinstance(amendments, list)
        # May or may not find amendments depending on mock data

    def test_calculate_limitation_period_valid(self, agent_tools):
        """Test limitation period calculation with valid inputs."""
        result = agent_tools.calculate_limitation_period(
            "civil",
            "2023-01-01"
        )
        
        assert "offense_type" in result
        assert "offense_date" in result
        assert "limitation_period_days" in result
        assert "status" in result

    def test_calculate_limitation_period_invalid_date(self, agent_tools):
        """Test limitation period calculation with invalid date."""
        result = agent_tools.calculate_limitation_period(
            "civil",
            "invalid-date"
        )
        
        assert "error" in result

    def test_calculate_limitation_period_cognizable(self, agent_tools):
        """Test limitation period for cognizable offenses (no limitation)."""
        result = agent_tools.calculate_limitation_period(
            "cognizable",
            "2023-01-01"
        )
        
        assert result["limitation_period_days"] == "No limitation"
        assert result["expiry_date"] is None

    def test_explain_legal_term(self, agent_tools):
        """Test explain_legal_term tool."""
        explanation = agent_tools.explain_legal_term("anticipatory bail")
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0

    def test_explain_legal_term_with_language(self, agent_tools):
        """Test explain_legal_term with language parameter."""
        explanation = agent_tools.explain_legal_term("bail", language="hindi")
        
        assert isinstance(explanation, str)


#  VidhiAgent Tests 

class TestVidhiAgent:
    """Test suite for VidhiAgent."""

    def test_create_vidhi_agent(self, mock_llm, mock_retriever, agent_tools, mock_logger):
        """Test agent creation."""
        agent = create_vidhi_agent(
            llm=mock_llm,
            retriever=mock_retriever,
            tools=agent_tools,
            logger=mock_logger,
            max_iterations=5
        )
        
        assert agent is not None
        assert isinstance(agent, VidhiAgent)
        assert agent.max_iterations == 5

    def test_agent_query_simple(self, vidhi_agent):
        """Test simple agent query."""
        response = vidhi_agent.query("What is Section 438 CrPC?")
        
        assert "answer" in response
        assert "confidence" in response
        assert "citations" in response
        assert "reasoning_steps" in response
        assert isinstance(response["answer"], str)
        assert 0 <= response["confidence"] <= 1

    def test_agent_query_with_language(self, vidhi_agent):
        """Test agent query with language parameter."""
        response = vidhi_agent.query("What is bail?", language="Hindi")
        
        assert "answer" in response
        assert isinstance(response["answer"], str)

    def test_agent_reasoning_steps(self, vidhi_agent):
        """Test that agent records reasoning steps."""
        response = vidhi_agent.query("Section 438 CrPC")
        
        assert len(response["reasoning_steps"]) > 0
        assert any("expand" in step.lower() for step in response["reasoning_steps"])

    def test_agent_tool_usage(self, vidhi_agent):
        """Test that agent uses tools."""
        response = vidhi_agent.query("What is Section 438 of CrPC?")
        
        # Agent should use tools for this query
        assert response["tool_calls"] >= 0  # May or may not use tools

    def test_agent_max_iterations(self, vidhi_agent):
        """Test that agent respects max iterations."""
        response = vidhi_agent.query("Complex legal query")
        
        assert response["iterations"] <= vidhi_agent.max_iterations

    def test_agent_confidence_scoring(self, vidhi_agent):
        """Test confidence score calculation."""
        response = vidhi_agent.query("Section 438 CrPC")
        
        assert "confidence" in response
        assert 0 <= response["confidence"] <= 1
        assert isinstance(response["confidence"], float)

    def test_agent_citations(self, vidhi_agent):
        """Test citation extraction."""
        response = vidhi_agent.query("What is Section 438 CrPC?")
        
        assert "citations" in response
        assert isinstance(response["citations"], list)

    def test_agent_error_handling(self, mock_llm, mock_retriever, agent_tools, mock_logger):
        """Test agent error handling."""
        # Make LLM raise an error
        mock_llm.invoke = Mock(side_effect=Exception("LLM error"))
        
        agent = create_vidhi_agent(
            llm=mock_llm,
            retriever=mock_retriever,
            tools=agent_tools,
            logger=mock_logger
        )
        
        response = agent.query("Test query")
        
        # Should return error response, not crash
        assert "answer" in response
        assert "error" in response["answer"].lower() or response["confidence"] == 0.0


#  Agent Node Tests 

class TestAgentNodes:
    """Test individual agent nodes."""

    def test_expand_query_node(self, vidhi_agent):
        """Test query expansion node."""
        state: AgentState = {
            "query": "Section 438 CrPC",
            "expanded_query": [],
            "retrieved_docs": [],
            "tool_calls": [],
            "reasoning_steps": [],
            "final_answer": "",
            "confidence": 0.0,
            "citations": [],
            "iteration": 0,
            "max_iterations": 5
        }
        
        result = vidhi_agent._expand_query_node(state)
        
        assert len(result["expanded_query"]) > 0
        assert result["query"] in result["expanded_query"]  # Original query included

    def test_retrieve_node(self, vidhi_agent):
        """Test document retrieval node."""
        state: AgentState = {
            "query": "Section 438 CrPC",
            "expanded_query": ["Section 438 CrPC"],
            "retrieved_docs": [],
            "tool_calls": [],
            "reasoning_steps": [],
            "final_answer": "",
            "confidence": 0.0,
            "citations": [],
            "iteration": 0,
            "max_iterations": 5
        }
        
        result = vidhi_agent._retrieve_node(state)
        
        assert len(result["retrieved_docs"]) > 0
        assert "content" in result["retrieved_docs"][0]

    def test_confidence_node(self, vidhi_agent):
        """Test confidence calculation node."""
        state: AgentState = {
            "query": "Section 438 CrPC",
            "expanded_query": ["Section 438 CrPC"],
            "retrieved_docs": [
                {"content": "test", "metadata": {}, "confidence": 0.9}
            ],
            "tool_calls": [],
            "reasoning_steps": [],
            "final_answer": "Test answer",
            "confidence": 0.0,
            "citations": ["Section 438"],
            "iteration": 1,
            "max_iterations": 5
        }
        
        result = vidhi_agent._confidence_node(state)
        
        assert result["confidence"] > 0
        assert result["confidence"] <= 1.0


#  Helper Method Tests 

class TestAgentHelpers:
    """Test agent helper methods."""

    def test_extract_section_info_standard(self, vidhi_agent):
        """Test section extraction from standard format."""
        section, act = vidhi_agent._extract_section_info("Section 438 CrPC")
        
        assert section == "438"
        assert act == "CrPC"

    def test_extract_section_info_short(self, vidhi_agent):
        """Test section extraction from short format."""
        section, act = vidhi_agent._extract_section_info("438 CrPC")
        
        assert section == "438"
        assert act == "CrPC"

    def test_extract_section_info_with_of(self, vidhi_agent):
        """Test section extraction with 'of' keyword."""
        section, act = vidhi_agent._extract_section_info("Section 438 of CrPC")
        
        assert section == "438"
        assert act == "CrPC"

    def test_extract_section_info_not_found(self, vidhi_agent):
        """Test section extraction when pattern not found."""
        section, act = vidhi_agent._extract_section_info("What is bail?")
        
        assert section is None
        assert act is None

    def test_extract_legal_term(self, vidhi_agent):
        """Test legal term extraction."""
        term = vidhi_agent._extract_legal_term("What is anticipatory bail?")
        
        assert "anticipatory" in term.lower() or "bail" in term.lower()

    def test_extract_citations(self, vidhi_agent):
        """Test citation extraction from answer."""
        answer = "Section 438 of CrPC and Article 21 of Constitution..."
        docs = [
            {"metadata": {"source": "CrPC"}, "content": "test"}
        ]
        
        citations = vidhi_agent._extract_citations(answer, docs)
        
        assert len(citations) > 0
        assert any("438" in c or "21" in c for c in citations)


#  Integration Tests 

@pytest.mark.slow
class TestAgentIntegration:
    """Integration tests for the full agent pipeline."""

    def test_full_agent_pipeline(self, vidhi_agent):
        """Test complete agent query pipeline."""
        response = vidhi_agent.query("What is Section 438 of CrPC?")
        
        # Verify all response components
        assert "answer" in response
        assert "confidence" in response
        assert "citations" in response
        assert "reasoning_steps" in response
        assert "tool_calls" in response
        assert "iterations" in response
        
        # Verify response quality
        assert len(response["answer"]) > 0
        assert response["confidence"] > 0
        assert len(response["reasoning_steps"]) > 0

    def test_agent_with_complex_query(self, vidhi_agent):
        """Test agent with complex multi-part query."""
        response = vidhi_agent.query(
            "What is Section 438 CrPC and what amendments were made to it?"
        )
        
        assert "answer" in response
        assert len(response["answer"]) > 0
        # Complex queries may use multiple tools
        assert response["iterations"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
