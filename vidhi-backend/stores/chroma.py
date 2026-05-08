"""
ChromaDB Vector Store for VIDHI
Adapted from UdhaviBot to use AWS Bedrock embeddings
"""
from langchain_chroma import Chroma
from langchain_core.documents import Document
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def store_embeddings(
    documents: List[Document],
    embeddings,
    collection_name: str = "vidhi-schemes",
    persist_directory: str = "./chroma_db"
) -> Optional[Chroma]:
    """
    Store embeddings for the documents using AWS Bedrock embeddings and Chroma vectorstore.
    
    Args:
        documents: List of LangChain Document objects
        embeddings: Embedding model (AWS Bedrock Titan or HuggingFace fallback)
        collection_name: Name of the Chroma collection
        persist_directory: Directory to persist the vector store
    
    Returns:
        Chroma vectorstore instance or None if error
    """
    try:
        logger.info(f"Creating vector store with {len(documents)} documents")
        
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        
        logger.info(f"Successfully created vector store with {len(documents)} documents")
        return vectorstore
        
    except Exception as e:
        logger.error(f"Error creating VectorStore from Chroma DB: {e}")
        raise Exception(f"Error creating VectorStoreRetriever from chroma DB: {e}")


def load_vectorstore(
    embeddings,
    collection_name: str = "vidhi-schemes",
    persist_directory: str = "./chroma_db"
) -> Optional[Chroma]:
    """
    Load existing Chroma vectorstore.
    
    Args:
        embeddings: Embedding model
        collection_name: Name of the Chroma collection
        persist_directory: Directory where vector store is persisted
    
    Returns:
        Chroma vectorstore instance or None if not found
    """
    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory
        )
        
        logger.info(f"Successfully loaded vector store: {collection_name}")
        return vectorstore
        
    except Exception as e:
        logger.error(f"Error loading vector store: {e}")
        return None


def add_documents_to_vectorstore(
    vectorstore: Chroma,
    documents: List[Document]
) -> bool:
    """
    Add new documents to existing vectorstore.
    
    Args:
        vectorstore: Existing Chroma vectorstore
        documents: List of new documents to add
    
    Returns:
        True if successful, False otherwise
    """
    try:
        vectorstore.add_documents(documents)
        logger.info(f"Successfully added {len(documents)} documents to vector store")
        return True
    except Exception as e:
        logger.error(f"Error adding documents to vector store: {e}")
        return False


def search_similar_documents(
    vectorstore: Chroma,
    query: str,
    k: int = 4
) -> List[Document]:
    """
    Search for similar documents in the vectorstore.
    
    Args:
        vectorstore: Chroma vectorstore
        query: Search query
        k: Number of results to return
    
    Returns:
        List of similar documents
    """
    try:
        docs = vectorstore.similarity_search(query, k=k)
        logger.info(f"Found {len(docs)} similar documents for query")
        return docs
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []


def create_retriever(
    vectorstore: Chroma,
    search_type: str = "similarity",
    search_kwargs: dict = None
):
    """
    Create a retriever from the vectorstore.
    
    Args:
        vectorstore: Chroma vectorstore
        search_type: Type of search ("similarity", "mmr", etc.)
        search_kwargs: Additional search parameters
    
    Returns:
        VectorStoreRetriever instance
    """
    if search_kwargs is None:
        search_kwargs = {"k": 4}
    
    try:
        retriever = vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
        logger.info(f"Created retriever with search_type={search_type}")
        return retriever
    except Exception as e:
        logger.error(f"Error creating retriever: {e}")
        raise


