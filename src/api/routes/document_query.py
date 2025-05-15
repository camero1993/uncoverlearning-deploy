from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.core.app_settings import settings
from src.core.error_handlers import QueryProcessingError
from src.infrastructure.rag.query_processor import LangChainRAGChain
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore

router = APIRouter()

# Initialize components
vector_store = LangChainVectorStore(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_KEY,
    gemini_api_key=settings.GEMINI_API_KEY,
    table_name=settings.SUPABASE_TABLE
)

rag_chain = LangChainRAGChain(
    vector_store=vector_store,
    gemini_api_key=settings.GEMINI_API_KEY,
    model_name=settings.GENERATION_MODEL
)

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
    try:
        # Extract file_title - if it's None or empty string, set to None
        file_title = request.file_title if request.file_title else None
        
        # Query the RAG chain (conversation history is handled internally)
        response = rag_chain.query(
            question=request.query,
            file_title=file_title
        )
        
        return JSONResponse(content={
            "answer": response["answer"],
            "chunks": [
                {
                    "id": doc.metadata["id"],
                    "fileId": doc.metadata["fileId"],
                    "position": doc.metadata["position"],
                    "extractedText": doc.page_content,
                    "originalName": doc.metadata["originalName"],
                    "downloadUrl": doc.metadata["downloadUrl"]
                }
                for doc in response["source_documents"]
            ]
        })
    except Exception as e:
        raise QueryProcessingError(str(e))

@router.get("/chat-history")
async def get_chat_history():
    """
    Retrieve the conversation history from the RAG chain's memory.
    """
    try:
        # Convert the conversation history to a list of messages
        history = []
        if hasattr(rag_chain, 'memory') and hasattr(rag_chain.memory, 'chat_memory'):
            for message in rag_chain.memory.chat_memory.messages:
                if hasattr(message, 'type') and hasattr(message, 'content'):
                    role = 'assistant' if message.type == 'ai' else 'user'
                    history.append({"role": role, "content": message.content})
        
        return history
    except Exception as e:
        raise QueryProcessingError(f"Failed to retrieve chat history: {str(e)}")

@router.delete("/chat-history")
async def clear_chat_history():
    """
    Clear the conversation history from the RAG chain's memory.
    """
    try:
        if hasattr(rag_chain, 'memory') and hasattr(rag_chain.memory, 'clear'):
            rag_chain.memory.clear()
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise QueryProcessingError(f"Failed to clear chat history: {str(e)}") 