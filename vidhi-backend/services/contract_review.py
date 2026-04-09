import logging
import json
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock

from configs import config

logger = logging.getLogger(__name__)

REVIEW_PROMPT = ChatPromptTemplate.from_template("""\
You are an expert contract review AI for VIDHI. Analyze the following contract text.
You MUST look for unfair terms, missing crucial clauses, unbalanced liabilities, and legally ambiguous phrasing.
{persona_instructions}

CONTRACT TEXT:
{contract_text}

Provide your analysis in STRICT JSON format with the following schema:
{{
  "overall_risk_score": "High/Medium/Low",
  "summary": "Brief summary of the contract and major concerns",
  "issues": [
    {{
      "original_clause": "The verbatim text from the contract that is an issue.",
      "suggested_redline": "Your suggested corrected text.",
      "reasoning": "Why this is an issue and why the redline improves it.",
      "severity": "High/Medium/Low"
    }}
  ]
}}
Ensure the output is ONLY valid JSON.
""")

class ContractReviewService:
    def __init__(self):
        self._logger = logger
        self.llm = ChatBedrock(
            model_id=config.BEDROCK_MODEL_ID_ADVANCED,
            region_name=config.AWS_REGION,
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 4096
            }
        )
        self.review_chain = REVIEW_PROMPT | self.llm

    def analyze_contract(self, contract_text: str, playbook_rules: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes a contract and returns suggested redlines and risk assessment.
        """
        try:
            self._logger.info("Executing AI Contract Review...")
            
            if playbook_rules:
                persona_instructions = f"INSTRUCTIONS: Please review this contract aggressively against the following custom playbook rules:\n{playbook_rules}"
            else:
                persona_instructions = "INSTRUCTIONS: Please review this contract for general fairness, protecting the rights of the underdog party appropriately."
                
            response = self.review_chain.invoke({
                "persona_instructions": persona_instructions,
                "contract_text": contract_text
            })
            
            output_content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in output_content:
                output_content = output_content.split("```json")[-1].split("```")[0].strip()
            elif "```" in output_content:
                output_content = output_content.split("```")[-1].split("```")[0].strip()
                
            parsed_json = json.loads(output_content)
            
            return {
                "success": True,
                "data": parsed_json
            }
            
        except Exception as e:
            self._logger.error(f"Error reviewing contract: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

contract_review_service = ContractReviewService()
