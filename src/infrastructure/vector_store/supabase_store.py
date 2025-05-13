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
        embedding_column: str = "embedding",
        text_column: str = "extractedText"
    ):
        """
        Initialize the vector store.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            gemini_api_key: Google Gemini API key
            table_name: Name of the table storing vectors
            embedding_column: Name of the column storing embeddings
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
        
        # Initialize vector store
        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            table_name=table_name,
            embedding=self.embeddings,
            embedding_column=embedding_column,
            text_column=text_column
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
        
        # Initialize GCP client
        storage_client = storage.Client()
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