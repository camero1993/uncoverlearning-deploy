import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Settings:
    """Application settings and configuration."""
    
    # API Settings
    API_TITLE = "UncoverLearning RAG Pipeline"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "RAG pipeline for educational content using LangChain and Gemini"
    
    # CORS Settings
    CORS_ORIGINS = [
        "https://uncoverlearning-deploy.vercel.app",
        "https://uncoverlearning.vercel.app",
        "https://uncoverlearning-deploy-ky6fmt5j1-magnus-projects-a977a13e.vercel.app",  # Specific deployment URL
        "https://*.vercel.app",  # Allow all vercel.app subdomains
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"  # Allow all origins for testing (remove in production if security is a concern)
    ]
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
    SUPABASE_TABLE: str = os.getenv("SUPABASE_TABLE", "chunks")
    
    # GCP Settings
    GCP_BUCKET: Optional[str] = os.getenv("BUCKET")
    GCP_DESTINATION_FOLDER: str = os.getenv("GCP_DESTINATION_FOLDER", "uploaded_docs")
    
    # Model Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "models/gemini-1.5-pro-latest")
    
    # Document Processing Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Search Settings
    MATCH_COUNT: int = int(os.getenv("MATCH_COUNT", "10"))
    FULL_TEXT_WEIGHT: float = float(os.getenv("FULL_TEXT_WEIGHT", "1.0"))
    SEMANTIC_WEIGHT: float = float(os.getenv("SEMANTIC_WEIGHT", "1.0"))
    RRF_K: int = int(os.getenv("RRF_K", "50"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate required settings."""
        required_settings = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_KEY": cls.SUPABASE_KEY,
            "GCP_BUCKET": cls.GCP_BUCKET,
            "GEMINI_API_KEY": cls.GEMINI_API_KEY
        }
        
        missing = [key for key, value in required_settings.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Create settings instance
settings = Settings() 