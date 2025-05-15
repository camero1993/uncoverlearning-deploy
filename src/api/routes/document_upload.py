from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from typing import Annotated, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.core.app_settings import settings
from src.core.error_handlers import DocumentProcessingError
from src.infrastructure.document_processing.pdf_processor import LangChainDocumentProcessor
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
import os
import tempfile
import logging
import traceback
import time
import uuid
import shutil
import base64
import json
from pathlib import Path

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum verbosity

router = APIRouter()

# Initialize components
try:
    logger.info("Initializing document processor with chunk_size=%d", settings.CHUNK_SIZE)
    document_processor = LangChainDocumentProcessor(
        chunk_size=settings.CHUNK_SIZE,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    logger.info("Document processor initialized successfully")
except Exception as e:
    logger.error("Failed to initialize document processor: %s", str(e))
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Initializing vector store with Supabase URL=%s, table=%s", 
                settings.SUPABASE_URL, settings.SUPABASE_TABLE)
    vector_store = LangChainVectorStore(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY,
        gemini_api_key=settings.GEMINI_API_KEY,
        table_name=settings.SUPABASE_TABLE
    )
    logger.info("Vector store initialized successfully")
    
    # Verify GCP credentials
    logger.info("Verifying GCP credentials")
    try:
        # Test GCP connection
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        test_content = b"Test content"
        test_url = vector_store.upload_to_gcp(
            buffer=test_content,
            filename=f"{test_id}.txt",
            destination=settings.GCP_DESTINATION_FOLDER
        )
        logger.info(f"GCP credentials verified. Test upload successful: {test_url}")
    except Exception as e:
        logger.warning(f"GCP credentials verification failed: {str(e)}")
        logger.warning("Document uploads may fail if GCP access is not configured properly")
        
except Exception as e:
    logger.error("Failed to initialize vector store: %s", str(e))
    logger.error(traceback.format_exc())
    raise

# Default max file size (10MB for single upload)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
MAX_FILE_SIZE_MB = MAX_FILE_SIZE / (1024 * 1024)

# Dictionary to store chunked upload sessions
# In a production environment, use a database or Redis for persistent storage
chunked_uploads = {}

# Models for chunked upload
class UploadInitRequest(BaseModel):
    """Request model for initiating a chunked file upload."""
    file_name: str
    total_chunks: int
    total_size: int
    mime_type: str = "application/pdf"

class UploadInitResponse(BaseModel):
    """Response model for successful chunked upload initialization."""
    upload_id: str
    expires_at: str

class ChunkUploadRequest(BaseModel):
    """Request model for uploading a chunk of a file."""
    upload_id: str
    chunk_index: int
    total_chunks: int
    chunk_data: str  # Base64 encoded binary data

class ChunkUploadResponse(BaseModel):
    """Response model for a successful chunk upload."""
    upload_id: str
    chunks_received: int
    total_chunks: int
    is_complete: bool

class FinalizeUploadRequest(BaseModel):
    """Request model for finalizing a chunked upload."""
    upload_id: str
    original_name: str

