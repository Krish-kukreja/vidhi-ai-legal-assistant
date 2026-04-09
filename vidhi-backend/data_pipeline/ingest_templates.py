import os
import sys
import logging
from typing import List
from langchain_core.documents import Document

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stores.chroma import store_embeddings, Chroma
from configs import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STANDARD_TEMPLATES = [
    {
        "title": "Non-Disclosure Agreement (NDA)",
        "type": "nda",
        "jurisdiction": "India",
        "description": "A standard mutual non-disclosure agreement for businesses protecting confidential information.",
        "content": """
MUTUAL NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement (the "Agreement") is entered into by and between [PARTY A NAME] ("Disclosing Party"), with its principal place of business at [PARTY A ADDRESS], and [PARTY B NAME] ("Receiving Party"), with its principal place of business at [PARTY B ADDRESS], collectively referred to as the "Parties".

1. Definition of Confidential Information. "Confidential Information" means any data or information that is proprietary to the Disclosing Party and not generally known to the public, whether in tangible or intangible form.

2. Obligations of Receiving Party. The Receiving Party shall hold and maintain the Confidential Information in strictest confidence for the sole and exclusive benefit of the Disclosing Party. 

3. Time Periods. The nondisclosure provisions of this Agreement shall survive the termination of this Agreement and Receiving Party's duty to hold Confidential Information in confidence shall remain in effect until the Confidential Information no longer qualifies as a trade secret or until Disclosing Party sends Receiving Party written notice releasing Receiving Party from this Agreement, whichever occurs first.

4. Governing Law. This Agreement shall be governed in accordance with the laws of India. Jurisdiction shall be exclusively in the courts of [JURISDICTION CITY].
"""
    },
    {
        "title": "Residential Rental Agreement",
        "type": "rental_agreement",
        "jurisdiction": "India",
        "description": "Standard 11-month residential rental/lease agreement used in India.",
        "content": """
RENTAL AGREEMENT

This Rental Agreement is made and executed on this [DATE] at [CITY], between:

[LANDLORD NAME], residing at [LANDLORD ADDRESS], hereinafter referred to as the "Landlord".
AND
[TENANT NAME], residing at [TENANT ADDRESS], hereinafter referred to as the "Tenant".

WHEREAS the Landlord is the absolute owner of the premises located at [PROPERTY ADDRESS] (hereinafter referred to as the "Schedule Property").

1. Term: The lease shall be for a period of 11 months commencing from [START DATE].
2. Rent: The monthly rent shall be Rs. [RENT AMOUNT]/-, payable on or before the [DAY OF MONTH] of every calendar month.
3. Security Deposit: The Tenant has paid a refundable interest-free security deposit of Rs. [DEPOSIT AMOUNT]/- to the Landlord.
4. Maintenance: The Tenant shall bear the electricity and water charges as per actual consumption. Routine maintenance shall be borne by the Tenant, whereas major structural repairs shall be handled by the Landlord.
5. Notice Period: Either party can terminate this agreement by giving [NOTICE PERIOD] months written notice to the other party.

IN WITNESS WHEREOF the parties hereto have signed this Agreement.
"""
    },
    {
        "title": "Employment Contract",
        "type": "employment_contract",
        "jurisdiction": "India",
        "description": "Standard employment contract for full-time employees in India.",
        "content": """
EMPLOYMENT AGREEMENT

This Employment Agreement is made on [DATE] between:
[COMPANY NAME], a company registered under the Companies Act, with its registered office at [COMPANY ADDRESS] (the "Employer").
AND
[EMPLOYEE NAME], residing at [EMPLOYEE ADDRESS] (the "Employee").

1. Position and Duties: The Employee will be employed as [JOB TITLE]. The Employee agrees to perform the duties assigned to them diligently and faithfully.
2. Compensation: The Employee's basic salary will be Rs. [SALARY AMOUNT] per annum, subject to applicable tax deductions.
3. Working Hours: The standard working hours are [WORKING HOURS] from [START DAY] to [END DAY].
4. Probation Period: The Employee will be on probation for a period of [PROBATION MONTHS] months, during which employment may be terminated by either side with [PROBATION NOTICE] days' notice.
5. Termination: Post-probation, the employment may be terminated by either party with [TERMINATION NOTICE] months' notice or pay in lieu thereof.
6. Confidentiality: The Employee agrees not to disclose any confidential information belonging to the Company.

Governing Law: The laws of India.
"""
    }
]

def ingest_templates():
    logger.info("Initializing template ingestion pipeline...")
    
    # Needs AWS config inside environment to get embeddings
    embeddings = config.get_embeddings()
    if not embeddings:
        logger.error("Could not load embeddings. Check AWS credentials.")
        return False
        
    docs = []
    
    for template in STANDARD_TEMPLATES:
        # Create a document
        text = f"Title: {template['title']}\nType: {template['type']}\nDescription: {template['description']}\n\nCONTENT:\n{template['content']}"
        
        doc = Document(
            page_content=text,
            metadata={
                "type": template["type"],
                "jurisdiction": template["jurisdiction"]
            }
        )
        docs.append(doc)
    
    logger.info(f"Loaded {len(docs)} template documents.")
    
    # Store to Chroma DB in a specific collection
    logger.info("Storing templates to ChromaDB 'vidhi-templates' collection...")
    try:
        vectorstore = store_embeddings(
            documents=docs,
            embeddings=embeddings,
            collection_name="vidhi-templates"
        )
        
        if vectorstore:
            logger.info("Template ingestion completed successfully!")
            return True
        else:
            logger.error("Failed to create vector store for templates.")
            return False
    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    ingest_templates()
