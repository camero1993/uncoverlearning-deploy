from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Annotated
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
    
    # Create a temporary directory for this request
    temp_dir = None
    temp_file_path = None
    
    try:
        # Create a temporary directory using tempfile for better portability
        temp_dir = tempfile.mkdtemp(prefix=f"upload_{request_id}_")
        logger.debug(f"[{request_id}] Created temporary directory: {temp_dir}")
        
        # Read file content
        logger.info(f"[{request_id}] Reading file content for {file.filename}")
        file_content = await file.read()
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        logger.info(f"[{request_id}] File size: {file_size_mb:.2f}MB")
        
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            logger.error(f"[{request_id}] File too large: {file_size_mb:.2f}MB")
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size is 10MB.")
        
        # Create a temporary file
        try:
            temp_file_path = os.path.join(temp_dir, f"{request_id}.pdf")
            logger.debug(f"[{request_id}] Creating temporary file at {temp_file_path}")
            
            with open(temp_file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"[{request_id}] File saved to temporary location: {temp_file_path}")
            
            # Verify file was written correctly
            if not os.path.exists(temp_file_path):
                raise Exception(f"Failed to write temporary file at {temp_file_path}")
                
            file_size = os.path.getsize(temp_file_path)
            if file_size != len(file_content):
                raise Exception(f"File size mismatch. Expected {len(file_content)}, got {file_size}")
                
            logger.debug(f"[{request_id}] File verification successful: {file_size} bytes")
                
        except Exception as e:
            logger.error(f"[{request_id}] Failed to create temporary file: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to create temporary file: {str(e)}")
        
        # Process steps with detailed logging for each stage
        try:
            # Step 1: Process PDF
            logger.info(f"[{request_id}] Processing PDF document")
            start_process = time.time()
            try:
                # Log document processor settings for debugging
                logger.debug(f"[{request_id}] Document processor configuration: chunk_size={document_processor.chunk_size}")
                documents = document_processor.process_pdf(pdf_path=temp_file_path)
                logger.info(f"[{request_id}] PDF processed successfully. Extracted {len(documents)} chunks in {time.time() - start_process:.2f} seconds")
                # Log a sample of the first document for debugging
                if documents and len(documents) > 0:
                    logger.debug(f"[{request_id}] First document sample: {documents[0].page_content[:100]}...")
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
            logger.info(f"[{request_id}] Uploading to Google Cloud Storage")
            start_gcp = time.time()
            try:
                # Log GCP configuration for debugging
                logger.debug(f"[{request_id}] GCP destination folder: {settings.GCP_DESTINATION_FOLDER}")
                gcp_url = vector_store.upload_to_gcp(
                    buffer=file_content,
                    filename=file.filename,
                    destination=settings.GCP_DESTINATION_FOLDER
                )
                logger.info(f"[{request_id}] File uploaded to GCP successfully in {time.time() - start_gcp:.2f} seconds")
                logger.debug(f"[{request_id}] GCP URL: {gcp_url}")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to upload to GCP: {str(e)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Failed to upload to GCP: {str(e)}")
            
            # Step 4: Insert file metadata
            logger.info(f"[{request_id}] Inserting file metadata to Supabase")
            start_meta = time.time()
            try:
                # Log Supabase configuration for debugging
                logger.debug(f"[{request_id}] Supabase table: {settings.SUPABASE_TABLE}")
                file_id = vector_store.insert_file_metadata(
                    title=original_name,
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
                        "originalName": original_name,
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
        logger.error(f"[{request_id}] Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        # Clean up temporary files
        logger.debug(f"[{request_id}] Cleaning up temporary files")
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.debug(f"[{request_id}] Removed temporary file: {temp_file_path}")
                
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"[{request_id}] Removed temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to clean up temporary files: {str(e)}")
            # Don't re-raise as this is just cleanup 