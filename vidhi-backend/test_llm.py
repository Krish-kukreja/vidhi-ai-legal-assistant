import os
import json
from dotenv import load_dotenv
import logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from configs import config
from stores.chroma import load_vectorstore, create_retriever
embeddings = config.get_embeddings()
vectorstore = load_vectorstore(embeddings)
if vectorstore:
    retriever = create_retriever(vectorstore)
else:
    retriever = None

from llm_setup.bedrock_setup import BedrockLLMService
llm_service = BedrockLLMService(logger=logger, retriever=retriever)

try:
    response = llm_service._conversational_rag_chain.invoke("Know My Rights")
except BaseException as e:
    import traceback
    with open("error_details.json", "w") as f:
        json.dump({"error": str(e), "traceback": traceback.format_exc()}, f)
