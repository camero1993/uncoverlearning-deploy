import os
import uuid
from typing import Dict, Any, List
from google.cloud import storage
from datetime import timedelta
from dotenv import load_dotenv
from gcp_credentials_loader import load_gcp_credentials
from src.infrastructure.document_processing.langchain_processor import LangChainDocumentProcessor
from src.infrastructure.vector_store.langchain_vector_store import LangChainVectorStore

# Load environment variables
load_dotenv()

# Load GCP credentials
gcp_credentials = load_gcp_credentials()
if gcp_credentials is None:
    print("FATAL ERROR: Google Cloud credentials not loaded. Cannot proceed with GCP operations.")
    import sys
    sys.exit(1)

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GCP_BUCKET = os.getenv("BUCKET")
gemini_api_key = os.getenv("GEMINI_API_KEY")

def upload_to_gcp(buffer: bytes, filename: str, destination: str) -> str:
    """Uploads a file buffer to a specified GCP bucket and destination."""
    if not GCP_BUCKET:
        raise ValueError("GCP_BUCKET environment variable is not set.")
        
    storage_client = storage.Client(credentials=gcp_credentials)
    bucket = storage_client.bucket(GCP_BUCKET)
    full_path = f"{destination}/{filename}"

    # Upload file
    blob = bucket.blob(full_path)
    blob.upload_from_string(buffer, content_type='application/pdf')

    # Generate signed URL for temporary access
    url = blob.generate_signed_url(expiration=timedelta(minutes=15))
    return url

def process_document(
    buffer: bytes,
    original_name: str,
    supabase_table: str,
    supabase_url: str,
    supabase_key: str,
    chunk_size: int,
    destination: str,
    model: str,
    gemini_api_key: str
) -> Dict[str, Any]:
    """
    Process a document using LangChain components.
    
    Args:
        buffer: PDF file content as bytes
        original_name: Original filename
        supabase_table: Supabase table name for file metadata
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        chunk_size: Size of text chunks
        destination: GCP destination folder
        model: Embedding model name
        gemini_api_key: Google Gemini API key
        
    Returns:
        Dictionary containing processing results
    """
    # Check required global variables
    if not SUPABASE_URL or not SUPABASE_KEY or not GCP_BUCKET or not gemini_api_key:
        missing = []
        if not SUPABASE_URL: missing.append("SUPABASE_URL")
        if not SUPABASE_KEY: missing.append("SUPABASE_KEY")
        if not GCP_BUCKET: missing.append("GCP_BUCKET")
        if not gemini_api_key: missing.append("gemini_api_key")
        raise ValueError(f"Missing required global variables for processing: {', '.join(missing)}")

    # Step 1: Upload to GCP
    print("📤 Uploading file to GCP...")
    file_extension = os.path.splitext(original_name)[1] if os.path.splitext(original_name)[1] else '.pdf'
    unique_filename = f"{os.path.splitext(original_name)[0]}_{uuid.uuid4().hex}{file_extension}"
    gcp_url = upload_to_gcp(buffer, unique_filename, destination)
    print(f"✅ Uploaded to GCP: {gcp_url}")

    # Step 2: Insert file metadata to Supabase
    print("📝 Inserting file record to Supabase...")
    file_id = uuid.uuid4().hex
    file_metadata = {
        "id": file_id,
        "title": original_name,
        "link": gcp_url,
        "license": "unknown",
        "in_database": True
    }

    # Initialize vector store for metadata insertion
    vector_store = LangChainVectorStore(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        gemini_api_key=gemini_api_key,
        table_name=supabase_table
    )
    
    # Insert metadata using vector store's client
    response = vector_store.supabase.table(supabase_table).insert(file_metadata).execute()
    if not response.data:
        raise Exception("Failed to insert file metadata into Supabase")
    
    inserted_file_record = response.data[0]
    file_id_from_db = inserted_file_record.get("id")
    if file_id_from_db:
        file_id = file_id_from_db
    else:
        print(f"Warning: Inserted file record did not return an 'id'. Using generated ID: {file_id}")

    print(f"✅ Inserted file record to Supabase with ID: {file_id}")

    # Step 3: Process document using LangChain
    print("📄 Processing document with LangChain...")
    processor = LangChainDocumentProcessor(
        chunk_size=chunk_size,
        gemini_api_key=gemini_api_key
    )
    
    # Save buffer to temporary file for processing
    temp_file = f"/tmp/{unique_filename}"
    with open(temp_file, "wb") as f:
        f.write(buffer)
    
    try:
        # Process the document
        documents = processor.process_pdf(pdf_path=temp_file)
        print(f"✅ Created {len(documents)} chunks.")
        
        # Step 4: Add documents to vector store
        print("⬆️ Adding documents to vector store...")
        
        # Prepare metadata for each document
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
        
        # Add documents to vector store
        vector_store.add_documents(documents, metadata_list)
        print("✅ Documents added to vector store.")
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    return {
        "file_url": gcp_url,
        "file_id": file_id,
        "total_chunks": len(documents)
    } 