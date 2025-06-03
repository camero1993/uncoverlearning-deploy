from fastapi import APIRouter
from .document_upload import router as documents_router
from .document_query import router as queries_router

# Create main router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(queries_router, prefix="/queries", tags=["queries"]) 