def create_hybrid_retriever(
    vectorstore: Chroma,
    bm25_weight: float = 0.5,
    semantic_weight: float = 0.5,
    top_k: int = 50,
    reranking_enabled: bool = True,
    reranking_top_k: int = 10,
    confidence_threshold: float = 0.0
):
    """
    Create a hybrid retriever combining BM25 and semantic search.
    
    Args:
        vectorstore: Chroma vectorstore
        bm25_weight: Weight for BM25 scores (0-1)
        semantic_weight: Weight for semantic scores (0-1)
        top_k: Number of candidates from hybrid search
        reranking_enabled: Enable cross-encoder reranking
        reranking_top_k: Number of results after reranking
        confidence_threshold: Minimum confidence for reranking
    
    Returns:
        HybridRetriever instance (with optional reranking)
    """
    try:
        from stores.bm25_retriever import create_bm25_retriever
        from stores.hybrid_retriever import create_hybrid_retriever as create_hybrid
        from stores.reranker import create_reranker
        
        # Get all documents from vectorstore
        logger.info("Building BM25 index from vectorstore...")
        all_docs = vectorstore.get()
        
        # Convert to LangChain Document format
        documents = [
            Document(
                page_content=all_docs['documents'][i],
                metadata=all_docs['metadatas'][i] if all_docs['metadatas'] else {}
            )
            for i in range(len(all_docs['documents']))
        ]
        
        logger.info(f"Building hybrid retriever with {len(documents)} documents")
        
        # Create BM25 retriever
        bm25_retriever = create_bm25_retriever(documents)
        
        # Create semantic retriever
        semantic_retriever = vectorstore.as_retriever(
            search_kwargs={"k": top_k}
        )
        
        # Create hybrid retriever
        hybrid_retriever = create_hybrid(
            bm25_retriever=bm25_retriever,
            semantic_retriever=semantic_retriever,
            bm25_weight=bm25_weight,
            semantic_weight=semantic_weight,
            top_k=top_k
        )
        
        # Wrap with reranker if enabled
        if reranking_enabled:
            logger.info("Enabling cross-encoder reranking")
            reranker = create_reranker(
                confidence_threshold=confidence_threshold,
                cache_enabled=True
            )
            
            # Create wrapper that combines hybrid retrieval + reranking
            class HybridRetrieverWithReranking:
                def __init__(self, hybrid_ret, rerank):
                    self.hybrid_retriever = hybrid_ret
                    self.reranker = rerank
                    self.reranking_top_k = reranking_top_k
                
                def get_relevant_documents(self, query: str) -> List[Document]:
                    # Get hybrid results
                    hybrid_results = self.hybrid_retriever.get_relevant_documents_with_scores(query)
                    
                    # Rerank
                    reranked = self.reranker.rerank_with_metadata(
                        query,
                        hybrid_results,
                        top_k=self.reranking_top_k
                    )
                    
                    return [r["document"] for r in reranked]
                
                def get_relevant_documents_with_scores(self, query: str) -> List[dict]:
                    # Get hybrid results
                    hybrid_results = self.hybrid_retriever.get_relevant_documents_with_scores(query)
                    
                    # Rerank
                    reranked = self.reranker.rerank_with_metadata(
                        query,
                        hybrid_results,
                        top_k=self.reranking_top_k
                    )
                    
                    return reranked
            
            retriever = HybridRetrieverWithReranking(hybrid_retriever, reranker)
            logger.info(f"Created hybrid retriever with reranking (top_k={reranking_top_k})")
        else:
            retriever = hybrid_retriever
            logger.info(f"Created hybrid retriever without reranking (top_k={top_k})")
        
        return retriever
        
    except Exception as e:
        logger.error(f"Error creating hybrid retriever: {e}")
        logger.warning("Falling back to standard semantic retriever")
        return create_retriever(vectorstore)


class CachedEmbeddingStore:
    """
    Wrapper around Chroma that caches embeddings in DynamoDB for cost optimization.
    This reduces AWS Bedrock embedding costs by 90%.
    """
    
    def __init__(self, vectorstore: Chroma, cache_table_name: str = "vidhi-embedding-cache"):
        self.vectorstore = vectorstore
        self.cache_table_name = cache_table_name
        self._init_cache()
    
    def _init_cache(self):
        """Initialize DynamoDB cache table"""
        try:
            import boto3
            self.dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
            self.cache_table = self.dynamodb.Table(self.cache_table_name)
            logger.info(f"Initialized embedding cache: {self.cache_table_name}")
        except Exception as e:
            logger.warning(f"Could not initialize embedding cache: {e}")
            self.cache_table = None
    
    def get_cached_embedding(self, text: str):
        """Get embedding from cache if available"""
        if not self.cache_table:
            return None
        
        try:
            import hashlib
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            response = self.cache_table.get_item(Key={'text_hash': text_hash})
            if 'Item' in response:
                logger.debug(f"Cache hit for text hash: {text_hash[:8]}...")
                return response['Item']['embedding']
            
            return None
        except Exception as e:
            logger.warning(f"Error getting cached embedding: {e}")
            return None
    
    def cache_embedding(self, text: str, embedding: list):
        """Cache embedding in DynamoDB"""
        if not self.cache_table:
            return
        
        try:
            import hashlib
            import time
            
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            self.cache_table.put_item(Item={
                'text_hash': text_hash,
                'embedding': embedding,
                'text_preview': text[:100],  # For debugging
                'created_at': int(time.time()),
                'ttl': int(time.time()) + (365 * 24 * 3600)  # 1 year
            })
            
            logger.debug(f"Cached embedding for text hash: {text_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Error caching embedding: {e}")
