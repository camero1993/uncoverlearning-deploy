from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.app_settings import settings
from src.api.routes import api_router

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the RAG API"} 