from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.core.app_settings import settings
from src.core.error_handlers import QueryProcessingError
from src.infrastructure.rag.query_processor import LangChainRAGChain
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
import logging
import traceback
import uuid

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum verbosity

router = APIRouter()

# Initialize components
try:
    logger.info("Initializing vector store for query processing")
    vector_store = LangChainVectorStore(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY,
        gemini_api_key=settings.GEMINI_API_KEY,
        table_name=settings.SUPABASE_TABLE
    )
    logger.info("Vector store initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize vector store: {str(e)}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info(f"Initializing RAG chain with model: {settings.GENERATION_MODEL}")
    rag_chain = LangChainRAGChain(
        vector_store=vector_store,
        gemini_api_key=settings.GEMINI_API_KEY,
        model_name=settings.GENERATION_MODEL
    )
    logger.info("RAG chain initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAG chain: {str(e)}")
    logger.error(traceback.format_exc())
    raise

class QueryRequest(BaseModel):
    """Request model for document queries."""
    query: str
    file_title: Optional[str] = None

@router.post("/query_document/")
async def query_document(request: QueryRequest):
    """
    Query the RAG pipeline with a question and optional file title.
    
    Conversation history is automatically maintained by the RAG chain's memory system,
    allowing for contextual follow-up questions without explicit history management.
    """
    request_id = uuid.uuid4().hex[:8]  # Generate a unique ID for this request
    logger.info(f"[{request_id}] Processing query: '{request.query}'")
    logger.debug(f"[{request_id}] File title filter: {request.file_title or 'None'}")
    
    try:
        # Extract file_title - if it's None or empty string, set to None
        file_title = request.file_title if request.file_title else None
        
        # Log vector store retrieval attempt
        logger.debug(f"[{request_id}] Performing vector store retrieval")
        
        # Query the RAG chain (conversation history is handled internally)
        response = rag_chain.query(
            question=request.query,
            file_title=file_title
        )
        
        # Log successful retrieval
        source_count = len(response["source_documents"]) if "source_documents" in response else 0
        logger.info(f"[{request_id}] Query processed successfully. Found {source_count} source documents")
        
        # Format source documents for response
        sources = []
        if "source_documents" in response and response["source_documents"]:
            for i, doc in enumerate(response["source_documents"]):
                try:
                    source = {
                        "id": doc.metadata.get("id", f"unknown_{i}"),
                        "fileId": doc.metadata.get("fileId", "unknown"),
                        "position": doc.metadata.get("position", i),
                        "extractedText": doc.page_content,
                        "originalName": doc.metadata.get("originalName", "unknown"),
                        "downloadUrl": doc.metadata.get("downloadUrl", "")
                    }
                    sources.append(source)
                except Exception as e:
                    logger.warning(f"[{request_id}] Error formatting source document {i}: {str(e)}")
        
        # Return formatted response
        return JSONResponse(content={
            "answer": response.get("answer", "No answer generated"),
            "chunks": sources
        })
    except Exception as e:
        logger.error(f"[{request_id}] Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        raise QueryProcessingError(str(e))

@router.get("/chat-history")
async def get_chat_history():
    """
    Retrieve the conversation history from the RAG chain's memory.
    """
    request_id = uuid.uuid4().hex[:8]
    logger.info(f"[{request_id}] Retrieving chat history")
    
    try:
        # Convert the conversation history to a list of messages
        history = []
        if hasattr(rag_chain, 'memory') and hasattr(rag_chain.memory, 'chat_memory'):
            for message in rag_chain.memory.chat_memory.messages:
                if hasattr(message, 'type') and hasattr(message, 'content'):
                    role = 'assistant' if message.type == 'ai' else 'user'
                    history.append({"role": role, "content": message.content})
            
            logger.info(f"[{request_id}] Retrieved {len(history)} messages from chat history")
        else:
            logger.warning(f"[{request_id}] No chat memory found in RAG chain")
        
        return history
    except Exception as e:
        logger.error(f"[{request_id}] Failed to retrieve chat history: {str(e)}")
        logger.error(traceback.format_exc())
        raise QueryProcessingError(f"Failed to retrieve chat history: {str(e)}")

@router.delete("/chat-history")
async def clear_chat_history():
    """
    Clear the conversation history from the RAG chain's memory.
    """
    request_id = uuid.uuid4().hex[:8]
    logger.info(f"[{request_id}] Clearing chat history")
    
    try:
        if hasattr(rag_chain, 'memory') and hasattr(rag_chain.memory, 'clear'):
            rag_chain.memory.clear()
            logger.info(f"[{request_id}] Chat history cleared successfully")
        else:
            logger.warning(f"[{request_id}] No chat memory found to clear")
            
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f"[{request_id}] Failed to clear chat history: {str(e)}")
        logger.error(traceback.format_exc())
        raise QueryProcessingError(f"Failed to clear chat history: {str(e)}") 