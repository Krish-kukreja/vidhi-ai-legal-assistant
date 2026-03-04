"""
Document processing utilities for VIDHI
Adapted from UdhaviBot with AWS compatibility
"""
from langchain_community.document_loaders import WebBaseLoader, JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import Iterable, List
import json
from langchain.schema import Document


def load_documents(website: str) -> list[Document]:
    """
    Loads documents from a given website.

    Args:
        website (str): The URL of the website to load documents from.

    Returns:
        list[Document]: A list of loaded documents.
    """
    loader = WebBaseLoader(website)
    return loader.load()


def format_documents(docs: list[Document]) -> str:
    """
    Formats a list of documents into a single string.

    Args:
        docs (list[Document]): The list of documents to format.

    Returns:
        str: The formatted documents as a single string.
    """
    return "\n\n".join(doc.page_content for doc in docs)


def split_documents(documents: Iterable[Document], chunk_size: int = 1000, chunk_overlap: int = 100) -> list[Document]:
    """
    Splits documents into smaller chunks.

    Args:
        documents (Iterable[Document]): The documents to split.
        chunk_size (int): Size of each chunk.
        chunk_overlap (int): Overlap between chunks.

    Returns:
        list[Document]: A list of split documents.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)


def load_json_to_langchain_document_schema(file_path: str) -> List[Document]:
    """
    Reads a JSON file and returns a list of Document objects.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        List[Document]: A list of Document objects from the JSON file.
    """
    loader = JSONLoader(
        file_path=file_path,
        jq_schema='.[]',
        text_content=False
    )

    documents = loader.load()
    return documents


def load_json_from_s3(bucket: str, key: str) -> List[Document]:
    """
    Loads JSON from S3 and converts to LangChain documents.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
    
    Returns:
        List[Document]: List of Document objects
    """
    import boto3
    import tempfile
    
    s3_client = boto3.client('s3', region_name='ap-south-1')
    
    # Download to temp file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
        s3_client.download_file(bucket, key, tmp_file.name)
        return load_json_to_langchain_document_schema(tmp_file.name)


def create_scheme_documents(schemes_data: list) -> List[Document]:
    """
    Converts scraped scheme data into LangChain Document objects.
    
    Args:
        schemes_data (list): List of scheme dictionaries
    
    Returns:
        List[Document]: List of Document objects
    """
    documents = []
    
    for scheme in schemes_data:
        # Create comprehensive text content
        content = f"""
Scheme Name: {scheme.get('scheme_name', 'N/A')}

Details: {scheme.get('details', 'Not Available')}

Benefits: {scheme.get('benefits', 'Not Available')}

Eligibility: {scheme.get('eligibility', 'Not Available')}

Application Process: {scheme.get('application_process', 'Not Available')}

Documents Required: {scheme.get('documents_required', 'Not Available')}

Tags: {', '.join(scheme.get('tags', []))}
"""
        
        metadata = {
            'scheme_name': scheme.get('scheme_name', 'N/A'),
            'scheme_link': scheme.get('scheme_link', ''),
            'sr_no': scheme.get('sr_no', ''),
            'tags': scheme.get('tags', [])
        }
        
        doc = Document(page_content=content.strip(), metadata=metadata)
        documents.append(doc)
    
    return documents
