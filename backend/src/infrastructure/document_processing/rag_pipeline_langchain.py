import os
import uuid
from typing import Dict, Any, List
from google.cloud import storage
from datetime import timedelta
from dotenv import load_dotenv
from langchain_core.documents import Document
from src.infrastructure.document_processing.langchain_processor import LangChainDocumentProcessor
from src.infrastructure.vector_store.supabase_store import LangChainVectorStore
from src.infrastructure.gcp.gcp_credentials_loader import load_gcp_credentials
import logging

# Load environment variables
load_dotenv()

# Load GCP credentials once at module level
gcp_creds = load_gcp_credentials()
if gcp_creds is None:
    logging.warning("GCP credentials not loaded via gcp_credentials_loader. Relying on ADC or environment for storage.Client().")
    # Depending on strictness, you might raise an error here if explicit creds are mandatory
    # raise EnvironmentError("Failed to load GCP credentials explicitly. Check gcp_credentials_loader.py and GOOGLE_APPLICATION_CREDENTIALS.")

# Environment variables
SUPABASE_URL_ENV = os.getenv("SUPABASE_URL") # Renamed to avoid conflict with arg
SUPABASE_KEY_ENV = os.getenv("SUPABASE_KEY") # Renamed to avoid conflict with arg
GCP_BUCKET_ENV = os.getenv("BUCKET")         # Renamed to avoid conflict
gemini_api_key_env = os.getenv("GEMINI_API_KEY") # Renamed to avoid conflict

