from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client
from google.cloud import storage
from datetime import timedelta
import os
from dotenv import load_dotenv
import uuid

# Attempt to import load_gcp_credentials. Assuming gcp_credentials_loader.py is at the project root.
# If it's located elsewhere (e.g., in src or src/core), adjust the import path accordingly.
try:
    from gcp_credentials_loader import load_gcp_credentials
except ImportError:
    # Fallback if the primary location fails, try assuming it's in src
    try:
        from src.gcp_credentials_loader import load_gcp_credentials
    except ImportError:
        load_gcp_credentials = None
        print("WARNING: gcp_credentials_loader.py not found. GCP operations might fail if credentials are not implicitly available.")

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
        text_column: str = "extractedText"
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
        
        if not all([self.supabase_url, self.supabase_key, self.gemini_api_key]):
            raise ValueError("Missing required credentials. Please provide or set environment variables.")
        
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
            table_name=table_name,
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
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LangChain Document objects
            metadata: Optional list of metadata dictionaries for each document
            
        Returns:
            List of document IDs
        """
        return self.vector_store.add_documents(documents, metadata)
    
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