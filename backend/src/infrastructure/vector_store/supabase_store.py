from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase.client import Client, create_client
from google.cloud import storage
from datetime import timedelta
import os
from dotenv import load_dotenv
import uuid
from ...infrastructure.gcp.gcp_credentials_loader import load_gcp_credentials
from tqdm import tqdm

# Load environment variables
load_dotenv()

class LangChainVectorStore:
    """Vector store implementation using LangChain's Supabase integration."""
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        table_name: str = "chunks",
        text_column: str = "content"
    ):
        """
        Initialize the vector store.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            gemini_api_key: Google Gemini API key
            table_name: Name of the table storing vectors
            text_column: Name of the column storing text content
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.gcp_bucket = os.getenv("BUCKET")
        self.table_name = table_name
        self.text_column = text_column
        
        if not all([self.supabase_url, self.supabase_key, self.gemini_api_key, self.table_name, self.text_column]):
            raise ValueError("Missing required credentials, table name, or text column name. Please provide or set environment variables.")
        
        # Initialize Supabase client
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.gemini_api_key
        )
        
        # Initialize vector store using the custom_match_documents function
        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name=self.table_name,
            query_name="custom_match_documents"
        )
    
    def upload_to_gcp(self, buffer: bytes, filename: str, destination: str) -> str:
        """
        Uploads a file buffer to GCP and returns a signed URL.
        
        Args:
            buffer: File content as bytes
            filename: Name of the file
            destination: Destination folder in GCP
            
        Returns:
            Signed URL for the uploaded file
        """
        if not self.gcp_bucket:
            raise ValueError("GCP_BUCKET environment variable is not set.")
        
        gcp_creds = None
        if load_gcp_credentials:
            gcp_creds = load_gcp_credentials()

        if not gcp_creds:
            # If load_gcp_credentials failed or was not found,
            # storage.Client() will try to use Application Default Credentials.
            # The original error indicates this was failing, so this path will likely still fail
            # unless ADC is configured correctly without relying on GOOGLE_APPLICATION_CREDENTIALS_JSON.
            # We log a warning here if the explicit loader was available but returned None.
            if load_gcp_credentials is not None: # Check if the function itself was found
                 print("WARNING: load_gcp_credentials() returned no credentials. Attempting default ADC for GCS client.")
            # No explicit error raise here, to allow storage.Client() to try its default mechanisms,
            # which is what it was doing before, though it was failing.
            # This keeps the original behavior path if explicit loading fails,
            # but the core issue is that default ADC was not found.
            # The ideal scenario is gcp_creds being successfully loaded.
        
        # Initialize GCP client
        # If gcp_creds is None, storage.Client() will attempt to find ADC itself.
        # If gcp_creds is successfully loaded, it will be used.
        try:
            if gcp_creds:
                project_id = gcp_creds.project_id if hasattr(gcp_creds, 'project_id') else None
                storage_client = storage.Client(credentials=gcp_creds, project=project_id)
                print("INFO: GCS client initialized with explicitly loaded credentials.")
            else:
                storage_client = storage.Client() # Relies on ADC
                print("INFO: GCS client initialized using default Application Default Credentials (ADC).")
        except Exception as e:
            print(f"ERROR: Failed to initialize GCS storage client: {e}")
            # This error might occur if even the default ADC check within storage.Client() fails
            # or if there's an issue with the explicitly passed credentials.
            raise # Re-raise the exception to indicate failure to initialize client

        bucket = storage_client.bucket(self.gcp_bucket)
        full_path = f"{destination}/{filename}"
        
        # Upload file
        blob = bucket.blob(full_path)
        blob.upload_from_string(buffer, content_type='application/pdf')
        
        # Generate signed URL
        url = blob.generate_signed_url(expiration=timedelta(minutes=15))
        return url
    
    def insert_file_metadata(self, title: str, link: str) -> str:
        """
        Inserts file metadata into Supabase and returns the file ID.
        
        Args:
            title: File title
            link: File URL
            
        Returns:
            File ID
        """
        file_id = uuid.uuid4().hex
        file_metadata = {
            "id": file_id,
            "title": title,
            "link": link,
            "license": "unknown",
            "in_database": True
        }
        
        # Insert metadata
        response = self.supabase.table("files").insert(file_metadata).execute()
        if not response.data:
            raise Exception("Failed to insert file metadata into Supabase")
        
        # Get file ID from response
        inserted_file_record = response.data[0]
        file_id_from_db = inserted_file_record.get("id")
        if file_id_from_db:
            file_id = file_id_from_db
        
        return file_id
    
    def add_documents(
        self,
        documents: List[Document],
        embeddings_list: Optional[List[List[float]]] = None # Accept pre-computed embeddings
    ) -> List[str]: # Return list of inserted chunk IDs
        """
        Manually add documents to the Supabase 'chunks' table, mapping metadata to columns.
        Each Document in the 'documents' list should already have its .metadata attribute set
        containing keys like 'fileId', 'position', 'originalName', 'downloadUrl'.
        
        Args:
            documents: List of LangChain Document objects, each with populated .metadata.
            embeddings_list: Optional list of embedding vectors, parallel to documents.
                           If not provided, they will be generated.

        Returns:
            List of UUIDs of the inserted chunks.
        """
        inserted_chunk_ids: List[str] = []
        document_embeddings: List[List[float]]

        if embeddings_list is not None:
            if len(documents) != len(embeddings_list):
                print("ERROR: Mismatch between number of documents and provided embeddings_list.")
                raise ValueError("Mismatch between documents and provided embeddings count.")
            document_embeddings = embeddings_list
            print(f"Using {len(document_embeddings)} pre-computed embeddings in add_documents.")
        else:
            document_contents = [doc.page_content for doc in documents]
            if not document_contents:
                print("No document contents to process in add_documents for embedding generation.")
                return []
            try:
                document_embeddings = self.embeddings.embed_documents(document_contents)
                print(f"Successfully generated {len(document_embeddings)} embeddings in add_documents.")
            except Exception as e_embed:
                print(f"ERROR generating embeddings in add_documents: {e_embed}")
                raise

        if len(documents) != len(document_embeddings):
            # This check is a bit redundant if embeddings_list path is taken, but good for safety
            print("ERROR: Mismatch between number of documents and final embeddings count.")
            raise ValueError("Mismatch between documents and final embeddings count.")

        print(f"Attempting to insert {len(documents)} chunks into Supabase table '{self.table_name}'...")
        for i, (doc, embedding_vector) in enumerate(zip(documents, document_embeddings)):
            # Ensure required metadata keys are present
            if not all(k in doc.metadata for k in ["fileId", "position", "originalName", "downloadUrl"]):
                print(f"ERROR: Missing required metadata for document at index {i}. Metadata: {doc.metadata}")
                # Skip this document or raise an error
                # For now, skipping to avoid partial failure of the batch without explicit error.
                # Consider raising an error if all documents must succeed.
                continue 

            chunk_uuid = doc.metadata.get("id", str(uuid.uuid4())) # Use provided ID or generate new
            
            chunk_data_to_insert = {
                "id": chunk_uuid,
                "fileId": doc.metadata["fileId"],
                "position": doc.metadata["position"],
                "originalName": doc.metadata["originalName"],
                "content": doc.page_content,  # Text content of the chunk
                "downloadUrl": doc.metadata["downloadUrl"],
                "embedding": embedding_vector # The generated embedding
                # 'fts' (full-text search) and 'created_at' columns are expected 
                # to be handled by Supabase (e.g., via triggers or default values).
            }
            try:
                self.supabase.table(self.table_name).insert(chunk_data_to_insert).execute()
                inserted_chunk_ids.append(chunk_uuid)
            except Exception as e_insert_chunk:
                print(f"ERROR inserting chunk {i} (ID: {chunk_uuid}, FileID: {doc.metadata.get('fileId')}): {e_insert_chunk}")
                # Decide on error handling: continue, or re-raise to stop all processing?
                # For now, re-raising to indicate failure of the overall add_documents call.
                raise Exception(f"Failed to insert chunk {i} (ID: {chunk_uuid}). Original error: {e_insert_chunk}") 
            
            if (i + 1) % 20 == 0 or (i + 1) == len(documents):
                    print(f"   ...stored chunk {i + 1}/{len(documents)} in add_documents.")
        
        print(f"Successfully inserted {len(inserted_chunk_ids)} chunks into '{self.table_name}'.")
        return inserted_chunk_ids
    
    def add_documents_batch(
        self,
        documents: List[Document],
        embeddings_list: Optional[List[List[float]]] = None,
        batch_size: int = 50
    ) -> List[str]:
        """
        Add documents to Supabase using batch insertion.
        
        Args:
            documents: List of LangChain Document objects
            embeddings_list: Optional list of embedding vectors, parallel to documents
            batch_size: Number of records to insert in each batch (default: 50)
            
        Returns:
            List of UUIDs of the inserted chunks
        """
        inserted_chunk_ids: List[str] = []
        document_embeddings: List[List[float]]

        # Validate and get embeddings
        if embeddings_list is not None:
            if len(documents) != len(embeddings_list):
                print("ERROR: Mismatch between number of documents and provided embeddings_list.")
                raise ValueError("Mismatch between documents and provided embeddings count.")
            document_embeddings = embeddings_list
            print(f"Using {len(document_embeddings)} pre-computed embeddings in add_documents_batch.")
        else:
            document_contents = [doc.page_content for doc in documents]
            if not document_contents:
                print("No document contents to process in add_documents_batch for embedding generation.")
                return []
            try:
                print("Generating embeddings...")
                # Process embeddings in batches of 20 to show progress
                embedding_batch_size = 20
                document_embeddings = []
                for i in tqdm(range(0, len(document_contents), embedding_batch_size), desc="Generating embeddings"):
                    batch = document_contents[i:i + embedding_batch_size]
                    batch_embeddings = self.embeddings.embed_documents(batch)
                    document_embeddings.extend(batch_embeddings)
                print(f"Successfully generated {len(document_embeddings)} embeddings.")
            except Exception as e_embed:
                print(f"ERROR generating embeddings in add_documents_batch: {e_embed}")
                raise

        if len(documents) != len(document_embeddings):
            print("ERROR: Mismatch between number of documents and final embeddings count.")
            raise ValueError("Mismatch between documents and final embeddings count.")

        # Prepare all chunks data first
        print("Preparing chunks data...")
        chunks_data = []
        for i, (doc, embedding_vector) in enumerate(tqdm(zip(documents, document_embeddings), total=len(documents), desc="Preparing chunks")):
            # Ensure required metadata keys are present
            if not all(k in doc.metadata for k in ["fileId", "position", "originalName", "downloadUrl"]):
                print(f"ERROR: Missing required metadata for document at index {i}. Metadata: {doc.metadata}")
                continue

            chunk_uuid = doc.metadata.get("id", str(uuid.uuid4()))
            chunks_data.append({
                "id": chunk_uuid,
                "fileId": doc.metadata["fileId"],
                "position": doc.metadata["position"],
                "originalName": doc.metadata["originalName"],
                "content": doc.page_content,
                "downloadUrl": doc.metadata["downloadUrl"],
                "embedding": embedding_vector
            })
            inserted_chunk_ids.append(chunk_uuid)

        # Insert in batches
        total_batches = (len(chunks_data) + batch_size - 1) // batch_size
        print(f"Inserting {len(chunks_data)} chunks in {total_batches} batches (size: {batch_size})...")
        
        for i in tqdm(range(0, len(chunks_data), batch_size), desc="Inserting chunks", total=total_batches):
            batch = chunks_data[i:i + batch_size]
            try:
                self.supabase.table(self.table_name).insert(batch).execute()
            except Exception as e_insert_batch:
                print(f"ERROR inserting batch starting at index {i}: {e_insert_batch}")
                raise Exception(f"Failed to insert batch starting at index {i}. Original error: {e_insert_batch}")

        print(f"Successfully inserted {len(inserted_chunk_ids)} chunks using batch insertion.")
        return inserted_chunk_ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search.
        
        Args:
            query: Search query
            k: Number of results to return
            filter: Optional filter conditions
            
        Returns:
            List of matching documents
        """
        return self.vector_store.similarity_search(query, k=k, filter=filter)
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        match_count: int = 10,
        full_text_weight: float = 1.0,
        semantic_weight: float = 1.0,
        rrf_k: int = 50,
        file_title: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using Supabase's RPC function.
        
        Args:
            query: Search query
            query_embedding: Query embedding vector
            match_count: Number of results to return
            full_text_weight: Weight for full-text search
            semantic_weight: Weight for semantic search
            rrf_k: RRF parameter
            file_title: Optional file title filter
            
        Returns:
            List of search results
        """
        try:
            response = self.supabase.rpc("hybrid_search", {
                "query_text": query,
                "query_embedding": query_embedding,
                "match_count": match_count,
                "full_text_weight": full_text_weight,
                "semantic_weight": semantic_weight,
                "rrf_k": rrf_k,
                "file_title": file_title
            }).execute()
            
            if response.data is None:
                print("Supabase RPC returned no data.")
                return []
            
            print(f"Supabase RPC returned {len(response.data)} results.")
            return response.data
            
        except Exception as e:
            print(f"Error during Supabase hybrid search: {e}")
            if hasattr(e, 'message'):
                print(f"Supabase Error Message: {e.message}")
            raise 