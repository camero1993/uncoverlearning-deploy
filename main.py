import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, JSONResponse, Body
from fastapi.middleware.cors import CORSMiddleware # Import CORS middleware
from typing import Annotated, Optional # Import Optional
from dotenv import load_dotenv
import io
from pydantic import BaseModel # Import BaseModel
# Note: Body is imported above with other fastapi imports

# Load environment variables from .env file
load_dotenv()

# Import functions from your rag_pipeline.py file
# Make sure rag_pipeline.py is in the same directory or accessible in your Python path
try:
    from rag_pipeline import (
        process_document,
        generate_gemini_embedding,
        hybrid_search,
        format_prompt_with_context,
        generate_gemini_response,
        # Assuming these variables are loaded globally in rag_pipeline.py now
        # SUPABASE_URL,
        # SUPABASE_KEY,
        # GCP_BUCKET,
        # gemini_api_key
    )
    # Re-load variables needed in main.py from environment if not imported
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    GCP_BUCKET = os.getenv("GCP_BUCKET") # Ensure this matches the env var name
    gemini_api_key = os.getenv("GEMINI_API_KEY")

except ImportError:
    raise ImportError("Could not import functions from rag_pipeline.py. Ensure the file exists and is in the correct path.")
except Exception as e:
    print(f"Error loading configurations or importing rag_pipeline: {e}")
    raise # Re-raise other exceptions during import/config loading


# Initialize FastAPI app
app = FastAPI()

# --- CORS Configuration ---
# Define the origins that are allowed to make requests to your backend.
# IMPORTANT: Replace the URL below with the actual URL(s) of your Vercel frontend deployment(s).
# If you have a custom domain, include that as well.
# If you are testing locally, you might add "http://localhost:3000" or whatever port your local frontend runs on.
# In production, AVOID using ["*"] as it allows *any* website to access your API, which is a security risk.
origins = [
    "https://uncoverlearning-deploy.vercel.app"
    # Add other Vercel deployment URLs or custom domains here if needed
    # "https://your-custom-domain.com",
    # "http://localhost:3000", # Example for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # List of origins that are allowed to make requests
    allow_credentials=True,     # Allow cookies to be included in requests
    allow_methods=["*"],        # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],        # Allow all headers
)

# --- Configuration (can be moved to .env or config file) ---
# Get configuration from environment variables loaded by dotenv
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "files") # Default to 'files' if not set
GCP_DESTINATION_FOLDER = os.getenv("GCP_DESTINATION_FOLDER", "uploaded_docs") # Default folder in GCP
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000)) # Default chunk size
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004") # Default embedding model
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "models/gemini-1.5-pro-latest") # Default generation model

# Hybrid Search Config (can also be in .env)
MATCH_COUNT = int(os.getenv("MATCH_COUNT", 10))
FULL_TEXT_WEIGHT = float(os.getenv("FULL_TEXT_WEIGHT", 1.0))
SEMANTIC_WEIGHT = float(os.getenv("SEMANTIC_WEIGHT", 1.0))
RRF_K = int(os.getenv("RRF_K", 50))

# --- API Endpoints ---