def upload_to_gcp(buffer: bytes, filename: str, destination: str) -> str:
    """Uploads a file buffer to a specified GCP bucket and destination."""
    if not GCP_BUCKET_ENV:
        raise ValueError("GCP_BUCKET environment variable is not set.")
        
    storage_client = storage.Client(credentials=gcp_creds)
    bucket = storage_client.bucket(GCP_BUCKET_ENV)
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
    files_table_name: str, # Clarified: this is for the 'files' metadata table
    supabase_url: str,
    supabase_key: str,
    chunk_size: int,
    gcp_destination_folder: str, # Clarified name
    # model: str, # model arg was unused, can be removed if not planned for future use
    gemini_api_key_param: str # Clarified name
) -> Dict[str, Any]:
    """
    Process a document using LangChain components.
    
    Args:
        buffer: PDF file content as bytes
        original_name: Original filename
        files_table_name: Supabase table name for file metadata (e.g., 'files')
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        chunk_size: Size of text chunks
        gcp_destination_folder: GCP destination folder
        gemini_api_key_param: Google Gemini API key for processing
        
    Returns:
        Dictionary containing processing results
    """
    # Debug: Print type and snippet of buffer at the beginning of process_document
    print(f"DEBUG: process_document received buffer type: {type(buffer)}")
    if isinstance(buffer, bytes):
        print(f"DEBUG: process_document received buffer snippet (first 100 bytes): {buffer[:100]}")
    elif isinstance(buffer, str):
        print(f"DEBUG: process_document received string buffer snippet (first 100 chars): {buffer[:100]}")
    else:
        print(f"DEBUG: process_document received buffer of unexpected type: {type(buffer)}, value: {buffer}")

    # Check required global variables (using renamed env vars to avoid confusion with params)
    if not SUPABASE_URL_ENV or not SUPABASE_KEY_ENV or not GCP_BUCKET_ENV or not gemini_api_key_env:
        missing = []
        if not SUPABASE_URL_ENV: missing.append("SUPABASE_URL_ENV")
        if not SUPABASE_KEY_ENV: missing.append("SUPABASE_KEY_ENV")
        if not GCP_BUCKET_ENV: missing.append("GCP_BUCKET_ENV")
        if not gemini_api_key_env: missing.append("GEMINI_API_KEY_ENV (for global init if needed)")
        # The gemini_api_key_param is passed directly to components, so its absence as a param is a different check.
        if not gemini_api_key_param: missing.append("gemini_api_key_param (function argument)")
        if missing:
            raise ValueError(f"Missing required variables/parameters for processing: {', '.join(missing)}")

    # Step 1: Upload to GCP
    print("📤 Uploading file to GCP...")
    file_extension = os.path.splitext(original_name)[1] if os.path.splitext(original_name)[1] else '.pdf'
    # Using a simpler UUID for the filename, the db_file_id will be the true unique ID for the file entity
    gcp_unique_filename = f"{os.path.splitext(original_name)[0]}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    # Debug: Print type and snippet of buffer just before calling upload_to_gcp
    print(f"DEBUG: Before upload_to_gcp, buffer type: {type(buffer)}")
    if isinstance(buffer, bytes):
        print(f"DEBUG: Before upload_to_gcp, buffer snippet (first 100 bytes): {buffer[:100]}")
    elif isinstance(buffer, str):
        print(f"DEBUG: Before upload_to_gcp, string buffer snippet (first 100 chars): {buffer[:100]}")
    else:
        print(f"DEBUG: Before upload_to_gcp, buffer of unexpected type: {type(buffer)}, value: {buffer}")
        
    gcp_url = upload_to_gcp(buffer, gcp_unique_filename, gcp_destination_folder)
    print(f"✅ Uploaded to GCP: {gcp_url}")

    # Initialize LangChainVectorStore. 
    # Its internal self.table_name will default to "chunks" or be set by SUPABASE_TABLE env var if LangChainVectorStore reads it.
    # Its self.text_column will default to "content".
    # This instance is used for its Supabase client and embedding object.
    vector_store_wrapper = LangChainVectorStore(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        gemini_api_key=gemini_api_key_param # Use the passed API key
        # table_name will default to "chunks" in LangChainVectorStore if not overridden by env var that it might read
    )
    # The actual chunks table name we'll insert into is vector_store_wrapper.table_name
    chunks_table_for_insertion = vector_store_wrapper.table_name 
    print(f"ℹ️ Chunks will be inserted into table: '{chunks_table_for_insertion}'")

    # Step 2: Insert file metadata to Supabase 'files' table
    print(f"📝 Inserting file record into Supabase table: '{files_table_name}'...")
    # Generate a true UUID for the file ID in the database
    db_file_id = str(uuid.uuid4()) 
    file_metadata = {
        "id": db_file_id,
        "title": original_name,
        "link": gcp_url,
        "license": "unknown",
        "in_database": True
    }

    # Insert metadata into the specified 'files_table_name'
    response = vector_store_wrapper.supabase.table(files_table_name).insert(file_metadata).execute()
    # Check if response indicates success and if data is present
    if not (hasattr(response, 'data') and response.data and len(response.data) > 0):
        # Attempt to get more detailed error if available from Postgrest
        error_message = "Failed to insert file metadata into Supabase or no data returned."
        if hasattr(response, 'error') and response.error:
            error_message += f" DB Error: {response.error.message if hasattr(response.error, 'message') else response.error}"
        raise Exception(error_message)
    
    # It's safer to use the db_file_id we generated, as insert_file_metadata in the test script did.
    # However, if the table has a default for 'id' or a trigger, response.data[0].get("id") could be different.
    # For consistency with the pattern of generating UUID in app code:
    actual_inserted_file_id = response.data[0].get("id", db_file_id)
    if actual_inserted_file_id != db_file_id:
        print(f"⚠️ DB returned ID '{actual_inserted_file_id}' for file metadata, but generated ID was '{db_file_id}'. Using DB-returned ID.")
        db_file_id = actual_inserted_file_id
    print(f"✅ Inserted file record. File ID for 'chunks.fileId': {db_file_id}")

    # Step 3: Process document using LangChain to get chunks
    print("📄 Processing document with LangChain DocumentProcessor...")
    processor = LangChainDocumentProcessor(
        chunk_size=chunk_size,
        gemini_api_key=gemini_api_key_param # Use the passed API key
    )
    
    # Save buffer to temporary file for LangChainDocumentProcessor.process_pdf (which expects a path)
    temp_pdf_path = f"/tmp/{gcp_unique_filename}" # Use the same unique name for temp file
    with open(temp_pdf_path, "wb") as f:
        f.write(buffer)
    
    processed_documents: List[Document] = []
    try:
        processed_documents = processor.process_pdf(pdf_path=temp_pdf_path)
        print(f"✅ Created {len(processed_documents)} chunks from PDF.")
        
        # Step 4: Generate Embeddings for these chunks
        print("🧠 Generating embeddings for documents...")
        if not processed_documents:
            print("⚠️ No documents processed, skipping embedding generation and insertion.")
            document_embeddings = []
        else:
            document_embeddings = processor.generate_embeddings(processed_documents)
            print(f"✅ Generated {len(document_embeddings)} embeddings.")
        
        # Step 5: Manually insert chunks and their embeddings into the Supabase 'chunks' table
        if processed_documents and document_embeddings:
            print(f"⬆️ Inserting {len(processed_documents)} chunks into Supabase table '{chunks_table_for_insertion}'...")
            for i, (doc, embedding_vector) in enumerate(zip(processed_documents, document_embeddings)):
                chunk_uuid = str(uuid.uuid4())  # Unique ID for each chunk
                chunk_data_to_insert = {
                    "id": chunk_uuid,
                    "fileId": db_file_id,  # Foreign key from 'files' table
                "position": i,
                "originalName": original_name,
                    "content": doc.page_content,  # Text content of the chunk
                    "downloadUrl": gcp_url,      # URL of the original PDF in GCP
                    "embedding": embedding_vector # The generated embedding
                }
                try:
                    vector_store_wrapper.supabase.table(chunks_table_for_insertion).insert(chunk_data_to_insert).execute()
                except Exception as e_insert_chunk:
                    print(f"❌ ERROR inserting chunk {i} (ID: {chunk_uuid}): {e_insert_chunk}")
                    # Decide on error handling: continue, or re-raise to stop all processing?
                    # For now, re-raising to indicate failure of the overall process_document.
                    raise Exception(f"Failed to insert chunk {i} (ID: {chunk_uuid}). Original error: {e_insert_chunk}") 
                
                # Optional: print progress for long uploads
                if (i + 1) % 20 == 0 or (i + 1) == len(processed_documents):
                     print(f"   ...stored chunk {i + 1}/{len(processed_documents)}")
            print(f"✅ All {len(processed_documents)} chunks and embeddings inserted into '{chunks_table_for_insertion}'.")
        elif not processed_documents:
            print("ℹ️ No chunks were processed or generated, so no chunks were inserted.")
        else:
            print("⚠️ Processed documents but no embeddings generated, or vice-versa. No chunks inserted.")
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            print(f"🗑️ Cleaned up temporary file: {temp_pdf_path}")
    
    return {
        "file_url": gcp_url,
        "file_id": db_file_id, # Return the actual ID used for fileId in chunks
        "total_chunks": len(processed_documents)
    } 