import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Import CORS middleware
from fastapi.staticfiles import StaticFiles # Import StaticFiles
from typing import Annotated, Optional, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Import LangChain components
from src.infrastructure.vector_store.langchain_vector_store import LangChainVectorStore
from src.infrastructure.rag.langchain_rag_chain import LangChainRAGChain
from src.infrastructure.document_processing.langchain_processor import LangChainDocumentProcessor

# Initialize FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="."), name="static") # <<< CHANGE THIS LINE


# --- CORS Configuration ---
# Define the origins that are allowed to make requests to your backend.
origins = [
    "https://uncoverlearning-deploy.vercel.app",  # Production Vercel deployment
    "http://localhost:3000",                      # React development server
    "http://127.0.0.1:3000"                       # Alternative localhost
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
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GCP_BUCKET = os.getenv("BUCKET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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

# Initialize components
vector_store = LangChainVectorStore(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_KEY,
    gemini_api_key=GEMINI_API_KEY,
    table_name=SUPABASE_TABLE
)

document_processor = LangChainDocumentProcessor(
    chunk_size=CHUNK_SIZE,
    gemini_api_key=GEMINI_API_KEY
)

rag_chain = LangChainRAGChain(
    vector_store=vector_store,
    gemini_api_key=GEMINI_API_KEY,
    model_name=GENERATION_MODEL
)

# --- API Endpoints ---

@app.post("/upload_document/")
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF file to process")],
    original_name: Annotated[str, Form(description="Name to save the document as")]
):
    """
    Uploads a PDF document, processes it using LangChain components,
    and stores the data in Supabase and GCP.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        # Read file content
        file_content = await file.read()
        
        # Save to temporary file for processing
        temp_file = f"/tmp/{file.filename}"
        with open(temp_file, "wb") as f:
            f.write(file_content)
        
        try:
            # Process document using LangChain
            documents = document_processor.process_pdf(pdf_path=temp_file)
            
            # Generate embeddings
            embeddings = document_processor.generate_embeddings(documents)
            
            # Upload to GCP and get URL
            gcp_url = vector_store.upload_to_gcp(
                buffer=file_content,
                filename=file.filename,
                destination=GCP_DESTINATION_FOLDER
            )
            
            # Insert file metadata
            file_id = vector_store.insert_file_metadata(
                title=original_name,
                link=gcp_url
            )
            
            # Add documents to vector store
            metadata_list = [
                {
                    "id": f"{file_id}_chunk_{i}",
                    "fileId": file_id,
                    "position": i,
                    "originalName": original_name,
                    "downloadUrl": gcp_url
                }
                for i in range(len(documents))
            ]
            
            vector_store.add_documents(documents, metadata_list)
            
            return JSONResponse(content={
                "message": "Document processed successfully",
                "details": {
                    "file_url": gcp_url,
                    "file_id": file_id,
                    "total_chunks": len(documents)
                }
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        print(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")


class QueryRequest(BaseModel):
    """
    Represents the expected structure of the JSON request body
    for the /query_document/ endpoint.
    """
    query: str # The user query is a required string
    file_title: Optional[str] = None # The file_title is an optional string
    conversation_history: Optional[List[Dict[str, Any]]] = None

@app.post("/query_document/")
# Accept the request body as an instance of the QueryRequest model
# FastAPI automatically handles reading and validating the JSON body
async def query_document(request: QueryRequest):
# Alternative (explicit Body):
# async def query_document(request_body: Annotated[QueryRequest, Body()]):
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
        print(f"Error during query processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {e}")


@app.get("/")
async def read_root():
    return {"message": "RAG Pipeline Wrapper API is running."}
