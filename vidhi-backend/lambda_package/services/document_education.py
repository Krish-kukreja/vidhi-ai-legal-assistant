"""
Document Education Service
Provides interactive teaching and simplified explanations of legal documents
"""

import json
from typing import Dict, List, Optional, Any
from llm_setup.bedrock_setup import get_llm


class DocumentEducationService:
    """Service for educating users about legal documents"""
    
    def __init__(self):
        self.llm = get_llm()
        self.legal_glossary = self._load_legal_glossary()
    
    def _load_legal_glossary(self) -> Dict[str, Dict[str, str]]:
        """Load legal term glossary with definitions and examples"""
        return {
            "indemnity": {
                "definition": "A promise to compensate someone for loss or damage",
                "simple": "If something goes wrong, you agree to pay for it",
                "example": "If you rent a house and someone gets hurt there, an indemnity clause means you pay for their medical bills, not the landlord",
                "hindi": "क्षतिपूर्ति - यदि कुछ गलत होता है, तो आप इसके लिए भुगतान करने के लिए सहमत हैं"
            },
            "force majeure": {
                "definition": "Unforeseeable circumstances that prevent contract fulfillment",
                "simple": "Events beyond anyone's control like natural disasters or war",
                "example": "If a flood destroys the property you were going to rent, the force majeure clause means neither party is blamed",
                "hindi": "अप्रत्याशित परिस्थिति - प्राकृतिक आपदा या युद्ध जैसी घटनाएं जो किसी के नियंत्रण में नहीं हैं"
            },
            "arbitration": {
                "definition": "Resolving disputes outside of court with a neutral third party",
                "simple": "Instead of going to court, you both agree to let someone else decide",
                "example": "If you and your landlord disagree about rent, an arbitrator (like a retired judge) will listen to both sides and make a decision",
                "hindi": "मध्यस्थता - अदालत के बाहर किसी तटस्थ व्यक्ति से विवाद का समाधान"
            },
            "lien": {
                "definition": "A legal right to keep possession of property until a debt is paid",
                "simple": "Someone can hold your property until you pay what you owe",
                "example": "If you don't pay your car loan, the bank has a lien and can take your car",
                "hindi": "धारणाधिकार - जब तक आप कर्ज नहीं चुकाते, कोई आपकी संपत्ति रख सकता है"
            },
            "jurisdiction": {
                "definition": "The authority of a court to hear and decide a case",
                "simple": "Which court has the power to handle your case",
                "example": "If you live in Mumbai and sign a contract there, Mumbai courts have jurisdiction, not Delhi courts",
                "hindi": "अधिकार क्षेत्र - कौन सी अदालत आपके मामले को सुन सकती है"
            },
            "consideration": {
                "definition": "Something of value exchanged in a contract",
                "simple": "What each person gives or gets in a deal",
                "example": "In a rental agreement, your consideration is rent money, landlord's consideration is letting you live there",
                "hindi": "प्रतिफल - अनुबंध में दिया या लिया जाने वाला मूल्यवान कुछ"
            },
            "breach": {
                "definition": "Breaking the terms of a contract",
                "simple": "Not doing what you promised in the agreement",
                "example": "If your landlord promised to fix the roof but doesn't, that's a breach of contract",
                "hindi": "उल्लंघन - अनुबंध में किए गए वादे को तोड़ना"
            },
            "termination": {
                "definition": "Ending a contract before its natural expiry",
                "simple": "Stopping the agreement early",
                "example": "If you want to leave your rented house before the lease ends, you need to follow the termination clause",
                "hindi": "समाप्ति - अनुबंध को समय से पहले खत्म करना"
            },
            "waiver": {
                "definition": "Voluntarily giving up a right or claim",
                "simple": "Agreeing not to use a right you have",
                "example": "If you sign a waiver at a gym, you agree not to sue them if you get injured",
                "hindi": "छूट - स्वेच्छा से किसी अधिकार को छोड़ना"
            },
            "liability": {
                "definition": "Legal responsibility for something",
                "simple": "Being responsible if something goes wrong",
                "example": "If you damage the rented property, you have liability to pay for repairs",
                "hindi": "दायित्व - कुछ गलत होने पर कानूनी जिम्मेदारी"
            }
        }
    
    def simplify_document(
        self, 
        document_text: str, 
        document_type: str,
        language: str = "english"
    ) -> Dict[str, Any]:
        """
        Break down document into sections with simplified explanations
        
        Args:
            document_text: The full document text
            document_type: Type of document (rental_agreement, loan_contract, etc.)
            language: User's preferred language
            
        Returns:
            Dictionary with sections and simplified explanations
        """
        
        prompt = f"""You are a legal educator helping citizens understand legal documents in India.

Document Type: {document_type}
Language: {language}

Document Text:
{document_text}

Please analyze this document and provide:

1. A brief summary (2-3 sentences) in simple language
2. Break it into logical sections (e.g., Parties, Payment Terms, Obligations, Termination)
3. For each section:
   - Original text
   - Simplified explanation in everyday language
   - Key points the user should know
   - Any red flags or important warnings

4. List of legal terms used and their simple definitions
5. Overall assessment: Is this document fair? Any concerning clauses?

Format your response as JSON with this structure:
{{
    "summary": "Simple 2-3 sentence summary",
    "sections": [
        {{
            "title": "Section name",
            "original_text": "Original clause text",
            "simplified": "Simple explanation",
            "key_points": ["Point 1", "Point 2"],
            "warnings": ["Warning if any"]
        }}
    ],
    "legal_terms": [
        {{
            "term": "Term name",
            "definition": "Simple definition",
            "example": "Real-world example"
        }}
    ],
    "overall_assessment": {{
        "fairness": "fair/unfair/needs_review",
        "concerns": ["List of concerns"],
        "recommendations": ["What user should do"]
    }}
}}

Use simple, conversational language. Avoid legal jargon. Explain as if talking to someone with no legal knowledge.
"""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            result = json.loads(response.content)
            
            # Add glossary terms for any legal terms found
            for term_obj in result.get("legal_terms", []):
                term_lower = term_obj["term"].lower()
                if term_lower in self.legal_glossary:
                    term_obj["glossary_definition"] = self.legal_glossary[term_lower]
            
            return result
            
        except json.JSONDecodeError:
            # If LLM doesn't return valid JSON, return structured error
            return {
                "summary": "Unable to parse document structure",
                "sections": [],
                "legal_terms": [],
                "overall_assessment": {
                    "fairness": "needs_review",
                    "concerns": ["Document analysis failed"],
                    "recommendations": ["Please consult a lawyer"]
                },
                "error": "Failed to parse LLM response"
            }
    
    def explain_clause(
        self,
        clause_text: str,
        document_context: str,
        language: str = "english",
        user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Provide detailed explanation of a specific clause
        
        Args:
            clause_text: The specific clause to explain
            document_context: Context from the full document
            language: User's preferred language
            user_profile: Optional user profile for personalized examples
            
        Returns:
            Detailed explanation with examples
        """
        
        # Personalize examples based on user profile
        context_hint = ""
        if user_profile:
            occupation = user_profile.get("occupation", "")
            location = user_profile.get("location", {}).get("state", "")
            if occupation:
                context_hint = f"\nUser is a {occupation}"
            if location:
                context_hint += f" from {location}"
            context_hint += ". Use relatable examples for this context."
        
        prompt = f"""You are explaining a legal clause to a citizen in India.

Clause to explain:
"{clause_text}"

Document context:
{document_context}

{context_hint}

Provide a detailed explanation in {language} that includes:

1. What this clause means in simple words
2. Why this clause exists (its purpose)
3. What it means for the person signing (their obligations/rights)
4. A real-world example that makes it clear
5. What could go wrong if they don't understand this
6. Any related legal concepts they should know

Use conversational language. Imagine you're explaining to a friend over tea.
"""
        
        response = self.llm.invoke(prompt)
        
        return {
            "clause": clause_text,
            "explanation": response.content,
            "language": language
        }
    
    def define_term(
        self,
        term: str,
        language: str = "english",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Define a legal term with examples
        
        Args:
            term: The legal term to define
            language: User's preferred language
            context: Optional context where the term appears
            
        Returns:
            Definition with examples
        """
        
        # Check glossary first
        term_lower = term.lower()
        glossary_entry = self.legal_glossary.get(term_lower)
        
        if glossary_entry:
            return {
                "term": term,
                "definition": glossary_entry["definition"],
                "simple_explanation": glossary_entry["simple"],
                "example": glossary_entry["example"],
                "translation": glossary_entry.get(language, glossary_entry.get("hindi", "")),
                "source": "glossary"
            }
        
        # If not in glossary, ask LLM
        context_text = f"\n\nContext where it appears:\n{context}" if context else ""
        
        prompt = f"""Define the legal term "{term}" in simple language for an Indian citizen.

{context_text}

Provide:
1. Legal definition
2. Simple explanation (as if explaining to a 10-year-old)
3. Real-world example from Indian context
4. Why this term matters in contracts/legal documents

Language: {language}
"""
        
        response = self.llm.invoke(prompt)
        
        return {
            "term": term,
            "explanation": response.content,
            "language": language,
            "source": "llm"
        }
    
    def interactive_qa(
        self,
        question: str,
        document_text: str,
        conversation_history: List[Dict[str, str]],
        language: str = "english"
    ) -> str:
        """
        Answer user questions about the document interactively
        
        Args:
            question: User's question
            document_text: The document being discussed
            conversation_history: Previous Q&A in this session
            language: User's preferred language
            
        Returns:
            Answer to the question
        """
        
        # Build conversation context
        history_text = ""
        for exchange in conversation_history[-5:]:  # Last 5 exchanges
            history_text += f"Q: {exchange['question']}\nA: {exchange['answer']}\n\n"
        
        prompt = f"""You are helping a citizen understand a legal document in India.

Document:
{document_text}

Previous conversation:
{history_text}

User's question: {question}

Provide a clear, simple answer in {language}. If the question is about a specific clause, quote it and explain. If they seem confused, offer to explain in a different way or give more examples.

Be patient, friendly, and encouraging. Remember, they may have limited legal knowledge.
"""
        
        response = self.llm.invoke(prompt)
        
        return response.content
    
    def generate_teaching_session(
        self,
        document_text: str,
        document_type: str,
        language: str = "english"
    ) -> Dict[str, Any]:
        """
        Create a structured teaching session for the document
        
        Args:
            document_text: The document to teach
            document_type: Type of document
            language: User's preferred language
            
        Returns:
            Structured teaching session with steps
        """
        
        prompt = f"""Create an interactive teaching session to help someone understand this {document_type}.

Document:
{document_text}

Design a step-by-step teaching session in {language} with:

1. Introduction: What type of document is this and why it matters
2. 5-7 teaching steps, each covering one important aspect
3. For each step:
   - What to focus on
   - Simple explanation
   - A question to check understanding
   - What to do next

4. Final summary and key takeaways
5. Warning signs to watch for

Format as JSON:
{{
    "introduction": "Intro text",
    "steps": [
        {{
            "step_number": 1,
            "title": "Step title",
            "focus": "What to look at",
            "explanation": "Simple explanation",
            "check_question": "Question to verify understanding",
            "next_action": "What to do next"
        }}
    ],
    "summary": "Key takeaways",
    "warnings": ["Important warnings"]
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "introduction": "Let's understand this document together",
                "steps": [],
                "summary": "Review complete",
                "warnings": [],
                "error": "Failed to generate teaching session"
            }


# Singleton instance
document_education_service = DocumentEducationService()
