import os # Added for debugging.
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.core.app_settings import settings
from src.api.routes import api_router
# from src.infrastructure.vector_store.langchain_vector_store import LangChainVectorStore  # Old import
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore  # Changed
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- TEMPORARY DEBUGGING ---
print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS as seen by main.py: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
# --- END TEMPORARY DEBUGGING ---

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    # Log headers selectively (to avoid logging sensitive info)
    headers_to_log = {k: v for k, v in request.headers.items() 
                     if k.lower() in ['origin', 'referer', 'user-agent', 'content-type']}
    logger.info(f"Headers: {headers_to_log}")
    
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Add CORS middleware with expanded configuration for better compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=[

        "https://uncoverlearning-vercel.vercel.app", # Backup Vercel Connection
        "https://uncover-learning.com" # Our Domain
        "https://uncoverlearning-deploy-mocha.vercel.app", # Current Vercel Connection
        # Local development
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_origin_regex=r"https://uncoverlearning-deploy.*\.vercel\.app",  # Allow all Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods for simplicity
    allow_headers=["*"],  # Allow all headers for simplicity
    expose_headers=["Content-Type", "Content-Length"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint."""
    # Simple health check or welcome message
    return {"message": "Welcome to the RAG API"} 