@router.post("/initiate_chunked_upload/", response_model=UploadInitResponse)
async def initiate_chunked_upload(request: UploadInitRequest):
    """
    Initiate a chunked upload process for a large file.
    Returns an upload_id that must be used for subsequent chunk uploads.
    """
    # Generate a unique upload ID
    upload_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex[:8]
    logger.info(f"[{request_id}] Initiating chunked upload for {request.file_name}, size: {request.total_size/1024/1024:.2f}MB, chunks: {request.total_chunks}")
    
    # Validate mime type
    if request.mime_type != "application/pdf":
        logger.error(f"[{request_id}] Invalid file type: {request.mime_type}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create a temporary directory for this upload
    temp_dir = tempfile.mkdtemp(prefix=f"chunked_{upload_id}_")
    
    # Initialize the upload session
    expires_at = time.time() + 3600  # 1 hour expiration
    
    chunked_uploads[upload_id] = {
        "file_name": request.file_name,
        "mime_type": request.mime_type,
        "total_chunks": request.total_chunks,
        "total_size": request.total_size,
        "chunks_received": 0,
        "temp_dir": temp_dir,
        "chunks": {},
        "expires_at": expires_at,
        "is_complete": False,
        "created_at": time.time(),
        "request_id": request_id
    }
    
    logger.info(f"[{request_id}] Chunked upload initiated: {upload_id}, expires at {time.ctime(expires_at)}")
    
    return UploadInitResponse(
        upload_id=upload_id,
        expires_at=time.ctime(expires_at)
    )

@router.post("/upload_chunk/", response_model=ChunkUploadResponse)
async def upload_chunk(request: ChunkUploadRequest):
    """
    Upload a chunk of a file in a chunked upload process.
    """
    # Validate upload ID exists
    if request.upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload session not found or expired")
    
    upload_session = chunked_uploads[request.upload_id]
    request_id = upload_session["request_id"]
    
    # Validate chunk index
    if request.chunk_index < 0 or request.chunk_index >= upload_session["total_chunks"]:
        logger.error(f"[{request_id}] Invalid chunk index: {request.chunk_index}, total chunks: {upload_session['total_chunks']}")
        raise HTTPException(status_code=400, detail="Invalid chunk index")
    
    # Validate upload is not already complete
    if upload_session["is_complete"]:
        logger.error(f"[{request_id}] Upload already finalized: {request.upload_id}")
        raise HTTPException(status_code=400, detail="Upload already finalized")
    
    try:
        # Decode base64 data
        chunk_data = base64.b64decode(request.chunk_data)
        
        # Save chunk to temporary file
        chunk_path = os.path.join(upload_session["temp_dir"], f"chunk_{request.chunk_index}")
        with open(chunk_path, "wb") as f:
            f.write(chunk_data)
        
        # Update upload session
        upload_session["chunks"][request.chunk_index] = chunk_path
        upload_session["chunks_received"] += 1
        
        # Log progress
        logger.info(f"[{request_id}] Received chunk {request.chunk_index + 1}/{upload_session['total_chunks']} "
                   f"for upload {request.upload_id}, size: {len(chunk_data)/1024:.2f}KB")
        
        # Check if all chunks have been received
        is_complete = upload_session["chunks_received"] == upload_session["total_chunks"]
        
        return ChunkUploadResponse(
            upload_id=request.upload_id,
            chunks_received=upload_session["chunks_received"],
            total_chunks=upload_session["total_chunks"],
            is_complete=is_complete
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error processing chunk: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing chunk: {str(e)}")

@router.post("/finalize_chunked_upload/")
async def finalize_chunked_upload(request: FinalizeUploadRequest):
    """
    Finalize a chunked upload, combining all chunks and processing the document.
    """
    # Validate upload ID exists
    if request.upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload session not found or expired")
    
    upload_session = chunked_uploads[request.upload_id]
    request_id = upload_session["request_id"]
    
    # Validate all chunks have been received
    if upload_session["chunks_received"] != upload_session["total_chunks"]:
        logger.error(f"[{request_id}] Not all chunks received: {upload_session['chunks_received']}/{upload_session['total_chunks']}")
        raise HTTPException(status_code=400, detail="Not all chunks have been uploaded")
    
    # Mark as complete to prevent further uploads
    upload_session["is_complete"] = True
    
    temp_dir = upload_session["temp_dir"]
    temp_file_path = os.path.join(temp_dir, f"complete_{request.upload_id}.pdf")
    
    try:
        logger.info(f"[{request_id}] Finalizing chunked upload {request.upload_id}, combining {upload_session['total_chunks']} chunks")
        
        # Combine all chunks into a single file
        with open(temp_file_path, "wb") as outfile:
            for i in range(upload_session["total_chunks"]):
                chunk_path = upload_session["chunks"][i]
                logger.debug(f"[{request_id}] Adding chunk {i} from {chunk_path}")
                with open(chunk_path, "rb") as infile:
                    outfile.write(infile.read())
        
        file_size = os.path.getsize(temp_file_path)
        logger.info(f"[{request_id}] Combined file size: {file_size/1024/1024:.2f}MB")
        
        # Read the file
        with open(temp_file_path, "rb") as f:
            file_content = f.read()
        
        # Now process the document
        start_time = time.time()
        
        # Process PDF document steps similar to the upload_document endpoint
        try:
            # Step 1: Process PDF
            logger.info(f"[{request_id}] Processing PDF document")
            start_process = time.time()
            try:
                documents = document_processor.process_pdf(pdf_path=temp_file_path)
                logger.info(f"[{request_id}] PDF processed successfully. Extracted {len(documents)} chunks in {time.time() - start_process:.2f} seconds")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to process PDF: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
            
            # Step 2: Generate embeddings
            logger.info(f"[{request_id}] Generating embeddings")
            start_embed = time.time()
            try:
                embeddings = document_processor.generate_embeddings(documents)
                logger.info(f"[{request_id}] Embeddings generated successfully in {time.time() - start_embed:.2f} seconds")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to generate embeddings: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")
            
            # Step 3: Upload to GCP
            filename = Path(request.original_name).name
            logger.info(f"[{request_id}] Uploading to Google Cloud Storage with filename: {filename}")
            start_gcp = time.time()
            try:
                gcp_url = vector_store.upload_to_gcp(
                    buffer=file_content,
                    filename=filename,
                    destination=settings.GCP_DESTINATION_FOLDER
                )
                logger.info(f"[{request_id}] File uploaded to GCP successfully in {time.time() - start_gcp:.2f} seconds")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to upload to GCP: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to upload to GCP: {str(e)}")
            
            # Step 4: Insert file metadata
            logger.info(f"[{request_id}] Inserting file metadata to Supabase")
            start_meta = time.time()
            try:
                file_id = vector_store.insert_file_metadata(
                    title=request.original_name,
                    link=gcp_url
                )
                logger.info(f"[{request_id}] File metadata inserted successfully in {time.time() - start_meta:.2f} seconds. File ID: {file_id}")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to insert file metadata: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to insert file metadata: {str(e)}")
            
            # Step 5: Add documents to vector store
            logger.info(f"[{request_id}] Adding documents to vector store")
            start_vector = time.time()
            try:
                metadata_list = [
                    {
                        "id": f"{file_id}_chunk_{i}",
                        "fileId": file_id,
                        "position": i,
                        "originalName": request.original_name,
                        "downloadUrl": gcp_url
                    }
                    for i in range(len(documents))
                ]
                
                vector_store.add_documents(documents, metadata_list)
                logger.info(f"[{request_id}] Documents added to vector store successfully in {time.time() - start_vector:.2f} seconds")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to add documents to vector store: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to add documents to vector store: {str(e)}")
            
            # Return success response
            total_time = time.time() - start_time
            logger.info(f"[{request_id}] Document upload and processing completed successfully in {total_time:.2f} seconds")
            
            # Clean up the session after successful processing
            del chunked_uploads[request.upload_id]
            
            return JSONResponse(content={
                "message": "Document processed successfully",
                "details": {
                    "file_url": gcp_url,
                    "file_id": file_id,
                    "total_chunks": len(documents),
                    "processing_time_seconds": total_time
                }
            })
        
        except HTTPException:
            # Re-raise HTTP exceptions as they're already formatted correctly
            raise
        except Exception as e:
            # Catch-all for any other exceptions
            logger.error(f"[{request_id}] Unexpected error in document processing: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error finalizing upload: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error finalizing upload: {str(e)}")
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"[{request_id}] Removed temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to clean up temporary files: {str(e)}")
            # Don't re-raise as this is just cleanup

@router.post("/upload_document/")
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF file to process")],
    original_name: Annotated[str, Form(description="Name to save the document as")]
):
    """
    Uploads a PDF document, processes it using LangChain components,
    and stores the data in Supabase and GCP.
    """
    start_time = time.time()
    request_id = uuid.uuid4().hex[:8]  # Generate a unique ID for this request
    logger.info(f"[{request_id}] Starting document upload process for file: {original_name}")
    
    # Validate file exists
    if not file:
        logger.error(f"[{request_id}] No file provided in the request")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        logger.error(f"[{request_id}] Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Read file content (in chunks to avoid memory issues with large files)
    logger.info(f"[{request_id}] Reading file content for {file.filename}")
    file_content = bytearray()
    chunk_size = 1024 * 1024  # Read 1MB at a time
    total_size = 0
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_content.extend(chunk)
        total_size += len(chunk)
        
        # Check file size limit during reading to avoid loading entire file into memory
        if total_size > MAX_FILE_SIZE:
            logger.error(f"[{request_id}] File too large: {total_size/(1024*1024):.2f}MB exceeds limit of {MAX_FILE_SIZE_MB}MB")
            # Instead of error, suggest chunked upload
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"File too large for direct upload. Maximum size is {MAX_FILE_SIZE_MB}MB. Your file is {total_size/(1024*1024):.2f}MB.",
                    "suggestion": "Use chunked upload API for files larger than 10MB."
                }
            )
    
    # Log final file size
    file_size_mb = total_size / (1024 * 1024)
    logger.info(f"[{request_id}] File size: {file_size_mb:.2f}MB")
    
    # Process the document
    return await process_document(
        request_id=request_id,
        file_content=file_content,
        original_name=original_name,
        filename=file.filename
    ) 