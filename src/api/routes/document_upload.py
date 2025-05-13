from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Annotated
from src.core.app_settings import settings
from src.core.error_handlers import DocumentProcessingError
from src.infrastructure.document_processing.pdf_processor import LangChainDocumentProcessor
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
import os

router = APIRouter()

# Initialize components
document_processor = LangChainDocumentProcessor(
    chunk_size=settings.CHUNK_SIZE,
    gemini_api_key=settings.GEMINI_API_KEY
)

vector_store = LangChainVectorStore(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_KEY,
    gemini_api_key=settings.GEMINI_API_KEY,
    table_name=settings.SUPABASE_TABLE
)

@router.post("/upload_document/")
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
                destination=settings.GCP_DESTINATION_FOLDER
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
        raise DocumentProcessingError(str(e)) 