@app.post("/upload_document/")
async def upload_document(file: Annotated[UploadFile, File(description="PDF file to process")], original_name: Annotated[str, Form(description="Name to save the document as")]):
    """
    Uploads a PDF document, processes it (extracts text, chunks, embeds),
    and stores the data in Supabase and GCP.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Read file content
    file_content = await file.read()

    # Process the document using the pipeline function
    try:
        processing_output = process_document(
            buffer=file_content,
            original_name=original_name,
            supabase_table=SUPABASE_TABLE,
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            chunk_size=CHUNK_SIZE,
            destination=GCP_DESTINATION_FOLDER,
            model=EMBEDDING_MODEL,
            gemini_api_key=gemini_api_key,
            # Removed gcp_credentials argument as it's handled globally in rag_pipeline.py
            # gcp_credentials=gcp_credentials # <-- Removed this line
        )
        return JSONResponse(content={"message": "Document processed successfully", "details": processing_output})
    except Exception as e:
        # Log the error for debugging
        print(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")


# Define the Pydantic model for the request body
class QueryRequest(BaseModel):
    """
    Represents the expected structure of the JSON request body
    for the /query_document/ endpoint.
    """
    query: str # The user query is a required string
    file_title: Optional[str] = None # The file_title is an optional string

# Ensure Body is imported from fastapi if using Annotated[..., Body()]
# from fastapi import ..., Body # If you use the explicit Annotated[..., Body()] form

@app.post("/query_document/")
# Accept the request body as an instance of the QueryRequest model
# FastAPI automatically handles reading and validating the JSON body
async def query_document(request_body: QueryRequest):
# Alternative (explicit Body):
# async def query_document(request_body: Annotated[QueryRequest, Body()]):
    """
    Performs a hybrid search on a HARDCODED document based on the user query.
    (Temporarily ignores file_title from the request).
    """
    # Get the query from the request body (this is needed for the search)
    query = request_body.query

    # You still receive request_body.file_title, but we will ignore its value for the search filtering below.
    # file_title_from_request = request_body.file_title # You can keep this line or comment it out

    if not query:
         raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # --- HARDCODE THE DOCUMENT IDENTIFIER HERE ---
    # Replace "test1" with the *actual* title (or fileId, depending on what your hybrid_search expects for filtering)
    # of the document you want to query from your Supabase table.
    # Based on your schema and hybrid_search, this should be the 'title' from the 'files' table.
    hardcoded_file_identifier = "test1" # <<< CHANGE THIS STRING to your desired document title >>>

    # If your hybrid_search expects the fileId instead of the title, use that here:
    # hardcoded_file_identifier = "Your Actual Hardcoded Document ID" # <<< Or the ID string

    # ---------------------------------------------

    # --- Set the variable used for the search to the hardcoded value ---
    # This overrides any value that might have come in from the frontend request body.
    file_title_for_search = hardcoded_file_identifier
    # The previous logic 'file_title_for_search = file_title_from_request if file_title_from_request is not None else ""'
    # is effectively bypassed or replaced by the line above when hardcoding is active.
    # ---------------------------------------------------------------------


    try:
        # Generate embedding for the user query (uses the query from the frontend)
        # gemini_api_key is assumed to be available globally or in this scope
        query_embedding = generate_gemini_embedding(query, gemini_api_key)

        # Perform hybrid search in Supabase
        # SUPABASE_URL, SUPABASE_KEY, MATCH_COUNT, etc. are assumed to be available globally or in this scope
        search_results = hybrid_search(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            query=query, # Pass the query from the frontend
            query_embedding=query_embedding,
            match_count=MATCH_COUNT,
            full_text_weight=FULL_TEXT_WEIGHT,
            semantic_weight=SEMANTIC_WEIGHT,
            rrf_k=RRF_K,
            # Pass the hardcoded identifier to hybrid_search
            # Make sure the parameter name 'file_title' matches what hybrid_search expects for filtering
            # (Based on your hybrid_search code, 'file_title' is correct)
            file_title=file_title_for_search
        )

        # ... rest of your query_document function body (handling search_results,
        # calling format_prompt_with_context and generate_gemini_response) ...

        if not search_results:
             return JSONResponse(content={"answer": "Could not find relevant information in the specified document.", "chunks": []})

        formatted_prompt = format_prompt_with_context(search_results, query)

        # gemini_api_key is assumed to be available globally or in this scope
        answer = generate_gemini_response(
            user_prompt=formatted_prompt,
            system_prompt="You are a helpful assistant that answers questions based on the provided document excerpts. If the information is not in the excerpts, state that you cannot answer based on the provided context.",
            gemini_api_key=gemini_api_key
        )

        return JSONResponse(content={"answer": answer, "chunks": search_results})


    except Exception as e:
        print(f"Error during query processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {e}")


@app.get("/")
async def read_root():
    return {"message": "RAG Pipeline Wrapper API is running."}
