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
    conversation_history: Optional[List[Dict[str, Any]]] = None

@router.post("/query_document/")
async def query_document(request: QueryRequest):
    """
    Query the RAG pipeline with a question and optional file title.
    """
    try:
        # Query the RAG chain
        response = rag_chain.query(
            question=request.query,
            file_title=request.file_title
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