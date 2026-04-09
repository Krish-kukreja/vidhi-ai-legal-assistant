import logging
import json
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
from langchain_community.tools import DuckDuckGoSearchRun

from configs import config

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = ChatPromptTemplate.from_template("""\
You are an expert Indian legal researcher assisting a lawyer.
Your task is to synthesize the search results from live case law databases and provide a clear, accurate, and citable summary.

USER QUERY:
{query}

LIVE WEB SEARCH RESULTS (DuckDuckGo scoped to Indian case law):
{search_results}

INSTRUCTIONS:
1. Provide a concise legal summary addressing the user's query utilizing the provided search results.
2. If the search results mention specific clauses, judgments, or IPC/BNS sections, highlight them.
3. If the search results do not confidently answer the query, state that the search yielded insufficient case law precedents.
4. Ensure the output is formatted elegantly in Markdown.
""")

class LiveResearchService:
    def __init__(self):
        self._logger = logger
        self.llm = ChatBedrock(
            model_id=config.BEDROCK_MODEL_ID_ADVANCED,
            region_name=config.AWS_REGION,
            model_kwargs={
                "temperature": 0.2,
                "max_tokens": 4096
            }
        )
        self.search_tool = DuckDuckGoSearchRun()
        self.research_chain = RESEARCH_PROMPT | self.llm

    def search_case_law(self, query: str) -> Dict[str, Any]:
        """
        Executes a live search scoped conditionally to Indian courts 
        and extracts an LLM-summarized answer.
        """
        try:
            self._logger.info(f"Executing Live Case Law Search for: {query}")
            
            # Augment query to target credible Indian case law sites
            search_query = f"{query} site:indiankanoon.org OR site:livelaw.in OR site:barandbench.com"
            raw_search_results = self.search_tool.run(search_query)
            
            self._logger.info(f"Retrieved {len(raw_search_results)} characters of search context.")
            
            # Synthesize results
            response = self.research_chain.invoke({
                "query": query,
                "search_results": raw_search_results
            })
            
            synthesis = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "success": True,
                "query": query,
                "raw_results": raw_search_results,
                "synthesis": synthesis
            }
            
        except Exception as e:
            self._logger.error(f"Error researching case law: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

live_research_service = LiveResearchService()
